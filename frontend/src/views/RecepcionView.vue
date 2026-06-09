<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import ProveedorFormModal from '../components/ProveedorFormModal.vue'
import { useAuthStore } from '../stores/auth'
import {
  mensajeFacturaNoEditable,
  puedeEditarFacturaCompras,
  puedeRegistrarFactura,
  puedeValidarDocumentacion,
  esSuperAdmin,
} from '../config/roles'
import { calcularLinea, formatoMoneda, sumarTotales } from '../utils/igv'

const facturas = ref([])
const proveedores = ref([])
const productos = ref([])
const loading = ref(true)
const filtroEstado = ref('')
const showModalFactura = ref(false)
const showModalItem = ref(false)
const showModalDetalle = ref(false)
const showModalValidar = ref(false)
const showModalProveedor = ref(false)
const showProveedorDropdown = ref(false)
const buscandoProveedor = ref(false)
const proveedorHint = ref('')
const facturaSeleccionada = ref(null)
const facturaValidar = ref(null)
const editFacturaId = ref(null)
const guardandoFactura = ref(false)
const validando = ref(false)
const facturaError = ref('')
const validarError = ref('')
const docFiles = ref([])
const comentariosValidacion = ref('')
const proveedorBusqueda = ref('')
const proveedorInicialRuc = ref('')
const proveedorInicialRazon = ref('')
const proveedorInicialDireccion = ref('')

const form = ref({
  serie: '',
  numero: '',
  proveedor: '',
  fecha_orden: '',
  observaciones: '',
})
const itemForm = ref({
  descripcion: '',
  laboratorio: '',
  cantidad: '',
  unidad_medida: 'UND',
  lote: '',
  fecha_vencimiento: '',
  producto: '',
  marca: '',
  precio_unitario: '',
  igv_incluido: true,
})
const itemFormError = ref('')
const itemsFactura = ref([])

const estadoBadge = {
  pendiente: 'badge-estado-pendiente',
  atendido: 'badge-estado-atendido',
  rechazado: 'badge-estado-rechazado',
}
const estadoLabel = {
  pendiente: 'P — Pendiente',
  atendido: 'A — Atendido',
  rechazado: 'R — Rechazado',
}
const unidadesMedida = ref([])
const auth = useAuthStore()

const esAdmin = computed(() => !!auth.user?.es_admin)
const puedeRegistrar = computed(() => puedeRegistrarFactura(auth.user))
const puedeValidarDocs = computed(() =>
  auth.user?.es_admin
  || (auth.user?.roles_codigos || []).some(r => ['jefe_almacen', 'supervisor_almacen'].includes(r)),
)

const facturasFiltradas = computed(() =>
  filtroEstado.value ? facturas.value.filter(o => o.estado === filtroEstado.value) : facturas.value
)

const numeroCompleto = computed(() => {
  const s = String(form.value.serie || '').trim()
  const n = form.value.numero
  if (!s || n === '' || n === null || n === undefined) return '—'
  const num = parseInt(n, 10)
  if (Number.isNaN(num)) return s
  return `${s}-${String(num).padStart(6, '0')}`
})

function labelProveedor(p) {
  return `${p.ruc} — ${p.razon_social}`
}

const proveedoresFiltrados = computed(() => {
  const q = proveedorBusqueda.value.trim().toLowerCase()
  if (!q) return proveedores.value.slice(0, 12)
  return proveedores.value.filter(p =>
    p.ruc.includes(q) || p.razon_social.toLowerCase().includes(q)
  ).slice(0, 12)
})

const rucDigitado = computed(() => {
  const q = proveedorBusqueda.value.trim()
  const solo = q.replace(/\D/g, '')
  return /^\d{11}$/.test(solo) ? solo : (/^\d+$/.test(q) ? q : '')
})

const proveedorNoEncontrado = computed(() => {
  if (form.value.proveedor) return false
  const q = proveedorBusqueda.value.trim()
  if (!q) return false
  if (rucDigitado.value) {
    return !proveedores.value.some(p => p.ruc === rucDigitado.value)
  }
  return q.length >= 2 && proveedoresFiltrados.value.length === 0
})

const itemImportesPreview = computed(() =>
  calcularLinea(itemForm.value.cantidad, itemForm.value.precio_unitario, itemForm.value.igv_incluido)
)

const totalesFactura = computed(() => sumarTotales(itemsFactura.value))

const productoItemSeleccionado = computed(() =>
  productos.value.find(p => p.id === Number(itemForm.value.producto))
)

const tituloModalFactura = computed(() =>
  editFacturaId.value ? 'Editar factura' : 'Nueva factura'
)

function puedeEditarFactura(f) {
  return puedeEditarFacturaCompras(auth.user, f)
}

function puedeValidarFactura(f) {
  return puedeValidarDocumentacion(auth.user, f)
}

function mensajeSinPermisoFactura(f) {
  return mensajeFacturaNoEditable(f?.estado)
}

