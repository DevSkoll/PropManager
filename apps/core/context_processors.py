"""
Context processors for PropManager.

Provides global context variables to all templates.
"""

import json
from django.urls import reverse, NoReverseMatch


def app_launcher_context(request):
    """
    Provide app tiles data for the navigation launcher.
    Only loaded for authenticated admin users.
    """
    # Skip for non-admin users
    if not request.user.is_authenticated:
        return {}

    if not getattr(request.user, 'is_admin_user', False):
        return {}

    from apps.core.dashboard_data import get_app_tiles, CATEGORY_INFO

    try:
        tiles = get_app_tiles()

        # Convert tiles to JSON-serializable format with resolved URLs
        tiles_data = []
        for tile in tiles:
            try:
                url = reverse(tile.url)
            except NoReverseMatch:
                url = '#'

            # Calculate badge if function exists
            badge = 0
            if tile.badge_func:
                try:
                    badge = tile.badge_func(request)
                except Exception:
                    badge = 0

            tiles_data.append({
                'id': tile.id,
                'name': tile.name,
                'description': tile.description,
                'icon': tile.icon,
                'url': url,
                'category': tile.category,
                'gradient': tile.gradient,
                'keywords': tile.keywords,
                'badge': badge if badge > 0 else None,
            })

        return {
            'app_tiles_json': json.dumps(tiles_data),
            'category_info_json': json.dumps(CATEGORY_INFO),
        }

    except Exception as e:
        # Fail silently - navigation should still work without app data
        return {
            'app_tiles_json': '[]',
            'category_info_json': '{}',
        }
