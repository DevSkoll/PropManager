/**
 * PropManager Navigation Launcher
 * AWS-style app launcher with search, recent apps, and pinned favorites
 */

(function() {
    'use strict';

    // ============================================
    // Configuration & State
    // ============================================

    const STORAGE_KEYS = {
        recentApps: 'pm_recentApps',
        pinnedApps: 'pm_pinnedApps'
    };

    const MAX_RECENT_APPS = 8;

    let appTiles = [];
    let categoryInfo = {};

    // ============================================
    // Initialize
    // ============================================

    document.addEventListener('DOMContentLoaded', function() {
        loadAppData();
        initGlobalSearch();
        initLauncherModal();
        initKeyboardShortcuts();
        updateRecentAppsDropdown();
    });

    function loadAppData() {
        try {
            const tilesEl = document.getElementById('appTilesData');
            const catEl = document.getElementById('categoryInfoData');

            if (tilesEl) {
                appTiles = JSON.parse(tilesEl.textContent || '[]');
            }
            if (catEl) {
                categoryInfo = JSON.parse(catEl.textContent || '{}');
            }
        } catch (e) {
            console.error('Failed to load app data:', e);
        }
    }

    // ============================================
    // Global Search (Top Nav) - Hybrid Search
    // ============================================

    let apiSearchTimeout;
    let currentSearchQuery = '';
    let lastApiResults = null;

    function initGlobalSearch() {
        const searchInput = document.getElementById('globalSearch');
        const searchResults = document.getElementById('searchResults');

        if (!searchInput || !searchResults) return;

        let searchTimeout;

        searchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            clearTimeout(apiSearchTimeout);
            const query = e.target.value.toLowerCase().trim();
            currentSearchQuery = query;

            if (query.length < 2) {
                searchResults.classList.remove('show');
                lastApiResults = null;
                return;
            }

            // Instant client-side app search
            searchTimeout = setTimeout(() => {
                const appResults = searchApps(query);
                renderHybridResults(appResults, lastApiResults, searchResults);
            }, 50);

            // Debounced server-side search
            apiSearchTimeout = setTimeout(async () => {
                try {
                    const apiData = await fetchSearchAPI(query);
                    if (currentSearchQuery === query) {
                        lastApiResults = apiData;
                        const appResults = searchApps(query);
                        renderHybridResults(appResults, apiData, searchResults);
                    }
                } catch (e) {
                    console.error('Search API error:', e);
                }
            }, 250);
        });

        searchInput.addEventListener('focus', function() {
            if (this.value.length >= 2) {
                searchResults.classList.add('show');
            }
        });

        // Close on click outside
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.nav-search-container')) {
                searchResults.classList.remove('show');
            }
        });

        // Keyboard navigation in search results
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                this.value = '';
                searchResults.classList.remove('show');
                lastApiResults = null;
                this.blur();
            } else if (e.key === 'Enter') {
                const firstResult = searchResults.querySelector('.search-result-item');
                if (firstResult) {
                    firstResult.click();
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                const items = searchResults.querySelectorAll('.search-result-item');
                if (items.length > 0) {
                    items[0].focus();
                }
            }
        });

        // Arrow key navigation within results
        searchResults.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                const items = Array.from(searchResults.querySelectorAll('.search-result-item'));
                const currentIndex = items.indexOf(document.activeElement);

                if (e.key === 'ArrowDown' && currentIndex < items.length - 1) {
                    items[currentIndex + 1].focus();
                } else if (e.key === 'ArrowUp') {
                    if (currentIndex > 0) {
                        items[currentIndex - 1].focus();
                    } else {
                        searchInput.focus();
                    }
                }
            } else if (e.key === 'Escape') {
                searchInput.focus();
                searchInput.value = '';
                searchResults.classList.remove('show');
            }
        });
    }

    async function fetchSearchAPI(query) {
        const response = await fetch(`/admin-portal/api/search/?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('Search API failed');
        }
        return await response.json();
    }

    function searchApps(query) {
        return appTiles.filter(app => {
            const searchText = [
                app.name,
                app.description,
                ...(app.keywords || [])
            ].join(' ').toLowerCase();

            return searchText.includes(query);
        }).slice(0, 5);
    }

    function renderHybridResults(appResults, apiData, container) {
        let html = '';
        let hasResults = false;

        // Apps first (highest priority)
        if (appResults.length > 0) {
            hasResults = true;
            html += renderCategory('Apps', 'bi-grid-3x3-gap', appResults.map(app => ({
                title: app.name,
                subtitle: getCategoryName(app.category),
                url: app.url,
                icon: app.icon,
                gradient: app.gradient,
                onClick: `trackAppLaunch('${app.id}', '${app.name}', '${app.url}')`
            })));
        }

        // API categories in priority order
        if (apiData && apiData.categories) {
            const categoryOrder = ['tenants', 'properties', 'units', 'leases', 'documents', 'work_orders', 'invoices'];

            for (const catKey of categoryOrder) {
                const cat = apiData.categories[catKey];
                if (cat && cat.results && cat.results.length > 0) {
                    hasResults = true;
                    html += renderCategory(cat.label, cat.icon, cat.results);
                }
            }
        }

        if (!hasResults) {
            html = `
                <div class="search-no-results">
                    <i class="bi bi-search me-2"></i>No results found
                </div>
            `;
        }

        container.innerHTML = html;
        container.classList.add('show');
    }

    function renderCategory(label, icon, results) {
        const itemsHTML = results.map(r => `
            <a href="${r.url}" class="search-result-item" tabindex="0" ${r.onClick ? `onclick="${r.onClick}"` : ''}>
                <div class="search-result-icon ${r.gradient ? 'gradient-' + r.gradient : ''}">
                    <i class="${r.icon || 'bi-link'}"></i>
                </div>
                <div class="search-result-info">
                    <div class="search-result-name">${escapeHtml(r.title)}</div>
                    <div class="search-result-category">${escapeHtml(r.subtitle || '')}</div>
                </div>
            </a>
        `).join('');

        return `
            <div class="search-category">
                <div class="search-category-header">
                    <i class="${icon} me-2"></i>${label}
                </div>
                ${itemsHTML}
            </div>
        `;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ============================================
    // Launcher Modal
    // ============================================

    function initLauncherModal() {
        const modal = document.getElementById('appLauncherModal');
        const searchInput = document.getElementById('launcherSearch');

        if (!modal) return;

        // Populate launcher when modal opens
        modal.addEventListener('show.bs.modal', function() {
            populateLauncher();
            setTimeout(() => {
                if (searchInput) searchInput.focus();
            }, 300);
        });

        // Clear search when modal closes
        modal.addEventListener('hidden.bs.modal', function() {
            if (searchInput) {
                searchInput.value = '';
                filterLauncherApps('');
            }
        });

        // Search within launcher
        if (searchInput) {
            let filterTimeout;
            searchInput.addEventListener('input', function(e) {
                clearTimeout(filterTimeout);
                filterTimeout = setTimeout(() => {
                    filterLauncherApps(e.target.value.toLowerCase().trim());
                }, 100);
            });

            searchInput.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    if (this.value) {
                        this.value = '';
                        filterLauncherApps('');
                    } else {
                        bootstrap.Modal.getInstance(modal).hide();
                    }
                } else if (e.key === 'Enter') {
                    const firstTile = document.querySelector('#launcherCategories .app-tile:not([style*="display: none"])');
                    if (firstTile) firstTile.click();
                }
            });
        }
    }

    function populateLauncher() {
        const categoriesContainer = document.getElementById('launcherCategories');
        const recentContainer = document.getElementById('modalRecentApps');
        const pinnedContainer = document.getElementById('pinnedApps');
        const pinnedSection = document.getElementById('pinnedSection');

        if (!categoriesContainer) return;

        // Populate recent apps
        const recentApps = getRecentApps();
        if (recentContainer) {
            if (recentApps.length > 0) {
                recentContainer.innerHTML = recentApps.slice(0, 6).map(recent => {
                    const app = appTiles.find(a => a.id === recent.id);
                    if (!app) return '';
                    return createAppTileHTML(app, false);
                }).filter(Boolean).join('');
            } else {
                recentContainer.innerHTML = '<p class="text-muted small">No recent apps</p>';
            }
        }

        // Populate pinned apps
        const pinnedIds = getPinnedApps();
        if (pinnedContainer && pinnedSection) {
            if (pinnedIds.length > 0) {
                pinnedContainer.innerHTML = pinnedIds.map(id => {
                    const app = appTiles.find(a => a.id === id);
                    if (!app) return '';
                    return createAppTileHTML(app, true);
                }).filter(Boolean).join('');
                pinnedSection.style.display = 'block';
            } else {
                pinnedSection.style.display = 'none';
            }
        }

        // Group apps by category
        const grouped = {};
        appTiles.forEach(app => {
            if (!grouped[app.category]) {
                grouped[app.category] = [];
            }
            grouped[app.category].push(app);
        });

        // Sort categories by order
        const sortedCategories = Object.keys(grouped).sort((a, b) => {
            const orderA = categoryInfo[a]?.order || 99;
            const orderB = categoryInfo[b]?.order || 99;
            return orderA - orderB;
        });

        // Render categories
        categoriesContainer.innerHTML = sortedCategories.map(cat => {
            const info = categoryInfo[cat] || { name: cat, icon: 'bi-folder' };
            const apps = grouped[cat];

            return `
                <div class="launcher-category" data-category="${cat}">
                    <div class="launcher-category-header">
                        <div class="launcher-category-icon gradient-${getGradientForCategory(cat)}">
                            <i class="${info.icon}"></i>
                        </div>
                        <span class="launcher-category-name">${info.name}</span>
                    </div>
                    <div class="launcher-grid">
                        ${apps.map(app => createAppTileHTML(app, false)).join('')}
                    </div>
                </div>
            `;
        }).join('');
    }

    function createAppTileHTML(app, showPinned = false) {
        const isPinned = getPinnedApps().includes(app.id);
        const badgeHTML = app.badge ? `<span class="app-tile-badge">${app.badge}</span>` : '';

        return `
            <a href="${app.url}"
               class="app-tile"
               data-app-id="${app.id}"
               data-name="${app.name.toLowerCase()}"
               data-description="${app.description.toLowerCase()}"
               data-keywords="${(app.keywords || []).join(' ').toLowerCase()}"
               onclick="trackAppLaunch('${app.id}', '${app.name}', '${app.url}')">
                <button type="button"
                        class="app-tile-pin ${isPinned ? 'pinned' : ''}"
                        onclick="event.preventDefault(); event.stopPropagation(); togglePin('${app.id}')"
                        title="${isPinned ? 'Unpin' : 'Pin to top'}">
                    <i class="bi bi-pin-angle${isPinned ? '-fill' : ''}"></i>
                </button>
                ${badgeHTML}
                <div class="app-tile-icon gradient-${app.gradient}">
                    <i class="${app.icon}"></i>
                </div>
                <div class="app-tile-name">${app.name}</div>
                <div class="app-tile-desc">${app.description}</div>
            </a>
        `;
    }

    function filterLauncherApps(query) {
        const categories = document.querySelectorAll('#launcherCategories .launcher-category');
        const noResults = document.getElementById('launcherNoResults');
        const recentSection = document.getElementById('recentSection');
        const pinnedSection = document.getElementById('pinnedSection');

        let visibleCount = 0;

        if (!query) {
            // Show all
            categories.forEach(cat => {
                cat.style.display = 'block';
                cat.querySelectorAll('.app-tile').forEach(tile => {
                    tile.style.display = 'flex';
                });
            });
            if (recentSection) recentSection.style.display = 'block';
            if (pinnedSection && getPinnedApps().length > 0) pinnedSection.style.display = 'block';
            noResults.style.display = 'none';
            return;
        }

        // Hide recent and pinned when searching
        if (recentSection) recentSection.style.display = 'none';
        if (pinnedSection) pinnedSection.style.display = 'none';

        categories.forEach(cat => {
            const tiles = cat.querySelectorAll('.app-tile');
            let catVisible = 0;

            tiles.forEach(tile => {
                const name = tile.dataset.name || '';
                const desc = tile.dataset.description || '';
                const keywords = tile.dataset.keywords || '';

                const matches = name.includes(query) ||
                              desc.includes(query) ||
                              keywords.includes(query);

                if (matches) {
                    tile.style.display = 'flex';
                    catVisible++;
                    visibleCount++;
                } else {
                    tile.style.display = 'none';
                }
            });

            cat.style.display = catVisible > 0 ? 'block' : 'none';
        });

        noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }

    // ============================================
    // Keyboard Shortcuts
    // ============================================

    function initKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + K: Focus global search
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.getElementById('globalSearch');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }

            // Ctrl/Cmd + /: Open launcher
            if ((e.metaKey || e.ctrlKey) && e.key === '/') {
                e.preventDefault();
                const modal = document.getElementById('appLauncherModal');
                if (modal) {
                    const bsModal = bootstrap.Modal.getOrCreateInstance(modal);
                    bsModal.toggle();
                }
            }
        });
    }

    // ============================================
    // Recent Apps Management
    // ============================================

    function getRecentApps() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEYS.recentApps) || '[]');
        } catch (e) {
            return [];
        }
    }

    function saveRecentApp(appId, appName, appUrl) {
        try {
            let recent = getRecentApps();

            // Remove if already exists
            recent = recent.filter(app => app.id !== appId);

            // Add to front
            recent.unshift({
                id: appId,
                name: appName,
                url: appUrl,
                timestamp: Date.now()
            });

            // Keep only last N
            recent = recent.slice(0, MAX_RECENT_APPS);

            localStorage.setItem(STORAGE_KEYS.recentApps, JSON.stringify(recent));
            updateRecentAppsDropdown();
        } catch (e) {
            console.error('Failed to save recent app:', e);
        }
    }

    function updateRecentAppsDropdown() {
        const container = document.getElementById('recentAppsList');
        if (!container) return;

        const recentApps = getRecentApps();

        if (recentApps.length === 0) {
            container.innerHTML = '<p class="dropdown-item-text text-muted small">No recent apps</p>';
            return;
        }

        container.innerHTML = recentApps.slice(0, 5).map(recent => {
            const app = appTiles.find(a => a.id === recent.id);
            const gradient = app ? app.gradient : 'gray';
            const icon = app ? app.icon : 'bi-app';
            const timeAgo = formatTimeAgo(recent.timestamp);

            return `
                <a href="${recent.url}" class="recent-app-item">
                    <div class="recent-app-icon gradient-${gradient}">
                        <i class="${icon}"></i>
                    </div>
                    <span class="recent-app-name">${recent.name}</span>
                    <span class="recent-app-time">${timeAgo}</span>
                </a>
            `;
        }).join('');
    }

    // ============================================
    // Pinned Apps Management
    // ============================================

    function getPinnedApps() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEYS.pinnedApps) || '[]');
        } catch (e) {
            return [];
        }
    }

    function togglePin(appId) {
        try {
            let pinned = getPinnedApps();

            if (pinned.includes(appId)) {
                pinned = pinned.filter(id => id !== appId);
            } else {
                pinned.unshift(appId);
            }

            localStorage.setItem(STORAGE_KEYS.pinnedApps, JSON.stringify(pinned));
            populateLauncher(); // Refresh launcher
        } catch (e) {
            console.error('Failed to toggle pin:', e);
        }
    }

    // ============================================
    // Helpers
    // ============================================

    function getCategoryName(categoryId) {
        return categoryInfo[categoryId]?.name || categoryId;
    }

    function getGradientForCategory(categoryId) {
        const gradients = {
            dashboard: 'purple',
            properties: 'blue',
            leases: 'teal',
            billing: 'green',
            maintenance: 'orange',
            tenant_programs: 'pink',
            communications: 'indigo',
            documents: 'cyan',
            reports: 'gray',
            operations: 'red'
        };
        return gradients[categoryId] || 'gray';
    }

    function formatTimeAgo(timestamp) {
        const seconds = Math.floor((Date.now() - timestamp) / 1000);

        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
        return new Date(timestamp).toLocaleDateString();
    }

    // ============================================
    // Global Functions (called from HTML)
    // ============================================

    window.trackAppLaunch = function(appId, appName, appUrl) {
        saveRecentApp(appId, appName, appUrl);
    };

    window.clearRecentApps = function() {
        localStorage.removeItem(STORAGE_KEYS.recentApps);
        updateRecentAppsDropdown();
    };

    window.togglePin = togglePin;

})();
