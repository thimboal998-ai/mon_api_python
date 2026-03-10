# ============================================
# APP.PY - VERSION COMPLÈTE AVEC OAUTH
# Application Flask principale
# ============================================
"""
Data Cleaning Dashboard v3.0
Application Flask pour le nettoyage de données avec authentification Google OAuth

Features:
- Upload de fichiers (CSV, Excel, JSON, XML)
- Nettoyage automatique des colonnes index parasites
- Détection outliers (méthode IQR)
- Traitement valeurs manquantes
- Suppression doublons
- Génération graphiques
- Export (CSV, PDF, Excel)
- Authentification Google OAuth
- Sauvegarde historique en base de données
"""

from flask import Flask, request, render_template, send_file, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
import os
import json
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from datetime import datetime
import traceback
import hashlib

# Imports locaux
from config import get_config
from  extensions import db, migrate, login_manager, oauth
from models import User, CleaningHistory, FileMeta
from modules.data_processor import DataProcessor
from modules.config_manager import ConfigManager

# Charger les variables d'environnement
load_dotenv()

# ============================================
# CRÉATION DE L'APPLICATION
# ============================================

def init_db(app):
    """
    Initialiser la base de données
    
    Args:
        app: Instance Flask
    """
    with app.app_context():
        # Créer toutes les tables
        db.create_all()
        print("✅ Base de données initialisée")

