# ============================================
# MODELS.PY
# Modèles de base de données SQLAlchemy
# ============================================
"""
Définition des modèles de données pour l'application.

Modèles:
- User : Utilisateurs authentifiés via Google OAuth
- CleaningHistory : Historique des nettoyages effectués
- FileMeta : Métadonnées des fichiers uploadés
"""

from datetime import datetime
from flask_login import UserMixin
from extensions import db
import json


# ============================================
# MODÈLE: USER
# ============================================

class User(UserMixin, db.Model):
    """
    Modèle utilisateur pour l'authentification Google OAuth
    
    Hérite de UserMixin pour Flask-Login (méthodes is_authenticated, etc.)
    """
    
    __tablename__ = 'users'
    
    # ========================================
    # COLONNES
    # ========================================
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True)
    
    # Informations Google
    google_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=True)
    given_name = db.Column(db.String(100), nullable=True)  # Prénom
    family_name = db.Column(db.String(100), nullable=True)  # Nom de famille
    picture = db.Column(db.String(500), nullable=True)  # URL photo de profil
    
    # Informations de compte
    email_verified = db.Column(db.Boolean, default=False)
    locale = db.Column(db.String(10), default='fr')  # Langue préférée
    
    # Statistiques utilisateur
    total_cleanings = db.Column(db.Integer, default=0)  # Nombre de nettoyages
    total_rows_cleaned = db.Column(db.Integer, default=0)  # Total de lignes nettoyées
    
    # Préférences utilisateur (JSON)
    preferences = db.Column(db.Text, default='{}')  # Stockage JSON des préférences
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Statut du compte
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    # ========================================
    # RELATIONS
    # ========================================
    
    # Relation one-to-many avec CleaningHistory
    cleaning_history = db.relationship(
        'CleaningHistory',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    # Relation one-to-many avec FileMeta
    files = db.relationship(
        'FileMeta',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    # ========================================
    # MÉTHODES
    # ========================================
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self):
        """
        Convertir l'utilisateur en dictionnaire (pour JSON)
        
        Returns:
            dict: Représentation JSON de l'utilisateur
        """
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'given_name': self.given_name,
            'family_name': self.family_name,
            'picture': self.picture,
            'total_cleanings': self.total_cleanings,
            'total_rows_cleaned': self.total_rows_cleaned,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def get_preferences(self):
        """
        Récupérer les préférences utilisateur
        
        Returns:
            dict: Préférences utilisateur
        """
        try:
            return json.loads(self.preferences) if self.preferences else {}
        except:
            return {}
    
    def set_preferences(self, prefs):
        """
        Définir les préférences utilisateur
        
        Args:
            prefs (dict): Nouvelles préférences
        """
        self.preferences = json.dumps(prefs)
    
    def update_last_login(self):
        """Mettre à jour la date de dernière connexion"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def increment_cleanings(self, rows_cleaned=0):
        """
        Incrémenter les statistiques de nettoyage
        
        Args:
            rows_cleaned (int): Nombre de lignes nettoyées
        """
        self.total_cleanings += 1
        self.total_rows_cleaned += rows_cleaned
        db.session.commit()


# ============================================
# MODÈLE: CLEANING HISTORY
# ============================================

class CleaningHistory(db.Model):
    """
    Historique des opérations de nettoyage de données
    """
    
    __tablename__ = 'cleaning_history'
    
    # ========================================
    # COLONNES
    # ========================================
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True)
    
    # Clé étrangère vers User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Informations du fichier
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # Taille en bytes
    file_extension = db.Column(db.String(10), nullable=True)
    
    # Statistiques AVANT nettoyage
    original_rows = db.Column(db.Integer, nullable=False)
    original_columns = db.Column(db.Integer, nullable=False)
    
    # Statistiques APRÈS nettoyage
    cleaned_rows = db.Column(db.Integer, nullable=False)
    cleaned_columns = db.Column(db.Integer, nullable=False)
    
    # Détails des problèmes détectés
    missing_values_found = db.Column(db.Integer, default=0)
    missing_values_fixed = db.Column(db.Integer, default=0)
    
    outliers_found = db.Column(db.Integer, default=0)
    outliers_fixed = db.Column(db.Integer, default=0)
    
    duplicates_found = db.Column(db.Integer, default=0)
    duplicates_removed = db.Column(db.Integer, default=0)
    
    # Configuration de nettoyage utilisée (JSON)
    cleaning_config = db.Column(db.Text, nullable=True)  # JSON des options
    
    # Résultats
    quality_score = db.Column(db.Float, default=0.0)  # Score de 0 à 100
    transformations = db.Column(db.Integer, default=0)  # Nombre de transformations
    
    # Colonnes nettoyées (liste JSON)
    columns_cleaned = db.Column(db.Text, nullable=True)  # Liste des colonnes finales
    
    # Chemins des fichiers
    input_file_path = db.Column(db.String(500), nullable=True)
    output_file_path = db.Column(db.String(500), nullable=True)
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    processing_time = db.Column(db.Float, nullable=True)  # Temps de traitement en secondes
    
    # Statut
    status = db.Column(db.String(20), default='completed')  # completed, failed, pending
    error_message = db.Column(db.Text, nullable=True)
    
    # ========================================
    # MÉTHODES
    # ========================================
    
    def __repr__(self):
        return f'<CleaningHistory {self.filename} by User {self.user_id}>'
    
    def to_dict(self):
        """
        Convertir en dictionnaire (pour JSON)
        
        Returns:
            dict: Représentation JSON de l'historique
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'file_size': self.file_size,
            'file_extension': self.file_extension,
            
            # Stats avant
            'original_rows': self.original_rows,
            'original_columns': self.original_columns,
            
            # Stats après
            'cleaned_rows': self.cleaned_rows,
            'cleaned_columns': self.cleaned_columns,
            
            # Problèmes
            'missing_values': {
                'found': self.missing_values_found,
                'fixed': self.missing_values_fixed
            },
            'outliers': {
                'found': self.outliers_found,
                'fixed': self.outliers_fixed
            },
            'duplicates': {
                'found': self.duplicates_found,
                'removed': self.duplicates_removed
            },
            
            # Résultats
            'quality_score': self.quality_score,
            'transformations': self.transformations,
            'processing_time': self.processing_time,
            
            # Config
            'cleaning_config': json.loads(self.cleaning_config) if self.cleaning_config else {},
            'columns_cleaned': json.loads(self.columns_cleaned) if self.columns_cleaned else [],
            
            # Meta
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status
        }
    
    def get_cleaning_config(self):
        """Récupérer la configuration de nettoyage"""
        try:
            return json.loads(self.cleaning_config) if self.cleaning_config else {}
        except:
            return {}
    
    def set_cleaning_config(self, config):
        """Définir la configuration de nettoyage"""
        self.cleaning_config = json.dumps(config)
    
    def get_columns_cleaned(self):
        """Récupérer la liste des colonnes nettoyées"""
        try:
            return json.loads(self.columns_cleaned) if self.columns_cleaned else []
        except:
            return []
    
    def set_columns_cleaned(self, columns):
        """Définir la liste des colonnes nettoyées"""
        self.columns_cleaned = json.dumps(columns)
    
    def calculate_reduction_percentage(self):
        """
        Calculer le pourcentage de réduction des lignes
        
        Returns:
            float: Pourcentage de lignes supprimées
        """
        if self.original_rows == 0:
            return 0.0
        
        removed = self.original_rows - self.cleaned_rows
        return round((removed / self.original_rows) * 100, 2)


