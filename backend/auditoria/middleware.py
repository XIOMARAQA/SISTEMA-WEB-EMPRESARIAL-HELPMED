from auditoria.services import registrar_desde_request


def _usuario_desde_request(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return user
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        auth = JWTAuthentication()
        result = auth.authenticate(request)
        if result:
            return result[0]
    except Exception:
        pass
    return user if user and user.is_authenticated else None


class AuditoriaMiddleware:
    """Registra automáticamente POST, PUT, PATCH y DELETE exitosos en la API."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/api/'):
            try:
                registrar_desde_request(request, response, usuario=_usuario_desde_request(request))
            except Exception:
                pass
        return response