def create_app():
    """
    Factory pattern pour créer l'application Flask
    
    Returns:
        Flask: Instance de l'application configurée
    """
    
    app = Flask(__name__)
    
    # Charger la configuration
    config = get_config()
    app.config.from_object(config)
    
    # Créer les dossiers nécessaires
    config.init_folders()
    
    # Initialiser les extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)
    
    # Créer les tables au démarrage (crucial pour Render)
    init_db(app)
    
    # Configuration OAuth Google
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
        client_kwargs={
            'scope': ' '.join(app.config['GOOGLE_OAUTH_SCOPES'])
        }
    )
    
    # Commande CLI pour initialiser la base de données
    @app.cli.command("init-db")
    def init_db_command():
        """Crée les tables de la base de données."""
        init_db(app)
        print("✅ Base de données initialisée avec succès.")

    print("\n" + "="*70)
    print("🚀 DATA CLEANING DASHBOARD v3.0")
    print("="*70)
    print(f"✅ Application initialisée")
    print(f"✅ Base de données: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
    # Configuration spécifique à l'environnement
    if app.config.get('ENV') == 'production' or os.getenv('FLASK_ENV') == 'production':
        # Appliquer ProxyFix pour Render/Proxy
        # Cela permet à Flask de savoir qu'il est derrière un proxy et de générer des URLs https
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        print("✅ ProxyFix activé (Production)")
    else:
        # En développement, autoriser le HTTP non sécurisé pour OAuth
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        print("✅ OAUTHLIB_INSECURE_TRANSPORT activé (Développement)")
    
    print(f"✅ Google OAuth: {'Configuré' if app.config['GOOGLE_CLIENT_ID'] else 'Non configuré'}")
    print("="*70 + "\n")
    
    return app


# Créer l'application
app = create_app()

# ============================================
# VARIABLES GLOBALES
# ============================================

current_processor = None
current_filename = None

# ============================================
# ENCODEUR JSON CUSTOM
# ============================================

class NpEncoder(json.JSONEncoder):
    """Encoder JSON pour gérer les types NumPy et pandas"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            # Vérifier si c'est un NaN numpy
            if np.isnan(obj):
                return None
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        if pd.isna(obj):
            return None
        return super(NpEncoder, self).default(obj)


# ============================================
# FLASK-LOGIN CONFIGURATION
# ============================================

@login_manager.user_loader
def load_user(user_id):
    """
    Callback pour Flask-Login : charger un utilisateur par son ID
    
    Args:
        user_id (str): ID de l'utilisateur
    
    Returns:
        User: Instance de l'utilisateur ou None
    """
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    """Handler pour les accès non autorisés"""
    return jsonify({
        'success': False,
        'error': 'Authentification requise'
    }), 401


# ============================================
# UTILITAIRES
# ============================================

def allowed_file(filename):
    """
    Vérifier si l'extension du fichier est autorisée
    
    Args:
        filename (str): Nom du fichier
    
    Returns:
        bool: True si autorisé
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def calculate_file_hash(filepath):
    """
    Calculer le hash SHA-256 d'un fichier
    
    Args:
        filepath (str): Chemin du fichier
    
    Returns:
        str: Hash hexadécimal
    """
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def clean_dataframe_columns(df):
    """
    Nettoyer le DataFrame en supprimant les colonnes index parasites
    
    Args:
        df (DataFrame): DataFrame à nettoyer
    
    Returns:
        DataFrame: DataFrame nettoyé sans colonnes index
    """
    import re
    
    print("\n🔍 NETTOYAGE DES COLONNES...")
    print(f"   Colonnes avant nettoyage : {list(df.columns)}")
    
    cols_to_drop = []
    
    for col in df.columns:
        col_lower = str(col).lower().strip()
        
        # Patterns de détection
        index_keywords = ['unnamed: 0', 'unnamed:0', 'unnamed_0', 'index', 
                         'level_0', 'level_1', 'id', 'rowid', 'row_id']
        
        # 1. Noms typiques
        if col_lower in index_keywords:
            cols_to_drop.append(col)
            print(f"   ❌ Colonne index détectée : '{col}'")
            continue
        
        # 2. Pattern "Unnamed: X"
        if re.match(r'^unnamed:?\s*\d+$', col_lower):
            cols_to_drop.append(col)
            print(f"   ❌ Colonne index détectée : '{col}'")
            continue
        
        # 3. Séquence numérique
        try:
            if df[col].dtype in ['int64', 'float64']:
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    expected_range = pd.Series(range(len(non_null)))
                    if non_null.reset_index(drop=True).equals(expected_range) or \
                       non_null.reset_index(drop=True).equals(expected_range + 1):
                        cols_to_drop.append(col)
                        print(f"   ❌ Colonne séquence numérique détectée : '{col}'")
        except:
            pass
    
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        print(f"   ✅ {len(cols_to_drop)} colonne(s) supprimée(s)")
    else:
        print("   ✅ Aucune colonne index détectée")
    
    print(f"   Colonnes après nettoyage : {list(df.columns)}")
    
    # Reset de l'index
    df = df.reset_index(drop=True)
    
    return df


def read_file(filepath):
    """
    Lire un fichier et retourner un DataFrame nettoyé
    
    Args:
        filepath (str): Chemin du fichier
    
    Returns:
        DataFrame: DataFrame nettoyé sans colonnes index
    """
    extension = filepath.rsplit('.', 1)[1].lower()
    
    try:
        df = None
        
        if extension == 'csv':
            print(f"\n📖 Lecture CSV : {filepath}")
            # Liste étendue de valeurs manquantes communes
            na_values = ['NA', 'n/a', 'na', '--', 'null', 'None', '', ' ']
            df = pd.read_csv(filepath, na_values=na_values)
            print(f"   Lignes : {len(df)}, Colonnes brutes : {len(df.columns)}")
            
        elif extension in ['xlsx', 'xls']:
            print(f"\n📖 Lecture Excel : {filepath}")
            na_values = ['NA', 'n/a', 'na', '--', 'null', 'None', '', ' ']
            df = pd.read_excel(filepath, na_values=na_values)
            print(f"   Lignes : {len(df)}, Colonnes brutes : {len(df.columns)}")
            
        elif extension == 'json':
            print(f"\n📖 Lecture JSON : {filepath}")
            with open(filepath, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                if isinstance(raw, list):
                    df = pd.DataFrame(raw)
                elif isinstance(raw, dict):
                     list_key = None
                     for k, v in raw.items():
                        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                            list_key = k
                            break
                     if list_key:
                        df = pd.DataFrame(raw[list_key])
                        for k, v in raw.items():
                            if k == list_key:
                                continue
                            if isinstance(v, dict):
                                for sub_k, sub_v in v.items():
                                    df[f"{k}.{sub_k}"] = sub_v
                            elif not isinstance(v, list):
                                df[k] = v
                     else:
                        df = pd.json_normalize(raw)
                else:
                    raise ValueError("Format JSON non supporté (ni liste, ni objet)")
                    print(f"   Lignes : {len(df)}, Colonnes brutes : {len(df.columns)}")
                
        elif extension == 'xml':
            print(f"\n📖 Lecture XML : {filepath}")
            df = pd.read_xml(filepath)
            
            # 🛡️ pd.read_xml ne supporte pas na_values. 
            # On doit remplacer manuellement les chaînes communes de valeurs manquantes.
            na_markers = ['NA', 'n/a', 'na', '--', 'null', 'None', '', ' ', 
                        'Missing', 'Unknown', 'inconnu', 'N/A', 'vide', 'Unknown', 
                        '?', 'NULL', '#N/A']
            for marker in na_markers:
                df = df.replace(marker, np.nan)
                
            print(f"   Lignes : {len(df)}, Colonnes brutes : {len(df.columns)}")
            
        else:
            raise ValueError(f"Format non supporté : {extension}")
        
        # Nettoyer les colonnes index
        df = clean_dataframe_columns(df)
        
        print(f"   ✅ DataFrame final : {len(df)} lignes × {len(df.columns)} colonnes")
        print(f"   📋 Colonnes finales : {list(df.columns)}")
        
        return df
        
    except Exception as e:
        raise Exception(f"Erreur lecture fichier : {str(e)}")


# ============================================
# ROUTES - PAGES
# ============================================

@app.route('/')
def index():
    """Page d'accueil / Dashboard principal"""
    print("\n" + "="*70)
    print("🏠 PAGE D'ACCUEIL")
    print("="*70)
    return render_template('dashboard.html')


# ============================================
# ROUTES - AUTHENTIFICATION
# ============================================

@app.route('/api/auth/check')
def check_auth():
    """
    Vérifier le statut d'authentification de l'utilisateur
    
    Returns:
        JSON: Statut d'authentification et infos utilisateur
    """
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        })
    else:
        return jsonify({
            'authenticated': False
        })


