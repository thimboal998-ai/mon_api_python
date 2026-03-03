// ============================================
// HISTORY.JS - GESTION HISTORIQUE DES NETTOYAGES
// Version 3.0 Ultra-Complète
// ============================================

/**
 * Module de gestion de l'historique des nettoyages
 * 
 * Fonctionnalités:
 * - Affichage de l'historique en modal ou page dédiée
 * - Pagination avec navigation avancée
 * - Recherche et filtres multiples
 * - Affichage des détails d'un nettoyage
 * - Téléchargement des exports précédents
 * - Suppression d'historiques
 * - Tri et organisation
 * 
 * @author Data Cleaning Dashboard Team
 * @version 3.0.0
 */

const HistoryModule = (function () {
    'use strict';

    // ========================================
    // VARIABLES PRIVÉES
    // ========================================

    let historyData = [];
    let currentPage = 1;
    let totalPages = 1;
    let totalItems = 0;
    let isLoading = false;

    const config = {
        apiUrl: '/api/history',
        detailsUrl: '/api/history',
        perPage: 10,
        cacheTimeout: 60000, // 1 minute
        maxRetries: 3
    };

    let lastFetch = null;
    let searchQuery = '';
    let statusFilter = 'all';

    // ========================================
    // INITIALISATION
    // ========================================

    function init() {
        console.log('📜 HistoryModule: Initialisation...');

        // Charger l'historique si l'utilisateur est connecté
        if (window.AuthModule && window.AuthModule.isAuthenticated()) {
            fetchHistory(1, true);
        }

        console.log('✅ HistoryModule: Initialisé');
    }

    // ========================================
    // RÉCUPÉRATION DE L'HISTORIQUE
    // ========================================

    async function fetchHistory(page = 1, forceRefresh = false) {
        // Cache: ne pas refetch si récent
        if (!forceRefresh && lastFetch && (Date.now() - lastFetch < config.cacheTimeout)) {
            console.log('📦 Utilisation du cache historique');
            return historyData;
        }

        if (isLoading) {
            console.log('⏳ Chargement déjà en cours...');
            return historyData;
        }

        isLoading = true;
        currentPage = page;

        try {
            const url = `${config.apiUrl}?page=${page}&per_page=${config.perPage}`;

            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': forceRefresh ? 'no-cache' : 'default'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.success) {
                historyData = data.history || [];
                totalPages = data.pages || 1;
                totalItems = data.total || 0;
                lastFetch = Date.now();

                console.log(`✅ Historique chargé: ${historyData.length} éléments (page ${page}/${totalPages})`);

                return historyData;
            } else {
                throw new Error(data.error || 'Erreur récupération historique');
            }

        } catch (error) {
            console.error('❌ Erreur récupération historique:', error);
            showNotification('❌ Erreur lors du chargement de l\'historique', 'error');
            historyData = [];
            return [];

        } finally {
            isLoading = false;
        }
    }

    // ========================================
    // AFFICHAGE DU MODAL HISTORIQUE
    // ========================================

    async function show() {
        console.log('📜 Affichage de l\'historique...');

        // Vérifier l'authentification
        if (!window.AuthModule || !window.AuthModule.isAuthenticated()) {
            showNotification('⚠️ Veuillez vous connecter pour voir votre historique', 'warning');
            if (window.AuthModule) {
                window.AuthModule.showAuthModal('Pour consulter votre historique, veuillez vous connecter');
            }
            return;
        }

        // Charger les données
        showNotification('📥 Chargement de l\'historique...', 'info', 2000);
        const history = await fetchHistory(1, true);

        // Créer le modal
        const modal = document.createElement('div');
        modal.id = 'history-modal';
        modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[9999] p-4 animate-fade-in overflow-y-auto';

        modal.innerHTML = createModalHTML(history);

        document.body.appendChild(modal);

        // Event listeners
        setupHistoryEventListeners();

        // Fermer au clic sur overlay
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                close();
            }
        });

        // Fermer avec Échap
        const escHandler = function (e) {
            if (e.key === 'Escape') {
                close();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    function createModalHTML(history) {
        return `
            <div class="bg-card border border-white/10 rounded-2xl w-full max-w-5xl shadow-2xl animate-scale my-8">
                <!-- Header -->
                <div class="flex items-center justify-between p-6 border-b border-white/5 bg-gradient-to-r from-primary/10 to-secondary/10">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-glow">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path>
                                <path d="M21 3v5h-5"></path>
                                <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"></path>
                                <path d="M3 21v-5h5"></path>
                            </svg>
                        </div>
                        <div>
                            <h2 class="text-xl font-bold text-white">Historique des Nettoyages</h2>
                            <p class="text-sm text-muted-foreground">${totalItems} nettoyage(s) au total</p>
                        </div>
                    </div>
                    <button onclick="HistoryModule.close()" class="text-muted-foreground hover:text-white transition-colors p-2 hover:bg-white/10 rounded-lg">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>

                <!-- Filtres et recherche -->
                <div class="p-6 border-b border-white/5 bg-white/5">
                    <div class="flex flex-col md:flex-row items-center gap-4">
                        <!-- Recherche -->
                        <div class="flex-1 w-full relative">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none">
                                <circle cx="11" cy="11" r="8"></circle>
                                <path d="m21 21-4.35-4.35"></path>
                            </svg>
                            <input type="text" 
                                   id="history-search" 
                                   placeholder="Rechercher par nom de fichier..." 
                                   class="w-full bg-background border border-white/10 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
                                   value="${searchQuery}">
                        </div>
                        
                        <!-- Filtre statut -->
                        <select id="history-filter-status" 
                                class="bg-background border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all">
                            <option value="all" ${statusFilter === 'all' ? 'selected' : ''}>Tous les statuts</option>
                            <option value="completed" ${statusFilter === 'completed' ? 'selected' : ''}>✅ Terminé</option>
                            <option value="failed" ${statusFilter === 'failed' ? 'selected' : ''}>❌ Échoué</option>
                        </select>
                        
                        <!-- Boutons actions -->
                        <div class="flex gap-2">
                            <button onclick="HistoryModule.refresh()" 
                                    class="px-4 py-2.5 bg-primary/10 border border-primary/20 text-primary rounded-lg hover:bg-primary/20 transition-all text-sm font-medium flex items-center gap-2 whitespace-nowrap"
                                    title="Actualiser">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21.5 2v6h-6"></path>
                                    <path d="M2.5 22v-6h6"></path>
                                    <path d="M2 11.5a10 10 0 0 1 18.8-4.3"></path>
                                    <path d="M22 12.5a10 10 0 0 1-18.8 4.2"></path>
                                </svg>
                                <span class="hidden sm:inline">Actualiser</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Liste -->
                <div id="history-list" class="p-6 max-h-[60vh] overflow-y-auto">
                    ${isLoading ? createLoadingHTML() : renderHistoryList(history)}
                </div>

                <!-- Pagination -->
                <div id="history-pagination" class="p-6 border-t border-white/5 bg-white/5">
                    ${renderPagination()}
                </div>
            </div>
        `;
    }

    function createLoadingHTML() {
        return `
            <div class="flex flex-col items-center justify-center py-12">
                <div class="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
                <p class="text-muted-foreground">Chargement de l'historique...</p>
            </div>
        `;
    }

    // ========================================
    // RENDU DE LA LISTE
    // ========================================

    function renderHistoryList(history) {
        if (!history || history.length === 0) {
            return `
                <div class="text-center py-16">
                    <div class="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                    </div>
                    <p class="text-white font-semibold text-lg mb-2">Aucun nettoyage dans votre historique</p>
                    <p class="text-sm text-muted-foreground mb-6">Commencez par nettoyer des données !</p>
                    <button onclick="HistoryModule.close()" class="px-6 py-3 bg-gradient-to-r from-primary to-secondary text-white rounded-lg font-semibold hover:shadow-glow transition-all">
                        Commencer maintenant
                    </button>
                </div>
            `;
        }

        return history.map((item, index) => {
            const date = new Date(item.created_at);
            const formattedDate = date.toLocaleDateString('fr-FR', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            const qualityColor = item.quality_score >= 90 ? 'text-green-400 bg-green-500/20 border-green-500/30' :
                item.quality_score >= 70 ? 'text-orange-400 bg-orange-500/20 border-orange-500/30' :
                    'text-red-400 bg-red-500/20 border-red-500/30';

            const reductionPercent = item.original_rows > 0
                ? Math.round(((item.original_rows - item.cleaned_rows) / item.original_rows) * 100)
                : 0;

            return `
                <div class="bg-white/5 border border-white/5 rounded-xl p-5 mb-3 hover:bg-white/10 hover:border-primary/30 transition-all cursor-pointer group animate-slide-up" 
                     style="animation-delay: ${index * 50}ms" 
                     onclick="HistoryModule.viewDetails(${item.id})">
                    
                    <div class="flex items-start justify-between mb-4">
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-3 mb-2">
                                <h3 class="font-semibold text-white group-hover:text-primary transition-colors truncate">${item.filename}</h3>
                                <span class="px-2.5 py-1 rounded-full bg-white/10 text-xs text-muted-foreground font-medium flex-shrink-0">
                                    ${item.file_extension || 'CSV'}
                                </span>
                                ${item.status === 'completed'
                    ? '<span class="px-2.5 py-1 rounded-full bg-green-500/20 text-green-400 text-xs font-medium flex-shrink-0">✓ Terminé</span>'
                    : '<span class="px-2.5 py-1 rounded-full bg-red-500/20 text-red-400 text-xs font-medium flex-shrink-0">✗ Échoué</span>'}
                            </div>
                            <p class="text-sm text-muted-foreground flex items-center gap-2">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <polyline points="12 6 12 12 16 14"></polyline>
                                </svg>
                                ${formattedDate}
                            </p>
                        </div>
                        
                        <div class="px-4 py-2 rounded-lg ${qualityColor} font-bold text-lg border flex-shrink-0 ml-4">
                            ${item.quality_score}%
                        </div>
                    </div>
                    
                    <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                        <div>
                            <p class="text-xs text-muted-foreground mb-1">Lignes</p>
                            <p class="text-sm text-white font-semibold">${item.original_rows.toLocaleString()} → ${item.cleaned_rows.toLocaleString()}</p>
                            ${reductionPercent > 0 ? `<p class="text-xs text-red-400 mt-0.5">-${reductionPercent}%</p>` : ''}
                        </div>
                        
                        <div>
                            <p class="text-xs text-muted-foreground mb-1">Colonnes</p>
                            <p class="text-sm text-white font-semibold">${item.cleaned_columns || item.original_columns}</p>
                        </div>
                        
                        <div>
                            <p class="text-xs text-muted-foreground mb-1">Manquantes</p>
                            <p class="text-sm text-orange-400 font-semibold">${item.missing_values?.fixed || 0}</p>
                            <p class="text-xs text-muted-foreground mt-0.5">sur ${item.missing_values?.found || 0}</p>
                        </div>
                        
                        <div>
                            <p class="text-xs text-muted-foreground mb-1">Outliers</p>
                            <p class="text-sm text-red-400 font-semibold">${item.outliers?.fixed || 0}</p>
                            <p class="text-xs text-muted-foreground mt-0.5">sur ${item.outliers?.found || 0}</p>
                        </div>
                        
                        <div>
                            <p class="text-xs text-muted-foreground mb-1">Doublons</p>
                            <p class="text-sm text-yellow-400 font-semibold">${item.duplicates?.removed || 0}</p>
                            <p class="text-xs text-muted-foreground mt-0.5">supprimés</p>
                        </div>
                    </div>
                    
                    <!-- Actions -->
                    <div class="flex items-center justify-end gap-2 mt-4 pt-4 border-t border-white/5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onclick="event.stopPropagation(); HistoryModule.viewDetails(${item.id})" 
                                class="px-3 py-1.5 bg-primary/10 border border-primary/20 text-primary rounded-lg hover:bg-primary/20 transition-all text-xs font-medium">
                            Voir détails
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // ========================================
    // RENDU PAGINATION
    // ========================================

    function renderPagination() {
        if (totalPages <= 1) {
            return `<p class="text-sm text-muted-foreground text-center">Page 1 sur 1</p>`;
        }

        let html = `
            <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div class="text-sm text-muted-foreground">
                    <span class="font-semibold text-white">${totalItems}</span> résultat(s) • 
                    Page <span class="font-semibold text-white">${currentPage}</span> sur <span class="font-semibold text-white">${totalPages}</span>
                </div>
                
                <div class="flex items-center gap-2">
                    <button onclick="HistoryModule.goToPage(${currentPage - 1})" 
                            ${currentPage === 1 ? 'disabled' : ''} 
                            class="px-3 py-2 rounded-lg border border-white/10 text-sm font-medium transition-all ${currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-white/5 hover:border-primary/30'}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="15 18 9 12 15 6"></polyline>
                        </svg>
                    </button>
                    
                    <div class="flex gap-1">
        `;

        // Pages numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
                html += `
                    <button onclick="HistoryModule.goToPage(${i})" 
                            class="px-3 py-2 rounded-lg text-sm font-medium transition-all ${i === currentPage ? 'bg-primary text-white' : 'hover:bg-white/5 border border-white/10'}">
                        ${i}
                    </button>
                `;
            } else if (i === currentPage - 2 || i === currentPage + 2) {
                html += `<span class="px-2 text-muted-foreground flex items-center">...</span>`;
            }
        }

        html += `
                    </div>
                    
                    <button onclick="HistoryModule.goToPage(${currentPage + 1})" 
                            ${currentPage === totalPages ? 'disabled' : ''} 
                            class="px-3 py-2 rounded-lg border border-white/10 text-sm font-medium transition-all ${currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : 'hover:bg-white/5 hover:border-primary/30'}">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        return html;
    }

    // ========================================
    // DÉTAILS D'UN NETTOYAGE
    // ========================================

    async function viewDetails(cleaningId) {
        console.log('🔄 Restauration du nettoyage:', cleaningId);

        // Afficher un loader
        showNotification('📥 Restauration des données...', 'info', 3000);

        try {
            const response = await fetch(`${config.detailsUrl}/${cleaningId}`, {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                console.log('✅ Données reçues, lancement restauration...');

                // Utiliser la fonction globale de restauration dans dashboard.js
                if (window.restoreDashboard) {
                    window.restoreDashboard(data);
                } else {
                    console.error('❌ Fonction restoreDashboard non trouvée');
                    showNotification('❌ Erreur critique: Système de dashboard non trouvé', 'error');
                }
            } else {
                throw new Error(data.error || 'Erreur restauration');
            }

        } catch (error) {
            console.error('❌ Erreur restauration:', error);
            showNotification('❌ ' + error.message, 'error');
        }
    }


    // ========================================
    // NAVIGATION & ACTIONS
    // ========================================

    async function goToPage(page) {
        if (page < 1 || page > totalPages || page === currentPage) return;

        const history = await fetchHistory(page);

        const listElement = document.getElementById('history-list');
        const paginationElement = document.getElementById('history-pagination');

        if (listElement) {
            listElement.innerHTML = renderHistoryList(history);
        }

        if (paginationElement) {
            paginationElement.innerHTML = renderPagination();
        }

        // Scroll to top
        const modal = document.getElementById('history-modal');
        if (modal) {
            modal.scrollTop = 0;
        }
    }

    async function refresh() {
        console.log('🔄 Actualisation de l\'historique...');

        const history = await fetchHistory(currentPage, true);

        const listElement = document.getElementById('history-list');
        const paginationElement = document.getElementById('history-pagination');

        if (listElement) {
            listElement.innerHTML = renderHistoryList(history);
        }

        if (paginationElement) {
            paginationElement.innerHTML = renderPagination();
        }

        showNotification('✅ Historique actualisé', 'success');
    }

    function close() {
        const modal = document.getElementById('history-modal');
        if (modal) {
            modal.classList.add('opacity-0');
            setTimeout(() => modal.remove(), 300);
        }
    }

    // ========================================
    // EVENT LISTENERS
    // ========================================

    function setupHistoryEventListeners() {
        // Recherche
        const searchInput = document.getElementById('history-search');
        if (searchInput) {
            searchInput.addEventListener('input', debounce(function (e) {
                searchQuery = e.target.value;
                filterHistory();
            }, 300));
        }

        // Filtre statut
        const statusFilter = document.getElementById('history-filter-status');
        if (statusFilter) {
            statusFilter.addEventListener('change', function (e) {
                statusFilter = e.target.value;
                filterHistory();
            });
        }
    }

    function filterHistory() {
        const query = searchQuery.toLowerCase();

        const filtered = historyData.filter(item => {
            const matchesSearch = !query || item.filename.toLowerCase().includes(query);
            const matchesStatus = statusFilter === 'all' || item.status === statusFilter;

            return matchesSearch && matchesStatus;
        });

        const listElement = document.getElementById('history-list');
        if (listElement) {
            listElement.innerHTML = renderHistoryList(filtered);
        }
    }

    // ========================================
    // UTILITAIRES
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

    function showNotification(message, type = 'info', duration = 4000) {
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type, duration);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    // ========================================
    // API PUBLIQUE
    // ========================================

    return {
        init: init,
        show: show,
        close: close,
        refresh: refresh,
        viewDetails: viewDetails,
        goToPage: goToPage,
        fetchHistory: fetchHistory,
        getHistory: () => historyData,
        getCurrentPage: () => currentPage,
        getTotalPages: () => totalPages
    };

})();

// Export global
window.HistoryModule = HistoryModule;

console.log('✅ history.js chargé (v3.0)');