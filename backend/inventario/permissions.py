from seguridad.actores import puede_modificar_inventario

from logistica.permissions import usuario_es_admin, usuario_tiene_rol


def puede_cuadre_fisico(user):
    return puede_modificar_inventario(user)


def puede_movimiento_inventario(user):
    return puede_modificar_inventario(user)
