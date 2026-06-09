from django.utils import timezone

from ambiental.models import AccionCorrectiva, IncidenteAmbiental, Medicion
from auditoria.models import RegistroAuditoria
from inventario.models import Inventario, MovimientoInventario
from reportes.formats import (
    NIVEL_TEXTO,
    PROB_LABELS,
    IMP_LABELS,
    crear_workbook,
    excel_ajustar_columnas,
    excel_celda_datos,
    excel_encabezado_tabla,
    excel_mapa_calor,
    excel_portada,
    fecha_generacion,
    pdf_encabezado,
    pdf_leyenda_riesgos,
    pdf_mapa_calor,
    pdf_nota,
    pdf_seccion,
    pdf_tabla,
    respuesta_excel,
    respuesta_pdf,
    valor_a_nivel,
)
from reportlab.platypus import Spacer
from riesgos.models import EvaluacionRiesgo, Riesgo


def _grid_evaluaciones(evaluaciones):
    grid = {}
    for ev in evaluaciones:
        grid.setdefault((ev.impacto, ev.probabilidad), []).append(ev.riesgo.codigo)
    return grid


def _evaluaciones_inherentes():
    return list(
        EvaluacionRiesgo.objects
        .filter(tipo='inherente')
        .select_related('riesgo', 'riesgo__activo', 'riesgo__amenaza')
        .order_by('-valor_riesgo', 'riesgo__codigo')
    )


# ── Matriz de Riesgos ─────────────────────────────────────────────────────────

def exportar_matriz_riesgos_excel():
    evaluaciones = _evaluaciones_inherentes()
    grid = _grid_evaluaciones(evaluaciones)

    wb = crear_workbook('Portada')
    ws0 = wb.active
    excel_portada(
        ws0,
        'Matriz de Riesgos ISO/IEC 27005',
        secciones=[
            'Evaluaciones inherentes',
            'Mapa de calor (Impacto × Probabilidad)',
            'Catálogo de riesgos',
        ],
        nota='Fórmula: VALOR = PROBABILIDAD × IMPACTO. Solo evaluaciones de tipo inherente.',
    )

    ws1 = wb.create_sheet('Evaluaciones')
    fila = excel_encabezado_tabla(
        ws1, 1,
        'Evaluaciones de riesgo — tipo inherente',
        ['Riesgo', 'Activo', 'Amenaza', 'Probabilidad', 'Impacto', 'Celda', 'Valor', 'Nivel', 'Fecha'],
    )
    for ev in evaluaciones:
        nivel = ev.nivel
        excel_celda_datos(ws1, fila, 1, ev.riesgo.codigo)
        excel_celda_datos(ws1, fila, 2, ev.riesgo.activo.nombre)
        excel_celda_datos(ws1, fila, 3, ev.riesgo.amenaza.nombre)
        excel_celda_datos(ws1, fila, 4, f'P{ev.probabilidad} — {PROB_LABELS[ev.probabilidad - 1]}')
        excel_celda_datos(ws1, fila, 5, f'I{ev.impacto} — {IMP_LABELS[ev.impacto - 1]}')
        excel_celda_datos(ws1, fila, 6, f'I{ev.impacto} × P{ev.probabilidad}', align='center')
        excel_celda_datos(ws1, fila, 7, ev.valor_riesgo, align='center')
        excel_celda_datos(ws1, fila, 8, NIVEL_TEXTO.get(nivel, ev.get_nivel_display()), nivel=nivel)
        excel_celda_datos(ws1, fila, 9, ev.fecha_evaluacion.strftime('%d/%m/%Y'), align='center')
        fila += 1
    excel_ajustar_columnas(ws1)

    ws2 = wb.create_sheet('Mapa de calor')
    excel_mapa_calor(ws2, 1, grid)
    for col in 'ABCDEF':
        ws2.column_dimensions[col].width = 16

    ws3 = wb.create_sheet('Riesgos')
    fila_r = excel_encabezado_tabla(
        ws3, 1, 'Catálogo de riesgos',
        ['Código', 'Activo', 'Amenaza', 'Descripción'],
    )
    for r in Riesgo.objects.select_related('activo', 'amenaza').order_by('codigo'):
        excel_celda_datos(ws3, fila_r, 1, r.codigo)
        excel_celda_datos(ws3, fila_r, 2, r.activo.nombre)
        excel_celda_datos(ws3, fila_r, 3, r.amenaza.nombre)
        excel_celda_datos(ws3, fila_r, 4, r.descripcion)
        fila_r += 1
    excel_ajustar_columnas(ws3, max_width=60)

    return respuesta_excel(wb, 'matriz-riesgos')


