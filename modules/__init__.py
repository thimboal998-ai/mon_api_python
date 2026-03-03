# ============================================
# __INIT__.PY - MODULES PACKAGE
# Initialisation du package modules
# ============================================

"""
Package modules pour l'application de nettoyage de données.

Ce package contient tous les modules métier de l'application :

Modules existants:
- data_processor : Classe principale de traitement de données
- config_manager : Gestionnaire de configurations de nettoyage
- pdf_generator : Générateur de rapports PDF professionnels

Nouveaux modules:
- auth_manager : Gestion de l'authentification OAuth (Google)
- export_manager : Dispatcher d'exports (CSV, Excel, PDF)
- excel_exporter : Export Excel multi-feuilles avancé
- chart_factory : Générateur de graphiques réutilisables (optionnel)

Version: 3.0.0
"""

from .data_processor import DataProcessor
from .config_manager import ConfigManager
from .pdf_generator import PDFReportGenerator

# Imports conditionnels pour les nouveaux modules
try:
    from .auth_manager import AuthManager
except ImportError:
    AuthManager = None
    print("⚠️  AuthManager non disponible")

try:
    from .export_manager import ExportManager
except ImportError:
    ExportManager = None
    print("⚠️  ExportManager non disponible")

try:
    from .excel_exporter import ExcelExporter
except ImportError:
    ExcelExporter = None
    print("⚠️  ExcelExporter non disponible")

try:
    from .chart_factory import ChartFactory
except ImportError:
    ChartFactory = None
    print("ℹ️  ChartFactory non disponible (optionnel)")

# Liste des exports publics
__all__ = [
    'DataProcessor',
    'ConfigManager',
    'PDFReportGenerator',
    'AuthManager',
    'ExportManager',
    'ExcelExporter',
    'ChartFactory'
]

__version__ = '3.0.0'
__author__ = 'Data Cleaning Dashboard Team'

print(f"✅ Package modules v{__version__} initialisé")