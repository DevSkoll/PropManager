"""
Core views for PropManager.
Includes health check endpoints for container orchestration.
"""

from django.http import JsonResponse
from django.db import connection
from django.conf import settings


def health_check(request):
    """
    Health check endpoint for container orchestration.

    Returns:
        - 200 OK with JSON {"status": "healthy"} when all systems operational
        - 503 Service Unavailable when database or other critical services fail

    Usage:
        curl http://localhost:8000/health/
    """
    health_data = {
        "status": "healthy",
        "checks": {},
    }
    status_code = 200

    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_data["checks"]["database"] = "connected"
    except Exception as e:
        health_data["status"] = "unhealthy"
        health_data["checks"]["database"] = f"error: {str(e)}"
        status_code = 503

    # Check Redis connectivity (if configured)
    redis_url = getattr(settings, "REDIS_URL", None)
    if redis_url:
        try:
            import redis

            r = redis.from_url(redis_url)
            r.ping()
            health_data["checks"]["redis"] = "connected"
        except Exception as e:
            health_data["status"] = "unhealthy"
            health_data["checks"]["redis"] = f"error: {str(e)}"
            status_code = 503

    return JsonResponse(health_data, status=status_code)


def liveness_check(request):
    """
    Simple liveness probe - just confirms the application is running.

    Usage:
        curl http://localhost:8000/live/
    """
    return JsonResponse({"status": "alive"})


def readiness_check(request):
    """
    Readiness probe - confirms the application can accept traffic.
    More thorough than liveness, includes database check.

    Usage:
        curl http://localhost:8000/ready/
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ready"})
    except Exception as e:
        return JsonResponse({"status": "not_ready", "error": str(e)}, status=503)
