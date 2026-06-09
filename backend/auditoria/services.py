"""Registro automático de trazabilidad — ISO 27005."""

from auditoria.models import RegistroAuditoria

RECURSO_MODULO = {
    'marcas': ('maestros', 'Marca'),
    'unidades-medida': ('maestros', 'Unidad de medida'),
    'proveedores': ('maestros', 'Proveedor'),
    'subcategorias': ('maestros', 'Subcategoría'),
    'categorias': ('maestros', 'Categoría'),
    'productos': ('maestros', 'Producto'),
    'ordenes-compra': ('recepcion', 'Factura / orden de compra'),
    'detalle-factura': ('recepcion', 'Detalle de factura'),
    'documentos': ('recepcion', 'Documento adjunto'),
    'incidencias-calidad': ('calidad', 'Incidencia de calidad'),
    'evidencias-calidad': ('calidad', 'Evidencia de calidad'),
    'mediciones': ('ambiental', 'Medición ambiental'),
    'acciones-correctivas': ('ambiental', 'Acción correctiva'),
    'inventarios': ('inventario', 'Inventario'),
    'movimientos-inventario': ('inventario', 'Movimiento de inventario'),
    'activos': ('riesgos', 'Activo'),
    'amenazas': ('riesgos', 'Amenaza'),
    'vulnerabilidades': ('riesgos', 'Vulnerabilidad'),
    'riesgos': ('riesgos', 'Riesgo'),
    'evaluaciones-riesgo': ('riesgos', 'Evaluación de riesgo'),
    'tratamientos-riesgo': ('riesgos', 'Tratamiento de riesgo'),
    'controles-iso27001': ('riesgos', 'Control ISO 27001'),
    'auditorias': ('auditoria', 'Auditoría formal'),
    'usuarios': ('seguridad', 'Usuario'),
    'roles': ('seguridad', 'Rol'),
    'notificaciones': ('notificaciones', 'Notificación'),
}

ACCION_POR_METODO = {
    'POST': 'Crear',
    'PUT': 'Actualizar',
    'PATCH': 'Actualizar',
    'DELETE': 'Eliminar',
}


def _ip_desde_request(request):
    if not request:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def registrar_accion(
    *,
    accion,
    modulo,
    descripcion='',
    usuario=None,
    tabla='',
    registro_id=None,
    ip_address=None,
    request=None,
):
    if ip_address is None and request is not None:
        ip_address = _ip_desde_request(request)
    RegistroAuditoria.objects.create(
        usuario=usuario if usuario and usuario.is_authenticated else None,
        accion=accion[:100],
        modulo=modulo[:50],
        tabla=(tabla or '')[:50],
        registro_id=registro_id,
        ip_address=ip_address,
        descripcion=descripcion or '',
    )


def registrar_desde_request(request, response, usuario=None):
    """Registra automáticamente operaciones exitosas en la API."""
    if request.method not in ACCION_POR_METODO:
        return
    if response.status_code >= 400:
        return

    path = request.path.rstrip('/')
    if path.startswith('/api/auth/login') or path.startswith('/api/auth/refresh'):
        return
    if path.startswith('/api/registros-auditoria'):
        return
    if path.startswith('/api/dashboard'):
        return

    partes = [p for p in path.replace('/api/', '').split('/') if p]
    if not partes:
        return

    recurso = partes[0]
    registro_id = None
    if len(partes) >= 2 and partes[1].isdigit():
        registro_id = int(partes[1])

    info = RECURSO_MODULO.get(recurso)
    if not info:
        modulo = 'sistema'
        entidad = recurso.replace('-', ' ')
    else:
        modulo, entidad = info

    accion = ACCION_POR_METODO[request.method]
    sufijo = f' (ID {registro_id})' if registro_id else ''
    descripcion = f'{accion} {entidad}{sufijo}'

    if usuario is None:
        usuario = getattr(request, 'user', None)

    registrar_accion(
        request=request,
        usuario=usuario,
        accion=accion,
        modulo=modulo,
        tabla=recurso,
        registro_id=registro_id,
        descripcion=descripcion,
    )
