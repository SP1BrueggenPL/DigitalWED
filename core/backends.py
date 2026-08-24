from django.contrib.auth.hashers import check_password
from .models import UserProfile


class ChipAuthBackend:
    """Authenticate using chip number + authorization code."""

    def authenticate(self, request, chip_number=None, auth_code=None):
        if not chip_number or not auth_code:
            return None
        try:
            profile = UserProfile.objects.select_related('user').get(chip_number=chip_number)
        except UserProfile.DoesNotExist:
            return None
        if not profile.auth_code_set:
            return None
        if not check_password(auth_code, profile.auth_code):
            return None
        user = profile.user
        if not user.is_active:
            return None
        return user

    def get_user(self, user_id):
        from django.contrib.auth.models import User
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
