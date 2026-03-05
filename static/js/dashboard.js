// ============================================
// DASHBOARD.JS - VERSION 3.0 ULTRA-COMPLÈTE
// Application complète de nettoyage de données
// ============================================

/**
 * Data Cleaning Dashboard v3.0
 * 
 * Fonctionnalités principales:
 * - Upload de fichiers (drag & drop)
 * - Parsing côté client avec PapaParse
 * - Nettoyage automatique des colonnes index
 * - Analyse des données
 * - Configuration du nettoyage
 * - Affichage dashboard avec tableau interactif
 * - Export (CSV, PDF, Excel)
 * - Intégration OAuth (via AuthModule)
 * 
 * @author Data Cleaning Dashboard Team
 * @version 3.0.0
 */

(function () {
    'use strict';

    // ========================================
    // UTILITAIRES DE BASE (Avant Initialisation)
    // ========================================
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function throttle(func, limit) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // ========================================
    // ÉTAT GLOBAL DE L'APPLICATION
    // ========================================

    const app = {
        // Données
        rawData: null,
        cleanedData: null,
        currentFilename: null,

        // Config
        cleaningConfig: {
            missingStrategy: 'auto',
            outliersMethod: 'cap',
            removeDuplicates: true
        },

        // Statistiques
        initialStats: null,
        finalStats: null,

        // UI State
        currentView: 'upload', // 'upload', 'config', 'dashboard'
        isProcessing: false,

        // Tableau interactif
        tableState: {
            allData: [],
            filteredData: [],
            displayedData: [],
            currentPage: 1,
            rowsPerPage: 25,
            sortColumn: null,
            sortDirection: 'asc',
            selectedRows: new Set(),
            modifiedCells: [], // Liste des cellules nettoyées {row, col}
            filters: {},
            density: 'normal' // 'compact', 'normal', 'comfortable'
        },

        // Graphiques
        chartPaths: null,

        // User
        currentUser: null
    };

    // Exposer app globalement pour AuthModule
    window.app = app;

    // ========================================
    // INITIALISATION
    // ========================================

    document.addEventListener('DOMContentLoaded', function () {
        console.log('🚀 Dashboard v3.0 - Initialisation...');

        initializeEventListeners();
        setupDragAndDrop();

        // Vérifier l'auth au démarrage
        if (window.AuthModule) {
            window.AuthModule.checkAuthStatus().then(isAuth => {
                if (isAuth) {
                    app.currentUser = window.AuthModule.getCurrentUser();
                    console.log('✅ Utilisateur connecté:', app.currentUser.email);
                }
            });
        }

        console.log('✅ Dashboard initialisé');
    });

    // ========================================
    // EVENT LISTENERS PRINCIPAUX
    // ========================================

    function initializeEventListeners() {
        // Upload
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');

        if (dropZone) {
            dropZone.addEventListener('click', () => fileInput.click());
        }

        if (fileInput) {
            fileInput.addEventListener('change', handleFileSelect);
        }

        // Bouton retour
        const btnBackUpload = document.getElementById('btn-back-upload');
        if (btnBackUpload) {
            btnBackUpload.addEventListener('click', () => showView('upload'));
        }

        // Bouton nettoyer
        const btnClean = document.getElementById('btn-clean');
        if (btnClean) {
            btnClean.addEventListener('click', handleCleanData);
        }

        // Bouton remove file
        const btnRemoveFile = document.getElementById('remove-file');
        if (btnRemoveFile) {
            btnRemoveFile.addEventListener('click', removeFile);
        }

        console.log('✅ Event listeners initialisés');
    }

    // ========================================
    // DRAG & DROP
    // ========================================

    function setupDragAndDrop() {
        const dropZone = document.getElementById('drop-zone');
        if (!dropZone) return;

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });

        // Highlight drop zone when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-over');
            }, false);
        });

        // Handle dropped files
        dropZone.addEventListener('drop', handleDrop, false);

        console.log('✅ Drag & Drop configuré');
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            handleFile(files[0]);
        }
    }

    // ========================================
    // GESTION DES FICHIERS
    // ========================================

    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            handleFile(file);
        }
    }

    async function handleFile(file) {
        console.log('\n📁 Fichier sélectionné:', file.name);

        // Vérifier la taille
        const maxSize = 16 * 1024 * 1024; // 16 MB
        if (file.size > maxSize) {
            showNotification('❌ Fichier trop volumineux (max 16 MB)', 'error');
            return;
        }

        // Vérifier l'extension
        const allowedExtensions = ['csv', 'xlsx', 'xls', 'json', 'xml'];
        const extension = file.name.split('.').pop().toLowerCase();

        if (!allowedExtensions.includes(extension)) {
            showNotification(`❌ Format non supporté. Formats acceptés: ${allowedExtensions.join(', ')}`, 'error');
            return;
        }

        // Afficher le loader
        showLoading('Lecture du fichier...');

        try {
            // Parser selon le type
            let parsedData;

            if (extension === 'csv') {
                parsedData = await parseCSV(file);
            } else if (extension === 'xlsx' || extension === 'xls') {
                // Pour Excel, on upload d'abord au serveur
                await uploadFileToServer(file);
                return; // Le serveur gérera le parsing
            } else if (extension === 'json') {
                parsedData = await parseJSON(file);
            } else if (extension === 'xml') {
                await uploadFileToServer(file);
                return;
            }

            // Nettoyer les colonnes index côté client
            cleanIndexColumns(parsedData);

            // Sauvegarder
            app.rawData = parsedData;
            app.currentFilename = file.name;

            // Afficher les infos du fichier
            displayFileInfo(file);

            // Upload au serveur pour l'analyse
            await uploadFileToServer(file);

        } catch (error) {
            console.error('❌ Erreur traitement fichier:', error);
            showNotification('❌ Erreur lors de la lecture du fichier', 'error');
            hideLoading();
        }
    }

    // ========================================
    // PARSING DES FICHIERS
    // ========================================

    function parseCSV(file) {
        return new Promise((resolve, reject) => {
            Papa.parse(file, {
                header: true,
                dynamicTyping: true,
                skipEmptyLines: true,
                complete: (results) => {
                    console.log('✅ CSV parsé:', results.data.length, 'lignes');

                    const data = {
                        data: results.data,
                        columns: results.meta.fields,
                        filename: file.name
                    };

                    resolve(data);
                },
                error: (error) => {
                    console.error('❌ Erreur parsing CSV:', error);
                    reject(error);
                }
            });
        });
    }

    function parseJSON(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = (e) => {
                try {
                    const jsonData = JSON.parse(e.target.result);

                    // Convertir en format tableau si nécessaire
                    let dataArray = Array.isArray(jsonData) ? jsonData : [jsonData];

                    // Extraire les colonnes
                    const columns = dataArray.length > 0 ? Object.keys(dataArray[0]) : [];

                    const data = {
                        data: dataArray,
                        columns: columns,
                        filename: file.name
                    };

                    console.log('✅ JSON parsé:', dataArray.length, 'lignes');
                    resolve(data);

                } catch (error) {
                    console.error('❌ Erreur parsing JSON:', error);
                    reject(error);
                }
            };

            reader.onerror = () => reject(reader.error);
            reader.readAsText(file);
        });
    }

    // ========================================
    // NETTOYAGE DES COLONNES INDEX
    // ========================================

    function cleanIndexColumns(parsedData) {
        console.log('\n🔍 Nettoyage des colonnes index...');
        console.log('   Colonnes avant:', parsedData.columns);

        const indexPatterns = [
            /^unnamed:?\s*\d*$/i,
            /^index$/i,
            /^level_\d+$/i,
            /^id$/i,
            /^row_?id$/i
        ];

        const columnsToRemove = [];

        parsedData.columns.forEach(col => {
            const colLower = String(col).toLowerCase().trim();

            // Vérifier les patterns
            const isIndexColumn = indexPatterns.some(pattern => pattern.test(colLower));

            if (isIndexColumn) {
                columnsToRemove.push(col);
                console.log('   ❌ Colonne index détectée:', col);
            }

            // Vérifier si c'est une séquence numérique
            if (parsedData.data.length > 0 && typeof parsedData.data[0][col] === 'number') {
                const values = parsedData.data.slice(0, 100).map(row => row[col]).filter(v => v !== null && v !== undefined);

                if (values.length > 10) {
                    const isSequence = values.every((val, idx) => idx === 0 || val === values[idx - 1] + 1 || val === idx);

                    if (isSequence && !columnsToRemove.includes(col)) {
                        columnsToRemove.push(col);
                        console.log('   ❌ Séquence numérique détectée:', col);
                    }
                }
            }
        });

        if (columnsToRemove.length > 0) {
            // Supprimer les colonnes
            parsedData.data = parsedData.data.map(row => {
                const newRow = { ...row };
                columnsToRemove.forEach(col => delete newRow[col]);
                return newRow;
            });

            parsedData.columns = parsedData.columns.filter(col => !columnsToRemove.includes(col));

            console.log(`   ✅ ${columnsToRemove.length} colonne(s) supprimée(s)`);
        } else {
            console.log('   ✅ Aucune colonne index détectée');
        }

        console.log('   Colonnes après:', parsedData.columns);
    }

    // ========================================
    // UPLOAD AU SERVEUR
    // ========================================

    async function uploadFileToServer(file) {
        const formData = new FormData();
        formData.append('file', file);

        showLoading('Upload du fichier...');

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            const result = await response.json();

            if (result.success) {
                console.log('✅ Upload réussi:', result.message);
                showNotification('✅ ' + result.message, 'success');

                // Lancer l'analyse
                await analyzeData();

            } else {
                throw new Error(result.error || 'Erreur upload');
            }

        } catch (error) {
            console.error('❌ Erreur upload:', error);
            showNotification('❌ ' + error.message, 'error');
            hideLoading();
        }
    }

    // ========================================
    // ANALYSE DES DONNÉES
    // ========================================

    async function analyzeData() {
        showLoading('Analyse des données...');

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            const result = await response.json();

            if (result.success) {
                console.log('✅ Analyse terminée');
                app.initialStats = result.stats;

                // Afficher la vue de configuration
                showConfigView(result.stats);

                hideLoading();

            } else {
                throw new Error(result.error || 'Erreur analyse');
            }

        } catch (error) {
            console.error('❌ Erreur analyse:', error);
            showNotification('❌ ' + error.message, 'error');
            hideLoading();
        }
    }

    // ========================================
    // VUE CONFIGURATION
    // ========================================

    function showConfigView(stats) {
        console.log('\n⚙️  Affichage configuration (Modal)...');

        const modal = document.getElementById('view-config');
        if (modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Empêcher le scroll du body
        }

        // Remplir les infos fichier
        document.getElementById('config-filename').textContent = app.currentFilename;
        document.getElementById('config-rows').textContent = stats.lignes_totales;

        // Afficher les KPIs
        document.getElementById('kpi-rows').textContent = stats.lignes_totales;
        document.getElementById('kpi-missing').textContent = stats.lignes_avec_valeurs_manquantes || 0;
        document.getElementById('kpi-outliers').textContent = stats.lignes_avec_outliers || 0;
        document.getElementById('kpi-duplicates').textContent = stats.doublons || 0;

        console.log('✅ Modal configuration affiché');
    }

    // Exposer pour le bouton fermer et le backdrop
    window.hideConfigModal = function () {
        const modal = document.getElementById('view-config');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = ''; // Réactiver le scroll
        }
    };

    // ========================================
    // NETTOYAGE DES DONNÉES
    // ========================================

    async function handleCleanData() {
        console.log('\n🧹 Lancement du nettoyage...');

        // Récupérer la configuration
        app.cleaningConfig = {
            missing_strategy: document.getElementById('missing-strategy').value,
            outliers_method: document.getElementById('outliers-method').value,
            remove_duplicates: document.getElementById('remove-duplicates').checked
        };

        console.log('   Config:', app.cleaningConfig);

        // Vérifier l'authentification
        if (!window.AuthModule || !window.AuthModule.isAuthenticated()) {
            console.log('⚠️  Utilisateur non connecté - Affichage modal OAuth');

            // Sauvegarder l'état pour reprendre après connexion
            sessionStorage.setItem('pendingClean', 'true');
            sessionStorage.setItem('cleaningConfig', JSON.stringify(app.cleaningConfig));
            sessionStorage.setItem('rawData', JSON.stringify(app.rawData));
            sessionStorage.setItem('currentFilename', app.currentFilename);

            // Afficher le modal OAuth
            if (window.AuthModule) {
                window.AuthModule.showAuthModal('Pour nettoyer vos données, veuillez vous connecter');
            } else {
                showNotification('❌ Module d\'authentification non disponible', 'error');
            }

            return;
        }

        // Lancer le nettoyage
        await performCleaning();
    }

    async function performCleaning() {
        showLoading('Nettoyage en cours...');

        try {
            const response = await fetch('/clean', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(app.cleaningConfig),
                credentials: 'include'
            });

            const result = await response.json();

            if (result.success) {
                console.log('✅ Nettoyage terminé');

                app.finalStats = result.stats;
                app.chartPaths = result.plot_paths;
                app.csvFilename = result.csv_filename; // Store the server-generated filename

                // Fermer le modal après nettoyage
                window.hideConfigModal();

                // Afficher le dashboard
                showDashboardView(result.stats, result.plot_paths);

                hideLoading();
                showNotification('✅ Nettoyage terminé avec succès !', 'success');

            } else {
                throw new Error(result.error || 'Erreur nettoyage');
            }

        } catch (error) {
            console.error('❌ Erreur nettoyage:', error);
            showNotification('❌ ' + error.message, 'error');
            hideLoading();
        }
    }

    // Exposer pour AuthModule
    window.performCleaning = performCleaning;

    // ========================================
    // VUE DASHBOARD
    // ========================================

    function showDashboardView(stats, plotPaths) {
        console.log('\n📊 Affichage dashboard...');

        // Changer de vue
        showView('dashboard');

        // Créer le HTML du dashboard
        const dashboardHTML = createDashboardHTML(stats, plotPaths);
        document.getElementById('view-dashboard').innerHTML = dashboardHTML;

        // Initialiser le tableau interactif
        if (stats.data_preview) {
            app.tableState.allData = stats.data_preview;
            app.tableState.filteredData = [...stats.data_preview];
            app.tableState.modifiedCells = stats.modified_cells || [];
            initializeDataTable(stats.data_preview, stats.colonnes);
        }

        // Charger les graphiques (Différé pour fluidité)
        setTimeout(() => loadGraphs(plotPaths), 100);

        // Setup event listeners du dashboard
        setupDashboardEventListeners();

        // Gérer le hash initial (ex: #data)
        if (window.location.hash) {
            scrollToSection(window.location.hash);
        }

        console.log('✅ Dashboard affiché');
    }

    // ========================================
    // RESTAURATION DE L'HISTORIQUE
    // ========================================

    window.restoreDashboard = function (data) {
        console.log('\n🔄 Restauration du dashboard depuis l\'historique...');

        if (!data || !data.success) {
            showNotification('❌ Données de restauration invalides', 'error');
            return;
        }

        // Mettre à jour l'état de l'application
        app.currentFilename = data.filename;
        app.finalStats = data.stats;
        app.chartPaths = data.plot_paths;
        app.csvFilename = data.csv_filename;

        // Afficher le dashboard
        showDashboardView(data.stats, data.plot_paths);

        // Fermer le modal de l'historique s'il est ouvert
        if (window.HistoryModule && typeof window.HistoryModule.closeHistory === 'function') {
            window.HistoryModule.closeHistory();
        }

        showNotification('✅ Historique restauré avec succès', 'success');
    };

    function createDashboardHTML(stats, plotPaths) {
        const s = stats.stats || stats;
        const quality = stats.quality || {};

        return `
            <!-- Sidebar -->
            <div class="dashboard-sidebar">
                <!-- Logo -->
                <div class="px-6 mb-6">
                    <div class="flex items-center gap-2">
                        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-glow">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
                                <path d="M12 2L13.5 8.5L18 10L13.5 11.5L12 18L10.5 11.5L6 10L10.5 8.5L12 2Z"/>
                            </svg>
                        </div>
                        <div>
                            <p class="text-sm font-bold text-white">Dashboard</p>
                            <p class="text-xs text-muted-foreground">Résultats</p>
                        </div>
                    </div>
                </div>
                
                <!-- Navigation -->
                <nav class="mb-6">
                    <p class="sidebar-section-title">Navigation</p>
                    <a href="#overview" class="sidebar-nav-item active">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="7" height="7"></rect>
                            <rect x="14" y="3" width="7" height="7"></rect>
                            <rect x="14" y="14" width="7" height="7"></rect>
                            <rect x="3" y="14" width="7" height="7"></rect>
                        </svg>
                        Vue d'ensemble
                    </a>
                    <a href="#data" class="sidebar-nav-item">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        Données
                    </a>
                    <a href="#charts" class="sidebar-nav-item">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="12" y1="20" x2="12" y2="10"></line>
                            <line x1="18" y1="20" x2="18" y2="4"></line>
                            <line x1="6" y1="20" x2="6" y2="16"></line>
                        </svg>
                        Graphiques
                    </a>
                    <a href="#stats" class="sidebar-nav-item">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                        </svg>
                        Statistiques
                    </a>
                </nav>
                
                <!-- Infos fichier -->
                <div class="px-6">
                    <p class="sidebar-section-title">Fichier</p>
                    <div class="bg-white/5 rounded-xl p-4 mb-4">
                        <p class="text-sm font-semibold text-white mb-1">${app.currentFilename}</p>
                        <p class="text-xs text-muted-foreground">${s.lignes_finales} lignes × ${s.colonnes_finales} colonnes</p>
                    </div>
                    
                    <button id="btn-back-config" class="w-full mb-3 bg-white/5 border border-white/10 text-white h-10 rounded-lg font-semibold hover:bg-white/10 transition-all flex items-center justify-center gap-2">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 20V10"></path>
                            <path d="M18 20V4"></path>
                            <path d="M6 20v-4"></path>
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        </svg>
                        ⚙️ Configurer
                    </button>
                    
                    <button id="btn-export" class="w-full bg-gradient-to-r from-primary to-secondary text-white h-10 rounded-lg font-semibold hover:shadow-glow transition-all flex items-center justify-center gap-2">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        Exporter
                    </button>
                </div>
            </div>
            
            <!-- Main Content -->
            <div class="ml-[280px] p-8">
                
                <!-- Header -->
                <div class="mb-8">
                    <div class="flex items-center justify-between mb-4">
                        <div>
                            <h1 class="text-3xl font-bold text-white mb-2">Données Nettoyées</h1>
                            <p class="text-muted-foreground">${app.currentFilename}</p>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="px-4 py-2 rounded-lg bg-green-500/20 text-green-400 font-semibold text-sm">
                                ${quality.score || 0}% Qualité
                            </span>
                        </div>
                    </div>
                </div>
                
                <!-- KPIs -->
                <div class="grid grid-cols-2 md:grid-cols-6 gap-4 mb-8">
                    <div class="kpi-card">
                        <div class="kpi-icon bg-blue-500/20">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2">
                                <rect x="3" y="3" width="7" height="7"></rect>
                                <rect x="14" y="3" width="7" height="7"></rect>
                                <rect x="14" y="14" width="7" height="7"></rect>
                                <rect x="3" y="14" width="7" height="7"></rect>
                            </svg>
                        </div>
                        <p class="kpi-label">Lignes</p>
                        <p class="kpi-value">${s.lignes_finales}</p>
                        <p class="kpi-change negative">-${s.lignes_initiales - s.lignes_finales}</p>
                    </div>
                    
                    <div class="kpi-card">
                        <div class="kpi-icon bg-purple-500/20">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#A855F7" stroke-width="2">
                                <line x1="8" y1="6" x2="21" y2="6"></line>
                                <line x1="8" y1="12" x2="21" y2="12"></line>
                                <line x1="8" y1="18" x2="21" y2="18"></line>
                                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                                <line x1="3" y1="18" x2="3.01" y2="18"></line>
                            </svg>
                        </div>
                        <p class="kpi-label">Colonnes</p>
                        <p class="kpi-value">${s.colonnes_finales}</p>
                    </div>
                    
                    <div class="kpi-card">
                        <div class="kpi-icon bg-orange-500/20">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#F97316" stroke-width="2">
                                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                            </svg>
                        </div>
                        <p class="kpi-label">Val. manquantes</p>
                        <p class="kpi-value">${s.valeurs_manquantes_traitees || 0}</p>
                        <p class="kpi-change positive">traitées</p>
                    </div>
                    
                    <div class="kpi-card">
                        <div class="kpi-icon bg-red-500/20">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2">
                                <circle cx="12" cy="12" r="10"></circle>
                                <line x1="12" y1="8" x2="12" y2="12"></line>
                                <line x1="12" y1="16" x2="12.01" y2="16"></line>
                            </svg>
                        </div>
                        <p class="kpi-label">Outliers</p>
                        <p class="kpi-value">${s.lignes_outliers_traitees || 0}</p>
                        <p class="kpi-change positive">traités</p>
                    </div>
                    
                    <div class="kpi-card">
                        <div class="kpi-icon bg-yellow-500/20">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#EAB308" stroke-width="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <line x1="9" y1="9" x2="15" y2="15"></line>
                                <line x1="15" y1="9" x2="9" y2="15"></line>
                            </svg>
                        </div>
                        <p class="kpi-label">Doublons</p>
                        <p class="kpi-value">${s.doublons_supprimes || 0}</p>
                        <p class="kpi-change positive">supprimés</p>
                    </div>
                    
                    <div class="kpi-card">
                        <div class="kpi-icon bg-green-500/20">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <p class="kpi-label">Score qualité</p>
                        <p class="kpi-value text-green-400">${quality.score || 0}%</p>
                    </div>
                </div>
                
                <!-- Tableau de données -->
                <div id="data-section" class="mb-8">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-2xl font-bold text-white">Données Nettoyées</h2>
                        
                        <!-- Contrôles du tableau -->
                        <div class="flex items-center gap-4">
                            <!-- Recherche -->
                            <div class="relative">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                                    <circle cx="11" cy="11" r="8"></circle>
                                    <path d="m21 21-4.35-4.35"></path>
                                </svg>
                                <input type="text" id="table-search" placeholder="Rechercher..." class="bg-background border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all">
                            </div>
                            
                            <!-- Densité -->
                            <div class="density-toggle">
                                <button class="density-option active" data-density="compact">Compact</button>
                                <button class="density-option" data-density="normal">Normal</button>
                                <button class="density-option" data-density="comfortable">Confortable</button>
                            </div>
                            
                            <!-- Validation des modifications -->
                            <button id="btn-validate" class="px-3 py-2 bg-green-600/10 border border-green-600/20 text-green-500 rounded-lg hover:bg-green-600/20 transition-all text-sm font-medium flex items-center gap-2">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                                Valider les modifications
                            </button>
                        </div>
                    </div>
                    
                    <!-- Tableau -->
                    <div class="table-container">
                        <table id="data-table" class="data-table">
                            <thead id="table-header">
                                <!-- Généré dynamiquement -->
                            </thead>
                            <tbody id="table-body">
                                <!-- Généré dynamiquement -->
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- Pagination -->
                    <div id="table-pagination" class="pagination-controls mt-4">
                        <!-- Généré dynamiquement -->
                    </div>
                </div>
                
                <!-- Graphiques -->
                <div id="charts-section" class="mb-8">
                    <h2 class="text-2xl font-bold text-white mb-6">Visualisations</h2>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div class="chart-container">
                            <p class="chart-title">📊 Distribution Avant/Après</p>
                            <img id="chart-distributions" src="" alt="Distributions" class="animate-fade-in">
                        </div>
                        
                        <div class="chart-container">
                            <p class="chart-title">📈 Histogrammes</p>
                            <img id="chart-histograms" src="" alt="Histogrammes" class="animate-fade-in">
                        </div>
                        
                        <div class="chart-container">
                            <p class="chart-title">🔗 Matrice de Corrélation</p>
                            <img id="chart-correlation" src="" alt="Corrélation" class="animate-fade-in">
                        </div>
                    </div>
                </div>
                


                ${createDescriptiveStatsHTML(stats.descriptive_stats)}
            </div>
        `;
    }

    function createDescriptiveStatsHTML(descriptiveStats) {
        if (!descriptiveStats || Object.keys(descriptiveStats).length === 0) {
            return '';
        }

        const columns = Object.keys(descriptiveStats);
        const metrics = ['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'];
        const metricLabels = {
            'count': 'Nombre',
            'mean': 'Moyenne',
            'std': 'Ecart-type',
            'min': 'Minimum',
            '25%': 'Q1 (25%)',
            '50%': 'Médiane (50%)',
            '75%': 'Q3 (75%)',
            'max': 'Maximum'
        };

        return `
            <div id="stats-section" class="mb-8 animate-slide-up" style="animation-delay: 200ms">
                <h2 class="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 20V10"></path>
                        <path d="M18 20V4"></path>
                        <path d="M6 20v-4"></path>
                    </svg>
                    Statistiques Descriptives
                </h2>
                
                <div class="bg-card border border-white/10 rounded-xl overflow-hidden shadow-lg">
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm text-left">
                            <thead class="text-xs text-muted-foreground uppercase bg-white/5 border-b border-white/10">
                                <tr>
                                    <th class="px-6 py-4 font-bold">Métrique</th>
                                    ${columns.map(col => `<th class="px-6 py-4 text-white font-semibold">${col}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-white/5">
                                ${metrics.map(metric => `
                                    <tr class="hover:bg-white/5 transition-colors">
                                        <td class="px-6 py-4 font-medium text-primary">${metricLabels[metric] || metric}</td>
                                        ${columns.map(col => {
            const val = descriptiveStats[col][metric];
            let formattedVal = val;
            if (typeof val === 'number') {
                formattedVal = val.toLocaleString('fr-FR', { maximumFractionDigits: 2 });
            } else if (val === null || val === undefined) {
                formattedVal = '-';
            }
            return `<td class="px-6 py-4 text-white/90">${formattedVal}</td>`;
        }).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }

    // ========================================
    // TABLEAU INTERACTIF
    // ========================================

    function initializeDataTable(data, columns) {
        console.log('\n📋 Initialisation tableau interactif...');

        // Créer les headers
        createTableHeaders(columns);

        // Créer les filtres
        createColumnFilters(columns);

        // Afficher la première page
        renderCurrentPage();

        // Créer la pagination
        updatePagination();

        console.log('✅ Tableau initialisé');
    }

    function createTableHeaders(columns) {
        const thead = document.getElementById('table-header');
        if (!thead) return;

        let html = '<tr>';

        // Checkbox pour sélectionner tout
        html += `
            <th class="w-12">
                <input type="checkbox" id="select-all" class="row-checkbox">
            </th>
        `;

        // Headers des colonnes
        columns.forEach(col => {
            html += `
                <th data-column="${col}" class="cursor-pointer hover:bg-white/10 transition-colors">
                    ${col}
                    <span class="sort-icon"></span>
                </th>
            `;
        });

        html += '</tr>';

        thead.innerHTML = html;

        // Event listeners
        thead.querySelectorAll('th[data-column]').forEach(th => {
            th.addEventListener('click', () => handleSort(th.dataset.column));
        });

        document.getElementById('select-all')?.addEventListener('change', handleSelectAll);
    }

    function createColumnFilters(columns) {
        // Déjà créés dans les headers
    }

    function renderCurrentPage() {
        const tbody = document.getElementById('table-body');
        if (!tbody) return;

        const { filteredData, currentPage, rowsPerPage } = app.tableState;

        const startIndex = (currentPage - 1) * rowsPerPage;
        const endIndex = startIndex + rowsPerPage;

        app.tableState.displayedData = filteredData.slice(startIndex, endIndex);

        // Optimisation : Lookup O(1) avec un Set
        const modifiedSet = new Set(app.tableState.modifiedCells.map(m => `${m.row},${m.col}`));
        let html = '';

        app.tableState.displayedData.forEach((row, idx) => {
            const globalIdx = startIndex + idx;
            const isSelected = app.tableState.selectedRows.has(globalIdx);
            html += `<tr class="${isSelected ? 'selected' : ''}" data-index="${globalIdx}">`;
            html += `<td><input type="checkbox" class="row-checkbox" data-index="${globalIdx}" ${isSelected ? 'checked' : ''}></td>`;

            Object.keys(row).forEach(col => {
                const value = row[col];
                const isModified = modifiedSet.has(`${globalIdx},${col}`);
                const cellClass = getCellClass(value, isModified);
                html += `<td class="${cellClass}" contenteditable="false">${formatCellValue(value)}</td>`;
            });
            html += '</tr>';
        });
        tbody.innerHTML = html;

        // Event listeners
        tbody.querySelectorAll('.row-checkbox').forEach(cb => {
            cb.addEventListener('change', handleRowSelect);
        });

        tbody.querySelectorAll('td[contenteditable]').forEach(td => {
            td.addEventListener('dblclick', () => {
                td.contentEditable = 'true';
                td.classList.add('editing');
                td.focus();
            });

            td.addEventListener('blur', () => {
                const tr = td.parentElement;
                const globalIdx = parseInt(tr.dataset.index);
                const colIndex = td.cellIndex - 1; // -1 car la première colonne est la checkbox
                const columns = Object.keys(app.tableState.allData[0]);
                const colName = columns[colIndex];

                let newValue = td.innerText.trim();

                // Tenter de convertir en nombre si possible
                if (!isNaN(newValue) && newValue !== '') {
                    newValue = parseFloat(newValue);
                }

                // Mettre à jour les données locales
                app.tableState.filteredData[globalIdx][colName] = newValue;

                td.contentEditable = 'false';
                td.classList.remove('editing');

                // Marquer comme modifié visuellement (optionnel, déjà géré au prochain rendu)
                td.classList.add('manual-edit');
                td.classList.add('outlier-value');
            });

            td.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    td.blur();
                }
                if (e.key === 'Escape') {
                    // Annuler le changement (on pourrait stocker la valeur initiale mais ici on simplifie)
                    td.innerText = formatCellValue(app.tableState.allData[parseInt(td.parentElement.dataset.index)][Object.keys(app.tableState.allData[0])[td.cellIndex - 1]]);
                    td.blur();
                }
            });
        });
    }

    async function validateManualChanges() {
        if (!app.tableState.allData || app.tableState.allData.length === 0) {
            showNotification('⚠️ Aucune donnée à valider', 'warning');
            return;
        }

        showLoading('Enregistrement des modifications...');

        try {
            const response = await fetch('/update_data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ data: app.tableState.allData }),
                credentials: 'include'
            });

            const result = await response.json();

            if (result.success) {
                showNotification('✅ Modifications enregistrées et exports mis à jour !', 'success');

                document.querySelectorAll('.manual-edit').forEach(el => {
                    el.classList.remove('manual-edit');
                });

                // Mettre à jour les stats si nécessaire
                if (result.stats) {
                    app.finalStats = result.stats;
                }

                // Mettre à jour le nom du fichier CSV pour l'export
                if (result.csv_filename) {
                    app.csvFilename = result.csv_filename;
                }
            } else {
                throw new Error(result.error || 'Erreur lors de la validation');
            }
        } catch (error) {
            console.error('❌ Erreur validation:', error);
            showNotification('❌ ' + error.message, 'error');
        } finally {
            hideLoading();
        }
    }

    function getCellClass(value, isModified = false) {
        let classes = [];

        if (value === null || value === undefined || value === '') {
            classes.push('null-value');
        } else if (typeof value === 'number') {
            classes.push('numeric-value');
        }

        // Appliquer la couleur rouge clair si modifiée (nettoyée)
        if (isModified) {
            classes.push('outlier-value');
        }

        return classes.join(' ');
    }

    function formatCellValue(value) {
        if (value === null || value === undefined || value === '') {
            return '<em>null</em>';
        }
        if (typeof value === 'number') {
            return value.toLocaleString('fr-FR');
        }
        return value;
    }

    // ========================================
    // FONCTIONS TABLEAU
    // ========================================

    function handleSort(column) {
        const { sortColumn, sortDirection } = app.tableState;

        if (sortColumn === column) {
            app.tableState.sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            app.tableState.sortColumn = column;
            app.tableState.sortDirection = 'asc';
        }

        // Tri
        app.tableState.filteredData.sort((a, b) => {
            const aVal = a[column];
            const bVal = b[column];

            if (aVal === null || aVal === undefined) return 1;
            if (bVal === null || bVal === undefined) return -1;

            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return app.tableState.sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
            }

            const aStr = String(aVal).toLowerCase();
            const bStr = String(bVal).toLowerCase();

            if (app.tableState.sortDirection === 'asc') {
                return aStr < bStr ? -1 : aStr > bStr ? 1 : 0;
            } else {
                return aStr > bStr ? -1 : aStr < bStr ? 1 : 0;
            }
        });

        // Mettre à jour les icônes
        document.querySelectorAll('th[data-column]').forEach(th => {
            th.classList.remove('sorted-asc', 'sorted-desc');
        });

        const th = document.querySelector(`th[data-column="${column}"]`);
        if (th) {
            th.classList.add(app.tableState.sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
        }

        // Re-render
        app.tableState.currentPage = 1;
        renderCurrentPage();
        updatePagination();
    }

    function handleFilter() {
        const filters = {};

        document.querySelectorAll('.column-filter').forEach(input => {
            if (input.value.trim()) {
                filters[input.dataset.column] = input.value.trim().toLowerCase();
            }
        });

        app.tableState.filters = filters;

        // Appliquer les filtres
        app.tableState.filteredData = app.tableState.allData.filter(row => {
            return Object.entries(filters).every(([col, filterValue]) => {
                const cellValue = String(row[col] || '').toLowerCase();
                return cellValue.includes(filterValue);
            });
        });

        // Reset à la page 1
        app.tableState.currentPage = 1;
        renderCurrentPage();
        updatePagination();
    }

    function handleSelectAll(e) {
        const isChecked = e.target.checked;

        if (isChecked) {
            app.tableState.displayedData.forEach((_, idx) => {
                const globalIdx = (app.tableState.currentPage - 1) * app.tableState.rowsPerPage + idx;
                app.tableState.selectedRows.add(globalIdx);
            });
        } else {
            app.tableState.selectedRows.clear();
        }

        renderCurrentPage();
    }

    function handleRowSelect(e) {
        const idx = parseInt(e.target.dataset.index);

        if (e.target.checked) {
            app.tableState.selectedRows.add(idx);
        } else {
            app.tableState.selectedRows.delete(idx);
        }

        renderCurrentPage();
    }

    function updatePagination() {
        const container = document.getElementById('table-pagination');
        if (!container) return;

        const { filteredData, currentPage, rowsPerPage } = app.tableState;
        const totalPages = Math.ceil(filteredData.length / rowsPerPage);

        let html = `
            <div class="flex items-center justify-between">
                <div class="text-sm text-muted-foreground">
                    ${filteredData.length} ligne(s) • Page ${currentPage} sur ${totalPages}
                </div>
                
                <div class="flex items-center gap-2">
                    <button class="pagination-button" onclick="window.changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
                        ← Précédent
                    </button>
                    
                    <div class="flex gap-1">
        `;

        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
                html += `
                    <button class="pagination-button ${i === currentPage ? 'active' : ''}" onclick="window.changePage(${i})">
                        ${i}
                    </button>
                `;
            } else if (i === currentPage - 2 || i === currentPage + 2) {
                html += `<span class="px-2 text-muted-foreground">...</span>`;
            }
        }

        html += `
                    </div>
                    
                    <button class="pagination-button" onclick="window.changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
                        Suivant →
                    </button>
                </div>
                
                <select id="rows-per-page" class="bg-background border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-primary outline-none">
                    <option value="10" ${rowsPerPage === 10 ? 'selected' : ''}>10 lignes</option>
                    <option value="25" ${rowsPerPage === 25 ? 'selected' : ''}>25 lignes</option>
                    <option value="50" ${rowsPerPage === 50 ? 'selected' : ''}>50 lignes</option>
                    <option value="100" ${rowsPerPage === 100 ? 'selected' : ''}>100 lignes</option>
                </select>
            </div>
        `;

        container.innerHTML = html;

        document.getElementById('rows-per-page')?.addEventListener('change', (e) => {
            app.tableState.rowsPerPage = parseInt(e.target.value);
            app.tableState.currentPage = 1;
            renderCurrentPage();
            updatePagination();
        });
    }

    window.changePage = function (page) {
        const totalPages = Math.ceil(app.tableState.filteredData.length / app.tableState.rowsPerPage);

        if (page < 1 || page > totalPages) return;

        app.tableState.currentPage = page;
        renderCurrentPage();
        updatePagination();
    };

    // ========================================
    // GRAPHIQUES
    // ========================================

    function loadGraphs(plotPaths) {
        if (!plotPaths) return;

        const timestamp = Date.now();

        const charts = {
            'chart-distributions': plotPaths.distributions,
            'chart-histograms': plotPaths.histograms,
            'chart-correlation': plotPaths.correlation
        };

        Object.entries(charts).forEach(([id, path]) => {
            const img = document.getElementById(id);
            if (img && path) {
                img.src = `${path}?t=${timestamp}`;
                img.style.cursor = 'zoom-in'; // Indiquer que c'est cliquable
                img.onclick = () => showImageModal(img.src);
                img.onerror = function () {
                    this.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect width="400" height="300" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" fill="%23999"%3EGraphique non disponible%3C/text%3E%3C/svg%3E';
                    this.style.cursor = 'default';
                    this.onclick = null;
                };
            }
        });
    }

    function showImageModal(src) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[10000] p-4 animate-fade-in';

        modal.innerHTML = `
            <div class="relative max-w-5xl w-full bg-card border border-white/10 rounded-2xl overflow-hidden shadow-2xl animate-scale">
                <!-- Header -->
                <div class="flex items-center justify-between p-4 border-b border-white/5 bg-white/5">
                    <h3 class="text-white font-semibold flex items-center gap-2">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                            <circle cx="9" cy="9" r="2"></circle>
                            <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"></path>
                        </svg>
                        Aperçu du Graphique
                    </h3>
                    <button onclick="this.closest('.fixed').remove()" class="text-muted-foreground hover:text-white transition-colors p-2 hover:bg-white/10 rounded-lg">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                
                <!-- Image -->
                <div class="p-2 bg-white flex items-center justify-center min-h-[300px]">
                    <img src="${src}" alt="Graphique agrandi" class="max-w-full max-h-[80vh] object-contain">
                </div>
                
                <!-- Footer -->
                <div class="p-4 bg-white/5 text-center">
                    <button onclick="this.closest('.fixed').remove()" class="px-6 py-2 bg-primary text-white rounded-lg font-semibold hover:opacity-90 transition-all">
                        Fermer
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Fermer au clic sur l'arrière-plan
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        // Fermer avec la touche Echap
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', handleEsc);
            }
        };
        document.addEventListener('keydown', handleEsc);
    }

    // ========================================
    // EVENT LISTENERS DASHBOARD
    // ========================================

    function setupDashboardEventListeners() {
        // Bouton export
        const btnExport = document.getElementById('btn-export');
        if (btnExport) {
            btnExport.addEventListener('click', showExportMenu);
        }

        // Bouton retour configuration
        const btnBackConfig = document.getElementById('btn-back-config');
        if (btnBackConfig) {
            btnBackConfig.addEventListener('click', () => {
                if (app.initialStats) {
                    showConfigView(app.initialStats);
                } else {
                    showNotification('⚠️ Statistiques initiales non disponibles', 'warning');
                }
            });
        }


        // Recherche globale
        const tableSearch = document.getElementById('table-search');
        if (tableSearch) {
            tableSearch.addEventListener('input', debounce(handleGlobalSearch, 300));
        }

        // Densité
        document.querySelectorAll('.density-option').forEach(btn => {
            btn.addEventListener('click', () => handleDensityChange(btn.dataset.density));
        });

        // Bouton valider les modifications
        const btnValidate = document.getElementById('btn-validate');
        if (btnValidate) {
            btnValidate.addEventListener('click', validateManualChanges);
        }

        // Navigation par ancres (Sidebar)
        document.querySelectorAll('.sidebar-nav-item').forEach(link => {
            link.addEventListener('click', function (e) {
                const href = this.getAttribute('href');
                if (href && href.startsWith('#')) {
                    e.preventDefault();
                    scrollToSection(href);
                }
            });
        });

        // Scroll spy pour mettre à jour l'item actif
        const dashboardView = document.getElementById('view-dashboard');
        if (dashboardView) {
            dashboardView.addEventListener('scroll', throttle(handleScrollSpy, 100));
        }
    }

    function scrollToSection(hash) {
        const id = hash.substring(1); // Enlever le #

        // Mapper les ancres vers les IDs de sections réels
        const sectionMap = {
            'overview': 'view-dashboard', // Haut de page
            'data': 'data-section',
            'charts': 'charts-section',
            'stats': 'stats-section'
        };

        const targetId = sectionMap[id] || id;
        const targetElement = document.getElementById(targetId);

        if (targetElement) {
            targetElement.scrollIntoView({ behavior: 'smooth' });

            // Mettre à jour l'URL sans recharger
            history.pushState(null, null, hash);

            // Mettre à jour la classe active
            updateActiveSidebarItem(hash);
        }
    }

    function updateActiveSidebarItem(hash) {
        document.querySelectorAll('.sidebar-nav-item').forEach(item => {
            const itemHash = item.getAttribute('href');
            item.classList.toggle('active', itemHash === hash);
        });
    }

    function handleScrollSpy() {
        if (app.currentView !== 'dashboard') return;

        const sections = [
            { id: '#stats', element: document.getElementById('stats-section') },
            { id: '#charts', element: document.getElementById('charts-section') },
            { id: '#data', element: document.getElementById('data-section') },
            { id: '#overview', element: document.getElementById('view-dashboard') }
        ];

        for (const section of sections) {
            if (section.element) {
                const rect = section.element.getBoundingClientRect();
                // Si le haut de la section est proche du haut de la fenêtre
                if (rect.top >= 0 && rect.top <= 200) {
                    updateActiveSidebarItem(section.id);
                    break;
                }
            }
        }
    }

    function handleGlobalSearch(e) {
        const query = e.target.value.toLowerCase().trim();

        if (!query) {
            app.tableState.filteredData = [...app.tableState.allData];
        } else {
            app.tableState.filteredData = app.tableState.allData.filter(row => {
                return Object.values(row).some(val =>
                    String(val).toLowerCase().includes(query)
                );
            });
        }

        app.tableState.currentPage = 1;
        renderCurrentPage();
        updatePagination();
    }

    function handleDensityChange(density) {
        app.tableState.density = density;

        const table = document.getElementById('data-table');
        if (table) {
            table.className = `data-table density-${density}`;
        }

        document.querySelectorAll('.density-option').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.density === density);
        });
    }

    // ========================================
    // EXPORT
    // ========================================

    function showExportMenu() {
        const menu = document.createElement('div');
        menu.className = 'fixed bottom-20 right-8 bg-card border border-white/10 rounded-xl shadow-2xl z-50 animate-slide-up';

        menu.innerHTML = `
            <div class="p-2">
                <button onclick="window.downloadFile('csv')" class="w-full text-left px-4 py-3 hover:bg-white/5 rounded-lg transition-colors flex items-center gap-3">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                    </svg>
                    <div>
                        <p class="text-sm font-semibold text-white">CSV</p>
                        <p class="text-xs text-muted-foreground">Données nettoyées</p>
                    </div>
                </button>
                
                <button onclick="window.downloadFile('pdf')" class="w-full text-left px-4 py-3 hover:bg-white/5 rounded-lg transition-colors flex items-center gap-3">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                    <div>
                        <p class="text-sm font-semibold text-white">PDF</p>
                        <p class="text-xs text-muted-foreground">Rapport complet</p>
                    </div>
                </button>
                
                <button onclick="window.downloadFile('excel')" class="w-full text-left px-4 py-3 hover:bg-white/5 rounded-lg transition-colors flex items-center gap-3">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="3" y1="9" x2="21" y2="9"></line>
                        <line x1="9" y1="21" x2="9" y2="9"></line>
                    </svg>
                    <div>
                        <p class="text-sm font-semibold text-white">Excel</p>
                        <p class="text-xs text-muted-foreground">Multi-feuilles</p>
                    </div>
                </button>
            </div>
        `;

        document.body.appendChild(menu);

        // Fermer en cliquant ailleurs
        setTimeout(() => {
            document.addEventListener('click', function closeMenu(e) {
                if (!menu.contains(e.target) && e.target.id !== 'btn-export') {
                    menu.remove();
                    document.removeEventListener('click', closeMenu);
                }
            });
        }, 100);
    }

    window.downloadFile = function (type) {
        if (!app.currentFilename) {
            showNotification('❌ Aucun fichier à télécharger. Veuillez d\'abord traiter un fichier.', 'error');
            return;
        }

        let filename;

        // Use server-provided filename if available (most robust)
        if (app.csvFilename) {
            const base = app.csvFilename.replace('cleaned_', '').replace('.csv', '');

            switch (type) {
                case 'csv':
                    filename = app.csvFilename;
                    break;
                case 'pdf':
                    filename = `rapport_${base}.pdf`;
                    break;
                case 'excel':
                    filename = `rapport_${base}.xlsx`;
                    break;
                default:
                    showNotification(`❌ Type de fichier inconnu : ${type}`, 'error');
                    return;
            }
        }
        // Fallback to client-side logic (fix for dots in filename)
        else {
            const baseName = app.currentFilename.substring(0, app.currentFilename.lastIndexOf('.')); // Correct split like Python rsplit

            switch (type) {
                case 'csv':
                    filename = `cleaned_${baseName}.csv`;
                    break;
                case 'pdf':
                    filename = `rapport_${baseName}.pdf`;
                    break;
                case 'excel':
                    filename = `rapport_${baseName}.xlsx`;
                    break;
                default:
                    showNotification(`❌ Type de fichier inconnu : ${type}`, 'error');
                    return;
            }
        }

        window.location.href = `/download/${type}/${filename}`;

        showNotification(`📥 Téléchargement de ${filename}...`, 'info');
    };


    // ========================================
    // NAVIGATION ENTRE VUES
    // ========================================

    function showView(viewName) {
        const views = ['upload', 'config', 'dashboard'];

        views.forEach(v => {
            const element = document.getElementById(`view-${v}`);
            if (element) {
                if (v === viewName) {
                    if (v === 'config') {
                        // Pour config, on ne cache pas forcément les autres car c'est un modal désormas
                        // Mais showConfigView gère déjà l'affichage, donc on peut ignorer ici ou adapter
                        element.classList.remove('hidden');
                    } else {
                        element.classList.remove('hidden', 'hidden-view');
                    }
                } else {
                    // Si on passe à upload ou dashboard, on s'assure que le modal config est fermé
                    if (v === 'config') {
                        element.classList.add('hidden');
                    } else {
                        element.classList.add('hidden-view');
                    }
                }
            }
        });

        app.currentView = viewName;
    }

    // ========================================
    // UTILITAIRES UI
    // ========================================

    function displayFileInfo(file) {
        const fileInfo = document.getElementById('file-info');
        const fileName = document.getElementById('file-name');
        const fileSize = document.getElementById('file-size');

        if (fileInfo && fileName && fileSize) {
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileInfo.classList.remove('hidden');
        }
    }

    function removeFile() {
        app.rawData = null;
        app.currentFilename = null;

        const fileInfo = document.getElementById('file-info');
        const fileInput = document.getElementById('file-input');

        if (fileInfo) fileInfo.classList.add('hidden');
        if (fileInput) fileInput.value = '';

        showView('upload');
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    function showLoading(message = 'Chargement...') {
        const overlay = document.getElementById('loading-overlay');
        const messageEl = document.getElementById('loading-message');

        if (overlay) {
            overlay.classList.remove('hidden');
            if (messageEl) messageEl.textContent = message;
        }

        app.isProcessing = true;
    }

    function hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }

        app.isProcessing = false;
    }

    function showNotification(message, type = 'info') {
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    // ========================================
    // UTILITAIRES
    // ========================================

})();