function abrirModalFactura() {
  if (!puedeRegistrar.value) {
    alert('Solo el jefe de compras puede registrar facturas.')
    return
  }
  editFacturaId.value = null
  facturaError.value = ''
  itemsFactura.value = []
  proveedorBusqueda.value = ''
  proveedorHint.value = ''
  form.value = {
    serie: '',
    numero: '',
    proveedor: '',
    fecha_orden: new Date().toISOString().slice(0, 10),
    observaciones: '',
  }
  showModalFactura.value = true
}

function mapDetalleToItem(d) {
  const productoId = d.producto?.id ?? d.producto
  return {
    numero_item: d.numero_item,
    descripcion: d.descripcion,
    laboratorio: d.laboratorio || '',
    marca: d.marca || '',
    cantidad: Number(d.cantidad),
    unidad_medida: d.unidad_medida || 'UND',
    precio_unitario: Number(d.precio_unitario),
    igv_incluido: !!d.igv_incluido,
    lote: d.lote || '',
    fecha_vencimiento: d.fecha_vencimiento || '',
    producto: productoId ? Number(productoId) : '',
  }
}

function detallePayload(it) {
  const producto = it.producto ? Number(it.producto) : null
  return {
    numero_item: it.numero_item,
    descripcion: it.descripcion,
    laboratorio: it.laboratorio,
    marca: it.marca,
    cantidad: it.cantidad,
    unidad_medida: it.unidad_medida,
    precio_unitario: it.precio_unitario,
    igv_incluido: it.igv_incluido,
    lote: it.lote,
    fecha_vencimiento: it.fecha_vencimiento || null,
    producto: Number.isNaN(producto) ? null : producto,
  }
}

async function abrirEditarFactura(f) {
  if (!puedeEditarFactura(f)) {
    alert(mensajeSinPermisoFactura(f))
    return
  }
  editFacturaId.value = f.id
  facturaError.value = ''
  proveedorHint.value = ''
  try {
    const { data } = await api.get(`/ordenes-compra/${f.id}/`)
    form.value = {
      serie: data.serie,
      numero: data.numero,
      proveedor: data.proveedor,
      fecha_orden: data.fecha_orden,
      observaciones: data.observaciones || '',
    }
    proveedorBusqueda.value = `${data.proveedor_ruc} — ${data.proveedor_nombre}`
    const detalles = (data.detalles?.length ? data.detalles : f.detalles) || []
    itemsFactura.value = detalles.map(mapDetalleToItem)
    showModalFactura.value = true
  } catch {
    editFacturaId.value = null
    alert('No se pudo cargar la factura para editar.')
  }
}

const loadError = ref('')

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const params = filtroEstado.value ? { estado: filtroEstado.value } : {}
    const ordRes = await api.get('/ordenes-compra/', { params })
    facturas.value = ordRes.data.results ?? ordRes.data ?? []

    const [provRes, prodRes, umRes] = await Promise.allSettled([
      api.get('/proveedores/'),
      api.get('/productos/'),
      api.get('/unidades-medida/'),
    ])
    if (provRes.status === 'fulfilled') {
      proveedores.value = provRes.value.data.results ?? provRes.value.data ?? []
    }
    if (prodRes.status === 'fulfilled') {
      productos.value = prodRes.value.data.results ?? prodRes.value.data ?? []
    }
    if (umRes.status === 'fulfilled') {
      unidadesMedida.value = umRes.value.data.results ?? umRes.value.data ?? []
    }
  } catch (err) {
    loadError.value = err.response?.data?.detail || 'No se pudieron cargar las facturas.'
    facturas.value = []
  } finally {
    loading.value = false
  }
}

function seleccionarProveedor(p) {
  form.value.proveedor = p.id
  proveedorBusqueda.value = labelProveedor(p)
  proveedorHint.value = ''
  showProveedorDropdown.value = false
}

function onProveedorInput() {
  form.value.proveedor = ''
  proveedorHint.value = ''
  showProveedorDropdown.value = true
}

function extraerRuc(texto) {
  const solo = String(texto || '').replace(/\D/g, '')
  return solo.length === 11 ? solo : ''
}

function abrirModalCrearProveedor(ruc = '', razon = '', direccion = '') {
  proveedorInicialRuc.value = ruc
  proveedorInicialRazon.value = razon
  proveedorInicialDireccion.value = direccion
  showProveedorDropdown.value = false
  showModalProveedor.value = true
}

async function buscarProveedor() {
  const q = proveedorBusqueda.value.trim()
  if (!q) {
    proveedorHint.value = 'Digite RUC o razón social.'
    return
  }

  facturaError.value = ''
  proveedorHint.value = ''
  buscandoProveedor.value = true

  try {
    const ruc = extraerRuc(q) || extraerRuc(rucDigitado.value)

    const localExacto = proveedores.value.find(p =>
      p.ruc === ruc || labelProveedor(p).toLowerCase() === q.toLowerCase()
    )
    if (localExacto) {
      seleccionarProveedor(localExacto)
      return
    }

    if (proveedoresFiltrados.value.length === 1 && !ruc) {
      seleccionarProveedor(proveedoresFiltrados.value[0])
      return
    }

    if (ruc) {
      const { data } = await api.get('/proveedores/consultar-ruc/', { params: { ruc } })
      if (data.ya_registrado && data.proveedor_id) {
        await load()
        const p = proveedores.value.find(x => x.id === data.proveedor_id)
        if (p) {
          seleccionarProveedor(p)
          return
        }
      }
      proveedorHint.value = 'Proveedor no registrado. Complete el formulario.'
      abrirModalCrearProveedor(data.ruc, data.razon_social || '', data.direccion || '')
      return
    }

    if (proveedoresFiltrados.value.length > 1) {
      showProveedorDropdown.value = true
      proveedorHint.value = 'Seleccione un proveedor de la lista.'
      return
    }

    proveedorHint.value = 'Proveedor no encontrado. Regístrelo ahora.'
    abrirModalCrearProveedor('', q, '')
  } catch (err) {
    proveedorHint.value = err.response?.data?.detail || 'No se pudo buscar el proveedor.'
  } finally {
    buscandoProveedor.value = false
  }
}

