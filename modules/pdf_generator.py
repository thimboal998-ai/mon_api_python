# ============================================
# PDF_GENERATOR.PY - VERSION CORRIGÉE (AUTO-RESIZE)
# ============================================

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
import os

class PDFReportGenerator:
    """Générateur de rapports PDF"""
    
    def __init__(self, filename='rapport_nettoyage.pdf'):
        self.filename = filename
        self.doc = SimpleDocTemplate(filename, pagesize=A4)
        self.styles = getSampleStyleSheet()
        self.elements = []
        self._create_custom_styles()
        print(f"📄 Générateur PDF initialisé : {filename}")
    
    def _create_custom_styles(self):
        """Créer des styles personnalisés"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#764ba2'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            spaceAfter=10
        ))
    
    def add_header(self, title='Rapport de Nettoyage de Données'):
        """Ajouter l'en-tête"""
        title_para = Paragraph(f'🧹 {title}', self.styles['CustomTitle'])
        self.elements.append(title_para)
        
        date_text = f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}"
        date_para = Paragraph(date_text, self.styles['Normal'])
        self.elements.append(date_para)
        self.elements.append(Spacer(1, 0.3*inch))
        
        line = Table([['']], colWidths=[7*inch])
        line.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#667eea'))
        ]))
        self.elements.append(line)
        self.elements.append(Spacer(1, 0.3*inch))
    
    def add_section(self, title):
        """Ajouter une section"""
        section_para = Paragraph(title, self.styles['CustomHeading'])
        self.elements.append(section_para)
    
    def add_statistics_table(self, stats):
        """Ajouter tableau de statistiques"""
        data = [['📊 Métrique', 'Valeur']]
        
        metrics = {
            'Lignes initiales': stats.get('lignes_initiales', 'N/A'),
            'Lignes finales': stats.get('lignes_finales', 'N/A'),
            'Colonnes': stats.get('colonnes_finales', 'N/A'),
            'Valeurs manquantes traitées': stats.get('valeurs_manquantes_traitees', 0),
            'Valeurs aberrantes traitées': stats.get('valeurs_aberrantes_traitees', 0),
            'Doublons supprimés': stats.get('doublons_supprimes', 0)
        }
        
        for key, value in metrics.items():
            data.append([key, str(value)])
        
        table = Table(data, colWidths=[4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))
    
    def add_quality_score(self, stats):
        """Ajouter score de qualité"""
        total_issues = (stats.get('valeurs_manquantes_trouvees', 0) +
                       stats.get('valeurs_aberrantes_trouvees', 0) +
                       stats.get('doublons_trouves', 0))
        
        total_fixed = (stats.get('valeurs_manquantes_traitees', 0) +
                      stats.get('valeurs_aberrantes_traitees', 0) +
                      stats.get('doublons_supprimes', 0))
        
        quality_score = (total_fixed / total_issues * 100) if total_issues > 0 else 100
        
        color = colors.green if quality_score >= 90 else colors.orange if quality_score >= 70 else colors.red
        message = "✅ Excellente" if quality_score >= 90 else "⚠️ Bonne" if quality_score >= 70 else "❌ À améliorer"
        
        text = f"<b>Score de Qualité : {quality_score:.1f}% - {message}</b>"
        para = Paragraph(text, self.styles['CustomBody'])
        
        table = Table([[para]], colWidths=[6*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), color),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))
    
    def add_transformation_history(self, history):
        """Ajouter historique"""
        self.add_section('📜 Historique des Transformations')
        
        step_names = {
            'detection_missing': '🔍 Détection valeurs manquantes',
            'handle_missing': '🛠️ Traitement valeurs manquantes',
            'detection_outliers': '🔍 Détection valeurs aberrantes',
            'handle_outliers': '🛠️ Traitement valeurs aberrantes',
            'detection_duplicates': '🔍 Détection doublons',
            'remove_duplicates': '🗑️ Suppression doublons',
            'normalize': '📊 Normalisation'
        }
        
        for i, transform in enumerate(history, 1):
            step = transform.get('step', 'Unknown')
            step_name = step_names.get(step, step)
            text = f"<b>Étape {i} :</b> {step_name}"
            para = Paragraph(text, self.styles['CustomBody'])
            self.elements.append(para)
        
        self.elements.append(Spacer(1, 0.2*inch))
    
    # === C'EST ICI LA CORRECTION PRINCIPALE ===
    def add_image(self, image_path, width=6*inch):
        """Ajouter image avec redimensionnement intelligent"""
        if os.path.exists(image_path):
            try:
                # 1. Créer l'objet Image
                img = Image(image_path)
                
                # 2. Récupérer les dimensions originales
                original_w = img.drawWidth
                original_h = img.drawHeight
                
                # 3. Définir les limites (Une page A4 fait ~11.7 pouces, on garde une marge)
                max_width = width
                max_height = 8.5 * inch  # Max 8.5 pouces de haut pour être sûr
                
                # 4. Calculer le facteur de réduction
                aspect = original_h / original_w
                
                # Si l'image dépasse la largeur voulue
                target_w = max_width
                target_h = target_w * aspect
                
                # Si la hauteur calculée dépasse le max autorisé (C'est votre erreur !)
                if target_h > max_height:
                    target_h = max_height
                    target_w = target_h / aspect
                
                # 5. Appliquer les nouvelles dimensions
                img.drawWidth = target_w
                img.drawHeight = target_h
                img.hAlign = 'CENTER'
                
                self.elements.append(img)
                self.elements.append(Spacer(1, 0.2*inch))
                
            except Exception as e:
                print(f"Erreur image: {e}")
                para = Paragraph(f"⚠️ Impossible d'afficher l'image", self.styles['CustomBody'])
                self.elements.append(para)
    
    def add_recommendations(self, stats):
        """Ajouter recommandations"""
        self.add_section('💡 Recommandations')
        
        recs = []
        if stats.get('valeurs_manquantes_trouvees', 0) > 0:
            recs.append("✅ Valeurs manquantes traitées. Vérifiez la méthode utilisée.")
        if stats.get('valeurs_aberrantes_trouvees', 0) > 0:
            recs.append("✅ Valeurs aberrantes corrigées.")
        if stats.get('doublons_supprimes', 0) > 0:
            recs.append("✅ Doublons supprimés.")
        
        recs.append("📊 Visualisez vos données avant/après.")
        recs.append("💾 Conservez une copie des originaux.")
        
        for rec in recs:
            para = Paragraph(f"• {rec}", self.styles['CustomBody'])
            self.elements.append(para)
        
        self.elements.append(Spacer(1, 0.2*inch))
    
    def add_descriptive_stats(self, descriptive_stats):
        """Ajouter tableau de statistiques descriptives"""
        if not descriptive_stats:
            return

        self.add_section('📈 Statistiques Descriptives')
        
        # Préparer les données pour le tableau
        # Colonnes: Métrique, col1, col2, ...
        columns = list(descriptive_stats.keys())
        metrics = ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']
        metric_labels = {
            'count': 'Nombre', 'mean': 'Moyenne', 'std': 'Ecart-type',
            'min': 'Mimimum', '25%': 'Q1 (25%)', '50%': 'Médiane',
            '75%': 'Q3 (75%)', 'max': 'Maximum'
        }
        
        # En-tête
        header = ['Métrique'] + columns
        data = [header]
        
        for metric in metrics:
            row = [metric_labels.get(metric, metric)]
            for col in columns:
                val = descriptive_stats[col].get(metric, 'N/A')
                if isinstance(val, (int, float)):
                    row.append(f"{val:.2f}")
                else:
                    row.append(str(val))
            data.append(row)
            
        # Calculer largeur colonnes
        # Page largeur dispo ~ 7.5 inch
        # Si trop de colonnes, ça va déborder/écraser. 
        # On fait simple pour l'instant: auto width ou fixe petit
        col_width = (7.5 * inch) / len(header)
        col_widths = [col_width] * len(header)

        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8), # Plus petit pour faire tenir
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))


    def add_data_table(self, df, limit=1000):
        """Ajouter tableau des données nettoyées"""
        self.add_section(f'📋 Données Nettoyées (Premières {min(len(df), limit)} lignes)')
        
        if df.empty:
            para = Paragraph("Aucune donnée à afficher.", self.styles['CustomBody'])
            self.elements.append(para)
            return

        # Limiter les lignes
        df_display = df.head(limit)
        
        # Convertir en liste de listes
        columns = df_display.columns.tolist()
        data = [columns] + df_display.astype(str).values.tolist()
        
        # Style du tableau données
        # On essaie d'adapter la taille police selon nombre colonnes
        font_size = 10
        if len(columns) > 8: font_size = 8
        if len(columns) > 12: font_size = 6
        
         # Largeur auto simpliste
        col_width = (7.5 * inch) / len(columns)
        
        table = Table(data, colWidths=[col_width] * len(columns))
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), font_size),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('FONTSIZE', (0, 1), (-1, -1), font_size),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ]))
        
        self.elements.append(table)
        self.elements.append(PageBreak())

    def add_page_break(self):
        """Saut de page"""
        self.elements.append(PageBreak())
    
    def generate(self, stats, plot_paths=None, transformation_history=None):
        """
        Générer le PDF (Méthode standard - legacy)
        NOTE: Si vous construisez le rapport manuellement via les méthodes add_*,
        utilisez finish() à la place de generate() pour éviter les doublons.
        """
        print(f"\n📄 Génération du rapport PDF...")
        
        self.add_header()
        
        self.add_section('📊 Résumé Exécutif')
        summary = f"Analyse de <b>{stats.get('lignes_initiales', 0)} lignes</b>. " \
                  f"<b>{stats.get('lignes_finales', 0)} lignes</b> conservées."
        para = Paragraph(summary, self.styles['CustomBody'])
        self.elements.append(para)
        self.elements.append(Spacer(1, 0.2*inch))
        
        self.add_quality_score(stats)
        
        self.add_section('📈 Statistiques Détaillées')
        self.add_statistics_table(stats)
        
        if transformation_history:
            self.add_transformation_history(transformation_history)
        
        if plot_paths and len(plot_paths) > 0:
            self.add_page_break()
            self.add_section('📊 Visualisations')
            
            for i, plot_path in enumerate(plot_paths, 1):
                if os.path.exists(plot_path):
                    graph_title = os.path.basename(plot_path).replace('_', ' ').replace('.png', '').title()
                    para = Paragraph(f"<b>Graphique {i} : {graph_title}</b>", self.styles['CustomBody'])
                    self.elements.append(para)
                    self.add_image(plot_path, width=6.5*inch)
                    if i < len(plot_paths):
                        self.add_page_break()
        
        self.add_page_break()
        self.add_recommendations(stats)
        
        self.finish()
        return self.filename

    def finish(self):
        """Finaliser et sauvegarder le PDF"""
        self.add_section('📞 Informations')
        final = f"<b>Rapport automatique - API Nettoyage</b><br/><br/>" \
                f"<i>Date : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>"
        para = Paragraph(final, self.styles['CustomBody'])
        self.elements.append(para)
        
        try:
            self.doc.build(self.elements)
            print(f"✅ PDF généré : {self.filename}")
            return self.filename
        except Exception as e:
            print(f"❌ Erreur PDF : {str(e)}")
            raise