def exportar_matriz_riesgos_pdf():
    evaluaciones = _evaluaciones_inherentes()
    grid = _grid_evaluaciones(evaluaciones)

    elementos = pdf_encabezado(
        'Matriz de Riesgos ISO/IEC 27005',
        'VALOR = PROBABILIDAD × IMPACTO · Evaluaciones de tipo inherente',
    )
    elementos.append(pdf_leyenda_riesgos())
    elementos.append(Spacer(1, 10))
    elementos.append(pdf_seccion('Evaluaciones de riesgo'))
    filas = [['Riesgo', 'Activo', 'Prob.', 'Imp.', 'Celda', 'Valor', 'Nivel']]
    niveles = []
    for ev in evaluaciones:
        filas.append([
            ev.riesgo.codigo,
            ev.riesgo.activo.nombre[:35],
            f'P{ev.probabilidad}',
            f'I{ev.impacto}',
            f'I{ev.impacto}×P{ev.probabilidad}',
            str(ev.valor_riesgo),
            NIVEL_TEXTO.get(ev.nivel, ev.get_nivel_display()),
        ])
        niveles.append(ev.nivel)
    elementos.append(pdf_tabla(
        filas,
        col_widths=[52, 130, 32, 32, 48, 38, 78],
        resaltar_col=6,
        niveles_fila=niveles,
    ))
    elementos.append(Spacer(1, 14))
    elementos.append(pdf_seccion('Mapa de calor'))
    elementos.append(pdf_nota(
        'Filas = Impacto (I5 → crítico) · Columnas = Probabilidad (P1 → muy baja). '
        'El número es el valor; debajo aparecen los códigos RSG ubicados en esa celda.'
    ))
    elementos.append(pdf_mapa_calor(grid))
    return respuesta_pdf(elementos, 'matriz-riesgos', horizontal=True)


# ── Inventario ────────────────────────────────────────────────────────────────

CUADRE_NIVEL = {'discrepancia': 'critico', 'conforme': 'bajo', 'pendiente': 'medio'}
CLASIF_NIVEL = {
    'retiro_inmediato': 'critico',
    'alta_prioridad': 'alto',
    'reposicion': 'medio',
    'conforme': 'bajo',
}


