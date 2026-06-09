"""
Acceso a módulos por rol — matriz de actores Seguricel S.A.C.

| Actor               | Puede (módulos)                         | No puede                          |
| ------------------- | --------------------------------------- | --------------------------------- |
| Jefe de Compras     | recepción, maestros, reportes           | inventario, calidad, ambiental    |
| Jefe de Almacén     | recepción*, calidad†, inventario, ambiental, reportes | maestros/compras, ejecutar QC |
| Operario de Almacén | inventario, ambiental                   | compras, calidad, reportes        |
| Control de Calidad  | calidad                                 | compras, inventario, ambiental    |
| Jefe de Operaciones | calidad†, inventario†, reportes         | registrar movimientos, ejecutar QC |
| Área Administrativa | inventario†, reportes                 | modificar almacén, compras        |
| Gerente General     | calidad†, inventario†, reportes         | operar almacén, ejecutar QC       |

* recepción: jefe almacén solo valida/rechaza documentación
† solo lectura / supervisión (acciones restringidas en actores.py)
"""

from seguridad.permissions import es_admin_o_superusuario

ACCESO_MODULOS = {
    'dashboard': {
        'admin', 'jefe_compras', 'jefe_almacen', 'supervisor_almacen',
        'operario_almacen', 'encargado_calidad', 'jefe_operaciones',
        'area_administrativa', 'gerente_general', 'auditor_seguridad',
    },
    'recepcion': {'admin', 'jefe_compras', 'jefe_almacen', 'supervisor_almacen'},
    'maestros': {'admin', 'jefe_compras'},
    'calidad': {
        'admin', 'jefe_almacen', 'supervisor_almacen', 'encargado_calidad',
        'jefe_operaciones', 'gerente_general',
    },
    'ambiental': {'admin', 'jefe_almacen', 'supervisor_almacen', 'operario_almacen'},
    'inventario': {
        'admin', 'jefe_almacen', 'supervisor_almacen', 'operario_almacen',
        'jefe_operaciones', 'area_administrativa', 'gerente_general',
    },
    'reportes': {
        'admin', 'jefe_compras', 'jefe_almacen', 'jefe_operaciones',
        'area_administrativa', 'gerente_general',
    },
    'riesgos': {'admin', 'auditor_seguridad'},
    'auditoria': {'admin', 'auditor_seguridad'},
    'usuarios': {'admin'},
}

RUTA_MODULO = {
    '/': 'dashboard',
    '/recepcion': 'recepcion',
    '/calidad': 'calidad',
    '/ambiental': 'ambiental',
    '/inventario': 'inventario',
    '/riesgos': 'riesgos',
    '/reportes': 'reportes',
    '/auditoria': 'auditoria',
    '/usuarios': 'usuarios',
}


def roles_usuario(user):
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {'admin'}
    return set(
        user.roles_asignados.filter(rol__activo=True).values_list('rol__codigo', flat=True)
    )


def puede_acceder_modulo(user, modulo):
    if es_admin_o_superusuario(user):
        return True
    permitidos = ACCESO_MODULOS.get(modulo, set())
    return bool(roles_usuario(user) & permitidos)


def modulos_permitidos(user):
    if es_admin_o_superusuario(user):
        return list(ACCESO_MODULOS.keys())
    roles = roles_usuario(user)
    return [m for m, rs in ACCESO_MODULOS.items() if roles & rs]
