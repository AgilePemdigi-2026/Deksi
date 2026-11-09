from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError


class AdminSetPasswordForm(SetPasswordForm):
    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("new_password1")
        if password and check_password(password, self.user.password):
            self.add_error("new_password1", ValidationError("Choose a different password.", code="password_unchanged"))
        return cleaned