function onProveedorBlur() {
  setTimeout(() => { showProveedorDropdown.value = false }, 180)
}

async function onProveedorCreado(proveedor) {
  showModalProveedor.value = false
  if (proveedor?.id) {
    const existe = proveedores.value.find(x => x.id === proveedor.id)
    if (!existe) proveedores.value.push(proveedor)
    else Object.assign(existe, proveedor)
    seleccionarProveedor(proveedor)
  } else {
    await load()
  }
}

function resetItemForm() {
  itemForm.value = {
    descripcion: '',
    laboratorio: '',
    cantidad: '',
    unidad_medida: 'UND',
    lote: '',
    fecha_vencimiento: '',
    producto: '',
    marca: '',
    precio_unitario: '',
    igv_incluido: true,
  }
  itemFormError.value = ''
}

function abrirModalItem() {
  resetItemForm()
  showModalItem.value = true
}

function confirmarItem() {
  itemFormError.value = ''
  if (!itemForm.value.descripcion?.trim() || !itemForm.value.cantidad) {
    itemFormError.value = 'Descripción y cantidad son obligatorios.'
    return
  }
  if (itemForm.value.precio_unitario === '' || Number(itemForm.value.precio_unitario) < 0) {
    itemFormError.value = 'Ingrese el precio unitario.'
    return
  }
  const prod = productoItemSeleccionado.value
  if (prod?.requiere_fecha_vencimiento && !itemForm.value.fecha_vencimiento) {
    itemFormError.value = 'Este producto requiere fecha de vencimiento.'
    return
  }
  itemsFactura.value.push({
    numero_item: itemsFactura.value.length + 1,
    ...itemForm.value,
    producto: itemForm.value.producto || null,
    precio_unitario: Number(itemForm.value.precio_unitario),
    cantidad: Number(itemForm.value.cantidad),
  })
  showModalItem.value = false
}

function importesItem(it) {
  return calcularLinea(it.cantidad, it.precio_unitario, it.igv_incluido)
}

function onProductoSelect() {
  const p = productoItemSeleccionado.value
  if (p) {
    itemForm.value.descripcion = p.nombre
    itemForm.value.unidad_medida = p.unidad_medida || p.unidad_codigo || 'UND'
    itemForm.value.laboratorio = p.laboratorio || ''
    itemForm.value.marca = p.marca_nombre || ''
  } else {
    itemForm.value.marca = ''
  }
}

function quitarItem(i) {
  itemsFactura.value.splice(i, 1)
  itemsFactura.value.forEach((it, idx) => { it.numero_item = idx + 1 })
}

async function guardarFactura() {
  if (!form.value.serie?.trim() || form.value.numero === '' || !form.value.proveedor || !form.value.fecha_orden || !itemsFactura.value.length) {
    facturaError.value = 'Complete serie, número, proveedor, fecha e ítems.'
    return
  }
  guardandoFactura.value = true
  const payload = {
    serie: form.value.serie.trim(),
    numero: parseInt(form.value.numero, 10),
    proveedor: form.value.proveedor,
    fecha_orden: form.value.fecha_orden,
    observaciones: form.value.observaciones,
    detalles: itemsFactura.value.map(detallePayload),
  }
  try {
    if (editFacturaId.value) {
      await api.put(`/ordenes-compra/${editFacturaId.value}/`, payload)
    } else {
      await api.post('/ordenes-compra/', payload)
    }
    showModalFactura.value = false
    editFacturaId.value = null
    await load()
  } catch (err) {
    const d = err.response?.data
    const detalleErr = d?.detalles?.[0]
    const primerDetalle = typeof detalleErr === 'object'
      ? Object.values(detalleErr).flat()[0]
      : detalleErr
    facturaError.value = d?.detail || d?.numero?.[0] || primerDetalle || 'Error al guardar la factura.'
  } finally {
    guardandoFactura.value = false
  }
}

async function eliminarFactura(f) {
  if (!puedeEditarFactura(f)) {
    alert(mensajeSinPermisoFactura(f))
    return
  }
  if (!confirm(`¿Eliminar la factura ${f.numero_completo}? Esta acción no se puede deshacer.`)) return
  try {
    await api.delete(`/ordenes-compra/${f.id}/`)
    if (editFacturaId.value === f.id) {
      showModalFactura.value = false
      editFacturaId.value = null
    }
    await load()
  } catch (err) {
    alert(err.response?.data?.detail || 'No se pudo eliminar la factura.')
  }
}

