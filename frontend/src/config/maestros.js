/** Configuración de entidades del módulo Datos Maestros (sin clientes ni vendedores). */

export const MAESTROS_MENU = [
  { to: '/datos-maestros/productos', icon: 'bi-box', label: 'Productos y servicios', key: 'productos' },
  { to: '/datos-maestros/categorias', icon: 'bi-tags', label: 'Categorías de producto', key: 'categorias' },
  { to: '/datos-maestros/subcategorias', icon: 'bi-diagram-3', label: 'Subcategorías', key: 'subcategorias' },
  { to: '/datos-maestros/marcas', icon: 'bi-bookmark-star', label: 'Marcas', key: 'marcas' },
  { to: '/datos-maestros/unidades', icon: 'bi-rulers', label: 'Unidades de medida', key: 'unidades' },
  { to: '/datos-maestros/proveedores', icon: 'bi-truck', label: 'Proveedores', key: 'proveedores' },
]

/** Ítems visibles por rol — solo jefe de compras gestiona catálogo y proveedores. */
export function maestrosVisibles(user) {
  if (!user) return []
  if (user.es_admin || user.is_superuser) return MAESTROS_MENU
  if ((user.roles_codigos || []).includes('jefe_compras')) return MAESTROS_MENU
  return []
}

export const MAESTROS_ENTIDADES = {
  categorias: {
    title: 'Categorías de producto',
    subtitle: 'Clasificación de productos e insumos médicos',
    endpoint: '/categorias/',
    columns: [
      { key: 'codigo', label: 'Código' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'descripcion', label: 'Descripción' },
    ],
    fields: [
      { key: 'codigo', label: 'Código', type: 'text', required: true, col: 4 },
      { key: 'nombre', label: 'Nombre', type: 'text', required: true, col: 8 },
      { key: 'descripcion', label: 'Descripción', type: 'textarea', col: 12 },
    ],
    empty: { codigo: '', nombre: '', descripcion: '' },
  },
  marcas: {
    title: 'Marcas',
    subtitle: 'Marcas comerciales de productos',
    endpoint: '/marcas/',
    columns: [
      { key: 'codigo', label: 'Código' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'descripcion', label: 'Descripción' },
    ],
    fields: [
      { key: 'codigo', label: 'Código', type: 'text', required: true, col: 4 },
      { key: 'nombre', label: 'Nombre', type: 'text', required: true, col: 8 },
      { key: 'descripcion', label: 'Descripción', type: 'textarea', col: 12 },
    ],
    empty: { codigo: '', nombre: '', descripcion: '' },
  },
  unidades: {
    title: 'Unidades de medida',
    subtitle: 'Unidades usadas en órdenes de compra e inventario',
    endpoint: '/unidades-medida/',
    columns: [
      { key: 'codigo', label: 'Código' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'simbolo', label: 'Símbolo' },
    ],
    fields: [
      { key: 'codigo', label: 'Código', type: 'text', required: true, col: 4 },
      { key: 'nombre', label: 'Nombre', type: 'text', required: true, col: 5 },
      { key: 'simbolo', label: 'Símbolo', type: 'text', col: 3 },
    ],
    empty: { codigo: '', nombre: '', simbolo: '' },
  },
}
