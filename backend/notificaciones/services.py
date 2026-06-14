from django.contrib.auth import get_user_model
from django.db.models import Q

from notificaciones.models import Notificacion

User = get_user_model()


def usuarios_por_roles(codigos_roles, excluir=None):
    """Usuarios activos con al menos uno de los roles operativos indicados."""
    roles = [r for r in (codigos_roles or []) if r and r != 'admin']
    if not roles:
        return User.objects.none()
    qs = User.objects.filter(
        estado=User.Estado.ACTIVO,
        is_active=True,
        roles_asignados__rol__codigo__in=roles,
        roles_asignados__rol__activo=True,
    ).distinct()
    if excluir:
        qs = qs.exclude(pk=excluir.pk)
    return qs


def usuarios_administradores(excluir=None):
    """Superusuarios y usuarios con rol admin reciben TODAS las notificaciones."""
    qs = User.objects.filter(estado=User.Estado.ACTIVO, is_active=True).filter(
        Q(is_superuser=True)
        | Q(roles_asignados__rol__codigo='admin', roles_asignados__rol__activo=True)
    ).distinct()
    if excluir:
        qs = qs.exclude(pk=excluir.pk)
    return qs


def destinatarios_notificacion(codigos_roles, excluir_usuario=None):
    """Une destinatarios por rol + administradores/superusuarios (sin duplicar)."""
    destinatarios = {}
    for usuario in usuarios_por_roles(codigos_roles, excluir=excluir_usuario):
        destinatarios[usuario.pk] = usuario
    for usuario in usuarios_administradores(excluir=excluir_usuario):
        destinatarios[usuario.pk] = usuario
    return list(destinatarios.values())


def destinatarios_alerta_seguridad(codigos_roles, excluir_usuario=None):
    """
    Destinatarios de alertas de acceso (ISO 27001).
    Incluye superusuarios aunque la cuenta esté bloqueada temporalmente.
    """
    destinatarios = {}
    for usuario in usuarios_por_roles(codigos_roles, excluir=excluir_usuario):
        destinatarios[usuario.pk] = usuario
    qs = User.objects.filter(
        Q(is_superuser=True)
        | Q(
            roles_asignados__rol__codigo='admin',
            roles_asignados__rol__activo=True,
            estado=User.Estado.ACTIVO,
            is_active=True,
        )
    ).distinct()
    if excluir_usuario:
        qs = qs.exclude(pk=excluir_usuario.pk)
    for usuario in qs:
        destinatarios[usuario.pk] = usuario
    return list(destinatarios.values())


def crear_notificacion(
    usuario,
    *,
    titulo,
    mensaje,
    tipo=Notificacion.Tipo.SISTEMA,
    prioridad=Notificacion.Prioridad.MEDIA,
    referencia_modulo='',
    referencia_id=None,
):
    notif = Notificacion.objects.create(
        usuario=usuario,
        titulo=titulo,
        mensaje=mensaje,
        tipo=tipo,
        prioridad=prioridad,
        referencia_modulo=referencia_modulo,
        referencia_id=referencia_id,
    )
    try:
        from notificaciones.mysmsgate import enviar_sms_mysmsgate
        enviar_sms_mysmsgate(notif)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('SMS MySMSGate no enviado para notificación %s', notif.pk)
    return notif


def notificar_por_roles(
    codigos_roles,
    *,
    titulo,
    mensaje,
    tipo=Notificacion.Tipo.SISTEMA,
    prioridad=Notificacion.Prioridad.MEDIA,
    referencia_modulo='',
    referencia_id=None,
    excluir_usuario=None,
):
    """
    Notifica a usuarios con los roles indicados (matriz en destinatarios.py).
    Superusuarios y rol admin reciben siempre la notificación.
    """
    creadas = []
    for usuario in destinatarios_notificacion(codigos_roles, excluir_usuario=excluir_usuario):
        creadas.append(
            crear_notificacion(
                usuario,
                titulo=titulo,
                mensaje=mensaje,
                tipo=tipo,
                prioridad=prioridad,
                referencia_modulo=referencia_modulo,
                referencia_id=referencia_id,
            )
        )
    return creadas


def notificar_seguridad_por_roles(
    codigos_roles,
    *,
    titulo,
    mensaje,
    prioridad=Notificacion.Prioridad.ALTA,
    referencia_modulo='auditoria',
    referencia_id=None,
    excluir_usuario=None,
):
    """Alertas de acceso: admin/superusuario + roles indicados (p. ej. auditor_seguridad)."""
    creadas = []
    for usuario in destinatarios_alerta_seguridad(codigos_roles, excluir_usuario=excluir_usuario):
        creadas.append(
            crear_notificacion(
                usuario,
                titulo=titulo,
                mensaje=mensaje,
                tipo=Notificacion.Tipo.SEGURIDAD,
                prioridad=prioridad,
                referencia_modulo=referencia_modulo,
                referencia_id=referencia_id,
            )
        )
    return creadas
