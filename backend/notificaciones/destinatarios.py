"""
Destinatarios de notificaciones por evento — matriz de actores Seguricel S.A.C.

Cada evento lista los roles operativos que deben recibir la alerta.
Superusuarios y rol «admin» reciben TODAS las notificaciones (ver services.py).

| Actor                  | Recibe notificaciones sobre…                                      |
| ---------------------- | ----------------------------------------------------------------- |
| Jefe de Compras        | Facturas rechazadas, conformidad, rechazos QC, stock/reposición   |
| Jefe de Almacén        | Recepción, inventario, ambiental, movimientos, discrepancias    |
| Operario de Almacén    | Tareas operativas (factura lista para inspección/traslado)      |
| Control de Calidad     | Inspecciones pendientes, rechazos, caducados, alertas ambientales|
| Jefe de Operaciones    | Rechazos críticos, vencimientos urgentes, incidentes ambientales |
| Área Administrativa    | Discrepancias de inventario y cuadre físico                       |
| Gerente General        | Rechazos QC, caducados, stock crítico, incidentes ambientales     |
| Auditor de Seguridad   | Alertas de acceso, login fallido, cuentas bloqueadas (ISO 27001)  |
"""

JEFE_COMPRAS = 'jefe_compras'
JEFE_ALMACEN = 'jefe_almacen'
SUPERVISOR_ALMACEN = 'supervisor_almacen'
OPERARIO_ALMACEN = 'operario_almacen'
ENCARGADO_CALIDAD = 'encargado_calidad'
JEFE_OPERACIONES = 'jefe_operaciones'
AREA_ADMINISTRATIVA = 'area_administrativa'
GERENTE_GENERAL = 'gerente_general'
AUDITOR_SEGURIDAD = 'auditor_seguridad'

# Supervisión de almacén (recepción, inventario, ambiental operativo)
ALMACEN_SUPERVISION = (JEFE_ALMACEN, SUPERVISOR_ALMACEN)

DESTINATARIOS = {
    # UC 01 — Recepción de insumos
    'factura_registrada': ALMACEN_SUPERVISION,
    'documentacion_rechazada': (JEFE_COMPRAS,),
    'documentacion_aprobada': (ENCARGADO_CALIDAD, OPERARIO_ALMACEN),
    # UC 02 — Control de calidad
    'calidad_con_rechazos_gestion': (JEFE_COMPRAS, JEFE_OPERACIONES, GERENTE_GENERAL),
    'calidad_con_rechazos_almacen': ALMACEN_SUPERVISION,
    'calidad_conforme_compras': (JEFE_COMPRAS,),
    'calidad_conforme_almacen': ALMACEN_SUPERVISION,
    # Control ambiental
    'incidente_ambiental': (
        ENCARGADO_CALIDAD,
        *ALMACEN_SUPERVISION,
        JEFE_OPERACIONES,
        GERENTE_GENERAL,
    ),
    # Inventario y vencimientos
    'vencimiento_reposicion': (*ALMACEN_SUPERVISION, JEFE_COMPRAS),
    'vencimiento_alta_prioridad': (*ALMACEN_SUPERVISION, JEFE_OPERACIONES),
    'vencimiento_retiro_inmediato': (ENCARGADO_CALIDAD, *ALMACEN_SUPERVISION, GERENTE_GENERAL),
    'stock_minimo': (*ALMACEN_SUPERVISION, JEFE_COMPRAS, GERENTE_GENERAL),
    'discrepancia_inventario': (AREA_ADMINISTRATIVA, *ALMACEN_SUPERVISION),
    'movimiento_inventario': ALMACEN_SUPERVISION,
    # Seguridad de la información — ISO 27001 / 27005
    'alerta_login_fallido': (AUDITOR_SEGURIDAD,),
    'cuenta_bloqueada': (AUDITOR_SEGURIDAD,),
}
