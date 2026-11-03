def is_admin(user):
    return bool(user.is_authenticated and user.is_active and user.is_staff)
