1. Installer Python
Télécharger Python 3 depuis https://www.python.org

Ouvrir le projet
Dézipper le projet Ouvrir le dossier Shift + clic droit → Ouvrir le cmd ici

Créer l’environnement virtuel python -m venv venv

Activer l’environnement virtuel venv\Scripts\activate

Installer les dépendances pip install matplotlib scikit-learn seaborn reportlab

Lancer l’application python app.py

-----------------OU vous pouvez utiliser ----------------------- pip install Flask Flask-SQLAlchemy Flask-Migrate Flask-Login Authlib requests python-dotenv gunicorn pandas numpy scikit-learn openpyxl XlsxWriter lxml reportlab matplotlib seaborn 

💡 Rappels utiles : La méthode recommandée : Au lieu de taper cette longue commande, vous pouvez simplement lancer celle-ci depuis le dossier de votre projet python -m venv venv source venv/bin/activate # Sur Mac/Linux

Puis lancez l'installation
pip install -r requirements.txt
