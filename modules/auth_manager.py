# ============================================
# AUTH_MANAGER.PY
# Gestion de l'authentification et des utilisateurs
# ============================================
"""
Module de gestion de l'authentification.

Fonctionnalités:
- Validation des tokens OAuth
- Gestion des sessions utilisateur
- Vérification des permissions
- Hashing de mots de passe (pour extension future)
- Rate limiting par utilisateur
"""

from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from flask_login import current_user
import hashlib
import secrets
import re


class AuthManager:
    """
    Gestionnaire d'authentification et d'autorisation
    """
    
    def __init__(self, app=None):
        """
        Initialisation du gestionnaire d'authentification
        
        Args:
            app: Instance Flask (optionnel)
        """
        self.app = app
        self.rate_limits = {}  # Cache des rate limits en mémoire
        
        if app is not None:
            self.init_app(app)
        
        print("🔐 AuthManager initialisé")
    
    
    def init_app(self, app):
        """
        Initialiser avec l'application Flask
        
        Args:
            app: Instance Flask
        """
        self.app = app
        
        # Configuration par défaut
        app.config.setdefault('AUTH_TOKEN_EXPIRY', 3600)  # 1 heure
        app.config.setdefault('AUTH_MAX_LOGIN_ATTEMPTS', 5)
        app.config.setdefault('AUTH_LOCKOUT_DURATION', 900)  # 15 minutes
        app.config.setdefault('AUTH_SESSION_LIFETIME', 604800)  # 7 jours
    
    
    # ========================================
    # VALIDATION
    # ========================================
    
    @staticmethod
    def validate_email(email):
        """
        Valider un email
        
        Args:
            email (str): Email à valider
        
        Returns:
            bool: True si valide
        """
        if not email:
            return False
        
        # Pattern email RFC 5322 simplifié
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        return re.match(pattern, email) is not None
    
    
    @staticmethod
    def validate_password(password):
        """
        Valider un mot de passe (pour extension future)
        
        Critères:
        - Minimum 8 caractères
        - Au moins une majuscule
        - Au moins une minuscule
        - Au moins un chiffre
        - Au moins un caractère spécial
        
        Args:
            password (str): Mot de passe à valider
        
        Returns:
            tuple: (bool, str) - (valide, message d'erreur)
        """
        if not password:
            return False, "Le mot de passe est requis"
        
        if len(password) < 8:
            return False, "Le mot de passe doit contenir au moins 8 caractères"
        
        if not re.search(r'[A-Z]', password):
            return False, "Le mot de passe doit contenir au moins une majuscule"
        
        if not re.search(r'[a-z]', password):
            return False, "Le mot de passe doit contenir au moins une minuscule"
        
        if not re.search(r'\d', password):
            return False, "Le mot de passe doit contenir au moins un chiffre"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Le mot de passe doit contenir au moins un caractère spécial"
        
        return True, "Mot de passe valide"
    
    
    @staticmethod
    def hash_password(password):
        """
        Hasher un mot de passe avec SHA-256 + salt
        (Pour extension future - utiliser bcrypt en production)
        
        Args:
            password (str): Mot de passe en clair
        
        Returns:
            str: Hash du mot de passe
        """
        # Générer un salt aléatoire
        salt = secrets.token_hex(16)
        
        # Hasher avec SHA-256
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        
        # Retourner salt + hash
        return f"{salt}${hashed}"
    
    
    @staticmethod
    def verify_password(password, hashed_password):
        """
        Vérifier un mot de passe
        
        Args:
            password (str): Mot de passe en clair
            hashed_password (str): Hash à vérifier
        
        Returns:
            bool: True si correspond
        """
        try:
            salt, stored_hash = hashed_password.split('$')
            
            # Recalculer le hash
            computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            
            # Comparaison sécurisée
            return secrets.compare_digest(computed_hash, stored_hash)
        
        except:
            return False
    
    
    # ========================================
    # TOKENS & SESSIONS
    # ========================================
    
    @staticmethod
    def generate_token(length=32):
        """
        Générer un token aléatoire sécurisé
        
        Args:
            length (int): Longueur du token
        
        Returns:
            str: Token hexadécimal
        """
        return secrets.token_urlsafe(length)
    
    
    @staticmethod
    def generate_api_key(user_id):
        """
        Générer une clé API pour un utilisateur
        
        Args:
            user_id (int): ID de l'utilisateur
        
        Returns:
            str: Clé API unique
        """
        # Timestamp + user_id + random
        timestamp = datetime.utcnow().isoformat()
        random_part = secrets.token_hex(16)
        
        # Hash SHA-256
        api_key = hashlib.sha256(
            f"{user_id}:{timestamp}:{random_part}".encode()
        ).hexdigest()
        
        return f"dcd_{api_key}"  # Préfixe "dcd" = Data Cleaning Dashboard
    
    
    # ========================================
    # PERMISSIONS & RÔLES
    # ========================================
    
    @staticmethod
    def check_permission(user, permission):
        """
        Vérifier si un utilisateur a une permission
        
        Args:
            user: Instance User
            permission (str): Nom de la permission
        
        Returns:
            bool: True si autorisé
        """
        # Admin a toutes les permissions
        if user.is_admin:
            return True
        
        # Mapping des permissions
        permissions_map = {
            'upload_file': True,  # Tous les utilisateurs
            'clean_data': True,
            'export_csv': True,
            'export_pdf': True,
            'export_excel': True,
            'view_history': True,
            'delete_history': True,
            'manage_users': lambda u: u.is_admin,
            'view_all_cleanings': lambda u: u.is_admin,
            'manage_settings': lambda u: u.is_admin
        }
        
        perm_check = permissions_map.get(permission, False)
        
        if callable(perm_check):
            return perm_check(user)
        
        return perm_check
    
    
    @staticmethod
    def require_permission(permission):
        """
        Décorateur pour vérifier une permission
        
        Args:
            permission (str): Nom de la permission requise
        
        Returns:
            function: Décorateur
        
        Usage:
            @require_permission('manage_users')
            def admin_route():
                pass
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated:
                    return jsonify({
                        'success': False,
                        'error': 'Authentification requise'
                    }), 401
                
                if not AuthManager.check_permission(current_user, permission):
                    return jsonify({
                        'success': False,
                        'error': 'Permission refusée'
                    }), 403
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    
    # ========================================
    # RATE LIMITING
    # ========================================
    
    def check_rate_limit(self, user_id, action, limit=10, window=60):
        """
        Vérifier le rate limit pour un utilisateur
        
        Args:
            user_id (int): ID de l'utilisateur
            action (str): Type d'action
            limit (int): Nombre max d'actions
            window (int): Fenêtre de temps en secondes
        
        Returns:
            tuple: (bool, int) - (autorisé, tentatives restantes)
        """
        now = datetime.utcnow()
        key = f"{user_id}:{action}"
        
        # Initialiser si pas encore de données
        if key not in self.rate_limits:
            self.rate_limits[key] = []
        
        # Nettoyer les anciennes tentatives
        cutoff = now - timedelta(seconds=window)
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key]
            if timestamp > cutoff
        ]
        
        # Vérifier le nombre de tentatives
        attempts = len(self.rate_limits[key])
        
        if attempts >= limit:
            return False, 0
        
        # Ajouter cette tentative
        self.rate_limits[key].append(now)
        
        return True, limit - attempts - 1
    
    
    @staticmethod
    def rate_limit(limit=10, window=60, action='default'):
        """
        Décorateur pour limiter le taux de requêtes
        
        Args:
            limit (int): Nombre max de requêtes
            window (int): Fenêtre en secondes
            action (str): Nom de l'action
        
        Returns:
            function: Décorateur
        
        Usage:
            @rate_limit(limit=5, window=60, action='upload')
            def upload_route():
                pass
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not current_user.is_authenticated:
                    return jsonify({
                        'success': False,
                        'error': 'Authentification requise'
                    }), 401
                
                manager = AuthManager()
                allowed, remaining = manager.check_rate_limit(
                    current_user.id,
                    action,
                    limit,
                    window
                )
                
                if not allowed:
                    return jsonify({
                        'success': False,
                        'error': f'Limite de {limit} requêtes par {window}s dépassée',
                        'retry_after': window
                    }), 429
                
                # Ajouter les headers de rate limit
                response = f(*args, **kwargs)
                
                if isinstance(response, tuple):
                    response_obj, status_code = response
                else:
                    response_obj = response
                    status_code = 200
                
                # Ajouter les headers si c'est une Response Flask
                if hasattr(response_obj, 'headers'):
                    response_obj.headers['X-RateLimit-Limit'] = str(limit)
                    response_obj.headers['X-RateLimit-Remaining'] = str(remaining)
                    response_obj.headers['X-RateLimit-Reset'] = str(int((datetime.utcnow() + timedelta(seconds=window)).timestamp()))
                
                return response_obj, status_code
            
            return decorated_function
        return decorator
    
    
    # ========================================
    # SÉCURITÉ
    # ========================================
    
    @staticmethod
    def sanitize_input(text, max_length=255):
        """
        Nettoyer et sécuriser une entrée utilisateur
        
        Args:
            text (str): Texte à nettoyer
            max_length (int): Longueur maximale
        
        Returns:
            str: Texte nettoyé
        """
        if not text:
            return ""
        
        # Convertir en string
        text = str(text)
        
        # Supprimer les espaces au début/fin
        text = text.strip()
        
        # Limiter la longueur
        text = text[:max_length]
        
        # Supprimer les caractères dangereux
        # (basique - utiliser bleach ou html.escape en production)
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        return text
    
    
    @staticmethod
    def is_safe_redirect(url):
        """
        Vérifier si une URL de redirection est sûre
        
        Args:
            url (str): URL à vérifier
        
        Returns:
            bool: True si sûre
        """
        if not url:
            return False
        
        # Autoriser seulement les URLs relatives
        if url.startswith('/'):
            return True
        
        # Bloquer les URLs externes
        return False
    
    
    @staticmethod
    def get_client_ip():
        """
        Obtenir l'IP réelle du client (même derrière un proxy)
        
        Returns:
            str: Adresse IP
        """
        # Vérifier les headers de proxy
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        
        if request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        
        return request.remote_addr
    
    
    # ========================================
    # LOGGING
    # ========================================
    
    @staticmethod
    def log_auth_event(user_id, event_type, details=None):
        """
        Logger un événement d'authentification
        
        Args:
            user_id (int): ID de l'utilisateur
            event_type (str): Type d'événement (login, logout, failed_login, etc.)
            details (dict): Détails supplémentaires
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'event_type': event_type,
            'ip': AuthManager.get_client_ip(),
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'details': details or {}
        }
        
        print(f"🔐 Auth Event: {event_type} - User {user_id} - IP {log_entry['ip']}")
        
        # En production, écrire dans un fichier de log ou une base de données
        # logger.info(json.dumps(log_entry))
    
    
    # ========================================
    # UTILITAIRES
    # ========================================
    
    @staticmethod
    def get_user_display_name(user):
        """
        Obtenir le nom d'affichage d'un utilisateur
        
        Args:
            user: Instance User
        
        Returns:
            str: Nom d'affichage
        """
        if user.name:
            return user.name
        
        if user.given_name and user.family_name:
            return f"{user.given_name} {user.family_name}"
        
        if user.email:
            return user.email.split('@')[0]
        
        return f"User {user.id}"
    
    
    @staticmethod
    def format_last_login(last_login):
        """
        Formater la date de dernière connexion
        
        Args:
            last_login (datetime): Date de dernière connexion
        
        Returns:
            str: Date formatée (ex: "Il y a 2 heures")
        """
        if not last_login:
            return "Jamais"
        
        now = datetime.utcnow()
        delta = now - last_login
        
        seconds = delta.total_seconds()
        
        if seconds < 60:
            return "À l'instant"
        
        minutes = int(seconds / 60)
        if minutes < 60:
            return f"Il y a {minutes} minute{'s' if minutes > 1 else ''}"
        
        hours = int(minutes / 60)
        if hours < 24:
            return f"Il y a {hours} heure{'s' if hours > 1 else ''}"
        
        days = int(hours / 24)
        if days < 30:
            return f"Il y a {days} jour{'s' if days > 1 else ''}"
        
        months = int(days / 30)
        if months < 12:
            return f"Il y a {months} mois"
        
        years = int(days / 365)
        return f"Il y a {years} an{'s' if years > 1 else ''}"


# ============================================
# FONCTIONS UTILITAIRES GLOBALES
# ============================================

def require_auth(f):
    """
    Décorateur simple pour exiger l'authentification
    
    Usage:
        @require_auth
        def protected_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'Authentification requise'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_admin(f):
    """
    Décorateur pour exiger les droits admin
    
    Usage:
        @require_admin
        def admin_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'Authentification requise'
            }), 401
        
        if not current_user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Droits administrateur requis'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


print("✅ AuthManager chargé avec succès")