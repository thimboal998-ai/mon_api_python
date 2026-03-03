# ============================================
# CONFIG_MANAGER.PY - GESTIONNAIRE DE CONFIGURATION
# Système de sauvegarde et chargement des options
# ============================================

import json
import os
from datetime import datetime

class ConfigManager:
    """
    🎯 CLASSE : Gestionnaire de configurations
    
    Permet de :
    - Sauvegarder les options de nettoyage
    - Charger des configurations prédéfinies
    - Créer des profils personnalisés
    - Partager des configurations
    """
    
    def __init__(self, config_dir='configs'):
        """
        Initialisation du gestionnaire
        
        Args:
            config_dir (str): Dossier pour stocker les configurations
        """
        self.config_dir = config_dir
        os.makedirs(config_dir, exist_ok=True)
        
        # Configurations par défaut
        self.default_configs = {
            'standard': {
                'name': 'Standard',
                'description': 'Configuration par défaut recommandée',
                'missing_strategy': 'auto',
                'outliers_method': 'cap',
                'normalize': True,
                'normalize_method': 'standard',
                'remove_duplicates': True
            },
            'conservative': {
                'name': 'Conservatrice',
                'description': 'Minimum de modifications, conserve le plus de données',
                'missing_strategy': 'median',
                'outliers_method': 'cap',
                'normalize': False,
                'normalize_method': 'standard',
                'remove_duplicates': True
            },
            'aggressive': {
                'name': 'Agressive',
                'description': 'Nettoyage en profondeur, supprime les problèmes',
                'missing_strategy': 'drop',
                'outliers_method': 'remove',
                'normalize': True,
                'normalize_method': 'standard',
                'remove_duplicates': True
            },
            'machine_learning': {
                'name': 'Machine Learning',
                'description': 'Optimisée pour le Machine Learning',
                'missing_strategy': 'median',
                'outliers_method': 'cap',
                'normalize': True,
                'normalize_method': 'standard',
                'remove_duplicates': True
            },
            'visualization': {
                'name': 'Visualisation',
                'description': 'Optimisée pour les graphiques et rapports',
                'missing_strategy': 'mean',
                'outliers_method': 'median',
                'normalize': False,
                'normalize_method': 'standard',
                'remove_duplicates': True
            }
        }
        
        print(f"⚙️  ConfigManager initialisé : {len(self.default_configs)} configurations par défaut")
    
    
    def save_config(self, config_name, config_data, overwrite=False):
        """
        Sauvegarder une configuration
        
        Args:
            config_name (str): Nom de la configuration
            config_data (dict): Données de configuration
            overwrite (bool): Écraser si existe déjà
        
        Returns:
            bool: True si succès, False sinon
        """
        filepath = os.path.join(self.config_dir, f"{config_name}.json")
        
        # Vérifier si existe déjà
        if os.path.exists(filepath) and not overwrite:
            print(f"⚠️  La configuration '{config_name}' existe déjà. Utilisez overwrite=True pour écraser.")
            return False
        
        # Ajouter des métadonnées
        config_with_meta = {
            'name': config_name,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'config': config_data
        }
        
        # Sauvegarder
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_with_meta, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Configuration '{config_name}' sauvegardée : {filepath}")
            return True
        
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde : {str(e)}")
            return False
    
    
    def load_config(self, config_name):
        """
        Charger une configuration
        
        Args:
            config_name (str): Nom de la configuration
        
        Returns:
            dict: Configuration ou None si non trouvée
        """
        # Vérifier dans les configurations par défaut
        if config_name in self.default_configs:
            print(f"✅ Configuration par défaut chargée : '{config_name}'")
            return self.default_configs[config_name]
        
        # Chercher dans les fichiers
        filepath = os.path.join(self.config_dir, f"{config_name}.json")
        
        if not os.path.exists(filepath):
            print(f"❌ Configuration '{config_name}' non trouvée")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ Configuration '{config_name}' chargée depuis : {filepath}")
            return data.get('config', data)
        
        except Exception as e:
            print(f"❌ Erreur lors du chargement : {str(e)}")
            return None
    
    
    def list_configs(self):
        """
        Lister toutes les configurations disponibles
        
        Returns:
            dict: Dictionnaire avec toutes les configurations
        """
        configs = {}
        
        # Ajouter les configurations par défaut
        for name, config in self.default_configs.items():
            configs[name] = {
                'type': 'default',
                'name': config['name'],
                'description': config['description']
            }
        
        # Ajouter les configurations personnalisées
        if os.path.exists(self.config_dir):
            for filename in os.listdir(self.config_dir):
                if filename.endswith('.json'):
                    config_name = filename[:-5]  # Enlever .json
                    
                    try:
                        with open(os.path.join(self.config_dir, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        configs[config_name] = {
                            'type': 'custom',
                            'name': data.get('name', config_name),
                            'created_at': data.get('created_at', 'Unknown'),
                            'description': data.get('config', {}).get('description', 'Configuration personnalisée')
                        }
                    except:
                        pass
        
        return configs
    
    
    def delete_config(self, config_name):
        """
        Supprimer une configuration personnalisée
        
        Args:
            config_name (str): Nom de la configuration
        
        Returns:
            bool: True si supprimé, False sinon
        """
        # Empêcher la suppression des configs par défaut
        if config_name in self.default_configs:
            print(f"❌ Impossible de supprimer une configuration par défaut")
            return False
        
        filepath = os.path.join(self.config_dir, f"{config_name}.json")
        
        if not os.path.exists(filepath):
            print(f"❌ Configuration '{config_name}' non trouvée")
            return False
        
        try:
            os.remove(filepath)
            print(f"✅ Configuration '{config_name}' supprimée")
            return True
        
        except Exception as e:
            print(f"❌ Erreur lors de la suppression : {str(e)}")
            return False
    
    
    def export_config(self, config_name, export_path):
        """
        Exporter une configuration vers un fichier spécifique
        
        Args:
            config_name (str): Nom de la configuration
            export_path (str): Chemin d'export
        
        Returns:
            bool: True si succès, False sinon
        """
        config = self.load_config(config_name)
        
        if config is None:
            return False
        
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'name': config_name,
                    'exported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'config': config
                }, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Configuration exportée vers : {export_path}")
            return True
        
        except Exception as e:
            print(f"❌ Erreur lors de l'export : {str(e)}")
            return False
    
    
    def import_config(self, import_path, config_name=None):
        """
        Importer une configuration depuis un fichier
        
        Args:
            import_path (str): Chemin du fichier à importer
            config_name (str): Nom pour la configuration (optionnel)
        
        Returns:
            bool: True si succès, False sinon
        """
        if not os.path.exists(import_path):
            print(f"❌ Fichier non trouvé : {import_path}")
            return False
        
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Déterminer le nom
            if config_name is None:
                config_name = data.get('name', 'imported_config')
            
            # Extraire la config
            config_data = data.get('config', data)
            
            # Sauvegarder
            return self.save_config(config_name, config_data, overwrite=False)
        
        except Exception as e:
            print(f"❌ Erreur lors de l'import : {str(e)}")
            return False
    
    
    def get_config_summary(self):
        """
        Obtenir un résumé de toutes les configurations
        
        Returns:
            dict: Résumé des configurations
        """
        configs = self.list_configs()
        
        summary = {
            'total': len(configs),
            'default': sum(1 for c in configs.values() if c['type'] == 'default'),
            'custom': sum(1 for c in configs.values() if c['type'] == 'custom'),
            'configs': configs
        }
        
        return summary
    
    
    def print_config_details(self, config_name):
        """
        Afficher les détails d'une configuration
        
        Args:
            config_name (str): Nom de la configuration
        """
        config = self.load_config(config_name)
        
        if config is None:
            return
        
        print(f"\n{'='*60}")
        print(f"📋 CONFIGURATION : {config.get('name', config_name)}")
        print(f"{'='*60}")
        
        if 'description' in config:
            print(f"\n📝 Description : {config['description']}")
        
        print(f"\n⚙️  Options :")
        print(f"   • Valeurs manquantes : {config.get('missing_strategy', 'N/A')}")
        print(f"   • Valeurs aberrantes : {config.get('outliers_method', 'N/A')}")
        print(f"   • Normalisation : {'Oui' if config.get('normalize', False) else 'Non'}")
        
        if config.get('normalize', False):
            print(f"   • Méthode de normalisation : {config.get('normalize_method', 'N/A')}")
        
        print(f"   • Supprimer doublons : {'Oui' if config.get('remove_duplicates', True) else 'Non'}")
        print(f"\n{'='*60}\n")


# Fonctions utilitaires

def get_config_manager():
    """
    Obtenir une instance du gestionnaire de configuration
    
    Returns:
        ConfigManager: Instance du gestionnaire
    """
    return ConfigManager()


def quick_save_config(config_name, missing_strategy, outliers_method, normalize, normalize_method):
    """
    Fonction rapide pour sauvegarder une configuration
    
    Args:
        config_name (str): Nom de la configuration
        missing_strategy (str): Stratégie pour valeurs manquantes
        outliers_method (str): Méthode pour valeurs aberrantes
        normalize (bool): Normaliser ou non
        normalize_method (str): Méthode de normalisation
    
    Returns:
        bool: True si succès
    """
    manager = ConfigManager()
    
    config_data = {
        'description': f'Configuration personnalisée : {config_name}',
        'missing_strategy': missing_strategy,
        'outliers_method': outliers_method,
        'normalize': normalize,
        'normalize_method': normalize_method,
        'remove_duplicates': True
    }
    
    return manager.save_config(config_name, config_data)


def quick_load_config(config_name):
    """
    Fonction rapide pour charger une configuration
    
    Args:
        config_name (str): Nom de la configuration
    
    Returns:
        dict: Configuration ou None
    """
    manager = ConfigManager()
    return manager.load_config(config_name)