function abrirValidar(factura) {
  if (!puedeValidarFactura(factura)) {
    alert('Solo el jefe de almacén puede validar facturas pendientes.')
    return
  }
  facturaValidar.value = factura
  comentariosValidacion.value = ''
  docFiles.value = []
  validarError.value = ''
  showModalValidar.value = true
}

function onDocSelect(e) { docFiles.value = Array.from(e.target.files) }

async function enviarValidacion() {
  validando.value = true
  validarError.value = ''
  try {
    for (const file of docFiles.value) {
      const fd = new FormData()
      fd.append('orden', facturaValidar.value.id)
      fd.append('tipo', 'certificado')
      fd.append('nombre', file.name)
      fd.append('archivo', file)
      await api.post('/documentos/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    }
    await api.post(`/ordenes-compra/${facturaValidar.value.id}/validar-documentacion/`, {
      comentarios_validacion: comentariosValidacion.value,
    })
    showModalValidar.value = false
    await load()
  } catch (err) {
    validarError.value = err.response?.data?.detail || 'Error al validar.'
  } finally {
    validando.value = false
  }
}

function verDetalle(f) {
  facturaSeleccionada.value = f
  showModalDetalle.value = true
}

async function rechazar(id) {
  const factura = facturas.value.find(f => f.id === id)
  if (!factura || !puedeValidarFactura(factura)) {
    alert('Solo el jefe de almacén puede rechazar facturas pendientes.')
    return
  }
  const motivo = prompt('Motivo / documentos faltantes (REQ 01):')
  if (motivo) {
    try {
      await api.post(`/ordenes-compra/${id}/rechazar/`, { motivo_rechazo: motivo })
      await load()
    } catch (err) {
      alert(err.response?.data?.detail || 'No se pudo rechazar la factura.')
    }
  }
}

onMounted(async () => {
  auth.syncFromStorage()
  if (auth.isAuthenticated && auth.user && auth.user.es_admin === undefined) {
    await auth.fetchProfile()
  }
  await load()
})
</script>

<template>
  <div>
    <PageHeader title="Recepción de Insumos" subtitle="Registro y validación de facturas de proveedores">
      <template #actions>
        <button v-if="puedeRegistrar" class="btn btn-primary" @click="abrirModalFactura">
          <i class="bi bi-plus-lg me-1"></i>Nueva factura
        </button>
      </template>
    </PageHeader>

    <div v-if="puedeValidarDocs && !puedeRegistrar" class="alert alert-info border-0 small mb-3">
      <i class="bi bi-info-circle me-1"></i>
      <strong>Jefe de Almacén:</strong> puede <em>ver</em> facturas y validar o rechazar las que estén en estado
      <span class="badge badge-estado-pendiente">P — Pendiente</span>.
      No puede editar ni eliminar el contenido registrado por compras.
    </div>
    <div v-else-if="puedeRegistrar" class="alert alert-info border-0 small mb-3">
      <i class="bi bi-info-circle me-1"></i>
      <strong>Jefe de Compras:</strong> registra facturas en estado pendiente. Puede editarlas o eliminarlas
      mientras sigan en <span class="badge badge-estado-pendiente">P</span>.
      Una vez aceptadas o rechazadas por almacén, ya no podrá modificarlas.
    </div>
    <div v-else-if="esSuperAdmin" class="alert alert-warning border-0 small mb-3">
      <i class="bi bi-shield-lock me-1"></i>
      <strong>Superusuario:</strong> acceso total. Puede registrar, editar, validar y eliminar facturas según el flujo.
    </div>

    <div v-if="loadError" class="alert alert-danger py-2">{{ loadError }}</div>

    <div class="btn-group mb-3">
      <button class="btn btn-sm" :class="!filtroEstado ? 'btn-primary' : 'btn-outline-primary'" @click="filtroEstado = ''; load()">Todas</button>
      <button class="btn btn-sm" :class="filtroEstado === 'pendiente' ? 'btn-warning' : 'btn-outline-warning'" @click="filtroEstado = 'pendiente'; load()">P — Pendiente</button>
      <button class="btn btn-sm" :class="filtroEstado === 'atendido' ? 'btn-success' : 'btn-outline-success'" @click="filtroEstado = 'atendido'; load()">A — Atendido</button>
      <button class="btn btn-sm" :class="filtroEstado === 'rechazado' ? 'btn-danger' : 'btn-outline-danger'" @click="filtroEstado = 'rechazado'; load()">R — Rechazado</button>
    </div>

    <div class="card">
      <div class="card-header bg-white fw-semibold">Facturas — FEAT 01</div>
      <div class="card-body p-0">
        <div v-if="loading" class="text-center py-4"><div class="spinner-border text-primary"></div></div>
        <div v-else class="table-responsive">
          <table class="table table-hover table-sm mb-0">
            <thead class="table-light">
              <tr>
                <th>N° Factura</th>
                <th>Estado</th>
                <th>Proveedor / RUC</th>
                <th>Fecha</th>
                <th>Ítems</th>
                <th>Control cal.</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in facturasFiltradas" :key="f.id">
                <td class="fw-semibold">{{ f.numero_completo }}</td>
                <td><span class="badge" :class="estadoBadge[f.estado]">{{ estadoLabel[f.estado] }}</span></td>
                <td>
                  <div>{{ f.proveedor_ruc }} — {{ f.proveedor_nombre }}</div>
                </td>
                <td>{{ f.fecha_orden }}</td>
                <td>{{ f.total_items || 0 }}</td>
                <td><span class="badge bg-secondary">{{ f.control_calidad_estado || '—' }}</span></td>
                <td>
                  <button class="btn btn-sm btn-outline-primary me-1" title="Ver detalle" @click="verDetalle(f)"><i class="bi bi-list-ul"></i></button>
                  <button
                    v-if="puedeEditarFactura(f)"
                    class="btn btn-sm btn-outline-secondary me-1"
                    title="Editar factura"
                    @click="abrirEditarFactura(f)"
                  ><i class="bi bi-pencil"></i></button>
                  <button
                    v-if="puedeEditarFactura(f)"
                    class="btn btn-sm btn-outline-danger"
                    title="Eliminar factura"
                    @click="eliminarFactura(f)"
                  ><i class="bi bi-trash"></i></button>
                  <button
                    v-if="puedeValidarFactura(f)"
                    class="btn btn-sm btn-success me-1"
                    title="UC 01 Validar documentación"
                    @click="abrirValidar(f)"
                  ><i class="bi bi-file-earmark-check"></i></button>
                  <button
                    v-if="puedeValidarFactura(f)"
                    class="btn btn-sm btn-danger me-1"
                    title="Rechazar documentación"
                    @click="rechazar(f.id)"
                  ><i class="bi bi-x-lg"></i></button>
                </td>
              </tr>
              <tr v-if="!facturasFiltradas.length"><td colspan="7" class="text-center text-muted py-4">Sin facturas</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Modal nueva factura -->
    <div v-if="showModalFactura" class="modal fade show d-block factura-modal-backdrop" tabindex="-1">
      <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content factura-modal">
          <div class="modal-header factura-modal-header border-0">
            <div class="d-flex align-items-center gap-3">
              <div class="factura-icon-wrap">
                <i class="bi bi-receipt-cutoff"></i>
              </div>
              <div>
                <h5 class="modal-title mb-0">{{ tituloModalFactura }}</h5>
                <span class="factura-numero-badge">{{ numeroCompleto }}</span>
              </div>
            </div>
            <button class="btn-close btn-close-white" @click="showModalFactura = false; editFacturaId = null"></button>
          </div>

          <div class="modal-body pt-2">
            <div v-if="facturaError" class="alert alert-danger py-2 mx-1">{{ facturaError }}</div>
            <div v-else-if="editFacturaId && !itemsFactura.length" class="alert alert-info py-2 mx-1">
              <i class="bi bi-info-circle me-1"></i>
              Esta factura no tiene ítems registrados. Agregue los productos con «Agregar ítem».
            </div>

            <section class="factura-section">
              <h6 class="factura-section-title"><i class="bi bi-file-earmark-text me-2"></i>Datos generales</h6>
              <div class="card factura-card mb-4">
                <div class="card-body">
                  <div class="row g-3 align-items-end">
                    <div class="col-md-3 col-lg-2">
                      <label class="form-label factura-label">Serie *</label>
                      <input v-model="form.serie" class="form-control" placeholder="F001" />
                    </div>
                    <div class="col-md-3 col-lg-2">
                      <label class="form-label factura-label">Número *</label>
                      <input v-model="form.numero" type="number" min="1" class="form-control" placeholder="100" />
                    </div>
                    <div class="col-md-6 col-lg-5 position-relative">
                      <label class="form-label factura-label">Proveedor *</label>
                      <div class="input-group">
                        <span class="input-group-text bg-white"><i class="bi bi-building text-muted"></i></span>
                        <input
                          v-model="proveedorBusqueda"
                          class="form-control"
                          :class="{ 'border-warning': proveedorNoEncontrado }"
                          placeholder="RUC o razón social..."
                          autocomplete="off"
                          @input="onProveedorInput"
                          @focus="showProveedorDropdown = true"
                          @blur="onProveedorBlur"
                          @keyup.enter="buscarProveedor"
                        />
                        <button
                          type="button"
                          class="btn"
                          :class="proveedorNoEncontrado ? 'btn-warning' : 'btn-outline-primary'"
                          :disabled="buscandoProveedor"
                          @click="buscarProveedor"
                        >
                          <span v-if="buscandoProveedor" class="spinner-border spinner-border-sm"></span>
                          <i v-else class="bi bi-search"></i>
                        </button>
                      </div>
                      <div v-if="proveedorHint" class="form-text text-warning">{{ proveedorHint }}</div>
                      <div v-else-if="proveedorNoEncontrado" class="form-text text-warning">
                        <i class="bi bi-exclamation-circle me-1"></i>No registrado — use buscar para crear.
                      </div>
                      <ul
                        v-if="showProveedorDropdown && proveedoresFiltrados.length && !form.proveedor"
                        class="list-group position-absolute w-100 shadow proveedor-dropdown"
                      >
                        <li
                          v-for="p in proveedoresFiltrados"
                          :key="p.id"
                          class="list-group-item list-group-item-action py-2 small"
                          @mousedown.prevent="seleccionarProveedor(p)"
                        >
                          {{ labelProveedor(p) }}
                        </li>
                      </ul>
                    </div>
                    <div class="col-md-6 col-lg-3">
                      <label class="form-label factura-label">Fecha *</label>
                      <input v-model="form.fecha_orden" type="date" class="form-control" />
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="factura-section">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="factura-section-title mb-0"><i class="bi bi-box-seam me-2"></i>Detalle de productos</h6>
                <button type="button" class="btn btn-primary btn-sm px-3" @click="abrirModalItem">
                  <i class="bi bi-plus-lg me-1"></i>Agregar ítem
                </button>
              </div>

              <div class="card factura-card overflow-hidden mb-3">
                <div class="table-responsive factura-table-wrap">
                  <table class="table table-hover factura-table mb-0">
                    <thead>
                      <tr>
                        <th class="text-center" style="width:40px">#</th>
                        <th>Producto</th>
                        <th>Marca</th>
                        <th>Lab.</th>
                        <th>Lote</th>
                        <th>Venc.</th>
                        <th class="text-end">Cant.</th>
                        <th>U.M.</th>
                        <th class="text-end">P. unit.</th>
                        <th class="text-center">IGV</th>
                        <th class="text-end">Importe</th>
                        <th class="text-center" style="width:48px"></th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(it, i) in itemsFactura" :key="i">
                        <td class="text-center text-muted">{{ it.numero_item }}</td>
                        <td class="fw-medium">{{ it.descripcion }}</td>
                        <td>{{ it.marca || '—' }}</td>
                        <td class="text-muted small">{{ it.laboratorio || '—' }}</td>
                        <td class="small">{{ it.lote || '—' }}</td>
                        <td class="small">{{ it.fecha_vencimiento || '—' }}</td>
                        <td class="text-end">{{ it.cantidad }}</td>
                        <td><span class="badge bg-light text-dark border">{{ it.unidad_medida }}</span></td>
                        <td class="text-end font-monospace">S/ {{ formatoMoneda(it.precio_unitario) }}</td>
                        <td class="text-center">
                          <span class="badge" :class="it.igv_incluido ? 'bg-success-subtle text-success' : 'bg-info-subtle text-info'">
                            {{ it.igv_incluido ? 'Incl.' : '+18%' }}
                          </span>
                        </td>
                        <td class="text-end font-monospace fw-semibold">S/ {{ formatoMoneda(importesItem(it).importe) }}</td>
                        <td class="text-center">
                          <button class="btn btn-sm btn-light text-danger border-0" title="Quitar" @click="quitarItem(i)">
                            <i class="bi bi-trash"></i>
                          </button>
                        </td>
                      </tr>
                      <tr v-if="!itemsFactura.length">
                        <td colspan="12" class="text-center py-5">
                          <i class="bi bi-inbox display-6 text-muted d-block mb-2"></i>
                          <span class="text-muted">Sin ítems. Pulse «Agregar ítem» para comenzar.</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div v-if="itemsFactura.length" class="row justify-content-end">
                <div class="col-md-5 col-lg-4">
                  <div class="factura-totals-box">
                    <div class="factura-total-row">
                      <span>Subtotal (sin IGV)</span>
                      <span class="font-monospace">S/ {{ formatoMoneda(totalesFactura.subtotal) }}</span>
                    </div>
                    <div class="factura-total-row">
                      <span>IGV (18%)</span>
                      <span class="font-monospace">S/ {{ formatoMoneda(totalesFactura.igv) }}</span>
                    </div>
                    <div class="factura-total-row factura-total-final">
                      <span>Importe total</span>
                      <span class="font-monospace">S/ {{ formatoMoneda(totalesFactura.importe) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <div class="modal-footer factura-modal-footer border-0">
            <button
              v-if="editFacturaId"
              type="button"
              class="btn btn-outline-danger me-auto"
              @click="eliminarFactura({ id: editFacturaId, numero_completo: numeroCompleto })"
            >
              <i class="bi bi-trash me-1"></i>Eliminar
            </button>
            <button class="btn btn-light border" @click="showModalFactura = false; editFacturaId = null">Cancelar</button>
            <button class="btn btn-success px-4" :disabled="guardandoFactura || !itemsFactura.length" @click="guardarFactura">
              <i class="bi bi-check2-circle me-1"></i>
              Guardar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal agregar ítem -->
    <div v-if="showModalItem" class="modal fade show d-block factura-modal-backdrop item-modal-backdrop" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content factura-modal">
          <div class="modal-header factura-modal-header border-0 py-3">
            <div class="d-flex align-items-center gap-2">
              <i class="bi bi-box-seam fs-5"></i>
              <h5 class="modal-title mb-0">Ítem {{ itemsFactura.length + 1 }}</h5>
            </div>
            <button type="button" class="btn-close btn-close-white" @click="showModalItem = false"></button>
          </div>
          <div class="modal-body">
            <div v-if="itemFormError" class="alert alert-danger py-2">{{ itemFormError }}</div>

            <section class="mb-4">
              <h6 class="factura-section-title small"><i class="bi bi-tag me-1"></i>Identificación</h6>
              <div class="row g-3">
                <div class="col-12">
                  <label class="form-label factura-label">Producto (catálogo)</label>
                  <select v-model="itemForm.producto" class="form-select" @change="onProductoSelect">
                    <option value="">Manual / sin catálogo</option>
                    <option v-for="p in productos" :key="p.id" :value="p.id">{{ p.codigo }} — {{ p.nombre }}</option>
                  </select>
                </div>
                <div class="col-12">
                  <label class="form-label factura-label">Descripción *</label>
                  <input v-model="itemForm.descripcion" class="form-control" />
                </div>
                <div class="col-md-6">
                  <label class="form-label factura-label">Marca</label>
                  <input v-model="itemForm.marca" class="form-control" placeholder="Desde catálogo o manual" />
                </div>
                <div class="col-md-6">
                  <label class="form-label factura-label">Laboratorio</label>
                  <input v-model="itemForm.laboratorio" class="form-control" />
                </div>
              </div>
            </section>

            <section class="mb-4">
              <h6 class="factura-section-title small"><i class="bi bi-clipboard-data me-1"></i>Cantidad y trazabilidad</h6>
              <div class="row g-3">
                <div class="col-md-3">
                  <label class="form-label factura-label">Lote</label>
                  <input v-model="itemForm.lote" class="form-control" />
                </div>
                <div class="col-md-3">
                  <label class="form-label factura-label">
                    Vencimiento
                    <span v-if="productoItemSeleccionado?.requiere_fecha_vencimiento" class="text-danger">*</span>
                  </label>
                  <input v-model="itemForm.fecha_vencimiento" type="date" class="form-control" />
                </div>
                <div class="col-md-3">
                  <label class="form-label factura-label">Cantidad *</label>
                  <input v-model="itemForm.cantidad" type="number" min="0.01" step="0.01" class="form-control" />
                </div>
                <div class="col-md-3">
                  <label class="form-label factura-label">U.M.</label>
                  <select v-model="itemForm.unidad_medida" class="form-select">
                    <option v-for="u in unidadesMedida" :key="u.id" :value="u.codigo">{{ u.codigo }}</option>
                  </select>
                </div>
              </div>
            </section>

            <section class="mb-3">
              <h6 class="factura-section-title small"><i class="bi bi-currency-dollar me-1"></i>Precio e impuestos</h6>
              <div class="row g-3 align-items-start">
                <div class="col-md-4">
                  <label class="form-label factura-label">Precio unitario (S/) *</label>
                  <div class="input-group">
                    <span class="input-group-text">S/</span>
                    <input v-model="itemForm.precio_unitario" type="number" min="0" step="0.01" class="form-control font-monospace" />
                  </div>
                </div>
                <div class="col-md-8">
                  <label class="form-label factura-label d-block">IGV (18%)</label>
                  <div class="btn-group w-100" role="group">
                    <input id="igv-si" v-model="itemForm.igv_incluido" class="btn-check" type="radio" :value="true" />
                    <label class="btn btn-outline-primary" for="igv-si"><i class="bi bi-check-circle me-1"></i>Incluye IGV</label>
                    <input id="igv-no" v-model="itemForm.igv_incluido" class="btn-check" type="radio" :value="false" />
                    <label class="btn btn-outline-primary" for="igv-no"><i class="bi bi-plus-circle me-1"></i>+ IGV 18%</label>
                  </div>
                </div>
              </div>
            </section>

            <div class="factura-totals-box factura-totals-inline">
              <div class="row text-center g-2">
                <div class="col-4">
                  <div class="text-muted small">Subtotal</div>
                  <div class="fw-semibold font-monospace">S/ {{ formatoMoneda(itemImportesPreview.subtotal) }}</div>
                </div>
                <div class="col-4">
                  <div class="text-muted small">IGV</div>
                  <div class="fw-semibold font-monospace">S/ {{ formatoMoneda(itemImportesPreview.igv) }}</div>
                </div>
                <div class="col-4">
                  <div class="text-muted small">Importe línea</div>
                  <div class="fw-bold text-primary font-monospace fs-5">S/ {{ formatoMoneda(itemImportesPreview.importe) }}</div>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer factura-modal-footer border-0">
            <button class="btn btn-light border" @click="showModalItem = false">Cancelar</button>
            <button class="btn btn-primary px-4" @click="confirmarItem">
              <i class="bi bi-plus-lg me-1"></i>Agregar a la factura
            </button>
          </div>
        </div>
      </div>
    </div>

    <ProveedorFormModal
      :show="showModalProveedor"
      :initial-ruc="proveedorInicialRuc"
      :initial-razon-social="proveedorInicialRazon"
      :initial-direccion="proveedorInicialDireccion"
      @close="showModalProveedor = false"
      @created="onProveedorCreado"
    />

    <!-- Modal validar -->
    <div v-if="showModalValidar" class="modal fade show d-block" tabindex="-1" style="background:rgba(0,0,0,.5)">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header bg-success text-white">
            <h5 class="modal-title"><i class="bi bi-file-earmark-check me-2"></i>UC 01 — Validar documentación</h5>
            <button class="btn-close btn-close-white" @click="showModalValidar = false"></button>
          </div>
          <div class="modal-body">
            <p class="small">Factura <strong>{{ facturaValidar?.numero_completo }}</strong> — Adjunte PDF y comentarios. Al enviar: P → A.</p>
            <div v-if="validarError" class="alert alert-danger py-2">{{ validarError }}</div>
            <div class="mb-3">
              <label class="form-label small">Documentos PDF</label>
              <input type="file" class="form-control" accept=".pdf" multiple @change="onDocSelect" />
            </div>
            <div class="mb-3">
              <label class="form-label small">Comentarios</label>
              <textarea v-model="comentariosValidacion" class="form-control" rows="3"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showModalValidar = false">Cancelar</button>
            <button class="btn btn-success" :disabled="validando" @click="enviarValidacion">
              Validar y cambiar a Atendido (A)
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal detalle -->
    <div v-if="showModalDetalle && facturaSeleccionada" class="modal fade show d-block" tabindex="-1" style="background:rgba(0,0,0,.5)">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Factura {{ facturaSeleccionada.numero_completo }}</h5>
            <button class="btn-close" @click="showModalDetalle = false"></button>
          </div>
          <div class="modal-body">
            <p><strong>Proveedor:</strong> {{ facturaSeleccionada.proveedor_ruc }} — {{ facturaSeleccionada.proveedor_nombre }}</p>
            <p><strong>Estado:</strong> {{ estadoLabel[facturaSeleccionada.estado] }}</p>
            <div class="row small mb-3 g-2">
              <div class="col-md-4"><strong>Subtotal:</strong> S/ {{ formatoMoneda(facturaSeleccionada.subtotal_factura) }}</div>
              <div class="col-md-4"><strong>IGV:</strong> S/ {{ formatoMoneda(facturaSeleccionada.igv_factura) }}</div>
              <div class="col-md-4"><strong>Total:</strong> S/ {{ formatoMoneda(facturaSeleccionada.importe_total_factura) }}</div>
            </div>
            <table class="table table-sm table-bordered">
              <thead class="table-light">
                <tr>
                  <th>#</th><th>Descripción</th><th>Marca</th><th>Lote</th><th>Venc.</th><th>Cant.</th><th>P. unit.</th><th>IGV</th><th>Importe</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in facturaSeleccionada.detalles" :key="d.id">
                  <td>{{ d.numero_item }}</td>
                  <td>{{ d.descripcion }}</td>
                  <td>{{ d.marca || '—' }}</td>
                  <td>{{ d.lote || '—' }}</td>
                  <td>{{ d.fecha_vencimiento || '—' }}</td>
                  <td>{{ d.cantidad }}</td>
                  <td class="text-end">{{ formatoMoneda(d.precio_unitario) }}</td>
                  <td class="small">{{ d.igv_incluido ? 'Incl.' : '+18%' }}</td>
                  <td class="text-end">{{ formatoMoneda(d.importe) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.factura-modal-backdrop {
  background: rgba(15, 23, 42, 0.55);
  z-index: 1050;
  backdrop-filter: blur(2px);
}

.item-modal-backdrop {
  z-index: 1070;
}

.factura-modal {
  border: none;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.2);
}

.factura-modal-header {
  background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
  color: #fff;
  padding: 1.25rem 1.5rem;
}

.factura-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.35rem;
}

.factura-numero-badge {
  display: inline-block;
  margin-top: 0.25rem;
  padding: 0.15rem 0.65rem;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2rem;
}

.factura-section-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #64748b;
  margin-bottom: 0.75rem;
}

.factura-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #475569;
  margin-bottom: 0.35rem;
}

.factura-card {
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  box-shadow: none;
  background: #fafbfc;
}

.factura-table-wrap {
  max-height: 320px;
}

.factura-table thead {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f1f5f9;
}

.factura-table thead th {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  border-bottom: 2px solid #e2e8f0;
  padding: 0.65rem 0.5rem;
  white-space: nowrap;
}

.factura-table tbody td {
  font-size: 0.875rem;
  padding: 0.6rem 0.5rem;
  vertical-align: middle;
  border-color: #f1f5f9;
}

.factura-table tbody tr:hover {
  background: #f8fafc;
}

.factura-totals-box {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 0.75rem;
  padding: 1rem 1.25rem;
}

.factura-totals-inline {
  margin-top: 0.5rem;
}

.factura-total-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0;
  font-size: 0.9rem;
  color: #475569;
}

.factura-total-final {
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  border-top: 2px solid #cbd5e1;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0d6efd;
}

.factura-modal-footer {
  background: #f8fafc;
  padding: 1rem 1.5rem;
}

.proveedor-dropdown {
  z-index: 1080;
  max-height: 220px;
  overflow-y: auto;
  top: 100%;
  margin-top: 2px;
  border-radius: 0.5rem;
}
</style>
