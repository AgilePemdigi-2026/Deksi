import json

from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.cache import add_never_cache_headers
from django.views.csrf import csrf_failure as django_csrf_failure
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .permissions import is_admin


def json_response(data, status=200):
    response = JsonResponse(data, status=status)
    add_never_cache_headers(response)
    return response


@never_cache
@require_GET
def csrf_bootstrap(request):
    return json_response({"csrfToken": get_token(request)})


@never_cache
@require_POST
def login_view(request):
    if request.content_type != "application/json":
        return json_response({"error": "Gunakan JSON untuk permintaan login.", "code": "unsupported_media_type"}, 415)
    try:
        payload = login_payload(request)
    except (ValueError, RecursionError, RequestDataTooBig):
        return json_response({"error": "Permintaan login tidak valid.", "code": "invalid_request"}, 400)
    user = authenticate(request, username=payload["identifier"], password=payload["password"])
    if user is None:
        return json_response(
            {"error": "Email/nama pengguna atau kata sandi tidak valid.", "code": "invalid_credentials"}, 401
        )
    login(request, user)
    return json_response(
        {
            "authenticated": True,
            "user": {"id": user.pk, "username": user.get_username(), "isAdmin": bool(user.is_active and user.is_staff)},
            "csrfToken": get_token(request),
        }
    )


def login_payload(request):
    if int(request.META.get("CONTENT_LENGTH") or 0) > 16384:
        raise ValueError
    body = request.body
    if len(body) > 16384:
        raise ValueError
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError
    identifier, password = payload.get("identifier"), payload.get("password")
    if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 254:
        raise ValueError
    if not isinstance(password, str) or not password or len(password) > 4096:
        raise ValueError
    identifier.encode("utf-8")
    password.encode("utf-8")
    return payload


@never_cache
@require_GET
def session_view(request):
    if not request.user.is_authenticated:
        return json_response({"authenticated": False, "user": None})
    if not is_admin(request.user):
        return json_response({"error": "Akses Admin diperlukan.", "code": "forbidden"}, 403)
    return json_response(
        {
            "authenticated": True,
            "user": {"id": request.user.pk, "username": request.user.get_username(), "isAdmin": True},
        }
    )


@never_cache
@require_POST
def logout_view(request):
    logout(request)
    return json_response({"authenticated": False, "user": None})


def csrf_failure(request, reason=""):
    if request.path_info.startswith("/api/auth/"):
        return json_response({"error": "Pemeriksaan keamanan gagal. Muat ulang formulir.", "code": "csrf_failed"}, 403)
    return django_csrf_failure(request, reason=reason)


def lockout_response(request, original_response=None, credentials=None):
    return json_response({"error": "Terlalu banyak percobaan masuk. Coba lagi nanti.", "code": "rate_limited"}, 429)
