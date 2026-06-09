from seguridad.models import Rol


def usuario_es_admin(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return Rol.objects.filter(
        usuarios_asignados__usuario=user,
        codigo='admin',
        activo=True,
    ).exists()


def usuario_tiene_rol(user, codigos):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return Rol.objects.filter(
        usuarios_asignados__usuario=user,
        codigo__in=codigos,
        activo=True,
    ).exists()


def puede_modificar_factura(user, orden):
    """
    Jefe de compras: editar/eliminar solo mientras la factura está pendiente (P).
    Una vez aceptada (A) o rechazada (R) por almacén, solo el administrador puede modificar.
    """
    if usuario_es_admin(user):
        return True, None
    if not usuario_tiene_rol(user, ['jefe_compras']):
        return False, 'Solo el jefe de compras puede modificar el contenido de la factura.'
    from logistica.models import OrdenCompra

    if orden.estado != OrdenCompra.Estado.PENDIENTE:
        if orden.estado == OrdenCompra.Estado.ATENDIDO:
            msg = (
                'La factura ya fue aceptada por almacén. '
                'No puede modificarla ni eliminarla.'
            )
        elif orden.estado == OrdenCompra.Estado.RECHAZADO:
            msg = (
                'La factura fue rechazada por almacén. '
                'No puede modificarla ni eliminarla.'
            )
        else:
            msg = 'La factura ya no está pendiente. No puede modificarla ni eliminarla.'
        return False, msg
    return True, None


def puede_ver_factura(user):
    return usuario_es_admin(user) or usuario_tiene_rol(
        user, ['jefe_compras', 'jefe_almacen', 'supervisor_almacen'],
    )


def puede_validar_documentacion(user):
    return usuario_es_admin(user) or usuario_tiene_rol(
        user, ['jefe_almacen', 'supervisor_almacen'],
    )


def puede_control_calidad(user):
    return usuario_es_admin(user) or usuario_tiene_rol(user, ['encargado_calidad'])


def puede_registrar_factura(user):
    return usuario_es_admin(user) or usuario_tiene_rol(user, ['jefe_compras'])
