# ============================================
# DATA_PROCESSOR.PY - VERSION 3.0 OPTIMISÉE
# Gestion avancée sans colonnes index
# ============================================
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os
import warnings
import re

warnings.filterwarnings('ignore')
plt.style.use('ggplot')
sns.set_palette("husl")


class DataProcessor:
    """
    Processeur de données avec détection intelligente des colonnes
    Version 3.0 - Sans colonnes index parasites
    """
    
    def __init__(self, dataframe):
        """
        Initialise le processeur avec nettoyage automatique
        
        Args:
            dataframe (DataFrame): DataFrame brut à nettoyer
        """
        try:
            print("\n" + "="*70)
            print("🔧 INITIALISATION DU DATA PROCESSOR v3.0")
            print("="*70)
            
            # Copie du DataFrame original
            self.df_original = dataframe.copy()
            self.df = dataframe.copy()
            
            print(f"\n📊 DataFrame initial :")
            print(f"   Lignes : {len(self.df)}")
            print(f"   Colonnes : {len(self.df.columns)}")
            print(f"   Colonnes : {list(self.df.columns)}")
            
            # Nettoyer les colonnes index automatiquement
            self._clean_index_columns()
            
            # Forcer la détection des types numériques (coercion des erreurs en NaN)
            self._coerce_numeric_columns()
            
            # Reset index pour sécurité
            self.df = self.df.reset_index(drop=True)
            self.df_original = self.df_original.copy()
            
            print(f"\n✅ DataFrame après nettoyage :")
            print(f"   Lignes : {len(self.df)}")
            print(f"   Colonnes : {len(self.df.columns)}")
            print(f"   Colonnes finales : {list(self.df.columns)}")
            
            # Initialiser les statistiques
            self.stats = {
                'lignes_initiales': int(len(self.df)),
                'colonnes_initiales': int(len(self.df.columns)),
                'lignes_finales': 0,
                'colonnes_finales': 0,
                
                'lignes_avec_valeurs_manquantes': 0,
                'lignes_avec_outliers': 0,
                'doublons_trouves': 0,
                
                'valeurs_manquantes_trouvees': 0,
                'valeurs_aberrantes_trouvees': 0,
                
                'valeurs_manquantes_traitees': 0,
                'lignes_outliers_traitees': 0,
                'valeurs_aberrantes_traitees': 0,
                'doublons_supprimes': 0,
                
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.transformation_history = []
            self.plot_paths = []
            self.plots_dir = 'static/plots'
            os.makedirs(self.plots_dir, exist_ok=True)
            
            # Suivi des modifications par cellule (index, colonne)
            self.modified_cells = set()
            
            print("\n" + "="*70)
            
        except Exception as e:
            print(f"❌ Erreur initialisation DataProcessor : {str(e)}")
            raise
    
    
    def _is_index_column(self, col_name, col_values):
        """
        Détecte si une colonne est un index parasite
        
        Args:
            col_name (str): Nom de la colonne
            col_values (Series): Valeurs de la colonne
        
        Returns:
            bool: True si c'est une colonne index
        """
        col_name_lower = str(col_name).lower().strip()
        
        # 1. Noms typiques
        index_keywords = [
            'unnamed: 0', 'unnamed:0', 'unnamed_0',
            'index', 'level_0', 'level_1',
            'id', 'rowid', 'row_id', 'row id',
            '__index__', '_index', 'idx'
        ]
        
        if col_name_lower in index_keywords:
            return True
        
        # 2. Pattern "Unnamed: X"
        if re.match(r'^unnamed:?\s*\d+$', col_name_lower):
            return True
        
        # 3. Séquence numérique
        try:
            if col_values.dtype in ['int64', 'float64']:
                non_null = col_values.dropna()
                if len(non_null) > 0:
                    expected_range = pd.Series(range(len(non_null)))
                    if non_null.reset_index(drop=True).equals(expected_range):
                        return True
                    if non_null.reset_index(drop=True).equals(expected_range + 1):
                        return True
        except:
            pass
        
        return False
    
    
    def _clean_index_columns(self):
        """Supprime les colonnes index détectées"""
        print("\n🔍 Détection des colonnes index...")
        
        cols_to_drop = []
        
        for col in self.df.columns:
            if self._is_index_column(col, self.df[col]):
                cols_to_drop.append(col)
                print(f"   ❌ Colonne index détectée : '{col}'")
        
        if cols_to_drop:
            self.df = self.df.drop(columns=cols_to_drop)
            self.df_original = self.df_original.drop(columns=cols_to_drop)
            print(f"   ✅ {len(cols_to_drop)} colonne(s) supprimée(s)")
        else:
            print("   ✅ Aucune colonne index détectée")
            
    def _coerce_numeric_columns(self):
        """
        Tente de convertir les colonnes 'object' qui sont majoritairement numériques
        en float64, en transformant les erreurs (ex: texte) en NaN.
        """
        print("\n🔍 Analyse des types de colonnes...")
        
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                # Tester si la colonne peut être numérique (au moins 50% de chiffres)
                # On nettoie les espaces et on tente la conversion
                s_clean = self.df[col].astype(str).str.strip().replace(['nan', 'None', 'null'], np.nan)
                
                # Compter combien de valeurs sont "numériques-like"
                numeric_count = pd.to_numeric(s_clean, errors='coerce').notnull().sum()
                non_null_count = s_clean.notnull().sum()
                
                if non_null_count > 0 and (numeric_count / non_null_count) > 0.5:
                    print(f"   🔄 Conversion de '{col}' en type numérique (Coercion)...")
                    self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
                    self.df_original[col] = pd.to_numeric(self.df_original[col], errors='coerce')
    def _clean_nan_values(self, obj):
        """
    Remplace récursivement NaN et Infinity par None
    pour garantir un JSON valide
    """
        import math
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {k: self._clean_nan_values(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._clean_nan_values(v) for v in obj]
        return obj
    
    
    def get_initial_stats(self):
        """
        Calcule les statistiques initiales
        
        Returns:
            dict: Statistiques détaillées
        """
        try:
            print("\n📊 Calcul des statistiques initiales...")
            
            # 1. Valeurs manquantes
            lignes_missing = int(self.df.isnull().any(axis=1).sum())
            total_missing = int(self.df.isnull().sum().sum())
            
            self.stats['lignes_avec_valeurs_manquantes'] = lignes_missing
            self.stats['valeurs_manquantes_trouvees'] = total_missing
            
            # 2. Doublons
            duplicates = int(self.df.duplicated().sum())
            self.stats['doublons_trouves'] = duplicates
            
            # 3. Outliers
            numeric_cols = self.df.select_dtypes(include=['int64', 'float64']).columns
            lignes_avec_outliers = set()
            outlier_details = {}
            total_outlier_values = 0
            
            for col in numeric_cols:
                try:
                    non_nan = self.df[col].dropna()
                    if len(non_nan) < 2:
                        continue
                    
                    Q1 = non_nan.quantile(0.25)
                    Q3 = non_nan.quantile(0.75)
                    IQR = Q3 - Q1
                    lower = Q1 - 1.5 * IQR
                    upper = Q3 + 1.5 * IQR
                    
                    outlier_mask = (self.df[col] < lower) | (self.df[col] > upper)
                    outlier_indices = self.df[outlier_mask].index.tolist()
                    outlier_count = len(outlier_indices)
                    
                    if outlier_count > 0:
                        outlier_details[col] = {
                            'count': outlier_count,
                            'lower_bound': float(lower),
                            'upper_bound': float(upper)
                        }
                        lignes_avec_outliers.update(outlier_indices)
                        total_outlier_values += outlier_count
                        
                except Exception as e:
                    continue
            
            self.stats['lignes_avec_outliers'] = len(lignes_avec_outliers)
            self.stats['valeurs_aberrantes_trouvees'] = total_outlier_values
            
            # 4. Aperçu des données (SANS INDEX)
            try:
                data_preview_raw = self.df.head(100).reset_index(drop=True).to_dict('records')
                data_preview = self._clean_nan_values(data_preview_raw)
            except:
                data_preview = []
            
            print(f"   • Lignes avec valeurs manquantes : {lignes_missing}")
            print(f"   • Doublons : {duplicates}")
            print(f"   • Valeurs aberrantes détectées : {len(lignes_avec_outliers)}")
            
            result = {
                'lignes_totales': self.stats['lignes_initiales'],
                'colonnes_totales': self.stats['colonnes_initiales'],
                
                'lignes_avec_valeurs_manquantes': lignes_missing,
                'lignes_avec_outliers': len(lignes_avec_outliers),
                'doublons': duplicates,
                
                'valeurs_manquantes': lignes_missing,
                'outliers': len(lignes_avec_outliers),
                
                'outlier_details': outlier_details,
                'colonnes': list(self.df.columns),
                'types_colonnes': self.df.dtypes.astype(str).to_dict(),
                'data_preview': data_preview
            }
            
            return self._clean_nan_values(result)
            
        except Exception as e:
            print(f"❌ Erreur get_initial_stats : {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'lignes_totales': len(self.df),
                'colonnes_totales': len(self.df.columns),
                'lignes_avec_valeurs_manquantes': 0,
                'valeurs_manquantes': 0,
                'lignes_avec_outliers': 0,
                'outliers': 0,
                'doublons': 0,
                'outlier_details': {},
                'colonnes': list(self.df.columns),
                'types_colonnes': {},
                'data_preview': []
            }
    
    
    def handle_missing_values(self, strategy='auto'):
        """Traite les valeurs manquantes"""
        try:
            print(f"\n🛠️ Traitement des valeurs manquantes (stratégie : {strategy})...")
            
            lignes_avant = int(self.df.isnull().any(axis=1).sum())
            
            if lignes_avant == 0:
                print("   ✅ Aucune valeur manquante")
                return 0
            
            if strategy == 'drop':
                rows_before = len(self.df)
                self.df = self.df.dropna()
                rows_after = len(self.df)
                valeurs_traitees = rows_before - rows_after
                print(f"   🗑️ {valeurs_traitees} lignes supprimées")
            
            else:
                valeurs_traitees = 0
                for col in self.df.columns:
                    missing_count = self.df[col].isnull().sum()
                    if missing_count == 0:
                        continue
                    
                    try:
                        # Déterminer la valeur de remplissage selon la stratégie et le type
                        val = None
                        is_numeric = pd.api.types.is_numeric_dtype(self.df[col])
                        
                        if strategy == 'mean' and is_numeric:
                            val = self.df[col].mean()
                        elif strategy == 'median' and is_numeric:
                            val = self.df[col].median()
                        elif strategy == 'mode' or strategy == 'auto':
                            if is_numeric:
                                # Pour les numériques : mode ou médiane
                                mode_res = self.df[col].mode()
                                val = mode_res[0] if not mode_res.empty else self.df[col].median()
                            else:
                                # 🛡️ Pour les colonnes texte/catégorielles : utiliser 'Inconnu'
                                # au lieu du mode global qui peut être hors contexte
                                # (ex: remplir State_Abbr manquant avec la valeur la + fréquente
                                # du dataset entier donnerait un mauvais état)
                                val = "Inconnu"
                        
                        # Fallback si val est toujours None
                        if val is None:
                            if is_numeric:
                                val = self.df[col].median() if strategy != 'mean' else self.df[col].mean()
                            else:
                                val = "Inconnu"

                        # Appliquer le remplissage
                        missing_indices = self.df[self.df[col].isnull()].index.tolist()
                        for idx in missing_indices:
                            self.modified_cells.add((idx, col))
                        
                        self.df[col] = self.df[col].fillna(val)
                        valeurs_traitees += missing_count
                        
                    except Exception as e:
                        print(f"   ⚠️ Erreur sur colonne '{col}': {str(e)}")
                        continue
            
            self.stats['valeurs_manquantes_traitees'] = valeurs_traitees
            
            self.transformation_history.append({
                'step': 'handle_missing_values',
                'strategy': strategy,
                'count': valeurs_traitees
            })
            
            print(f"   ✅ {valeurs_traitees} valeurs traitées")
            return valeurs_traitees
            
        except Exception as e:
            print(f"❌ Erreur : {str(e)}")
            return 0
    
    
    def handle_outliers(self, method='cap'):
        """Traite les valeurs aberrantes"""
        try:
            print(f"\n🛠️ Traitement des outliers (méthode : {method})...")
            
            numeric_cols = self.df.select_dtypes(include=['int64', 'float64']).columns
            
            if len(numeric_cols) == 0:
                print("   ⚠️ Aucune colonne numérique")
                return 0
            
            lignes_avec_outliers = set()
            
            for col in numeric_cols:
                try:
                    non_nan = self.df[col].dropna()
                    if len(non_nan) < 2:
                        continue
                    
                    Q1 = non_nan.quantile(0.25)
                    Q3 = non_nan.quantile(0.75)
                    IQR = Q3 - Q1
                    median_col = non_nan.median()
                    
                    # 🛡️ CV ROBUSTE = IQR / médiane (insensible aux extrêmes).
                    # Permet de détecter les distributions naturellement très étalées
                    # (comptages de votes, populations) sans être trompé par les outliers eux-mêmes.
                    # Un CV robuste > 0.6 indique une dispersion naturellement très large
                    # où chaque valeur est légitime (pas un outlier de mesure).
                    if median_col != 0:
                        rcv = IQR / abs(median_col)
                        if rcv > 0.6:
                            print(f"   ⏭️ Colonne '{col}' ignorée (dispersion naturelle élevée, rCV={rcv:.2f})")
                            continue
                    
                    lower = Q1 - 1.5 * IQR
                    upper = Q3 + 1.5 * IQR
                    
                    mask = (self.df[col] < lower) | (self.df[col] > upper)
                    lignes_avec_outliers.update(self.df[mask].index.tolist())
                except Exception as e:
                    continue
            
            lignes_avant = len(lignes_avec_outliers)
            
            if lignes_avant == 0:
                print("   ✅ Aucun outlier")
                return 0
            
            for col in numeric_cols:
                try:
                    non_nan = self.df[col].dropna()
                    if len(non_nan) < 2:
                        continue
                    
                    Q1 = non_nan.quantile(0.25)
                    Q3 = non_nan.quantile(0.75)
                    IQR = Q3 - Q1
                    median_col = non_nan.median()
                    
                    # 🛡️ Même vérification rCV robuste que dans la phase de détection
                    if median_col != 0:
                        rcv = IQR / abs(median_col)
                        if rcv > 0.6:
                            continue
                    
                    lower = Q1 - 1.5 * IQR
                    upper = Q3 + 1.5 * IQR
                    
                    mask = (self.df[col] < lower) | (self.df[col] > upper)
                    count = int(mask.sum())
                    
                    if count == 0:
                        continue
                    
                    # Enregistrer les modifications
                    outlier_indices = self.df[mask].index.tolist()
                    for idx in outlier_indices:
                        self.modified_cells.add((idx, col))

                    if method == 'cap':
                        # ✅ Remplacer l'outlier par la médiane robuste (sans les outliers)
                        # pour éviter de plafonner à une valeur IQR hors du domaine réel
                        median_val = round(float(self.df.loc[~mask, col].median()), 2)
                        self.df.loc[mask, col] = median_val
                        print(f"   🔧 '{col}' : {count} outlier(s) remplacé(s) par la médiane ({median_val})")
                    elif method == 'median':
                        median_val = round(float(self.df[col].median()), 2)
                        self.df.loc[mask, col] = median_val
                    
                except Exception as e:
                    continue
            
            if method == 'remove':
                len_before = len(self.df)
                # Utiliser errors='ignore' au cas où certaines lignes auraient été supprimées par handle_missing_values
                self.df = self.df.drop(list(lignes_avec_outliers), errors='ignore')
                len_after = len(self.df)
                lignes_supprimees = len_before - len_after
                self.stats['lignes_outliers_traitees'] = lignes_supprimees
            else:
                self.stats['lignes_outliers_traitees'] = lignes_avant
            
            self.stats['valeurs_aberrantes_traitees'] = lignes_avant
            
            self.transformation_history.append({
                'step': 'handle_outliers',
                'method': method,
                'count': lignes_avant
            })
            
            print(f"   ✅ {lignes_avant} lignes traitées")
            return lignes_avant
            
        except Exception as e:
            print(f"❌ Erreur : {str(e)}")
            return 0
    
    
    def remove_duplicates(self):
        """Supprime les doublons"""
        try:
            print("\n🗑️ Suppression des doublons...")
            
            lignes_avant = len(self.df)
            self.df = self.df.drop_duplicates()
            lignes_apres = len(self.df)
            
            doublons_supprimes = lignes_avant - lignes_apres
            
            self.stats['doublons_supprimes'] = doublons_supprimes
            
            self.transformation_history.append({
                'step': 'remove_duplicates',
                'count': doublons_supprimes
            })
            
            if doublons_supprimes > 0:
                print(f"   ✅ {doublons_supprimes} doublons supprimés")
            else:
                print("   ✅ Aucun doublon")
            
            return doublons_supprimes
            
        except Exception as e:
            print(f"❌ Erreur : {str(e)}")
            return 0
    
    
    def generate_plots(self):
        """Génère les graphiques de visualisation"""
        try:
            print("\n🎨 Génération des graphiques...")
            
            plot_paths = {}
            
            numeric_cols = self.df_original.select_dtypes(include=['int64', 'float64']).columns
            common_cols = [c for c in numeric_cols if c in self.df.columns]
            
            if len(common_cols) == 0:
                print("   ⚠️ Aucune colonne numérique")
                return plot_paths
            
            cols_to_plot = common_cols[:4]
            
            sns.set_style("whitegrid")
            sns.set_palette("Set2")
            
            # Graphique 1 : Boxplots
            try:
                fig, axes = plt.subplots(1, 2, figsize=(16, 6))
                fig.suptitle("📊 Distribution - AVANT et APRÈS", fontsize=16, fontweight='bold')
                
                sns.boxplot(data=self.df_original[cols_to_plot], ax=axes[0])
                axes[0].set_title("AVANT", fontsize=12, fontweight='bold')
                axes[0].set_ylabel("Valeur", fontsize=10)
                axes[0].grid(True, alpha=0.3)
                
                sns.boxplot(data=self.df[cols_to_plot], ax=axes[1])
                axes[1].set_title("APRÈS", fontsize=12, fontweight='bold')
                axes[1].set_ylabel("Valeur", fontsize=10)
                axes[1].grid(True, alpha=0.3)
                
                plt.tight_layout()
                
                path1 = os.path.join(self.plots_dir, 'distributions.png')
                plt.savefig(path1, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close()
                
                plot_paths['distributions'] = '/static/plots/distributions.png'
                
            except Exception as e:
                print(f"   ❌ Erreur boxplots : {str(e)}")
            
            # Graphique 2 : Histogrammes
            try:
                fig, axes = plt.subplots(2, 2, figsize=(16, 10))
                fig.suptitle("📊 Histogrammes", fontsize=16, fontweight='bold')
                
                axes = axes.flatten()
                colors = ['skyblue', 'lightgreen', 'salmon', 'gold']
                
                for i, col in enumerate(cols_to_plot):
                    if i < len(axes):
                        axes[i].hist(self.df[col].dropna(), bins=20,
                                   color=colors[i % len(colors)],
                                   alpha=0.7, edgecolor='black')
                        axes[i].set_title(col, fontsize=12, fontweight='bold')
                        axes[i].set_xlabel('Valeur', fontsize=10)
                        axes[i].set_ylabel('Fréquence', fontsize=10)
                        axes[i].grid(True, alpha=0.3, axis='y')
                
                for j in range(i+1, len(axes)):
                    axes[j].axis('off')
                
                plt.tight_layout()
                
                path2 = os.path.join(self.plots_dir, 'histograms.png')
                plt.savefig(path2, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close()
                
                plot_paths['histograms'] = '/static/plots/histograms.png'
                
            except Exception as e:
                print(f"   ❌ Erreur histogrammes : {str(e)}")
            
            # Graphique 3 : Corrélation
            try:
                corr_matrix = self.df[common_cols].corr().round(2)
                
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
                
                plt.title("🔗 Corrélation", fontsize=14, fontweight='bold', pad=20)
                plt.tight_layout()
                
                path3 = os.path.join(self.plots_dir, 'correlation.png')
                plt.savefig(path3, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close()
                
                plot_paths['correlation'] = '/static/plots/correlation.png'
                
            except Exception as e:
                print(f"   ❌ Erreur corrélation : {str(e)}")
            
            self.plot_paths = plot_paths
            
            print(f"   ✅ {len(plot_paths)} graphiques générés")
            
            return plot_paths
            
        except Exception as e:
            print(f"❌ Erreur generate_plots : {str(e)}")
            return {}
    
    
    def calculate_quality_score(self):
        """Calcule le score de qualité"""
        try:
            total_issues = (
                self.stats['lignes_avec_valeurs_manquantes'] +
                self.stats['lignes_avec_outliers'] +
                self.stats['doublons_trouves']
            )
            
            total_fixed = (
                self.stats.get('valeurs_manquantes_traitees', 0) +
                self.stats.get('lignes_outliers_traitees', 0) +
                self.stats.get('doublons_supprimes', 0)
            )
            
            if total_issues == 0:
                score = 100.0
            else:
                score = round((total_fixed / total_issues) * 100, 1)
            
            score = min(score, 100.0)
            
            if score >= 90:
                label, color = "Excellent", "success"
            elif score >= 70:
                label, color = "Bon", "info"
            elif score >= 50:
                label, color = "Moyen", "warning"
            else:
                label, color = "Faible", "danger"
            
            return {
                'score': score,
                'label': label,
                'color': color,
                'total_issues': total_issues,
                'total_fixed': total_fixed
            }
            
        except Exception as e:
            print(f"❌ Erreur calculate_quality_score : {str(e)}")
            return {
                'score': 0.0,
                'label': 'Erreur',
                'color': 'danger',
                'total_issues': 0,
                'total_fixed': 0
            }
    
    
    def get_final_stats(self):
        """Récupère les statistiques finales"""
        try:
            self.stats['lignes_finales'] = len(self.df)
            self.stats['colonnes_finales'] = len(self.df.columns)
            
            quality = self.calculate_quality_score()
            
            numeric_cols = self.df.select_dtypes(include=['int64', 'float64']).columns
            descriptive_stats = {}
            
            if len(numeric_cols) > 0:
                desc = self.df[numeric_cols].describe().round(2)
                descriptive_stats = self._clean_nan_values(desc.to_dict())
            
            try:
                data_preview = self.df.head(100).reset_index(drop=True).to_dict('records')
            except:
                data_preview = []
            
            # Préparer le masque des modifications (nécessite de mapper l'index actuel au preview)
            # Puisque le preview est head(100) avec reset_index(drop=True), 
            # on doit filtrer modified_cells pour les 100 premières lignes AFFICHÉES
            current_index_list = self.df.head(100).index.tolist()
            api_modified_cells = []
            for i, idx in enumerate(current_index_list):
                for col in self.df.columns:
                    if (idx, col) in self.modified_cells:
                        api_modified_cells.append({'row': i, 'col': col})

            return self._clean_nan_values({
                'stats': self.stats,
                'quality': quality,
                'descriptive_stats': descriptive_stats,
                'data_preview': data_preview,
                'modified_cells': api_modified_cells,
                'transformation_history': self.transformation_history,
                'plot_paths': self.plot_paths,
                'colonnes': list(self.df.columns)
            })
            
        except Exception as e:
            print(f"❌ Erreur get_final_stats : {str(e)}")
            return {
                'stats': self.stats,
                'quality': {'score': 0, 'label': 'Erreur', 'color': 'danger'},
                'descriptive_stats': {},
                'data_preview': [],
                'transformation_history': [],
                'plot_paths': {},
                'colonnes': list(self.df.columns)
            }
    
    
    def export_to_csv(self, filepath):
        """Exporte les données nettoyées en CSV (SANS INDEX)"""
        try:
            self.df.to_csv(filepath, index=False, encoding='utf-8')
            print(f"\n💾 CSV exporté (sans index) : {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Erreur export : {str(e)}")
            return None
    
    
    def get_dataframe(self):
        """Récupère le DataFrame nettoyé"""
        return self.df.copy()


print("✅ DataProcessor v3.0 chargé (Gestion optimale des colonnes)")