@app.route('/api/auth/google')
def google_login():
    """
    Initier le flux OAuth Google
    
    Returns:
        Redirect: Redirection vers la page de connexion Google
    """
    # Préférer l'URL configurée si présente (surtout pour le développement)
    config_redirect = app.config.get('GOOGLE_REDIRECT_URI')
    if config_redirect:
        redirect_uri = config_redirect
    else:
        redirect_uri = url_for('google_callback', _external=True)
    
    print(f"DEBUG: Redirect URI used: {redirect_uri}")
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/api/auth/google/callback')
def google_callback():
    """
    Callback OAuth Google après authentification
    
    Returns:
        Redirect: Redirection vers l'application
    """
    try:
        # Récupérer le token
        token = oauth.google.authorize_access_token()
        
        # Récupérer les infos utilisateur
        user_info = token.get('userinfo')
        
        if not user_info:
            user_info = oauth.google.get('userinfo').json()
        
        print(f"\n✅ Connexion OAuth réussie : {user_info.get('email')}")
        
        # Vérifier si l'utilisateur existe
        user = User.query.filter_by(email=user_info['email']).first()
        
        if not user:
            # Créer nouvel utilisateur
            user = User(
                google_id=user_info.get('sub'),
                email=user_info.get('email'),
                name=user_info.get('name'),
                given_name=user_info.get('given_name'),
                family_name=user_info.get('family_name'),
                picture=user_info.get('picture'),
                email_verified=user_info.get('email_verified', False),
                locale=user_info.get('locale', 'fr')
            )
            
            db.session.add(user)
            db.session.commit()
            
            print(f"   ✅ Nouvel utilisateur créé : {user.email} (ID: {user.id})")
        else:
            # Mettre à jour les infos
            user.name = user_info.get('name', user.name)
            user.given_name = user_info.get('given_name', user.given_name)
            user.family_name = user_info.get('family_name', user.family_name)
            user.picture = user_info.get('picture', user.picture)
            user.email_verified = user_info.get('email_verified', user.email_verified)
            
            db.session.commit()
            
            print(f"   ✅ Utilisateur existant connecté : {user.email} (ID: {user.id})")
        
        # Mettre à jour la date de dernière connexion
        user.update_last_login()
        
        # Connecter l'utilisateur
        login_user(user, remember=True)
        
        # Rediriger vers l'app avec succès
        return redirect('/?auth=success')
        
    except Exception as e:
        print(f"❌ Erreur OAuth : {str(e)}")
        traceback.print_exc()
        return redirect('/?auth=error')


@app.route('/api/auth/logout')
@login_required
def logout():
    """
    Déconnecter l'utilisateur
    
    Returns:
        JSON: Confirmation de déconnexion
    """
    user_email = current_user.email
    logout_user()
    
    print(f"✅ Déconnexion : {user_email}")
    
    return jsonify({
        'success': True,
        'message': 'Déconnecté avec succès'
    })


