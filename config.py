# ============================================
# CONFIG.PY
# Configuration centralisée de l'application
# ============================================
"""
Configuration de l'application Flask.

Variables d'environnement requises (.env):
- SECRET_KEY : Clé secrète Flask (génération sécurisée recommandée)
- GOOGLE_CLIENT_ID : ID client OAuth Google
- GOOGLE_CLIENT_SECRET : Secret client OAuth Google
- DATABASE_URL : URL de la base de données (optionnel, défaut SQLite)
"""

import os
from datetime import timedelta
from pathlib import Path

# ============================================
# CHEMINS DE BASE
# ============================================

# Répertoire racine du projet
BASE_DIR = Path(__file__).resolve().parent

# ============================================
# CLASSE DE CONFIGURATION
# ============================================

class Config:
    """
    Configuration principale de l'application Flask
    """
    
    # ========================================
    # SÉCURITÉ
    # ========================================
    
    # Clé secrète Flask (pour sessions, CSRF, etc.)
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-CHANGE-ME-IN-PRODUCTION')
    
    # Protection CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Pas de limite de temps pour les tokens CSRF
    
    # Sessions sécurisées
    SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'  # HTTPS uniquement en prod
    SESSION_COOKIE_HTTPONLY = True  # Pas d'accès JavaScript
    SESSION_COOKIE_SAMESITE = 'Lax'  # Essentiel pour OAuth et CSRF
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Durée de session: 7 jours
    
    # ========================================
    # BASE DE DONNÉES
    # ========================================
    
    # URL de la base de données (SQLite par défaut)
    db_path = os.path.join(BASE_DIR, 'database', 'app.db')
    
    # Gestion robuste de l'URI de base de données
    _db_url = os.getenv('DATABASE_URL', '')
    if not _db_url or (_db_url.startswith('sqlite:///') and 'app.db' in _db_url and not _db_url.startswith('sqlite:////')):
        # Force absolute path for SQLite if default or relative path detected
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path
    else:
        SQLALCHEMY_DATABASE_URI = _db_url
    
    # Désactiver le suivi des modifications (économie mémoire)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Echo des requêtes SQL en développement
    SQLALCHEMY_ECHO = os.getenv('FLASK_ENV') == 'development'
    
    # Pool de connexions
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # ========================================
    # GOOGLE OAUTH 2.0
    # ========================================
    
    # Credentials OAuth Google
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', '')
    
    # URL de découverte OpenID Connect
    GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    
    # Scopes OAuth (informations demandées à Google)
    GOOGLE_OAUTH_SCOPES = ['openid', 'email', 'profile']
    
    # ========================================
    # UPLOAD DE FICHIERS
    # ========================================
    
    # Taille maximale des fichiers uploadés (16 MB)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Extensions de fichiers autorisées
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json', 'xml'}
    
    # Dossiers de stockage
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    PROCESSED_FOLDER = BASE_DIR / 'processed'
    REPORTS_FOLDER = BASE_DIR / 'reports_out'
    TEMP_FOLDER = BASE_DIR / 'temp'
    PLOTS_FOLDER = BASE_DIR / 'static' / 'plots'
    DATABASE_FOLDER = BASE_DIR / 'database'
    CONFIGS_FOLDER = BASE_DIR / 'configs'
    
    # Créer les dossiers automatiquement
    @staticmethod
    def init_folders():
        """Créer tous les dossiers nécessaires au démarrage"""
        folders = [
            Config.UPLOAD_FOLDER,
            Config.PROCESSED_FOLDER,
            Config.REPORTS_FOLDER,
            Config.TEMP_FOLDER,
            Config.PLOTS_FOLDER,
            Config.DATABASE_FOLDER,
            Config.CONFIGS_FOLDER
        ]
        
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
        
        print("✅ Tous les dossiers ont été créés/vérifiés")
    
    # ========================================
    # TRAITEMENT DES DONNÉES
    # ========================================
    
    # Nombre maximum de lignes pour l'aperçu des données
    DATA_PREVIEW_MAX_ROWS = 100
    
    # Nombre de colonnes maximum pour les graphiques
    PLOTS_MAX_COLUMNS = 4
    
    # DPI des graphiques générés
    PLOTS_DPI = 150
    
    # ========================================
    # LOGGING
    # ========================================
    
    # Niveau de log
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Fichier de log
    LOG_FILE = BASE_DIR / 'logs' / 'app.log'
    
    # Format des logs
    LOG_FORMAT = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    
    # ========================================
    # CACHE
    # ========================================
    
    # Type de cache (simple en développement)
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # ========================================
    # RATE LIMITING
    # ========================================
    
    # Limite de requêtes (pour éviter les abus)
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '200 per hour'
    
    # ========================================
    # CORS (Cross-Origin Resource Sharing)
    # ========================================
    
    # Origines autorisées pour les requêtes CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5000').split(',')
    
    # ========================================
    # EMAILS (OPTIONNEL - pour notifications futures)
    # ========================================
    
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@datacleaning.app')


# ============================================
# CONFIGURATIONS PAR ENVIRONNEMENT
# ============================================

class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False
    
    # Forcer HTTPS en production
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'
    
    # Clés secrètes obligatoires en production
    @staticmethod
    def validate():
        """Valider que toutes les variables critiques sont définies"""
        required_vars = [
            'SECRET_KEY',
            'GOOGLE_CLIENT_ID',
            'GOOGLE_CLIENT_SECRET'
        ]
        
        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            raise ValueError(
                f"❌ Variables d'environnement manquantes: {', '.join(missing)}\n"
                f"Veuillez les définir dans votre fichier .env"
            )


class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# ============================================
# SÉLECTION DE LA CONFIGURATION
# ============================================

config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """
    Récupérer la configuration selon l'environnement
    
    Returns:
        Config: Classe de configuration appropriée
    """
    env = os.getenv('FLASK_ENV', 'development')
    config = config_by_name.get(env, DevelopmentConfig)
    
    # Valider en production
    if env == 'production':
        ProductionConfig.validate()
    
    print(f"✅ Configuration chargée: {config.__name__}")
    return config


# ============================================
# UTILITAIRES
# ============================================

def print_config_summary(config):
    """
    Afficher un résumé de la configuration (pour debug)
    
    Args:
        config: Instance de configuration
    """
    print("\n" + "="*60)
    print("📋 RÉSUMÉ DE LA CONFIGURATION")
    print("="*60)
    print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"Debug: {config.DEBUG}")
    print(f"Database: {config.SQLALCHEMY_DATABASE_URI[:50]}...")
    print(f"Max Upload Size: {config.MAX_CONTENT_LENGTH / (1024*1024):.0f} MB")
    print(f"Allowed Extensions: {', '.join(config.ALLOWED_EXTENSIONS)}")
    print(f"Google OAuth: {'✅ Configuré' if config.GOOGLE_CLIENT_ID else '❌ Non configuré'}")
    print("="*60 + "\n")