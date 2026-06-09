from decimal import Decimal

from calidad.models import IncidenciaCalidad
from logistica.models import OrdenCompra


def _detalle_base(det, orden):
    return {
        'orden_id': orden.id,
        'numero_factura': orden.numero_completo,
        'fecha_control': orden.fecha_control_calidad,
        'control_calidad_estado': orden.control_calidad_estado,
        'proveedor_nombre': orden.proveedor.razon_social,
        'detalle_factura_id': det.id,
        'numero_item': det.numero_item,
        'descripcion': det.descripcion,
        'marca': det.marca or '',
        'laboratorio': det.laboratorio or '',
        'lote': det.lote or '',
        'fecha_vencimiento': det.fecha_vencimiento,
        'cantidad_factura': det.cantidad,
        'unidad_medida': det.unidad_medida,
        'producto_codigo': det.producto.codigo if det.producto_id else '',
        'producto_nombre': det.producto.nombre if det.producto_id else det.descripcion,
    }


def _evidencias_payload(incidencia, request):
    items = []
    for ev in incidencia.evidencias.all():
        url = ''
        if ev.archivo and request:
            url = request.build_absolute_uri(ev.archivo.url)
        items.append({
            'id': ev.id,
            'nombre': ev.nombre,
            'url': url,
            'creado_en': ev.creado_en,
        })
    return items


def obtener_resultados_control_calidad(request):
    ordenes = (
        OrdenCompra.objects.filter(estado=OrdenCompra.Estado.ATENDIDO)
        .exclude(control_calidad_estado=OrdenCompra.EstadoCalidad.PENDIENTE)
        .select_related('proveedor')
        .prefetch_related('detalles', 'detalles__producto')
        .order_by('-fecha_control_calidad', '-serie', '-numero')
    )

    incidencias = (
        IncidenciaCalidad.objects.filter(orden__in=ordenes)
        .select_related('orden', 'orden__proveedor', 'detalle_factura', 'producto', 'registrado_por')
        .prefetch_related('evidencias')
        .order_by('-creado_en')
    )
    inc_por_detalle = {}
    for inc in incidencias:
        if inc.detalle_factura_id:
            inc_por_detalle[(inc.orden_id, inc.detalle_factura_id)] = inc

    aceptados = []
    for orden in ordenes:
        for det in orden.detalles.all():
            inc = inc_por_detalle.get((orden.id, det.id))
            if inc:
                cant_aceptada = det.cantidad - inc.cantidad_rechazada
                if cant_aceptada <= 0:
                    continue
            else:
                cant_aceptada = det.cantidad

            row = _detalle_base(det, orden)
            row['cantidad_aceptada'] = cant_aceptada
            aceptados.append(row)

    rechazados = []
    for inc in incidencias:
        det = inc.detalle_factura
        orden = inc.orden
        if not orden:
            continue

        if det:
            row = _detalle_base(det, orden)
        else:
            row = {
                'orden_id': orden.id,
                'numero_factura': orden.numero_completo,
                'fecha_control': orden.fecha_control_calidad,
                'control_calidad_estado': orden.control_calidad_estado,
                'proveedor_nombre': orden.proveedor.razon_social,
                'detalle_factura_id': None,
                'numero_item': '—',
                'descripcion': inc.producto.nombre if inc.producto_id else 'Ítem sin detalle',
                'marca': '',
                'laboratorio': '',
                'lote': '',
                'fecha_vencimiento': None,
                'cantidad_factura': inc.cantidad_rechazada,
                'unidad_medida': inc.producto.unidad_medida if inc.producto_id else '—',
                'producto_codigo': inc.producto.codigo if inc.producto_id else '',
                'producto_nombre': inc.producto.nombre if inc.producto_id else '',
            }

        cant_factura = row['cantidad_factura'] if isinstance(row['cantidad_factura'], Decimal) else Decimal(str(row['cantidad_factura']))
        row.update({
            'incidencia_id': inc.id,
            'cantidad_rechazada': inc.cantidad_rechazada,
            'cantidad_aceptada': max(Decimal('0'), cant_factura - inc.cantidad_rechazada) if det else Decimal('0'),
            'motivo': inc.motivo,
            'comentarios': inc.comentarios,
            'estado_incidencia': inc.estado,
            'registrado_por': inc.registrado_por.get_full_name() or inc.registrado_por.username,
            'creado_en': inc.creado_en,
            'evidencias': _evidencias_payload(inc, request),
        })
        rechazados.append(row)

    return aceptados, rechazados
