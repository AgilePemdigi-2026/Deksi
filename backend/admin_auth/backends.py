from ipaddress import ip_address

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.utils.crypto import salted_hmac

from .permissions import is_admin


def resolve_identifier(identifier):
    model = get_user_model()
    identifier = model.normalize_username(identifier.strip())
    matches = list(
        model._default_manager.filter(Q(**{model.USERNAME_FIELD: identifier}) | Q(email__iexact=identifier)).distinct()[
            :2
        ]
    )
    return matches[0] if len(matches) == 1 else None


class AdminBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        user = resolve_identifier(username)
        if user is None:
            get_user_model()().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user) and is_admin(user):
            return user
        return None


def axes_username(request, credentials=None):
    identifier = (credentials or {}).get("username", request.POST.get("username", ""))
    if not isinstance(identifier, str):
        identifier = ""
    user = resolve_identifier(identifier)
    identity = f"user:{user.pk}" if user is not None else f"identifier:{identifier.strip().casefold()}"
    return salted_hmac("deksi.admin_auth.rate_key", identity, algorithm="sha256").hexdigest()


def client_ip(request):
    try:
        return str(ip_address(request.META.get("REMOTE_ADDR")))
    except (ValueError, TypeError):
        return None