# ============================================
# ROUTES - UPLOAD & TRAITEMENT
# ============================================

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload et validation du fichier
    
    Returns:
        JSON: Résultat de l'upload
    """
    global current_filename, current_processor
    
    print("\n" + "="*70)
    print("📤 UPLOAD DE FICHIER")
    print("="*70)
    
    try:
        # 1. Vérifications de base
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nom de fichier vide'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Format non supporté. Formats acceptés : {", ".join(app.config["ALLOWED_EXTENSIONS"])}'
            }), 400
        
        # 2. Sauvegarder le fichier
        filename = secure_filename(file.filename)
        
        # Ajouter timestamp au nom pour éviter collisions
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}{ext}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        current_filename = filename
        
        # Calculer la taille du fichier
        file_size = os.path.getsize(filepath)
        
        print(f"✅ Fichier uploadé : {filename}")
        print(f"   Chemin : {filepath}")
        print(f"   Taille : {file_size / 1024:.2f} KB")
        
        # 3. Si l'utilisateur est connecté, enregistrer les métadonnées
        if current_user.is_authenticated:
            file_meta = FileMeta(
                user_id=current_user.id,
                filename=filename,
                original_filename=file.filename,
                file_path=filepath,
                file_size=file_size,
                file_extension=ext[1:],  # Sans le point
                mime_type=file.content_type,
                file_hash=calculate_file_hash(filepath),
                status='uploaded'
            )
            
            db.session.add(file_meta)
            db.session.commit()
            
            print(f"   ✅ Métadonnées enregistrées (ID: {file_meta.id})")
        
        # 4. Validation du contenu
        try:
            df = read_file(filepath)
            
            # Vérifier que le DataFrame n'est pas vide
            if len(df) == 0:
                return jsonify({
                    'success': False,
                    'error': 'Le fichier est vide (0 lignes)'
                }), 400
            
            if len(df.columns) == 0:
                return jsonify({
                    'success': False,
                    'error': 'Le fichier ne contient aucune colonne valide'
                }), 400
            
            print(f"   ✅ Validation réussie : {len(df)} lignes × {len(df.columns)} colonnes")
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Fichier invalide ou corrompu : {str(e)}'
            }), 400
        
        return jsonify({
            'success': True,
            'filename': filename,
            'message': f'Fichier uploadé avec succès ({len(df)} lignes, {len(df.columns)} colonnes)'
        })
    
    except Exception as e:
        print(f"❌ Erreur upload : {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/analyze', methods=['POST'])
def analyze_data():
    """
    Analyse des données uploadées
    
    Returns:
        JSON: Statistiques initiales
    """
    global current_processor, current_filename
    
    print("\n" + "="*70)
    print("🔍 ANALYSE DES DONNÉES")
    print("="*70)
    
    try:
        if not current_filename:
            return jsonify({'success': False, 'error': 'Aucun fichier uploadé'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], current_filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Fichier introuvable'}), 404
        
        # Lire et nettoyer le fichier
        df = read_file(filepath)
        
        # Créer le processeur
        current_processor = DataProcessor(df)
        
        # Obtenir les statistiques initiales
        stats = current_processor.get_initial_stats()
        
        print(f"\n✅ ANALYSE TERMINÉE")
        print(f"   Lignes : {stats['lignes_totales']}")
        print(f"   Colonnes : {stats['colonnes_totales']}")
        print(f"   Colonnes finales : {stats['colonnes']}")
        print(f"   Lignes avec valeurs manquantes : {stats.get('lignes_avec_valeurs_manquantes', 0)}")
        print(f"   Lignes avec outliers : {stats.get('lignes_avec_outliers', 0)}")
        print(f"   Doublons : {stats.get('doublons', 0)}")
        
        response_data = {
            'success': True,
            'stats': stats
        }
        
        return app.response_class(
            response=json.dumps(response_data, cls=NpEncoder),
            status=200,
            mimetype='application/json'
        )
    
    except Exception as e:
        print(f"❌ Erreur analyse : {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/clean', methods=['POST'])
@login_required
def clean_data():
    """
    Nettoyage des données avec les options choisies
    
    Returns:
        JSON: Statistiques finales et chemins des graphiques
    """
    global current_processor, current_filename
    
    print("\n" + "="*70)
    print("🧹 NETTOYAGE DES DONNÉES")
    print("="*70)
    
    try:
        if not current_processor:
            return jsonify({'success': False, 'error': 'Aucune analyse effectuée'}), 400
        
        # Démarrer le chronomètre
        start_time = datetime.now()
        
        # Récupérer les options
        options = request.get_json() or {}
        
        missing_strategy = options.get('missing_strategy', 'auto')
        outliers_method = options.get('outliers_method', 'cap')
        remove_duplicates = options.get('remove_duplicates', True)
        
        print(f"\n⚙️  OPTIONS DE NETTOYAGE :")
        print(f"   • Valeurs manquantes : {missing_strategy}")
        print(f"   • Valeurs aberrantes : {outliers_method}")
        print(f"   • Supprimer doublons : {remove_duplicates}")
        print(f"   • Utilisateur : {current_user.email}")
        
        # Statistiques AVANT nettoyage
        stats_before = current_processor.get_initial_stats()
        
        # Appliquer les traitements
        current_processor.handle_missing_values(strategy=missing_strategy)
        current_processor.handle_outliers(method=outliers_method)
        
        if remove_duplicates:
            current_processor.remove_duplicates()
        else:
            print("   ⏭️  Doublons conservés (option désactivée)")
        
        # Générer les graphiques
        plot_paths = current_processor.generate_plots()
        
        # Sauvegarder le CSV nettoyé
        base_name = current_filename.rsplit('.', 1)[0]
        csv_filename = f"cleaned_{base_name}.csv"
        csv_path = os.path.join(app.config['PROCESSED_FOLDER'], csv_filename)
        
        current_processor.export_to_csv(csv_path)
        
        # Récupérer les statistiques finales
        final_data = current_processor.get_final_stats()
        
        # Calculer le temps de traitement
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Sauvegarder dans l'historique
        cleaning_history = CleaningHistory(
            user_id=current_user.id,
            filename=current_filename,
            file_size=os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], current_filename)),
            file_extension=current_filename.rsplit('.', 1)[1],
            
            # Stats AVANT
            original_rows=stats_before['lignes_totales'],
            original_columns=stats_before['colonnes_totales'],
            
            # Stats APRÈS
            cleaned_rows=final_data['stats']['lignes_finales'],
            cleaned_columns=final_data['stats']['colonnes_finales'],
            
            # Problèmes
            missing_values_found=stats_before.get('lignes_avec_valeurs_manquantes', 0),
            missing_values_fixed=final_data['stats']['valeurs_manquantes_traitees'],
            
            outliers_found=stats_before.get('lignes_avec_outliers', 0),
            outliers_fixed=final_data['stats']['lignes_outliers_traitees'],
            
            duplicates_found=stats_before.get('doublons', 0),
            duplicates_removed=final_data['stats']['doublons_supprimes'],
            
            # Résultats
            quality_score=final_data['quality']['score'],
            transformations=len(final_data['transformation_history']),
            
            # Paths
            input_file_path=os.path.join(app.config['UPLOAD_FOLDER'], current_filename),
            output_file_path=csv_path,
            
            # Meta
            processing_time=processing_time,
            status='completed'
        )
        
        # Sauvegarder la config et les colonnes
        cleaning_history.set_cleaning_config(options)
        cleaning_history.set_columns_cleaned(final_data['colonnes'])
        
        db.session.add(cleaning_history)
        
        # Incrémenter les stats utilisateur
        current_user.increment_cleanings(rows_cleaned=final_data['stats']['lignes_finales'])
        
        db.session.commit()
        
        print(f"\n✅ NETTOYAGE TERMINÉ")
        print(f"   CSV exporté : {csv_filename}")
        print(f"   Graphiques générés : {len(plot_paths)}")
        print(f"   Score de qualité : {final_data['quality']['score']}%")
        print(f"   Colonnes finales : {final_data['colonnes']}")
        print(f"   Temps de traitement : {processing_time:.2f}s")
        print(f"   Historique ID : {cleaning_history.id}")
        
        response_data = {
            'success': True,
            'stats': final_data,
            'plot_paths': plot_paths,
            'csv_filename': csv_filename,
            'cleaning_id': cleaning_history.id
        }
        
        return app.response_class(
            response=json.dumps(response_data, cls=NpEncoder),
            status=200,
            mimetype='application/json'
        )
    
    except Exception as e:
        print(f"❌ Erreur nettoyage : {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# ROUTES - MODIFICATIONS MANUELLES
# ============================================

@app.route('/update_data', methods=['POST'])
@login_required
def update_data():
    """
    Met à jour le DataFrame avec les modifications manuelles de l'utilisateur
    """
    global current_processor, current_filename
    
    if not current_processor:
        return jsonify({'success': False, 'error': 'Aucun processeur actif'}), 400
        
    try:
        data = request.json.get('data')
        if not data:
            return jsonify({'success': False, 'error': 'Données manquantes'}), 400
            
        # Convertir les données JSON en DataFrame
        new_preview_df = pd.DataFrame(data)
        
        # S'assurer que le DataFrame actuel existe
        if current_processor.df is None:
            return jsonify({'success': False, 'error': 'DataFrame inexistant'}), 400
            
        # Nombre de lignes à mettre à jour (maximum 100 généralement)
        num_rows_to_update = len(new_preview_df)
        
        # Vérifier que les colonnes correspondent
        if list(new_preview_df.columns) != list(current_processor.df.columns):
            # Tenter de réordonner les colonnes si elles sont juste dans un ordre différent
            try:
                new_preview_df = new_preview_df[current_processor.df.columns]
            except:
                return jsonify({'success': False, 'error': 'Les colonnes ne correspondent pas'}), 400

        # Mettre à jour les N premières lignes du DataFrame original
        # On utilise .iloc pour cibler les positions exactes
        current_processor.df.iloc[0:num_rows_to_update] = new_preview_df.values
        
        # Recalculer les stats et la qualité après modification manuelle
        current_processor.calculate_quality_score()
        
        # Déterminer le nom du fichier CSV (doit correspondre à celui utilisé dans clean_data)
        # On essaie de retrouver le nom généré lors du dernier nettoyage
        csv_filename = f"cleaned_{os.path.splitext(current_filename)[0]}.csv"
        csv_path = os.path.join(app.config['PROCESSED_FOLDER'], csv_filename)
        
        # Exporter à nouveau le CSV pour que les téléchargements soient à jour
        current_processor.export_to_csv(csv_path)
        
        print(f"✅ Données mises à jour manuellement pour {current_filename}")
        
        # Préparer les stats pour le front-end (en nettoyant les NaN)
        final_stats = current_processor.get_final_stats()
        
        # Préparer la réponse
        response_data = {
            'success': True,
            'message': 'Données mises à jour avec succès',
            'stats': final_stats,
            'csv_filename': csv_filename
        }
        
        return app.response_class(
            response=json.dumps(response_data, cls=NpEncoder),
            status=200,
            mimetype='application/json'
        )
        
    except Exception as e:
        print(f"❌ Erreur mise à jour données : {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# ROUTES - TÉLÉCHARGEMENT
# ============================================

@app.route('/download/<file_type>/<filename>')
def download_file(file_type, filename):
    """
    Téléchargement des fichiers nettoyés (CSV ou PDF)
    
    Args:
        file_type (str): Type de fichier ('csv' ou 'pdf')
        filename (str): Nom du fichier
    
    Returns:
        File: Fichier à télécharger
    """
    print(f"\n📥 TÉLÉCHARGEMENT : {file_type} - {filename}")
    
    try:
        if file_type == 'csv':
            filepath = os.path.join(app.config['PROCESSED_FOLDER'], filename)
            mimetype = 'text/csv'
        
        elif file_type == 'pdf':
            if current_processor:
                from modules.pdf_generator import PDFReportGenerator
                
                pdf_path = os.path.join(app.config['REPORTS_FOLDER'], filename)
                
                # Générer le PDF
                generator = PDFReportGenerator(pdf_path)
                
                final_data = current_processor.get_final_stats()
                
                # Construire le PDF
                generator.add_header('Rapport de Nettoyage de Données')
                
                # 1. Données Nettoyées (DEMANDE UTILISATEUR : EN PREMIER)
                df = current_processor.get_dataframe()
                generator.add_data_table(df)
                
                # 2. Statistiques Descriptives
                if 'descriptive_stats' in final_data:
                    generator.add_descriptive_stats(final_data['descriptive_stats'])
                
                # 3. Résumé Exécutif (Manquant dans le code précédent)
                generator.add_section('📊 Résumé Exécutif')
                summary = f"Analyse de <b>{final_data['stats'].get('lignes_initiales', 0)} lignes</b>. " \
                          f"<b>{final_data['stats'].get('lignes_finales', 0)} lignes</b> conservées."
                from reportlab.platypus import Paragraph, Spacer
                from reportlab.lib.units import inch
                generator.elements.append(Paragraph(summary, generator.styles['CustomBody']))
                generator.elements.append(Spacer(1, 0.2*inch))
                
                # 4. Qualité et Stats
                generator.add_quality_score(final_data['stats'])
                
                generator.add_section('📈 Statistiques Détaillées')
                generator.add_statistics_table(final_data['stats'])
                
                if final_data['transformation_history']:
                    generator.add_transformation_history(final_data['transformation_history'])
                
                # Ajouter les graphiques
                if current_processor.plot_paths:
                    generator.add_page_break()
                    generator.add_section('📊 Visualisations')
                    
                    i = 1
                    for plot_name, plot_path in current_processor.plot_paths.items():
                        full_path = plot_path.replace('/static/', 'static/')
                        if os.path.exists(full_path):
                            graph_title = os.path.basename(full_path).replace('_', ' ').replace('.png', '').title()
                            generator.elements.append(Paragraph(f"<b>Graphique {i} : {graph_title}</b>", generator.styles['CustomBody']))
                            generator.add_image(full_path, width=6.5*inch)
                            
                            if i < len(current_processor.plot_paths):
                                generator.add_page_break()
                            i += 1
                
                generator.add_page_break()
                generator.add_recommendations(final_data['stats'])
                
                generator.finish()
                
                filepath = pdf_path
                mimetype = 'application/pdf'
            else:
                return jsonify({'error': 'Aucune analyse disponible'}), 400
        
        elif file_type == 'excel':
            if current_processor:
                from modules.excel_exporter import ExcelExporter
                
                excel_path = os.path.join(app.config['REPORTS_FOLDER'], filename)
                
                # Récupérer les données
                df = current_processor.get_dataframe()
                final_data = current_processor.get_final_stats()
                
                # Métadonnées
                metadata = {
                    'filename': filename.replace('rapport_', '').replace('.xlsx', '.csv'), # Tentative de reconstruction
                    'generated_by': 'Mon API Nettoyage'
                }
                
                # Initialiser et exporter
                exporter = ExcelExporter()
                exporter.export(
                    data=df,
                    stats=final_data,
                    charts=current_processor.plot_paths,
                    output_path=excel_path,
                    metadata=metadata
                )
                
                filepath = excel_path
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:
                return jsonify({'error': 'Aucune analyse disponible'}), 400

        else:
            return jsonify({'error': 'Type de fichier invalide'}), 400
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Fichier introuvable'}), 404
        
        print(f"✅ Envoi du fichier : {filepath}")
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
    
    except Exception as e:
        print(f"❌ Erreur téléchargement : {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ROUTES - HISTORIQUE
# ============================================

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur récupération historique : {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history')
@login_required
def get_history():
    """
    Récupérer l'historique des nettoyages de l'utilisateur
    
    Returns:
        JSON: Liste des nettoyages
    """
    try:
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Récupérer l'historique
        history_query = CleaningHistory.query.filter_by(
            user_id=current_user.id
        ).order_by(CleaningHistory.created_at.desc())
        
        # Paginer
        pagination = history_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        history_list = [item.to_dict() for item in pagination.items]
        
        response_data = {
            'success': True,
            'history': history_list,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }
        
        return app.response_class(
            response=json.dumps(response_data, cls=NpEncoder),
            status=200,
            mimetype='application/json'
        )
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur récupération historique : {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history/<int:cleaning_id>')
@login_required
def get_cleaning_details(cleaning_id):
    """
    Récupérer les détails d'un nettoyage pour restauration complète
    """
    global current_processor, current_filename
    
    try:
        cleaning = CleaningHistory.query.filter_by(
            id=cleaning_id,
            user_id=current_user.id
        ).first()
        
        if not cleaning:
            return jsonify({'success': False, 'error': 'Nettoyage introuvable'}), 404
        
        print(f"\n📂 RESTAURATION DE L'HISTORIQUE ID: {cleaning_id}")
        
        # 1. Charger les données originales pour les plots "Avant"
        if not os.path.exists(cleaning.input_file_path):
            return jsonify({'success': False, 'error': 'Fichier original introuvable sur le serveur'}), 404
            
        df_original = read_file(cleaning.input_file_path)
        
        # 2. Re-initialiser le processeur avec les données originales
        current_processor = DataProcessor(df_original)
        current_filename = cleaning.filename
        
        # 3. Charger les données nettoyées pour les plots "Après"
        if not os.path.exists(cleaning.output_file_path):
            # Si le fichier nettoyé n'existe plus, on essaie de le régénérer avec la config d'origine
            print("   ⚠️  Fichier nettoyé manquant, régénération...")
            config = cleaning.get_cleaning_config()
            current_processor.handle_missing_values(strategy=config.get('missing_strategy', 'auto'))
            current_processor.handle_outliers(method=config.get('outliers_method', 'cap'))
            if config.get('remove_duplicates', True):
                current_processor.remove_duplicates()
        else:
            # Charger les données déjà nettoyées
            df_cleaned = pd.read_csv(cleaning.output_file_path)
            current_processor.df = df_cleaned
            
        # 4. Régénérer les graphiques
        plot_paths = current_processor.generate_plots()
        
        # 5. Préparer les stats finales pour le dashboard
        final_data = current_processor.get_final_stats()
        
        # S'assurer que le nom du fichier CSV est bien celui de l'historique
        csv_filename = os.path.basename(cleaning.output_file_path)
        
        return app.response_class(
            response=json.dumps({
                'success': True,
                'stats': final_data,
                'plot_paths': plot_paths,
                'csv_filename': csv_filename,
                'filename': cleaning.filename,
                'cleaning_id': cleaning_id
            }, cls=NpEncoder),
            status=200,
            mimetype='application/json'
        )
    
    except Exception as e:
        print(f"❌ Erreur restauration historique : {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# ROUTES - STATISTIQUES UTILISATEUR
# ============================================

@app.route('/api/user/stats')
@login_required
def get_user_stats():
    """
    Récupérer les statistiques de l'utilisateur
    
    Returns:
        JSON: Statistiques globales
    """
    try:
        from models import get_user_stats
        
        stats = get_user_stats(current_user.id)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        print(f"❌ Erreur récupération stats : {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# ROUTES - RESET
# ============================================

@app.route('/reset', methods=['POST'])
def reset_app():
    """Réinitialiser l'application"""
    global current_processor, current_filename
    
    print("\n" + "="*70)
    print("🔄 RÉINITIALISATION")
    print("="*70)
    
    try:
        current_processor = None
        current_filename = None
        
        print("✅ Application réinitialisée")
        
        return jsonify({
            'success': True,
            'message': 'Application réinitialisée'
        })
    
    except Exception as e:
        print(f"❌ Erreur : {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# GESTION DES ERREURS
# ============================================

@app.errorhandler(404)
def not_found(error):
    """Erreur 404"""
    return jsonify({'error': 'Route non trouvée'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Erreur 500"""
    db.session.rollback()
    return jsonify({'error': 'Erreur serveur interne'}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Erreur 413 - Fichier trop volumineux"""
    return jsonify({
        'error': f'Fichier trop volumineux. Maximum : {app.config["MAX_CONTENT_LENGTH"] / (1024*1024):.0f} MB'
    }), 413

# ============================================
# LANCEMENT DU SERVEUR
# ============================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 DATA CLEANING DASHBOARD v3.0")
    print("="*70)
    print("\n🌐 URL : http://localhost:5000")
    print("\n📁 Dossiers :")
    print(f"   • Uploads    : {app.config['UPLOAD_FOLDER']}")
    print(f"   • Processed  : {app.config['PROCESSED_FOLDER']}")
    print(f"   • Reports    : {app.config['REPORTS_FOLDER']}")
    print(f"   • Plots      : {app.config['PLOTS_FOLDER']}")
    print(f"   • Database   : {app.config['DATABASE_FOLDER']}")
    print("\n✨ FONCTIONNALITÉS :")
    print("   ✅ Google OAuth 2.0")
    print("   ✅ Sauvegarde historique en DB")
    print("   ✅ Détection colonnes index parasites")
    print("   ✅ Nettoyage intelligent (IQR)")
    print("   ✅ Export CSV/PDF")
    print("\n⚠️  Arrêt : CTRL+C\n")
    print("="*70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)