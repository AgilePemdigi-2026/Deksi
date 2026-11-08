"""Local-only reset API; delivery/timing production acceptance remains a separate gate."""

import json
import logging
import re
import unicodedata
from functools import wraps
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import RequestDataTooBig, ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .backends import client_ip
from .forms import AdminSetPasswordForm
from .reset_limits import consume
from .views import json_response

logger = logging.getLogger(__name__)
ACCEPTED = {"code": "reset_request_accepted", "accepted": True}
FIELD_LIMITS = {"email": 254, "uid": 256, "token": 256, "newPassword": 4096, "confirmPassword": 4096}


class ResetInputError(ValueError):
    def __init__(self, code, status=400):
        self.code, self.status = code, status


def response(data, status=200):
    result = json_response(data, status)
    result["Referrer-Policy"] = "no-referrer"
    result["X-Robots-Tag"] = "noindex, nofollow"
    return result


def frontend_origin():
    value = getattr(settings, "ADMIN_PASSWORD_RESET_FRONTEND_ORIGIN", "")
    parsed = urlsplit(value)
    if (
        not value
        or any(char.isspace() for char in value)
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.scheme not in ("https", "http")
        or (parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"))
    ):
        raise ValueError("Invalid reset origin configuration")
    port = parsed.port  # urlsplit also rejects malformed and out-of-range ports.
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Invalid reset origin configuration")
    return value.rstrip("/")


def configured():
    return (
        getattr(settings, "ADMIN_PASSWORD_RESET_ENABLED", False) is True
        and settings.MAILERS.get("default", {}).get("BACKEND") == "django.core.mail.backends.locmem.EmailBackend"
        and settings.PASSWORD_RESET_TIMEOUT == 1800
        and bool(frontend_origin())
    )


def endpoint(view):
    @wraps(view)
    def wrapped(request):
        if request.method != "POST":
            result = response({"code": "method_not_allowed"}, 405)
            result["Allow"] = "POST"
            return result
        try:
            if not configured():
                return response({"code": "reset_unavailable"}, 503)
            return view(request)
        except ResetInputError as error:
            return response({"code": error.code}, error.status)
        except Exception:
            # Never log exception values, request bodies or reset capabilities.
            logger.error("Reset operation failed; diagnostic details suppressed to protect credentials.")
            return response({"code": "reset_unavailable"}, 503)

    return wrapped


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def payload(request, fields):
    if request.content_type != "application/json":
        raise ResetInputError("unsupported_media_type", 415)
    try:
        length = int(request.META.get("CONTENT_LENGTH") or 0)
        if length < 0:
            raise ValueError
        if length > 16384:
            raise ResetInputError("request_too_large", 413)
        body = request.body
        if len(body) > 16384:
            raise ResetInputError("request_too_large", 413)
        data = json.loads(body.decode("utf-8"), object_pairs_hook=unique_pairs)
        if not isinstance(data, dict) or set(data) != set(fields):
            raise ValueError
        for field in fields:
            value = data[field]
            if not isinstance(value, str) or not value or len(value) > FIELD_LIMITS[field]:
                raise ValueError
            value.encode("utf-8")
        for field in ("uid", "token"):
            if field in data and not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", data[field]):
                raise ResetInputError("invalid_reset_link")
        if "email" in data:
            data["email"] = data["email"].strip()
            validate_email(data["email"])
        return data
    except RequestDataTooBig:
        raise ResetInputError("request_too_large", 413) from None
    except ResetInputError:
        raise
    except (ValueError, RecursionError, ValidationError):
        raise ResetInputError("invalid_request") from None


def canonical_email(value):
    return unicodedata.normalize("NFKC", value).casefold()


def recipient(email):
    # User.email is not unique/canonical-indexed. Fail closed across ALL roles,
    # including Unicode equivalents on SQLite; review scan cost before public deployment.
    identity = canonical_email(email)
    matches = []
    for user in get_user_model()._default_manager.exclude(email="").iterator(chunk_size=200):
        if canonical_email(user.email) == identity:
            matches.append(user)
            if len(matches) > 1:
                return None
    if len(matches) != 1:
        return None
    user = matches[0]
    return user if user.is_active and user.is_staff and user.has_usable_password() else None


@endpoint
def request_reset(request):
    data = payload(request, ("email",))
    if not consume("request-ip", client_ip(request) or "invalid", 20):
        return response({"code": "rate_limited"}, 429)
    if not consume("request-email", canonical_email(data["email"]), 3):
        return response(ACCEPTED, 202)
    try:
        user = recipient(data["email"])
        if user is not None:
            fragment = urlencode(
                {"uid": urlsafe_base64_encode(force_bytes(user.pk)), "token": default_token_generator.make_token(user)}
            )
            reset_url = frontend_origin() + "/admin/reset-password#" + fragment
            message = render_to_string(
                "admin_auth/password_reset_email.txt", {"reset_url": reset_url, "timeout_minutes": 30}
            )
            send_mail(
                subject="DEKSI — Pemulihan kata sandi Admin",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
    except Exception:
        logger.warning("Reset request acknowledged; target processing failed (details suppressed).")
    return response(ACCEPTED, 202)


def capability_user(data):
    try:
        identity = urlsafe_base64_decode(data["uid"]).decode("ascii")
        if not identity.isdecimal() or len(identity) > 19:
            return None
        pk = int(identity)
        if pk < 1 or pk > 9223372036854775807 or urlsafe_base64_encode(force_bytes(pk)) != data["uid"]:
            return None
        user = get_user_model()._default_manager.filter(pk=pk).first()
        if user is None or not default_token_generator.check_token(user, data["token"]):
            return None
        unique = recipient(user.email)
        return user if unique is not None and unique.pk == user.pk else None
    except (ValueError, UnicodeError, OverflowError):
        return None


@endpoint
def check_reset(request):
    data = payload(request, ("uid", "token"))
    if not consume("capability-ip", client_ip(request) or "invalid", 20):
        return response({"code": "rate_limited"}, 429)
    if capability_user(data) is None:
        return response({"code": "invalid_reset_link"}, 400)
    return response({"valid": True})


def commit_password(user, form):
    """CAS the token-bound snapshot; plain check-token + save is not single-use under races."""
    previous_hash = user.password
    expected = {
        "pk": user.pk,
        "password": previous_hash,
        "email": user.email,
        "last_login": user.last_login,
        "is_active": True,
        "is_staff": True,
    }
    form.save(commit=False)
    raw = user._password
    user._password = None
    with transaction.atomic():
        if get_user_model()._default_manager.filter(**expected).update(password=user.password) != 1:
            return False
        # CAS bypasses User.save(); retain Django's password-validator lifecycle after commit.
        transaction.on_commit(lambda: password_validation.password_changed(raw, user))
    return True


@endpoint
def confirm_reset(request):
    data = payload(request, ("uid", "token", "newPassword", "confirmPassword"))
    if not consume("capability-ip", client_ip(request) or "invalid", 20):
        return response({"code": "rate_limited"}, 429)
    user = capability_user(data)
    if user is None:
        return response({"code": "invalid_reset_link"}, 400)
    form = AdminSetPasswordForm(user, {"new_password1": data["newPassword"], "new_password2": data["confirmPassword"]})
    if not form.is_valid():
        fields = {}
        allowed = {
            "password_too_short",
            "password_too_common",
            "password_too_similar",
            "password_entirely_numeric",
            "password_unchanged",
            "password_mismatch",
        }
        for errors in form.errors.as_data().values():
            for error in errors:
                code = error.code if error.code in allowed else "password_invalid"
                field = "confirmPassword" if code == "password_mismatch" else "newPassword"
                fields.setdefault(field, []).append(code)
        return response({"code": "password_validation_failed", "fields": fields}, 400)
    if not commit_password(user, form):
        return response({"code": "invalid_reset_link"}, 400)
    return response({"code": "reset_complete", "authenticated": False})