def exportar_inventario_excel():
    wb = crear_workbook('Portada')
    excel_portada(
        wb.active,
        'Inventario y Kardex',
        secciones=['Stock actual', 'Movimientos (kardex)', 'Productos por vencer (30 días)'],
    )

    hoy = timezone.now().date()

    ws = wb.create_sheet('Stock')
    fila = excel_encabezado_tabla(
        ws, 1, 'Stock actual',
        ['Código', 'Producto', 'Lote', 'Cantidad', 'Física', 'Cuadre', 'Vencimiento', 'Clasificación', 'Ubicación'],
    )
    for inv in Inventario.objects.select_related('producto').order_by('producto__codigo', 'lote'):
        clasif = inv.clasificacion or inv.calcular_clasificacion()
        excel_celda_datos(ws, fila, 1, inv.producto.codigo)
        excel_celda_datos(ws, fila, 2, inv.producto.nombre)
        excel_celda_datos(ws, fila, 3, inv.lote)
        excel_celda_datos(ws, fila, 4, float(inv.cantidad), align='right')
        excel_celda_datos(ws, fila, 5, float(inv.cantidad_fisica) if inv.cantidad_fisica is not None else '—', align='right')
        excel_celda_datos(ws, fila, 6, inv.get_cuadre_estado_display(), nivel=CUADRE_NIVEL.get(inv.cuadre_estado))
        excel_celda_datos(ws, fila, 7, inv.fecha_vencimiento.strftime('%d/%m/%Y') if inv.fecha_vencimiento else '—', align='center')
        excel_celda_datos(ws, fila, 8, inv.get_clasificacion_display() if inv.clasificacion else clasif, nivel=CLASIF_NIVEL.get(clasif, 'bajo'))
        excel_celda_datos(ws, fila, 9, inv.ubicacion)
        fila += 1
    excel_ajustar_columnas(ws)

    ws2 = wb.create_sheet('Kardex')
    fila_k = excel_encabezado_tabla(
        ws2, 1, 'Movimientos de inventario',
        ['Código', 'Fecha', 'Tipo', 'Producto', 'Lote', 'Cantidad', 'Stock ant.', 'Stock post.', 'Tercero', 'Motivo'],
    )
    for mov in MovimientoInventario.objects.select_related(
        'inventario', 'inventario__producto',
    ).order_by('-creado_en')[:2000]:
        excel_celda_datos(ws2, fila_k, 1, mov.codigo)
        excel_celda_datos(ws2, fila_k, 2, mov.creado_en.strftime('%d/%m/%Y %H:%M'), align='center')
        excel_celda_datos(ws2, fila_k, 3, mov.get_tipo_display())
        excel_celda_datos(ws2, fila_k, 4, mov.inventario.producto.nombre)
        excel_celda_datos(ws2, fila_k, 5, mov.inventario.lote)
        excel_celda_datos(ws2, fila_k, 6, float(mov.cantidad), align='right')
        excel_celda_datos(ws2, fila_k, 7, float(mov.stock_anterior), align='right')
        excel_celda_datos(ws2, fila_k, 8, float(mov.stock_posterior), align='right')
        excel_celda_datos(ws2, fila_k, 9, mov.tercero_nombre or mov.tercero_documento)
        excel_celda_datos(ws2, fila_k, 10, mov.motivo)
        fila_k += 1
    excel_ajustar_columnas(ws2)

    ws3 = wb.create_sheet('Por vencer')
    fila_v = excel_encabezado_tabla(
        ws3, 1, 'Productos por vencer en los próximos 30 días',
        ['Código', 'Producto', 'Lote', 'Cantidad', 'Vencimiento', 'Días restantes'],
    )
    for inv in Inventario.objects.select_related('producto').filter(
        cantidad__gt=0,
        fecha_vencimiento__isnull=False,
        fecha_vencimiento__lte=hoy + timezone.timedelta(days=30),
        fecha_vencimiento__gte=hoy,
    ).order_by('fecha_vencimiento'):
        dias = (inv.fecha_vencimiento - hoy).days
        nivel = 'critico' if dias <= 7 else 'alto' if dias <= 15 else 'medio'
        excel_celda_datos(ws3, fila_v, 1, inv.producto.codigo)
        excel_celda_datos(ws3, fila_v, 2, inv.producto.nombre)
        excel_celda_datos(ws3, fila_v, 3, inv.lote)
        excel_celda_datos(ws3, fila_v, 4, float(inv.cantidad), align='right')
        excel_celda_datos(ws3, fila_v, 5, inv.fecha_vencimiento.strftime('%d/%m/%Y'), align='center')
        excel_celda_datos(ws3, fila_v, 6, dias, nivel=nivel, align='center')
        fila_v += 1
    excel_ajustar_columnas(ws3)

    return respuesta_excel(wb, 'inventario')


# ── Control Ambiental ─────────────────────────────────────────────────────────

