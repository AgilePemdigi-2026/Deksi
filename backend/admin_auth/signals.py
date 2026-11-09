from datetime import timedelta

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

from .permissions import is_admin


@receiver(user_logged_in, dispatch_uid="admin_auth.absolute_session_expiry")
def set_session_expiry(sender, request, user, **kwargs):
    if is_admin(user):
        request.session.set_expiry(timezone.now() + timedelta(hours=8))
