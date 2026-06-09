"""
Notificaciones in-app según flujo de negocio — Logística y Almacén (Seguricel S.A.C.)
Sin correo: cada evento notifica a los roles responsables (ver destinatarios.py).
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from notificaciones.destinatarios import DESTINATARIOS
from notificaciones.models import Notificacion
from notificaciones.services import notificar_por_roles, notificar_seguridad_por_roles
from logistica.permissions import usuario_es_admin, usuario_tiene_rol
from seguridad.models import IntentoLogin

VENTANA_ALERTA_LOGIN_MIN = 15

MOTIVOS_LOGIN_CRITICOS = frozenset({
    'Cuenta bloqueada por intentos fallidos',
    'Cuenta inactiva o bloqueada',
})


def _factura_label(orden):
    return getattr(orden, 'numero_completo', str(orden.pk))


def _roles(evento):
    return DESTINATARIOS[evento]


# —— Proceso 1: Recepción de insumos ——

def notificar_factura_registrada(orden, actor=None):
    """Jefe de compras registra factura → Jefe de almacén valida documentación."""
    ref = _factura_label(orden)
    notificar_por_roles(
        _roles('factura_registrada'),
        titulo='Nueva factura pendiente de validación',
        mensaje=(
            f'La factura {ref} del proveedor {orden.proveedor.razon_social} '
            f'requiere validación documental (UC 01).'
        ),
        tipo=Notificacion.Tipo.SISTEMA,
        prioridad=Notificacion.Prioridad.MEDIA,
        referencia_modulo='recepcion',
        referencia_id=orden.id,
        excluir_usuario=actor,
    )


def notificar_documentacion_rechazada(orden, actor=None):
    """Documentación incompleta → Jefe de compras regulariza."""
    ref = _factura_label(orden)
    motivo = (orden.motivo_rechazo or 'Documentación incompleta').strip()
    notificar_por_roles(
        _roles('documentacion_rechazada'),
        titulo='Factura rechazada — documentación incompleta',
        mensaje=f'La factura {ref} fue rechazada en validación documental. Motivo: {motivo}',
        tipo=Notificacion.Tipo.CALIDAD,
        prioridad=Notificacion.Prioridad.ALTA,
        referencia_modulo='recepcion',
        referencia_id=orden.id,
        excluir_usuario=actor,
    )


def notificar_documentacion_aprobada(orden, actor=None):
    """Documentación OK → Control de calidad inspecciona; operarios trasladan a inspección."""
    ref = _factura_label(orden)
    notificar_por_roles(
        _roles('documentacion_aprobada'),
        titulo='Factura lista para control de calidad',
        mensaje=(
            f'La factura {ref} fue validada documentalmente. '
            f'Proceda con inspección física en zona de inspección (UC 02).'
        ),
        tipo=Notificacion.Tipo.CALIDAD,
        prioridad=Notificacion.Prioridad.MEDIA,
        referencia_modulo='calidad',
        referencia_id=orden.id,
        excluir_usuario=actor,
    )


def notificar_control_calidad_finalizado(orden, rechazos, actor=None):
    """Cierre de control de calidad → informar según resultado."""
    ref = _factura_label(orden)
    if rechazos:
        notificar_por_roles(
            _roles('calidad_con_rechazos_gestion'),
            titulo='Reporte de productos rechazados',
            mensaje=(
                f'Control de calidad de {ref} finalizado con {rechazos} ítem(s) rechazado(s). '
                f'Revise incidencias y gestione con el proveedor.'
            ),
            tipo=Notificacion.Tipo.CALIDAD,
            prioridad=Notificacion.Prioridad.ALTA,
            referencia_modulo='calidad',
            referencia_id=orden.id,
            excluir_usuario=actor,
        )
        notificar_por_roles(
            _roles('calidad_con_rechazos_almacen'),
            titulo='Recepción con observaciones de calidad',
            mensaje=(
                f'Factura {ref}: {rechazos} ítem(s) rechazado(s). '
                f'Stock ingresado solo por cantidades aceptadas.'
            ),
            tipo=Notificacion.Tipo.CALIDAD,
            prioridad=Notificacion.Prioridad.MEDIA,
            referencia_modulo='inventario',
            referencia_id=orden.id,
            excluir_usuario=actor,
        )
    else:
        notificar_por_roles(
            _roles('calidad_conforme_compras'),
            titulo='Conformidad de recepción',
            mensaje=f'La factura {ref} fue recepcionada conforme. Sin productos rechazados.',
            tipo=Notificacion.Tipo.CALIDAD,
            prioridad=Notificacion.Prioridad.MEDIA,
            referencia_modulo='recepcion',
            referencia_id=orden.id,
            excluir_usuario=actor,
        )
        notificar_por_roles(
            _roles('calidad_conforme_almacen'),
            titulo='Mercadería lista para almacenamiento',
            mensaje=f'Factura {ref}: control de calidad conforme. Stock actualizado en inventario.',
            tipo=Notificacion.Tipo.INVENTARIO,
            prioridad=Notificacion.Prioridad.MEDIA,
            referencia_modulo='inventario',
            referencia_id=orden.id,
            excluir_usuario=actor,
        )


# —— Proceso 2: Control ambiental y vencimientos ——

def notificar_incidente_ambiental(medicion, actor=None):
    """Medición fuera de rango → calidad, almacén, operaciones y gerencia."""
    notificar_por_roles(
        _roles('incidente_ambiental'),
        titulo='Alerta ambiental — temperatura fuera de rango',
        mensaje=(
            f'Medición del {medicion.fecha} a las {medicion.hora}: '
            f'{medicion.temperatura}°C (rango 20–25°C). Ubicación: {medicion.ubicacion}. '
            f'Se requiere acción correctiva.'
        ),
        tipo=Notificacion.Tipo.AMBIENTAL,
        prioridad=Notificacion.Prioridad.ALTA,
        referencia_modulo='ambiental',
        referencia_id=medicion.id,
        excluir_usuario=actor,
    )


def notificar_clasificacion_vencimiento(inventario, clasificacion_anterior=None):
    """Alertas por escenario de vencimiento (REQ 05)."""
    producto = inventario.producto.nombre
    lote = inventario.lote
    dias = ''
    if inventario.fecha_vencimiento:
        from django.utils import timezone
        d = (inventario.fecha_vencimiento - timezone.now().date()).days
        dias = f' ({d} días)' if d >= 0 else ' (caducado)'

    if clasificacion_anterior == inventario.clasificacion:
        return

    if inventario.clasificacion == 'reposicion':
        notificar_por_roles(
            _roles('vencimiento_reposicion'),
            titulo='Producto para reposición (30–60 días)',
            mensaje=f'{producto} — Lote {lote}{dias}. Elaborar reporte de reposición.',
            tipo=Notificacion.Tipo.INVENTARIO,
            prioridad=Notificacion.Prioridad.MEDIA,
            referencia_modulo='inventario',
            referencia_id=inventario.id,
        )
    elif inventario.clasificacion == 'alta_prioridad':
        notificar_por_roles(
            _roles('vencimiento_alta_prioridad'),
            titulo='Producto alta prioridad (<30 días)',
            mensaje=f'{producto} — Lote {lote}{dias}. Requiere revisión urgente.',
            tipo=Notificacion.Tipo.INVENTARIO,
            prioridad=Notificacion.Prioridad.ALTA,
            referencia_modulo='inventario',
            referencia_id=inventario.id,
        )
    elif inventario.clasificacion == 'retiro_inmediato':
        notificar_por_roles(
            _roles('vencimiento_retiro_inmediato'),
            titulo='Medicamento caducado — retiro inmediato',
            mensaje=(
                f'{producto} — Lote {lote} caducado o por retirar. '
                f'Separar del inventario activo y generar informe.'
            ),
            tipo=Notificacion.Tipo.INVENTARIO,
            prioridad=Notificacion.Prioridad.CRITICA,
            referencia_modulo='inventario',
            referencia_id=inventario.id,
        )


def notificar_stock_minimo(inventario):
    """Stock en o bajo mínimo → almacén, compras y gerencia."""
    if not inventario.producto.stock_minimo or inventario.cantidad > inventario.producto.stock_minimo:
        return
    from datetime import timedelta
    from django.utils import timezone

    desde = timezone.now() - timedelta(hours=24)
    if Notificacion.objects.filter(
        titulo='Alerta de stock mínimo',
        referencia_modulo='inventario',
        referencia_id=inventario.id,
        creado_en__gte=desde,
    ).exists():
        return
    notificar_por_roles(
        _roles('stock_minimo'),
        titulo='Alerta de stock mínimo',
        mensaje=(
            f'{inventario.producto.nombre} — Lote {inventario.lote}: '
            f'stock {inventario.cantidad} (mín. {inventario.producto.stock_minimo}). '
            f'Planificar reabastecimiento.'
        ),
        tipo=Notificacion.Tipo.INVENTARIO,
        prioridad=Notificacion.Prioridad.ALTA,
        referencia_modulo='inventario',
        referencia_id=inventario.id,
    )


def notificar_discrepancia_inventario(inventario, actor=None):
    """Cuadre físico con diferencia → área administrativa y jefe de almacén."""
    diff = inventario.cantidad_fisica - inventario.cantidad
    mensaje = (
        f'{inventario.producto.nombre} — Lote {inventario.lote}: '
        f'sistema {inventario.cantidad}, físico {inventario.cantidad_fisica} '
        f'(diferencia {diff:+}). Revise con almacén.'
    )
    notificar_por_roles(
        _roles('discrepancia_inventario'),
        titulo='Discrepancia de inventario — cuadre físico',
        mensaje=mensaje,
        tipo=Notificacion.Tipo.INVENTARIO,
        prioridad=Notificacion.Prioridad.ALTA,
        referencia_modulo='inventario',
        referencia_id=inventario.id,
        excluir_usuario=actor,
    )


def notificar_movimiento_inventario(movimiento, actor=None):
    """Operario registra entrada/salida → jefe de almacén supervisa."""
    if actor and (
        usuario_es_admin(actor)
        or usuario_tiene_rol(actor, _roles('movimiento_inventario'))
    ):
        return
    inv = movimiento.inventario
    tipo_label = 'Entrada' if movimiento.tipo == 'entrada' else 'Salida'
    notificar_por_roles(
        _roles('movimiento_inventario'),
        titulo=f'{tipo_label} de inventario registrada',
        mensaje=(
            f'{inv.producto.nombre} — Lote {inv.lote}: {tipo_label.lower()} de '
            f'{movimiento.cantidad} {inv.producto.unidad_medida}. '
            f'Stock actual: {movimiento.stock_posterior}.'
        ),
        tipo=Notificacion.Tipo.INVENTARIO,
        prioridad=Notificacion.Prioridad.BAJA,
        referencia_modulo='inventario',
        referencia_id=inv.id,
        excluir_usuario=actor,
    )


def alertar_inventario_actualizado(inventario, clasificacion_anterior=None):
    """Dispara alertas de vencimiento y stock mínimo tras actualizar inventario."""
    if clasificacion_anterior != inventario.clasificacion:
        notificar_clasificacion_vencimiento(inventario, clasificacion_anterior)
    notificar_stock_minimo(inventario)


# —— Seguridad — acceso e ISO 27001 / 27005 ——

def _intentos_fallidos_recientes(username, ip=None, minutos=VENTANA_ALERTA_LOGIN_MIN):
    desde = timezone.now() - timedelta(minutes=minutos)
    qs = IntentoLogin.objects.filter(
        exitoso=False,
        username=username,
        creado_en__gte=desde,
    )
    if ip:
        qs = qs.filter(ip_address=ip)
    return qs.count()


def _ya_notifico_login(username, titulo_parcial, minutos=VENTANA_ALERTA_LOGIN_MIN):
    desde = timezone.now() - timedelta(minutes=minutos)
    return Notificacion.objects.filter(
        tipo=Notificacion.Tipo.SEGURIDAD,
        titulo__icontains=titulo_parcial,
        mensaje__icontains=username,
        creado_en__gte=desde,
    ).exists()


def notificar_alerta_login(username, ip, motivo, max_attempts=None):
    """
    Alerta a admin + auditor de seguridad en eventos sospechosos de acceso.
    No notifica cada typo aislado; sí al alcanzar el umbral o en bloqueos.
    """
    max_attempts = max_attempts or getattr(settings, 'MAX_LOGIN_ATTEMPTS', 3)
    ip_txt = ip or 'desconocida'
    intentos = _intentos_fallidos_recientes(username, ip)

    if motivo in MOTIVOS_LOGIN_CRITICOS:
        evento = 'cuenta_bloqueada'
        prioridad = Notificacion.Prioridad.CRITICA
        titulo = 'Cuenta bloqueada — intentos de acceso'
        if motivo == 'Cuenta inactiva o bloqueada':
            titulo = 'Acceso denegado — cuenta inactiva o bloqueada'
            prioridad = Notificacion.Prioridad.ALTA
        mensaje = (
            f'Usuario «{username}» desde IP {ip_txt}. '
            f'Motivo: {motivo}. Revise el registro de auditoría.'
        )
        if _ya_notifico_login(username, titulo[:30]):
            return []
    elif intentos >= max_attempts:
        evento = 'alerta_login_fallido'
        prioridad = Notificacion.Prioridad.ALTA
        titulo = 'Intentos de acceso fallidos — posible incidente'
        mensaje = (
            f'Usuario «{username}» desde IP {ip_txt}: {intentos} intentos fallidos '
            f'en los últimos {VENTANA_ALERTA_LOGIN_MIN} min. Motivo: {motivo}.'
        )
        if _ya_notifico_login(username, 'Intentos de acceso'):
            return []
    else:
        return []

    return notificar_seguridad_por_roles(
        _roles(evento),
        titulo=titulo,
        mensaje=mensaje,
        prioridad=prioridad,
        referencia_modulo='auditoria',
    )
