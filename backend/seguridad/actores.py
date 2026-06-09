"""Permisos de acciones por actor — matriz Seguricel S.A.C."""

from logistica.permissions import usuario_es_admin, usuario_tiene_rol

ROLES_INVENTARIO_ESCRITURA = ('jefe_almacen', 'supervisor_almacen', 'operario_almacen')
ROLES_INVENTARIO_LECTURA = ('jefe_operaciones', 'area_administrativa', 'gerente_general')
ROLES_AMBIENTAL_ESCRITURA = ('operario_almacen', 'jefe_almacen', 'supervisor_almacen')
ROLES_MAESTROS_COMPRAS = ('jefe_compras',)


def puede_modificar_inventario(user):
    """Registra movimientos, cuadre físico y operaciones de almacén."""
    return usuario_es_admin(user) or usuario_tiene_rol(user, ROLES_INVENTARIO_ESCRITURA)


def puede_ver_inventario(user):
    """Consulta stock, kardex y discrepancias (solo lectura para roles de supervisión)."""
    return puede_modificar_inventario(user) or usuario_tiene_rol(user, ROLES_INVENTARIO_LECTURA)


def puede_registrar_medicion_ambiental(user):
    return usuario_es_admin(user) or usuario_tiene_rol(user, ROLES_AMBIENTAL_ESCRITURA)


def puede_gestionar_maestros_compras(user):
    """Proveedores, catálogo y datos para compras."""
    return usuario_es_admin(user) or usuario_tiene_rol(user, ROLES_MAESTROS_COMPRAS)


def puede_ejecutar_control_calidad(user):
    """Inspecciona productos y emite informes de conformidad/rechazo."""
    return usuario_es_admin(user) or usuario_tiene_rol(user, ['encargado_calidad'])
