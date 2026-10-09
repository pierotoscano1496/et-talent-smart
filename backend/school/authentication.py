import hashlib
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from .models import AccessToken


class BearerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header:
            return None
        if len(header) != 2 or header[0].lower() != b"bearer":
            raise AuthenticationFailed("Sesión inválida.")
        digest = hashlib.sha256(header[1]).hexdigest()
        token = AccessToken.objects.select_related("user").filter(
            digest=digest, expires_at__gt=timezone.now(), user__is_active=True,
        ).first()
        if token is None:
            raise AuthenticationFailed("La sesión expiró o no es válida.")
        return token.user, token

    def authenticate_header(self, request):
        return "Bearer"