def exportar_ambiental_pdf():
    elementos = pdf_encabezado(
        'Control Ambiental',
        'Rango óptimo de temperatura: 20 °C – 25 °C',
    )
    elementos.append(pdf_seccion('Mediciones diarias'))
    filas = [['Fecha', 'Hora', 'Temp. °C', 'Humedad %', 'Ubicación', 'Estado', 'Responsable']]
    for m in Medicion.objects.select_related('responsable').order_by('-fecha', '-hora')[:500]:
        filas.append([
            m.fecha.strftime('%d/%m/%Y'),
            m.hora.strftime('%H:%M'),
            str(m.temperatura),
            str(m.humedad),
            m.ubicacion,
            '⚠ Fuera de rango' if m.fuera_rango else 'Normal',
            m.responsable.get_full_name() or m.responsable.username,
        ])
    elementos.append(pdf_tabla(filas, col_widths=[62, 42, 48, 52, 95, 68, 85]))
    elementos.append(Spacer(1, 12))
    elementos.append(pdf_seccion('Incidentes ambientales'))
    inc_filas = [['Fecha', 'Temperatura', 'Descripción']]
    for inc in IncidenteAmbiental.objects.select_related('medicion').order_by('-creado_en')[:200]:
        inc_filas.append([
            inc.medicion.fecha.strftime('%d/%m/%Y'),
            f'{inc.medicion.temperatura} °C',
            inc.descripcion[:100],
        ])
    elementos.append(pdf_tabla(inc_filas, col_widths=[70, 70, 280]))
    elementos.append(Spacer(1, 12))
    elementos.append(pdf_seccion('Acciones correctivas'))
    acc_filas = [['Descripción', 'Estado', 'Responsable', 'Fecha programada']]
    for a in AccionCorrectiva.objects.filter(origen='ambiental').select_related('responsable')[:200]:
        acc_filas.append([
            a.descripcion[:90],
            a.get_estado_display(),
            a.responsable.get_full_name() or a.responsable.username,
            a.fecha_programada.strftime('%d/%m/%Y') if a.fecha_programada else '—',
        ])
    elementos.append(pdf_tabla(acc_filas, col_widths=[200, 70, 85, 75]))
    return respuesta_pdf(elementos, 'ambiental', horizontal=True)


def exportar_ambiental_excel():
    wb = crear_workbook('Portada')
    excel_portada(
        wb.active,
        'Control Ambiental',
        secciones=['Mediciones', 'Incidentes', 'Acciones correctivas'],
        nota='Rango óptimo de temperatura: 20 °C – 25 °C',
    )

    ws = wb.create_sheet('Mediciones')
    fila = excel_encabezado_tabla(
        ws, 1, 'Mediciones diarias',
        ['Fecha', 'Hora', 'Temp. °C', 'Humedad %', 'Ubicación', 'Estado', 'Observaciones', 'Responsable'],
    )
    for m in Medicion.objects.select_related('responsable').order_by('-fecha', '-hora'):
        nivel = 'critico' if m.fuera_rango else None
        excel_celda_datos(ws, fila, 1, m.fecha.strftime('%d/%m/%Y'), align='center')
        excel_celda_datos(ws, fila, 2, m.hora.strftime('%H:%M'), align='center')
        excel_celda_datos(ws, fila, 3, float(m.temperatura), align='right', nivel=nivel)
        excel_celda_datos(ws, fila, 4, float(m.humedad), align='right')
        excel_celda_datos(ws, fila, 5, m.ubicacion)
        excel_celda_datos(ws, fila, 6, 'Fuera de rango' if m.fuera_rango else 'Normal', nivel=nivel)
        excel_celda_datos(ws, fila, 7, m.observaciones)
        excel_celda_datos(ws, fila, 8, m.responsable.get_full_name() or m.responsable.username)
        fila += 1
    excel_ajustar_columnas(ws)

    ws2 = wb.create_sheet('Incidentes')
    fila_i = excel_encabezado_tabla(ws2, 1, 'Incidentes ambientales', ['Fecha', 'Temperatura', 'Descripción'])
    for inc in IncidenteAmbiental.objects.select_related('medicion').order_by('-creado_en'):
        excel_celda_datos(ws2, fila_i, 1, inc.medicion.fecha.strftime('%d/%m/%Y'), align='center')
        excel_celda_datos(ws2, fila_i, 2, float(inc.medicion.temperatura), align='right', nivel='alto')
        excel_celda_datos(ws2, fila_i, 3, inc.descripcion)
        fila_i += 1
    excel_ajustar_columnas(ws2, max_width=55)

    ws3 = wb.create_sheet('Acciones')
    fila_a = excel_encabezado_tabla(
        ws3, 1, 'Acciones correctivas (ambiental)',
        ['Descripción', 'Estado', 'Responsable', 'Fecha programada', 'Fecha cierre'],
    )
    for a in AccionCorrectiva.objects.filter(origen='ambiental').select_related('responsable'):
        nivel = 'bajo' if a.estado == 'completada' else 'medio'
        excel_celda_datos(ws3, fila_a, 1, a.descripcion)
        excel_celda_datos(ws3, fila_a, 2, a.get_estado_display(), nivel=nivel)
        excel_celda_datos(ws3, fila_a, 3, a.responsable.get_full_name() or a.responsable.username)
        excel_celda_datos(ws3, fila_a, 4, a.fecha_programada.strftime('%d/%m/%Y') if a.fecha_programada else '—', align='center')
        excel_celda_datos(ws3, fila_a, 5, a.fecha_cierre.strftime('%d/%m/%Y') if a.fecha_cierre else '—', align='center')
        fila_a += 1
    excel_ajustar_columnas(ws3, max_width=55)

    return respuesta_excel(wb, 'ambiental')


