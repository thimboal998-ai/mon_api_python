# ============================================
# EXTENSIONS.PY
# Centralisation des extensions Flask
# ============================================
"""
Ce fichier centralise toutes les extensions Flask pour éviter
les imports circulaires et faciliter l'initialisation de l'application.

Extensions incluses:
- SQLAlchemy : ORM pour la base de données
- Flask-Migrate : Gestion des migrations de schéma
- Flask-Login : Gestion des sessions utilisateur
- Authlib OAuth : Authentification Google OAuth 2.0
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth

# ============================================
# INITIALISATION DES EXTENSIONS
# ============================================

# SQLAlchemy - ORM pour la base de données
db = SQLAlchemy()

# Flask-Migrate - Gestion des migrations
migrate = Migrate()

# Flask-Login - Gestion des sessions utilisateur
login_manager = LoginManager()

# Configuration du login manager
login_manager.login_view = 'index'  # Redirection si non connecté
login_manager.login_message = None  # Pas de message flash par défaut
login_manager.session_protection = 'strong'  # Protection des sessions

# Authlib OAuth - Authentification Google
oauth = OAuth()

print("✅ Extensions Flask initialisées")