# ============================================
# MODÈLE: FILE META
# ============================================

class FileMeta(db.Model):
    """
    Métadonnées des fichiers uploadés par les utilisateurs
    """
    
    __tablename__ = 'file_meta'
    
    # ========================================
    # COLONNES
    # ========================================
    
    # Clé primaire
    id = db.Column(db.Integer, primary_key=True)
    
    # Clé étrangère vers User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Informations du fichier
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Taille en bytes
    file_extension = db.Column(db.String(10), nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    
    # Hash du fichier (pour détecter les doublons)
    file_hash = db.Column(db.String(64), nullable=True, index=True)
    
    # Statut
    status = db.Column(db.String(20), default='uploaded')  # uploaded, processing, processed, error
    
    # Métadonnées
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Lien vers l'historique de nettoyage (optionnel)
    cleaning_history_id = db.Column(db.Integer, db.ForeignKey('cleaning_history.id'), nullable=True)
    
    # ========================================
    # MÉTHODES
    # ========================================
    
    def __repr__(self):
        return f'<FileMeta {self.original_filename}>'
    
    def to_dict(self):
        """
        Convertir en dictionnaire (pour JSON)
        
        Returns:
            dict: Représentation JSON du fichier
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_extension': self.file_extension,
            'mime_type': self.mime_type,
            'status': self.status,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }
    
    def get_file_size_human(self):
        """
        Obtenir la taille du fichier en format lisible
        
        Returns:
            str: Taille formatée (ex: "2.5 MB")
        """
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


# ============================================
# FONCTIONS UTILITAIRES
# ============================================

def get_user_stats(user_id):
    """
    Récupérer les statistiques d'un utilisateur
    
    Args:
        user_id (int): ID de l'utilisateur
    
    Returns:
        dict: Statistiques de l'utilisateur
    """
    user = User.query.get(user_id)
    if not user:
        return None
    
    total_cleanings = CleaningHistory.query.filter_by(user_id=user_id).count()
    total_files = FileMeta.query.filter_by(user_id=user_id).count()
    
    # Calculer les moyennes
    avg_quality = db.session.query(
        db.func.avg(CleaningHistory.quality_score)
    ).filter_by(user_id=user_id).scalar() or 0
    
    return {
        'total_cleanings': total_cleanings,
        'total_files': total_files,
        'total_rows_cleaned': user.total_rows_cleaned,
        'average_quality_score': round(avg_quality, 2)
    }


def cleanup_old_files(days=30):
    """
    Nettoyer les fichiers plus anciens que X jours
    
    Args:
        days (int): Nombre de jours
    
    Returns:
        int: Nombre de fichiers supprimés
    """
    from datetime import timedelta
    import os
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    old_files = FileMeta.query.filter(
        FileMeta.uploaded_at < cutoff_date
    ).all()
    
    count = 0
    for file_meta in old_files:
        # Supprimer le fichier physique
        try:
            if os.path.exists(file_meta.file_path):
                os.remove(file_meta.file_path)
        except:
            pass
        
        # Supprimer l'enregistrement
        db.session.delete(file_meta)
        count += 1
    
    db.session.commit()
    
    print(f"✅ {count} fichiers anciens supprimés")
    return count