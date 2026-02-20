/**
 * PropManager Dashboard Launcher
 * Handles search, filtering, keyboard navigation, and favorites
 */

(function() {
    'use strict';

    const appGrid = document.getElementById('appGrid');
    const searchInput = document.getElementById('appSearch');
    const noResults = document.getElementById('noResults');

    if (!appGrid || !searchInput) return;

    // ============================================
    // Search & Filter
    // ============================================

    let searchTimeout;

    searchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            filterApps(e.target.value.toLowerCase());
        }, 200);
    });

    function filterApps(query) {
        if (!query.trim()) {
            showAllApps();
            return;
        }

        const tiles = appGrid.querySelectorAll('.app-tile');
        const categories = appGrid.querySelectorAll('.category-section');
        let visibleCount = 0;

        // Filter tiles
        tiles.forEach(tile => {
            const name = tile.dataset.name || '';
            const description = tile.dataset.description || '';
            const keywords = tile.dataset.keywords || '';

            const matches = name.includes(query) ||
                          description.includes(query) ||
                          keywords.includes(query);

            if (matches) {
                tile.style.display = 'flex';
                visibleCount++;
            } else {
                tile.style.display = 'none';
            }
        });

        // Hide empty categories
        categories.forEach(category => {
            const visibleTiles = category.querySelectorAll('.app-tile[style*="display: flex"]');
            category.style.display = visibleTiles.length > 0 ? 'block' : 'none';
        });

        // Show/hide no results
        if (visibleCount === 0) {
            noResults.style.display = 'block';
            appGrid.style.display = 'none';
        } else {
            noResults.style.display = 'none';
            appGrid.style.display = 'block';
        }
    }

    function showAllApps() {
        const tiles = appGrid.querySelectorAll('.app-tile');
        const categories = appGrid.querySelectorAll('.category-section');

        tiles.forEach(tile => tile.style.display = 'flex');
        categories.forEach(category => category.style.display = 'block');

        noResults.style.display = 'none';
        appGrid.style.display = 'block';
    }

    // ============================================
    // Keyboard Shortcuts
    // ============================================

    document.addEventListener('keydown', function(e) {
        // CMD/CTRL + K to focus search
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }

        // ESC to clear search
        if (e.key === 'Escape' && document.activeElement === searchInput) {
            searchInput.value = '';
            searchInput.blur();
            showAllApps();
        }
    });

    // ============================================
    // Keyboard Navigation
    // ============================================

    let focusedIndex = -1;

    searchInput.addEventListener('keydown', function(e) {
        if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Enter') {
            return;
        }

        const visibleTiles = Array.from(
            appGrid.querySelectorAll('.app-tile:not([style*="display: none"])')
        );

        if (visibleTiles.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            focusedIndex = Math.min(focusedIndex + 1, visibleTiles.length - 1);
            visibleTiles[focusedIndex].focus();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            focusedIndex = Math.max(focusedIndex - 1, 0);
            visibleTiles[focusedIndex].focus();
        } else if (e.key === 'Enter' && visibleTiles.length > 0) {
            e.preventDefault();
            visibleTiles[0].click();
        }
    });

    // ============================================
    // Analytics Tracking
    // ============================================

    appGrid.addEventListener('click', function(e) {
        const tile = e.target.closest('.app-tile');
        if (!tile) return;

        const appId = tile.dataset.appId;
        const appName = tile.dataset.name;

        // Track app launch (can integrate with analytics service)
        console.log('App launched:', appName, appId);

        // Save to recent apps (localStorage)
        saveRecentApp(appId, appName);
    });

    function saveRecentApp(appId, appName) {
        try {
            let recent = JSON.parse(localStorage.getItem('recentApps') || '[]');

            // Remove if already exists
            recent = recent.filter(app => app.id !== appId);

            // Add to front
            recent.unshift({
                id: appId,
                name: appName,
                timestamp: Date.now()
            });

            // Keep only last 10
            recent = recent.slice(0, 10);

            localStorage.setItem('recentApps', JSON.stringify(recent));
        } catch (e) {
            console.error('Failed to save recent app:', e);
        }
    }

    // ============================================
    // Favorites (Future Enhancement)
    // ============================================

    // TODO: Implement favorites toggle
    // - Add star icon to each tile
    // - Store favorites in localStorage or user preferences
    // - Show favorites section at top of grid

    // ============================================
    // Performance: Lazy Load Badges
    // ============================================

    // For future: If badge calculations become expensive,
    // fetch them via AJAX after initial page load

})();
