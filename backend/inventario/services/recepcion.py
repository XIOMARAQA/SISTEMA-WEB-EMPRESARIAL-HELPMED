from decimal import Decimal

from django.db import transaction

from inventario.models import Inventario, MovimientoInventario


def _cantidad_aceptada(detalle, item=None):
    if item is None:
        return detalle.cantidad
    if item.get('estado') == 'conforme':
        return detalle.cantidad
    rechazada = Decimal(str(item.get('cantidad_rechazada', detalle.cantidad)))
    return detalle.cantidad - rechazada


def _item_por_detalle(items, detalle_id):
    if not items:
        return None
    for item in items:
        if item.get('detalle_factura') == detalle_id:
            return item
    return None


def registrar_entrada_desde_factura(orden, user, items=None):
    """
    Registra entradas de inventario tras control de calidad.
    items: lista del control con detalle_factura, estado, cantidad_rechazada.
    Si items es None, ingresa la cantidad total de cada ítem (sin rechazos).
    """
    proveedor = orden.proveedor
    entradas = []
    omitidos = []

    with transaction.atomic():
        for det in orden.detalles.select_related('producto'):
            if not det.producto_id:
                omitidos.append(det.descripcion)
                continue

            if MovimientoInventario.objects.filter(
                referencia=orden.numero_completo,
                observaciones__contains=f'Ítem #{det.numero_item}:',
            ).exists():
                continue

            item = _item_por_detalle(items, det.id)
            cantidad_aceptada = _cantidad_aceptada(det, item)
            if cantidad_aceptada <= 0:
                continue

            lote = (det.lote or 'SIN-LOTE').strip() or 'SIN-LOTE'
            ubicacion = 'Almacén principal'

            inv, created = Inventario.objects.get_or_create(
                producto=det.producto,
                lote=lote,
                ubicacion=ubicacion,
                defaults={
                    'cantidad': Decimal('0'),
                    'fecha_vencimiento': det.fecha_vencimiento,
                },
            )
            if not created:
                if det.fecha_vencimiento and not inv.fecha_vencimiento:
                    inv.fecha_vencimiento = det.fecha_vencimiento

            stock_anterior = inv.cantidad
            stock_posterior = stock_anterior + cantidad_aceptada
            clasificacion_anterior = inv.clasificacion
            inv.cantidad = stock_posterior
            inv.clasificacion = inv.calcular_clasificacion()
            inv.save(update_fields=['cantidad', 'fecha_vencimiento', 'clasificacion'])

            from notificaciones.flujos import alertar_inventario_actualizado
            alertar_inventario_actualizado(inv, clasificacion_anterior=clasificacion_anterior)

            mov = MovimientoInventario.objects.create(
                inventario=inv,
                codigo=MovimientoInventario.generar_codigo(MovimientoInventario.Tipo.ENTRADA),
                tipo=MovimientoInventario.Tipo.ENTRADA,
                cantidad=cantidad_aceptada,
                stock_anterior=stock_anterior,
                stock_posterior=stock_posterior,
                tercero_tipo=MovimientoInventario.TerceroTipo.PROVEEDOR,
                tercero_documento=proveedor.ruc,
                tercero_nombre=proveedor.razon_social,
                doc_fecha=orden.fecha_orden,
                doc_tipo='FACTURA',
                doc_serie=orden.serie,
                doc_numero=str(orden.numero),
                motivo='Entrada por recepción — control de calidad',
                referencia=orden.numero_completo,
                observaciones=f'Ítem #{det.numero_item}: {det.descripcion}',
                registrado_por=user,
            )
            entradas.append(mov.id)

    return {'entradas': len(entradas), 'omitidos_sin_producto': omitidos}


def cantidad_aceptada_desde_incidencias(detalle, orden):
    """Calcula cantidad aceptada usando incidencias ya registradas (backfill)."""
    from calidad.models import IncidenciaCalidad

    inc = IncidenciaCalidad.objects.filter(
        orden=orden, detalle_factura=detalle,
    ).first()
    if inc:
        return detalle.cantidad - inc.cantidad_rechazada
    return detalle.cantidad


def registrar_entrada_desde_factura_controlada(orden, user):
    """Backfill: reconstruye entradas a partir de incidencias existentes."""
    items = []
    for det in orden.detalles.all():
        from calidad.models import IncidenciaCalidad
        inc = IncidenciaCalidad.objects.filter(orden=orden, detalle_factura=det).first()
        if inc:
            items.append({
                'detalle_factura': det.id,
                'estado': 'rechazado',
                'cantidad_rechazada': inc.cantidad_rechazada,
            })
        else:
            items.append({'detalle_factura': det.id, 'estado': 'conforme'})
    return registrar_entrada_desde_factura(orden, user, items)