# ── Auditoría ─────────────────────────────────────────────────────────────────

def exportar_auditoria_pdf():
    elementos = pdf_encabezado(
        'Auditoría del Sistema',
        'Registro de acciones y trazabilidad de usuarios',
    )
    elementos.append(pdf_seccion('Últimos registros'))
    filas = [['Fecha y hora', 'Usuario', 'Acción', 'Módulo', 'Descripción']]
    for r in RegistroAuditoria.objects.select_related('usuario').order_by('-creado_en')[:1000]:
        usuario = (r.usuario.get_full_name() or r.usuario.username) if r.usuario else '—'
        filas.append([
            r.creado_en.strftime('%d/%m/%Y %H:%M'),
            usuario,
            r.accion,
            r.modulo,
            (r.descripcion or '')[:90],
        ])
    elementos.append(pdf_tabla(filas, col_widths=[82, 75, 78, 58, 195]))
    return respuesta_pdf(elementos, 'auditoria', horizontal=True)


def exportar_auditoria_excel():
    wb = crear_workbook('Portada')
    excel_portada(
        wb.active,
        'Auditoría del Sistema',
        secciones=['Registro de acciones del sistema'],
        nota='Trazabilidad de operaciones por usuario, módulo y fecha.',
    )

    ws = wb.create_sheet('Registros')
    fila = excel_encabezado_tabla(
        ws, 1, 'Registro de auditoría',
        ['Fecha', 'Usuario', 'Acción', 'Módulo', 'Tabla', 'Registro ID', 'IP', 'Descripción'],
    )
    for r in RegistroAuditoria.objects.select_related('usuario').order_by('-creado_en')[:5000]:
        excel_celda_datos(ws, fila, 1, r.creado_en.strftime('%d/%m/%Y %H:%M'), align='center')
        excel_celda_datos(ws, fila, 2, (r.usuario.get_full_name() or r.usuario.username) if r.usuario else '—')
        excel_celda_datos(ws, fila, 3, r.accion)
        excel_celda_datos(ws, fila, 4, r.modulo)
        excel_celda_datos(ws, fila, 5, r.tabla)
        excel_celda_datos(ws, fila, 6, r.registro_id or '', align='center')
        excel_celda_datos(ws, fila, 7, r.ip_address or '')
        excel_celda_datos(ws, fila, 8, r.descripcion)
        fila += 1
    excel_ajustar_columnas(ws, max_width=50)

    return respuesta_excel(wb, 'auditoria')


EXPORTADORES = {
    'matriz-riesgos': {'pdf': exportar_matriz_riesgos_pdf, 'excel': exportar_matriz_riesgos_excel},
    'inventario': {'excel': exportar_inventario_excel},
    'ambiental': {'pdf': exportar_ambiental_pdf, 'excel': exportar_ambiental_excel},
    'auditoria': {'pdf': exportar_auditoria_pdf, 'excel': exportar_auditoria_excel},
}
