// ============================================
// AUTH.JS - GESTION AUTHENTIFICATION OAUTH
// Version 3.0 Ultra-Complète
// ============================================

/**
 * Module de gestion de l'authentification Google OAuth
 * 
 * Fonctionnalités:
 * - Vérification du statut d'authentification
 * - Affichage du menu utilisateur avec avatar
 * - Modal de connexion Google OAuth
 * - Gestion du callback OAuth
 * - Déconnexion
 * - Gestion du "pending clean" (reprise après OAuth)
 * - Affichage historique et statistiques
 * - Rate limiting et sécurité
 * 
 * @author Data Cleaning Dashboard Team
 * @version 3.0.0
 */

const AuthModule = (function () {
    'use strict';

    // ========================================
    // VARIABLES PRIVÉES
    // ========================================

    let currentUser = null;
    let authCheckInterval = null;
    let isInitialized = false;

    const config = {
        checkAuthUrl: '/api/auth/check',
        loginUrl: '/api/auth/google',
        logoutUrl: '/api/auth/logout',
        checkInterval: 60000, // Vérifier toutes les minutes
        sessionStorageKeys: {
            pendingClean: 'pendingClean',
            cleaningConfig: 'cleaningConfig',
            rawData: 'rawData',
            returnUrl: 'authReturnUrl',
            welcomeShown: 'welcomeShown'
        }
    };

    // ========================================
    // INITIALISATION
    // ========================================

    function init() {
        if (isInitialized) {
            console.log('⚠️  AuthModule déjà initialisé');
            return;
        }

        console.log('🔐 AuthModule: Initialisation...');

        // Vérifier le statut auth au chargement
        checkAuthStatus();

        // Vérifier périodiquement (session expirée?)
        startAuthCheckInterval();

        // Event listeners
        setupEventListeners();

        // Vérifier si on revient d'OAuth
        handleOAuthCallback();

        isInitialized = true;
        console.log('✅ AuthModule: Initialisé');
    }

    // ========================================
    // VÉRIFICATION DU STATUT AUTH
    // ========================================

    async function checkAuthStatus(silent = false) {
        try {
            const response = await fetch(config.checkAuthUrl, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.authenticated && data.user) {
                currentUser = data.user;
                updateUIForAuthenticatedUser(data.user);

                if (!silent) {
                    console.log('✅ Utilisateur connecté:', data.user.email);
                }

                return true;
            } else {
                currentUser = null;
                updateUIForUnauthenticatedUser();

                if (!silent) {
                    console.log('ℹ️  Utilisateur non connecté');
                }

                return false;
            }

        } catch (error) {
            console.error('❌ Erreur vérification auth:', error);

            // En cas d'erreur, considérer comme non connecté
            currentUser = null;
            updateUIForUnauthenticatedUser();

            return false;
        }
    }

    // ========================================
    // MISE À JOUR DE L'INTERFACE
    // ========================================

    function updateUIForAuthenticatedUser(user) {
        // Avatar et menu utilisateur
        const avatarContainer = document.getElementById('user-avatar-container');
        const loginButton = document.getElementById('btn-login');

        if (!avatarContainer || !loginButton) {
            console.warn('⚠️  Éléments UI auth non trouvés');
            return;
        }

        // Masquer bouton login
        loginButton.classList.add('hidden');

        // Afficher avatar
        avatarContainer.classList.remove('hidden');
        avatarContainer.innerHTML = createUserMenuHTML(user);

        // Setup event listeners du menu
        setupUserMenuListeners(avatarContainer);

        // Badge de bienvenue (première connexion de la session)
        const welcomeKey = config.sessionStorageKeys.welcomeShown;
        if (!sessionStorage.getItem(welcomeKey)) {
            showWelcomeNotification(user);
            sessionStorage.setItem(welcomeKey, 'true');
        }
    }

    function createUserMenuHTML(user) {
        const displayName = user.given_name || user.name || 'Utilisateur';
        const avatar = user.picture || getDefaultAvatar(user.email);

        return `
            <div class="relative group">
                <div class="flex items-center gap-3 cursor-pointer">
                    <img src="${avatar}" 
                         alt="${displayName}" 
                         class="w-10 h-10 rounded-full border-2 border-white/10 group-hover:border-primary transition-all duration-300 object-cover"
                         onerror="this.src='${getDefaultAvatar(user.email)}'">
                    <div class="hidden md:block">
                        <p class="text-sm font-semibold text-white group-hover:text-primary transition-colors">${displayName}</p>
                        <p class="text-xs text-muted-foreground">${truncateEmail(user.email)}</p>
                    </div>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="hidden md:block text-muted-foreground group-hover:text-white transition-colors">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                </div>
                
                <!-- Dropdown menu -->
                <div id="user-dropdown" class="hidden absolute top-full right-0 mt-3 w-72 bg-card border border-white/10 rounded-xl shadow-2xl z-[9999] animate-slide-down overflow-hidden">
                    <!-- Header du dropdown -->
                    <div class="p-4 border-b border-white/5 bg-gradient-to-r from-primary/10 to-secondary/10">
                        <div class="flex items-center gap-3">
                            <img src="${avatar}" 
                                 alt="${displayName}" 
                                 class="w-12 h-12 rounded-full border-2 border-white/20 object-cover"
                                 onerror="this.src='${getDefaultAvatar(user.email)}'">
                            <div class="flex-1">
                                <p class="text-sm font-semibold text-white">${user.name || 'Utilisateur'}</p>
                                <p class="text-xs text-muted-foreground">${user.email}</p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Stats rapides -->
                    <div class="p-4 border-b border-white/5 bg-white/5">
                        <div class="grid grid-cols-2 gap-3 text-center">
                            <div>
                                <p class="text-lg font-bold text-primary" id="user-stat-cleanings">-</p>
                                <p class="text-xs text-muted-foreground">Nettoyages</p>
                            </div>
                            <div>
                                <p class="text-lg font-bold text-green-400" id="user-stat-score">-</p>
                                <p class="text-xs text-muted-foreground">Score moyen</p>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Actions -->
                    <div class="p-2">
                        <button onclick="AuthModule.viewHistory()" class="w-full text-left px-4 py-3 text-sm text-white hover:bg-white/5 rounded-lg transition-all flex items-center gap-3 group">
                            <div class="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center group-hover:bg-blue-500/30 transition-colors">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path>
                                    <path d="M21 3v5h-5"></path>
                                    <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path>
                                    <path d="M3 21v-5h5"></path>
                                </svg>
                            </div>
                            <div>
                                <p class="font-medium">Historique</p>
                                <p class="text-xs text-muted-foreground">Vos nettoyages passés</p>
                            </div>
                        </button>
                        
                        <button onclick="AuthModule.viewStats()" class="w-full text-left px-4 py-3 text-sm text-white hover:bg-white/5 rounded-lg transition-all flex items-center gap-3 group">
                            <div class="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center group-hover:bg-green-500/30 transition-colors">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="12" y1="20" x2="12" y2="10"></line>
                                    <line x1="18" y1="20" x2="18" y2="4"></line>
                                    <line x1="6" y1="20" x2="6" y2="16"></line>
                                </svg>
                            </div>
                            <div>
                                <p class="font-medium">Statistiques</p>
                                <p class="text-xs text-muted-foreground">Vos performances</p>
                            </div>
                        </button>
                    </div>
                    
                    <!-- Déconnexion -->
                    <div class="p-2 border-t border-white/5">
                        <button onclick="AuthModule.logout()" class="w-full text-left px-4 py-3 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-all flex items-center gap-3 group">
                            <div class="w-8 h-8 rounded-lg bg-red-500/20 flex items-center justify-center group-hover:bg-red-500/30 transition-colors">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                                    <polyline points="16 17 21 12 16 7"></polyline>
                                    <line x1="21" y1="12" x2="9" y2="12"></line>
                                </svg>
                            </div>
                            <div>
                                <p class="font-medium">Déconnexion</p>
                                <p class="text-xs text-muted-foreground">Se déconnecter du compte</p>
                            </div>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    function setupUserMenuListeners(container) {
        const trigger = container.querySelector('.group');
        const dropdown = document.getElementById('user-dropdown');

        if (!trigger || !dropdown) return;

        // Toggle dropdown au clic
        trigger.addEventListener('click', function (e) {
            e.stopPropagation();
            dropdown.classList.toggle('hidden');

            // Charger les stats si dropdown ouvert
            if (!dropdown.classList.contains('hidden')) {
                loadUserStats();
            }
        });

        // Fermer dropdown en cliquant ailleurs
        document.addEventListener('click', function closeDropdown(e) {
            if (!container.contains(e.target) && !dropdown.classList.contains('hidden')) {
                dropdown.classList.add('hidden');
            }
        });

        // Empêcher fermeture au clic dans le dropdown
        dropdown.addEventListener('click', function (e) {
            e.stopPropagation();
        });
    }

    async function loadUserStats() {
        try {
            const response = await fetch('/api/user/stats', {
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success && data.stats) {
                const stats = data.stats;

                const cleaningsEl = document.getElementById('user-stat-cleanings');
                const scoreEl = document.getElementById('user-stat-score');

                if (cleaningsEl) cleaningsEl.textContent = stats.total_cleanings || 0;
                if (scoreEl) scoreEl.textContent = `${stats.average_quality_score || 0}%`;
            }

        } catch (error) {
            console.error('❌ Erreur chargement stats:', error);
        }
    }

    function updateUIForUnauthenticatedUser() {
        const avatarContainer = document.getElementById('user-avatar-container');
        const loginButton = document.getElementById('btn-login');

        if (!avatarContainer || !loginButton) return;

        // Masquer avatar
        avatarContainer.classList.add('hidden');
        avatarContainer.innerHTML = '';

        // Afficher bouton login
        loginButton.classList.remove('hidden');
    }

    // ========================================
    // MODAL D'AUTHENTIFICATION
    // ========================================

    function showAuthModal(message = null) {
        console.log('🔐 Affichage modal OAuth...');

        // Supprimer modal existant si présent
        const existingModal = document.getElementById('auth-modal-overlay');
        if (existingModal) {
            existingModal.remove();
        }

        // Créer le modal
        const modal = document.createElement('div');
        modal.id = 'auth-modal-overlay';
        modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[9999] p-4 animate-fade-in';

        modal.innerHTML = `
            <div class="bg-card border border-white/10 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl animate-scale">
                <!-- Header -->
                <div class="text-center mb-6">
                    <div class="w-16 h-16 bg-gradient-to-br from-primary to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-glow animate-pulse-glow">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
                            <polyline points="10 17 15 12 10 7"></polyline>
                            <line x1="15" y1="12" x2="3" y2="12"></line>
                        </svg>
                    </div>
                    <h3 class="text-xl font-bold text-white mb-2">🔐 Connexion Requise</h3>
                    <p class="text-muted-foreground text-sm">
                        ${message || 'Pour continuer, veuillez vous connecter avec votre compte Google'}
                    </p>
                </div>

                <!-- Avantages -->
                <div class="mb-6 space-y-2 bg-white/5 rounded-xl p-4">
                    <p class="text-xs font-semibold text-white mb-3">✨ Avec un compte, vous pouvez :</p>
                    
                    <div class="flex items-start gap-3 text-xs text-muted-foreground">
                        <div class="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <span>Sauvegarder votre historique de nettoyage</span>
                    </div>
                    
                    <div class="flex items-start gap-3 text-xs text-muted-foreground">
                        <div class="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <span>Télécharger vos rapports ultérieurement</span>
                    </div>
                    
                    <div class="flex items-start gap-3 text-xs text-muted-foreground">
                        <div class="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <span>Suivre vos statistiques et performances</span>
                    </div>
                    
                    <div class="flex items-start gap-3 text-xs text-muted-foreground">
                        <div class="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <span>Accéder à vos fichiers depuis n'importe où</span>
                    </div>
                </div>

                <!-- Bouton Google -->
                <button id="modal-google-signin" class="w-full bg-white hover:bg-gray-100 text-gray-900 h-12 rounded-xl font-semibold flex items-center justify-center gap-3 transition-all shadow-lg hover:shadow-xl mb-3 group">
                    <svg width="20" height="20" viewBox="0 0 24 24" class="flex-shrink-0">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    <span class="group-hover:translate-x-0.5 transition-transform">Continuer avec Google</span>
                </button>

                <!-- Bouton annuler -->
                <button id="modal-cancel-auth" class="w-full text-muted-foreground hover:text-white text-sm transition-colors py-2">
                    Annuler
                </button>

                <!-- Privacy notice -->
                <div class="mt-4 pt-4 border-t border-white/10">
                    <p class="text-xs text-muted-foreground text-center">
                        🔒 En vous connectant, vous acceptez notre 
                        <a href="#" class="text-primary hover:underline">politique de confidentialité</a>
                    </p>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Event: Bouton Google
        document.getElementById('modal-google-signin').addEventListener('click', function () {
            // Sauvegarder l'URL de retour
            sessionStorage.setItem(config.sessionStorageKeys.returnUrl, window.location.pathname);

            // Rediriger vers OAuth
            window.location.href = config.loginUrl;
        });

        // Event: Annuler
        document.getElementById('modal-cancel-auth').addEventListener('click', function () {
            modal.classList.add('opacity-0');
            setTimeout(() => modal.remove(), 300);
            console.log('❌ Connexion annulée');
        });

        // Event: Clic sur overlay pour fermer
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                modal.classList.add('opacity-0');
                setTimeout(() => modal.remove(), 300);
            }
        });

        // Event: Échap pour fermer
        const escHandler = function (e) {
            if (e.key === 'Escape') {
                modal.classList.add('opacity-0');
                setTimeout(() => modal.remove(), 300);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    // ========================================
    // CALLBACK OAUTH
    // ========================================

    function handleOAuthCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        const authStatus = urlParams.get('auth');

        if (authStatus === 'success') {
            console.log('✅ Retour OAuth réussi');

            // Nettoyer l'URL
            const cleanUrl = window.location.pathname + window.location.hash;
            window.history.replaceState({}, document.title, cleanUrl);

            // Recharger le statut auth
            checkAuthStatus();

            // Notification de bienvenue
            showNotification('✅ Connexion réussie ! Bienvenue 🎉', 'success');

            // Vérifier si on avait un nettoyage en attente
            setTimeout(() => {
                checkPendingClean();
            }, 500);

            // Rediriger vers l'URL de retour si présente
            const returnUrl = sessionStorage.getItem(config.sessionStorageKeys.returnUrl);
            if (returnUrl && returnUrl !== window.location.pathname) {
                sessionStorage.removeItem(config.sessionStorageKeys.returnUrl);
                setTimeout(() => {
                    window.location.href = returnUrl;
                }, 1000);
            }

        } else if (authStatus === 'error') {
            console.error('❌ Erreur OAuth');
            showNotification('❌ Erreur lors de la connexion Google. Veuillez réessayer.', 'error');

            // Nettoyer l'URL
            const cleanUrl = window.location.pathname + window.location.hash;
            window.history.replaceState({}, document.title, cleanUrl);
        }
    }

    // ========================================
    // PENDING CLEAN (REPRISE APRÈS OAUTH)
    // ========================================

    function checkPendingClean() {
        const pendingClean = sessionStorage.getItem(config.sessionStorageKeys.pendingClean);

        if (pendingClean === 'true') {
            console.log('🔄 Reprise du nettoyage en attente...');

            // Récupérer les données sauvegardées
            const cleaningConfig = sessionStorage.getItem(config.sessionStorageKeys.cleaningConfig);
            const rawData = sessionStorage.getItem(config.sessionStorageKeys.rawData);

            if (cleaningConfig && rawData) {
                // Restaurer les données dans l'app
                if (window.app) {
                    try {
                        window.app.cleaningConfig = JSON.parse(cleaningConfig);
                        window.app.rawData = JSON.parse(rawData);
                        window.app.currentFilename = sessionStorage.getItem('currentFilename');
                    } catch (error) {
                        console.error('❌ Erreur parsing données:', error);
                    }
                }

                // Nettoyer le sessionStorage
                sessionStorage.removeItem(config.sessionStorageKeys.pendingClean);
                sessionStorage.removeItem(config.sessionStorageKeys.cleaningConfig);
                sessionStorage.removeItem(config.sessionStorageKeys.rawData);
                sessionStorage.removeItem('currentFilename');

                // Déclencher le nettoyage si la fonction existe
                if (typeof window.performCleaning === 'function') {
                    showNotification('🔄 Reprise du nettoyage...', 'info');

                    setTimeout(() => {
                        window.performCleaning();
                    }, 1000);
                } else {
                    console.warn('⚠️  Fonction performCleaning non disponible');
                }
            }
        }
    }

    // ========================================
    // DÉCONNEXION
    // ========================================

    async function logout() {
        console.log('👋 Déconnexion...');

        // Confirmation
        const confirmed = confirm('Êtes-vous sûr de vouloir vous déconnecter ?');
        if (!confirmed) return;

        try {
            const response = await fetch(config.logoutUrl, {
                method: 'GET',
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success) {
                currentUser = null;
                updateUIForUnauthenticatedUser();

                // Nettoyer le sessionStorage
                Object.values(config.sessionStorageKeys).forEach(key => {
                    sessionStorage.removeItem(key);
                });

                showNotification('👋 Déconnexion réussie. À bientôt !', 'info');

                // Recharger la page après 1 seconde
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                throw new Error(data.error || 'Erreur déconnexion');
            }

        } catch (error) {
            console.error('❌ Erreur déconnexion:', error);
            showNotification('❌ Erreur lors de la déconnexion', 'error');
        }
    }

    // ========================================
    // VÉRIFICATION PÉRIODIQUE
    // ========================================

    function startAuthCheckInterval() {
        // Vérifier toutes les minutes si la session est toujours valide
        authCheckInterval = setInterval(() => {
            checkAuthStatus(true); // Silent check
        }, config.checkInterval);

        console.log('⏰ Vérification auth périodique activée');
    }

    function stopAuthCheckInterval() {
        if (authCheckInterval) {
            clearInterval(authCheckInterval);
            authCheckInterval = null;
            console.log('⏹️  Vérification auth périodique arrêtée');
        }
    }

    // ========================================
    // NAVIGATION
    // ========================================

    function viewHistory() {
        console.log('📜 Affichage de l\'historique...');

        // Fermer le dropdown
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown) {
            dropdown.classList.add('hidden');
        }

        // Si HistoryModule existe, l'utiliser
        if (window.HistoryModule && typeof window.HistoryModule.show === 'function') {
            window.HistoryModule.show();
        } else {
            // Fallback: naviguer vers la page historique
            window.location.href = '/history';
        }
    }

    async function viewStats() {
        console.log('📊 Affichage des statistiques...');

        // Fermer le dropdown
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown) {
            dropdown.classList.add('hidden');
        }

        // Afficher un modal avec les stats
        try {
            const response = await fetch('/api/user/stats', {
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success && data.stats) {
                showStatsModal(data.stats);
            } else {
                throw new Error(data.error || 'Erreur chargement stats');
            }

        } catch (error) {
            console.error('❌ Erreur récupération stats:', error);
            showNotification('❌ Erreur lors du chargement des statistiques', 'error');
        }
    }

    function showStatsModal(stats) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[9999] p-4 animate-fade-in';

        modal.innerHTML = `
            <div class="bg-card border border-white/10 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl animate-scale">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="text-xl font-bold text-white">📊 Vos Statistiques</h3>
                    <button onclick="this.closest('.fixed').remove()" class="text-muted-foreground hover:text-white transition-colors">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                
                <div class="space-y-4">
                    <div class="bg-gradient-to-r from-primary/10 to-purple-500/10 rounded-xl p-5 border border-primary/20">
                        <p class="text-3xl font-bold text-primary mb-1">${stats.total_cleanings}</p>
                        <p class="text-sm text-muted-foreground">Nettoyages effectués</p>
                    </div>
                    
                    <div class="bg-gradient-to-r from-green-500/10 to-emerald-500/10 rounded-xl p-5 border border-green-500/20">
                        <p class="text-3xl font-bold text-green-400 mb-1">${stats.total_rows_cleaned.toLocaleString('fr-FR')}</p>
                        <p class="text-sm text-muted-foreground">Lignes nettoyées au total</p>
                    </div>
                    
                    <div class="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-xl p-5 border border-blue-500/20">
                        <p class="text-3xl font-bold text-blue-400 mb-1">${stats.average_quality_score}%</p>
                        <p class="text-sm text-muted-foreground">Score moyen de qualité</p>
                    </div>
                    
                    <div class="bg-gradient-to-r from-orange-500/10 to-yellow-500/10 rounded-xl p-5 border border-orange-500/20">
                        <p class="text-3xl font-bold text-orange-400 mb-1">${stats.total_files || stats.total_cleanings}</p>
                        <p class="text-sm text-muted-foreground">Fichiers traités</p>
                    </div>
                </div>
                
                <button onclick="this.closest('.fixed').remove()" class="w-full mt-6 bg-gradient-to-r from-primary to-secondary hover:opacity-90 text-white h-10 rounded-xl font-semibold transition-all">
                    Fermer
                </button>
            </div>
        `;

        document.body.appendChild(modal);

        // Fermer au clic sur overlay
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    // ========================================
    // EVENT LISTENERS
    // ========================================

    function setupEventListeners() {
        // Bouton de login dans le header
        const loginButton = document.getElementById('btn-login');
        if (loginButton) {
            loginButton.addEventListener('click', function () {
                showAuthModal();
            });
        }
    }

    // ========================================
    // UTILITAIRES
    // ========================================

    function showWelcomeNotification(user) {
        const firstName = user.given_name || user.name?.split(' ')[0] || 'Utilisateur';

        showNotification(
            `🎉 Bienvenue ${firstName} ! Vous êtes maintenant connecté.`,
            'success',
            6000
        );
    }

    function showNotification(message, type = 'info', duration = 4000) {
        // Utiliser la fonction globale si elle existe
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type, duration);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    function getDefaultAvatar(email) {
        // Générer un avatar basé sur l'email (UI Avatars)
        const initial = email ? email.charAt(0).toUpperCase() : 'U';
        return `https://ui-avatars.com/api/?name=${encodeURIComponent(initial)}&background=667EEA&color=fff&size=128`;
    }

    function truncateEmail(email, maxLength = 20) {
        if (!email || email.length <= maxLength) return email;

        const [local, domain] = email.split('@');
        if (local.length > maxLength - 3) {
            return local.substring(0, maxLength - 3) + '...@' + domain;
        }
        return email;
    }

    // ========================================
    // API PUBLIQUE
    // ========================================

    return {
        // Méthodes principales
        init: init,
        checkAuthStatus: checkAuthStatus,
        showAuthModal: showAuthModal,
        logout: logout,

        // Navigation
        viewHistory: viewHistory,
        viewStats: viewStats,

        // Getters
        getCurrentUser: () => currentUser,
        isAuthenticated: () => currentUser !== null,
        getConfig: () => ({ ...config }),

        // Utilitaires
        showNotification: showNotification
    };

})();

// ========================================
// AUTO-INITIALISATION
// ========================================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', AuthModule.init);
} else {
    AuthModule.init();
}

// Export global
window.AuthModule = AuthModule;

console.log('✅ auth.js chargé (v3.0)');