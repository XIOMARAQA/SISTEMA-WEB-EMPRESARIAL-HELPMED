/**
 * Matriz de actores — espejo de backend/seguridad/modulos.py y actores.py
 */

export const RUTA_MODULO = {
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

const ROLES_ALMACEN_ESCRITURA = ['jefe_almacen', 'supervisor_almacen', 'operario_almacen']
const ROLES_INVENTARIO_LECTURA = ['jefe_operaciones', 'area_administrativa', 'gerente_general']
const ROLES_DISCREPANCIAS = ['area_administrativa', 'jefe_almacen', 'supervisor_almacen', 'gerente_general']
const ROLES_AMBIENTAL_ESCRITURA = ['operario_almacen', 'jefe_almacen', 'supervisor_almacen']

/** Administrador o superusuario: acceso total al sistema. */
export function esSuperAdmin(user) {
  if (!user) return false
  return !!(user.es_admin || user.is_superuser)
}

export function puedeVerRuta(user, path) {
  if (!user) return false
  if (esSuperAdmin(user)) return true
  const modulos = user.modulos_permitidos || []
  if (path.startsWith('/datos-maestros')) return modulos.includes('maestros')
  const base = Object.keys(RUTA_MODULO).find(r => r !== '/' && path.startsWith(r)) || '/'
  const modulo = RUTA_MODULO[base]
  return modulos.includes(modulo)
}

/** Cuadre físico y movimientos: solo personal de almacén en ejecución. */
export function puedeCuadreFisico(user) {
  if (!user) return false
  if (esSuperAdmin(user)) return true
  const roles = user.roles_codigos || []
  return roles.some(r => ROLES_ALMACEN_ESCRITURA.includes(r))
}

export function puedeMovimientoInventario(user) {
  return puedeCuadreFisico(user)
}

/** Inventario solo lectura: operaciones, área administrativa, gerencia. */
export function inventarioSoloLectura(user) {
  if (!user) return false
  if (esSuperAdmin(user)) return false
  const roles = user.roles_codigos || []
  return roles.some(r => ROLES_INVENTARIO_LECTURA.includes(r))
}

export function puedeVerInventario(user) {
  return puedeCuadreFisico(user) || inventarioSoloLectura(user)
}

export function puedeRegistrarMedicionAmbiental(user) {
  if (!user) return false
  if (esSuperAdmin(user)) return true
  const roles = user.roles_codigos || []
  return roles.some(r => ROLES_AMBIENTAL_ESCRITURA.includes(r))
}

export function puedeEjecutarControlCalidad(user) {
  if (!user) return false
  if (esSuperAdmin(user)) return true
  return (user.roles_codigos || []).includes('encargado_calidad')
}

export function puedeGestionarMaestros(user) {
  if (!user) return false
  if (esSuperAdmin(user)) return true
  return (user.roles_codigos || []).includes('jefe_compras')
}

/** Evalúa discrepancias: lectura de cuadre sin editar conteos. */
export function puedeEvaluarDiscrepancias(user) {
  if (!user) return false
  if (esSuperAdmin(user)) return true
  const roles = user.roles_codigos || []
  return roles.some(r => ROLES_DISCREPANCIAS.includes(r))
}

export function tieneModulo(user, modulo) {
  if (!user) return false
  if (esSuperAdmin(user)) return true
  return (user.modulos_permitidos || []).includes(modulo)
}

export function etiquetaRoles(user) {
  if (!user) return ''
  if (user.is_superuser) return 'Superusuario'
  if (user.es_admin) return 'Administrador del sistema'
  const roles = user.roles || []
  if (roles.length) return roles.map(r => r.nombre).join(' · ')
  return 'Usuario'
}

export function verSeccionLogistica(user) {
  if (!user) return false
  if (esSuperAdmin(user)) return true
  return ['recepcion', 'calidad', 'ambiental', 'inventario', 'reportes', 'maestros'].some(
    m => tieneModulo(user, m),
  )
}

export function verSeccionRiesgos(user) {
  if (!user) return false
  if (esSuperAdmin(user)) return true
  return tieneModulo(user, 'riesgos') || tieneModulo(user, 'auditoria')
}

/** Recepción — Jefe de Compras registra/edita/elimina solo en estado pendiente. */
export function puedeRegistrarFactura(user) {
  if (!user) return false
  if (esSuperAdmin(user)) return true
  return (user.roles_codigos || []).includes('jefe_compras')
}

export function puedeEditarFacturaCompras(user, factura) {
  if (!user || !factura) return false
  if (esSuperAdmin(user)) return true
  if (!(user.roles_codigos || []).includes('jefe_compras')) return false
  return factura.estado === 'pendiente'
}

export function puedeValidarDocumentacion(user, factura) {
  if (!user || !factura) return false
  if (factura.estado !== 'pendiente') return false
  if (esSuperAdmin(user)) return true
  const roles = user.roles_codigos || []
  return roles.some(r => ['jefe_almacen', 'supervisor_almacen'].includes(r))
}

export function mensajeFacturaNoEditable(estado) {
  if (estado === 'atendido') {
    return 'La factura ya fue aceptada por almacén. No puede modificarla ni eliminarla.'
  }
  if (estado === 'rechazado') {
    return 'La factura fue rechazada por almacén. No puede modificarla ni eliminarla.'
  }
  return 'Solo puede editar o eliminar facturas en estado pendiente (P).'
}

/** Ruta inicial tras login según el rol principal del actor. */
export function rutaInicioPorRol(user) {
  if (!user) return '/'
  if (tieneModulo(user, 'dashboard')) return '/'
  const orden = ['recepcion', 'calidad', 'inventario', 'ambiental', 'reportes', 'maestros', 'riesgos', 'auditoria']
  const modulos = user.modulos_permitidos || []
  const modulo = orden.find(m => modulos.includes(m))
  const rutas = {
    recepcion: '/recepcion',
    calidad: '/calidad',
    inventario: '/inventario',
    ambiental: '/ambiental',
    reportes: '/reportes',
    maestros: '/datos-maestros/productos',
    riesgos: '/riesgos',
    auditoria: '/auditoria',
  }
  return rutas[modulo] || '/'
}
