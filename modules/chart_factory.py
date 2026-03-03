# ============================================
# CHART_FACTORY.PY
# Factory de génération de graphiques
# ============================================
"""
Factory pour générer des graphiques réutilisables.

Types de graphiques:
- Boxplots (distributions avant/après)
- Histogrammes
- Heatmap de corrélation
- Barres comparatives
- Line plots

Ce module est OPTIONNEL - il factoriserait le code de génération
de graphiques si vous voulez réutiliser cette logique ailleurs.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path


class ChartFactory:
    """
    Factory de génération de graphiques professionnels
    """
    
    def __init__(self, output_dir='static/plots', dpi=150, style='ggplot'):
        """
        Initialisation du générateur de graphiques
        
        Args:
            output_dir (str): Dossier de sortie
            dpi (int): Résolution des images
            style (str): Style matplotlib
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.dpi = dpi
        self.style = style
        
        # Appliquer le style
        plt.style.use(self.style)
        sns.set_palette("husl")
        
        print(f"📊 ChartFactory initialisé (output: {self.output_dir}, dpi: {self.dpi})")
    
    
    def create_boxplot_comparison(self, df_before, df_after, columns=None, filename='boxplot_comparison.png'):
        """
        Créer un boxplot comparatif avant/après
        
        Args:
            df_before (DataFrame): Données avant nettoyage
            df_after (DataFrame): Données après nettoyage
            columns (list): Colonnes à afficher (max 4)
            filename (str): Nom du fichier
        
        Returns:
            str: Chemin du fichier généré
        """
        # Sélectionner les colonnes numériques
        if columns is None:
            numeric_cols = df_before.select_dtypes(include=['int64', 'float64']).columns
            columns = list(numeric_cols[:4])  # Max 4 colonnes
        
        if len(columns) == 0:
            print("⚠️  Aucune colonne numérique pour le boxplot")
            return None
        
        # Créer la figure
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('📊 Distribution - AVANT et APRÈS', fontsize=16, fontweight='bold')
        
        # Boxplot AVANT
        sns.boxplot(data=df_before[columns], ax=axes[0])
        axes[0].set_title('AVANT', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Valeur', fontsize=10)
        axes[0].grid(True, alpha=0.3)
        axes[0].tick_params(axis='x', rotation=45)
        
        # Boxplot APRÈS
        sns.boxplot(data=df_after[columns], ax=axes[1])
        axes[1].set_title('APRÈS', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Valeur', fontsize=10)
        axes[1].grid(True, alpha=0.3)
        axes[1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Sauvegarder
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"   ✅ Boxplot créé : {filepath}")
        return str(filepath)
    
    
    def create_histograms(self, df, columns=None, filename='histograms.png'):
        """
        Créer des histogrammes pour plusieurs colonnes
        
        Args:
            df (DataFrame): Données
            columns (list): Colonnes à afficher
            filename (str): Nom du fichier
        
        Returns:
            str: Chemin du fichier généré
        """
        if columns is None:
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            columns = list(numeric_cols[:4])
        
        if len(columns) == 0:
            print("⚠️  Aucune colonne numérique pour les histogrammes")
            return None
        
        # Créer la grille
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('📊 Histogrammes', fontsize=16, fontweight='bold')
        
        axes = axes.flatten()
        colors = ['skyblue', 'lightgreen', 'salmon', 'gold']
        
        for i, col in enumerate(columns):
            if i < len(axes):
                axes[i].hist(df[col].dropna(), bins=20,
                           color=colors[i % len(colors)],
                           alpha=0.7, edgecolor='black')
                axes[i].set_title(col, fontsize=12, fontweight='bold')
                axes[i].set_xlabel('Valeur', fontsize=10)
                axes[i].set_ylabel('Fréquence', fontsize=10)
                axes[i].grid(True, alpha=0.3, axis='y')
        
        # Masquer les axes inutilisés
        for j in range(len(columns), len(axes)):
            axes[j].axis('off')
        
        plt.tight_layout()
        
        # Sauvegarder
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"   ✅ Histogrammes créés : {filepath}")
        return str(filepath)
    
    
    def create_correlation_heatmap(self, df, filename='correlation.png'):
        """
        Créer une heatmap de corrélation
        
        Args:
            df (DataFrame): Données
            filename (str): Nom du fichier
        
        Returns:
            str: Chemin du fichier généré
        """
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
        
        if len(numeric_cols) < 2:
            print("⚠️  Pas assez de colonnes numériques pour la corrélation")
            return None
        
        # Calculer la matrice de corrélation
        corr_matrix = df[numeric_cols].corr().round(2)
        
        # Créer la figure
        plt.figure(figsize=(10, 8))
        
        sns.heatmap(corr_matrix,
                   annot=True,
                   cmap='coolwarm',
                   center=0,
                   linewidths=1,
                   linecolor='black',
                   square=True,
                   cbar_kws={'label': 'Corrélation'},
                   fmt='.2f',
                   vmin=-1, vmax=1)
        
        plt.title('🔗 Corrélation', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        
        # Sauvegarder
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"   ✅ Heatmap créée : {filepath}")
        return str(filepath)
    
    
    def create_bar_chart(self, data, labels, title='Bar Chart', filename='barchart.png'):
        """
        Créer un graphique en barres
        
        Args:
            data (list): Valeurs
            labels (list): Étiquettes
            title (str): Titre
            filename (str): Nom du fichier
        
        Returns:
            str: Chemin du fichier généré
        """
        plt.figure(figsize=(10, 6))
        
        bars = plt.bar(labels, data, color='skyblue', edgecolor='black', alpha=0.7)
        
        # Ajouter les valeurs sur les barres
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0f}',
                    ha='center', va='bottom', fontsize=10)
        
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel('Catégories', fontsize=12)
        plt.ylabel('Valeurs', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        
        # Sauvegarder
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"   ✅ Bar chart créé : {filepath}")
        return str(filepath)


print("✅ ChartFactory chargé avec succès")