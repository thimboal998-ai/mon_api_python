# ============================================
# EXPORT_MANAGER.PY
# Dispatcher d'exports multi-formats
# ============================================
"""
Gestionnaire centralisé des exports de données.

Formats supportés:
- CSV : Export simple des données nettoyées
- Excel : Export multi-feuilles avec stats et graphiques
- PDF : Rapport professionnel avec visualisations
- ZIP : Archive contenant tous les formats

Usage:
    manager = ExportManager()
    filepath = manager.export(
        format='excel',
        data=cleaned_df,
        stats=cleaning_stats,
        charts=chart_paths
    )
"""

import os
from datetime import datetime
from pathlib import Path
import zipfile
import pandas as pd
import shutil


class ExportManager:
    """
    Gestionnaire centralisé des exports
    """
    
    def __init__(self, output_dir='reports_out'):
        """
        Initialisation du gestionnaire d'exports
        
        Args:
            output_dir (str): Dossier de sortie des exports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.supported_formats = ['csv', 'excel', 'pdf', 'zip']
        
        print(f"📦 ExportManager initialisé (output: {self.output_dir})")
    
    
    def export(self, format, data, stats=None, charts=None, filename=None, user_id=None, metadata=None):
        """
        Exporter les données dans le format spécifié
        
        Args:
            format (str): Format d'export ('csv', 'excel', 'pdf', 'zip')
            data (DataFrame or dict): Données à exporter
            stats (dict): Statistiques de nettoyage
            charts (dict or list): Chemins des graphiques
            filename (str): Nom de fichier personnalisé (optionnel)
            user_id (int): ID de l'utilisateur (pour organiser par user)
            metadata (dict): Métadonnées supplémentaires
        
        Returns:
            str: Chemin du fichier généré
        
        Raises:
            ValueError: Si le format n'est pas supporté
        """
        if format not in self.supported_formats:
            raise ValueError(
                f"Format '{format}' non supporté. "
                f"Formats disponibles : {', '.join(self.supported_formats)}"
            )
        
        print(f"\n📤 Export demandé : {format}")
        
        # Convertir data en DataFrame si nécessaire
        if isinstance(data, dict):
            df = pd.DataFrame(data)
        else:
            df = data
        
        # Créer le dossier utilisateur si nécessaire
        if user_id:
            user_dir = self.output_dir / str(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)
        else:
            user_dir = self.output_dir
        
        # Générer le nom de fichier
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"export_{timestamp}"
        
        # Dispatcher vers la méthode appropriée
        if format == 'csv':
            return self._export_csv(df, user_dir, filename)
        
        elif format == 'excel':
            return self._export_excel(df, stats, charts, user_dir, filename, metadata)
        
        elif format == 'pdf':
            return self._export_pdf(stats, charts, user_dir, filename, metadata)
        
        elif format == 'zip':
            return self._export_all(df, stats, charts, user_dir, filename, metadata)
    
    
    # ========================================
    # EXPORT CSV
    # ========================================
    
    def _export_csv(self, df, output_dir, filename):
        """
        Exporter en CSV
        
        Args:
            df (DataFrame): Données à exporter
            output_dir (Path): Dossier de sortie
            filename (str): Nom du fichier
        
        Returns:
            str: Chemin du fichier
        """
        filepath = output_dir / f"{filename}.csv"
        
        print(f"   💾 Export CSV vers : {filepath}")
        
        # Export sans index
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        file_size = os.path.getsize(filepath)
        print(f"   ✅ CSV exporté : {file_size / 1024:.2f} KB")
        
        return str(filepath)
    
    
    # ========================================
    # EXPORT EXCEL
    # ========================================
    
    def _export_excel(self, df, stats, charts, output_dir, filename, metadata):
        """
        Exporter en Excel multi-feuilles
        
        Args:
            df (DataFrame): Données nettoyées
            stats (dict): Statistiques
            charts (dict): Chemins des graphiques
            output_dir (Path): Dossier de sortie
            filename (str): Nom du fichier
            metadata (dict): Métadonnées
        
        Returns:
            str: Chemin du fichier
        """
        try:
            from .excel_exporter import ExcelExporter
            
            exporter = ExcelExporter()
            filepath = exporter.export(
                data=df,
                stats=stats,
                charts=charts,
                output_path=output_dir / f"{filename}.xlsx",
                metadata=metadata
            )
            
            return filepath
        
        except ImportError:
            print("   ⚠️  ExcelExporter non disponible, export CSV de secours")
            return self._export_csv(df, output_dir, filename)
    
    
    # ========================================
    # EXPORT PDF
    # ========================================
    
    def _export_pdf(self, stats, charts, output_dir, filename, metadata):
        """
        Exporter en PDF
        
        Args:
            stats (dict): Statistiques
            charts (dict): Chemins des graphiques
            output_dir (Path): Dossier de sortie
            filename (str): Nom du fichier
            metadata (dict): Métadonnées
        
        Returns:
            str: Chemin du fichier
        """
        from .pdf_generator import PDFReportGenerator
        
        filepath = output_dir / f"{filename}.pdf"
        
        print(f"   📄 Export PDF vers : {filepath}")
        
        generator = PDFReportGenerator(str(filepath))
        
        # Construire le PDF
        generator.add_header(
            title=metadata.get('title', 'Rapport de Nettoyage de Données')
        )
        
        if stats:
            generator.add_statistics_table(stats.get('stats', stats))
            generator.add_quality_score(stats.get('stats', stats))
            
            if stats.get('transformation_history'):
                generator.add_transformation_history(stats['transformation_history'])
        
        # Ajouter les graphiques
        if charts:
            if isinstance(charts, dict):
                chart_paths = charts.values()
            else:
                chart_paths = charts
            
            for chart_path in chart_paths:
                # Convertir chemin web en chemin système
                if isinstance(chart_path, str):
                    chart_path = chart_path.replace('/static/', 'static/')
                
                if os.path.exists(chart_path):
                    generator.add_image(chart_path, width=6.5)
        
        if stats:
            generator.add_recommendations(stats.get('stats', stats))
        
        # Générer
        generator.generate(stats.get('stats', stats) if stats else {})
        
        file_size = os.path.getsize(filepath)
        print(f"   ✅ PDF exporté : {file_size / 1024:.2f} KB")
        
        return str(filepath)
    
    
    # ========================================
    # EXPORT ZIP (TOUS LES FORMATS)
    # ========================================
    
    def _export_all(self, df, stats, charts, output_dir, filename, metadata):
        """
        Exporter dans tous les formats et créer une archive ZIP
        
        Args:
            df (DataFrame): Données
            stats (dict): Statistiques
            charts (dict): Graphiques
            output_dir (Path): Dossier de sortie
            filename (str): Nom du fichier
            metadata (dict): Métadonnées
        
        Returns:
            str: Chemin de l'archive ZIP
        """
        print(f"   📦 Création de l'archive complète...")
        
        # Créer un dossier temporaire pour les exports
        temp_dir = output_dir / f"temp_{filename}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 1. Export CSV
            csv_path = self._export_csv(df, temp_dir, filename)
            
            # 2. Export Excel
            try:
                excel_path = self._export_excel(df, stats, charts, temp_dir, filename, metadata)
            except Exception as e:
                print(f"   ⚠️  Erreur export Excel : {str(e)}")
                excel_path = None
            
            # 3. Export PDF
            try:
                pdf_path = self._export_pdf(stats, charts, temp_dir, filename, metadata)
            except Exception as e:
                print(f"   ⚠️  Erreur export PDF : {str(e)}")
                pdf_path = None
            
            # 4. Copier les graphiques
            charts_dir = temp_dir / 'charts'
            charts_dir.mkdir(exist_ok=True)
            
            if charts:
                chart_paths = charts.values() if isinstance(charts, dict) else charts
                
                for i, chart_path in enumerate(chart_paths, 1):
                    if isinstance(chart_path, str):
                        chart_path = chart_path.replace('/static/', 'static/')
                    
                    if os.path.exists(chart_path):
                        chart_filename = f"chart_{i}{os.path.splitext(chart_path)[1]}"
                        shutil.copy2(chart_path, charts_dir / chart_filename)
            
            # 5. Créer un README
            readme_path = temp_dir / 'README.txt'
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write("DATA CLEANING DASHBOARD - EXPORT COMPLET\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Date d'export : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("Contenu de l'archive :\n")
                f.write(f"- {filename}.csv : Données nettoyées au format CSV\n")
                if excel_path:
                    f.write(f"- {filename}.xlsx : Rapport Excel multi-feuilles\n")
                if pdf_path:
                    f.write(f"- {filename}.pdf : Rapport PDF professionnel\n")
                f.write("- charts/ : Graphiques de visualisation\n\n")
                
                if stats:
                    f.write("Statistiques :\n")
                    s = stats.get('stats', stats)
                    f.write(f"- Lignes nettoyées : {s.get('lignes_finales', 'N/A')}\n")
                    f.write(f"- Colonnes : {s.get('colonnes_finales', 'N/A')}\n")
                    f.write(f"- Score de qualité : {stats.get('quality', {}).get('score', 'N/A')}%\n")
            
            # 6. Créer l'archive ZIP
            zip_path = output_dir / f"{filename}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            file_size = os.path.getsize(zip_path)
            print(f"   ✅ Archive ZIP créée : {file_size / (1024*1024):.2f} MB")
            
            return str(zip_path)
        
        finally:
            # Nettoyer le dossier temporaire
            try:
                shutil.rmtree(temp_dir)
                print(f"   🧹 Dossier temporaire nettoyé")
            except:
                pass
    
    
    # ========================================
    # UTILITAIRES
    # ========================================
    
    def list_exports(self, user_id=None):
        """
        Lister tous les exports disponibles
        
        Args:
            user_id (int): Filtrer par utilisateur (optionnel)
        
        Returns:
            list: Liste des exports avec métadonnées
        """
        if user_id:
            search_dir = self.output_dir / str(user_id)
        else:
            search_dir = self.output_dir
        
        if not search_dir.exists():
            return []
        
        exports = []
        
        for ext in ['.csv', '.xlsx', '.pdf', '.zip']:
            for filepath in search_dir.glob(f"*{ext}"):
                stat = filepath.stat()
                
                exports.append({
                    'filename': filepath.name,
                    'format': ext[1:],  # Sans le point
                    'size': stat.st_size,
                    'size_human': self._format_size(stat.st_size),
                    'created_at': datetime.fromtimestamp(stat.st_ctime),
                    'path': str(filepath)
                })
        
        # Trier par date de création (plus récent en premier)
        exports.sort(key=lambda x: x['created_at'], reverse=True)
        
        return exports
    
    
    def delete_export(self, filepath):
        """
        Supprimer un export
        
        Args:
            filepath (str): Chemin du fichier à supprimer
        
        Returns:
            bool: True si succès
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"🗑️  Export supprimé : {filepath}")
                return True
            return False
        
        except Exception as e:
            print(f"❌ Erreur suppression : {str(e)}")
            return False
    
    
    def cleanup_old_exports(self, days=7, user_id=None):
        """
        Nettoyer les exports plus anciens que X jours
        
        Args:
            days (int): Nombre de jours
            user_id (int): Filtrer par utilisateur (optionnel)
        
        Returns:
            int: Nombre de fichiers supprimés
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        
        exports = self.list_exports(user_id)
        count = 0
        
        for export in exports:
            if export['created_at'] < cutoff:
                if self.delete_export(export['path']):
                    count += 1
        
        print(f"🧹 {count} export(s) ancien(s) supprimé(s)")
        return count
    
    
    @staticmethod
    def _format_size(size_bytes):
        """
        Formater une taille en bytes de manière lisible
        
        Args:
            size_bytes (int): Taille en bytes
        
        Returns:
            str: Taille formatée (ex: "2.5 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


print("✅ ExportManager chargé avec succès")