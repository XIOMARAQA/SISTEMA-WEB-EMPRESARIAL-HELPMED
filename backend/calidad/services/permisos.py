from seguridad.permissions import es_admin_o_superusuario


def permisos_vista_resultados(user):
    """
    Visibilidad y ejecución en control de calidad según actor.
    Solo Control de Calidad ejecuta inspecciones; demás roles consultan.
    """
    if es_admin_o_superusuario(user):
        return {
            'aceptados': True,
            'rechazados': True,
            'ver_todo': True,
            'ejecutar_control': True,
        }

    roles = set(
        user.roles_asignados.filter(rol__activo=True).values_list('rol__codigo', flat=True)
    )

    base = {
        'aceptados': False,
        'rechazados': False,
        'ver_todo': False,
        'ejecutar_control': 'encargado_calidad' in roles,
    }

    if 'encargado_calidad' in roles:
        return {**base, 'aceptados': True, 'rechazados': True, 'ver_todo': True}

    if roles & {'jefe_almacen', 'supervisor_almacen', 'jefe_operaciones', 'gerente_general'}:
        return {**base, 'aceptados': True, 'rechazados': True}

    if 'operario_almacen' in roles:
        return {**base, 'aceptados': True}

    if 'auditor_seguridad' in roles:
        return {**base, 'aceptados': True, 'rechazados': True}

    return base
