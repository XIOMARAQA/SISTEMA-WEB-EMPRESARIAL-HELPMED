from rest_framework.permissions import BasePermission


def es_admin_o_superusuario(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.roles_asignados.filter(rol__codigo='admin', rol__activo=True).exists()


class EsAdminOSuperusuario(BasePermission):
    """Solo administrador del sistema o superusuario Django."""

    message = 'Acceso restringido a administradores.'

    def has_permission(self, request, view):
        return es_admin_o_superusuario(request.user)


class TieneAlgunRol(BasePermission):
    """Permite si el usuario tiene al menos uno de los roles indicados en la vista."""

    message = 'No tiene permiso para esta acción.'

    def has_permission(self, request, view):
        if es_admin_o_superusuario(request.user):
            return True
        roles_requeridos = getattr(view, 'roles_requeridos', None) or []
        if not roles_requeridos:
            return True
        return request.user.roles_asignados.filter(
            rol__codigo__in=roles_requeridos, rol__activo=True,
        ).exists()
