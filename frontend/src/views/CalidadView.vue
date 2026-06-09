<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import { useAuthStore } from '../stores/auth'
import { puedeEjecutarControlCalidad } from '../config/roles'
import { formatoMoneda } from '../utils/igv'

const auth = useAuthStore()
const tab = ref('control')
const subTabResultados = ref('aceptados')
const facturasAtendidas = ref([])
const resultados = ref({ aceptados: [], rechazados: [], permisos: {}, totales: {} })
const loading = ref(true)
const loadingResultados = ref(false)
const facturaExpandidaId = ref(null)
const revisiones = reactive({})
const procesandoFacturaId = ref(null)
const errores = reactive({})


const permisos = computed(() => resultados.value.permisos || {})
const puedeEjecutar = computed(() =>
  !!permisos.value.ejecutar_control || puedeEjecutarControlCalidad(auth.user)
)
const puedeVerAceptados = computed(() => !!permisos.value.aceptados || !!auth.user?.es_admin)
const puedeVerRechazados = computed(() => !!permisos.value.rechazados || !!auth.user?.es_admin)
const esAdmin = computed(() => !!auth.user?.es_admin)

const facturasPendientes = computed(() =>
  facturasAtendidas.value.filter(x => x.control_calidad_estado === 'pendiente')
)

async function asegurarDetalleFactura(factura) {
  if (factura.detalles?.length) return factura
  if (!factura.total_items) return factura
  try {
    const { data } = await api.get(`/ordenes-compra/${factura.id}/`)
    return {
      ...factura,
      detalles: data.detalles || [],
      importe_total_factura: data.importe_total_factura,
      subtotal_factura: data.subtotal_factura,
      igv_factura: data.igv_factura,
      proveedor_ruc: data.proveedor_ruc,
    }
  } catch {
    return factura
  }
}

function initRevision(factura) {
  if (!factura?.detalles?.length) return
  if (revisiones[factura.id]) return
  revisiones[factura.id] = {}
  for (const d of factura.detalles) {
    revisiones[factura.id][d.id] = {
      estado: 'conforme',
      cantidad_rechazada: d.cantidad,
      motivo: '',
      comentarios: '',
      evidencia: null,
      evidenciaNombre: '',
    }
  }
}

function resumenFactura(facturaId) {
  const rev = revisiones[facturaId]
  if (!rev) return { conformes: 0, rechazados: 0, total: 0 }
  const vals = Object.values(rev)
  return {
    total: vals.length,
    conformes: vals.filter(r => r.estado === 'conforme').length,
    rechazados: vals.filter(r => r.estado === 'rechazado').length,
  }
}

function marcarTodosConformes(factura) {
  initRevision(factura)
  for (const d of factura.detalles) {
    revisiones[factura.id][d.id].estado = 'conforme'
    revisiones[factura.id][d.id].cantidad_rechazada = d.cantidad
    revisiones[factura.id][d.id].motivo = ''
    revisiones[factura.id][d.id].evidencia = null
    revisiones[factura.id][d.id].evidenciaNombre = ''
  }
}

function setEstadoItem(factura, detalle, estado) {
  initRevision(factura)
  const r = revisiones[factura.id][detalle.id]
  r.estado = estado
  if (estado === 'conforme') {
    r.motivo = ''
    r.cantidad_rechazada = detalle.cantidad
    r.evidencia = null
    r.evidenciaNombre = ''
  }
}

function onEvidenciaSelect(facturaId, detalleId, event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (!/\.(png|jpe?g)$/i.test(file.name)) {
    errores[facturaId] = 'La evidencia debe ser PNG o JPG.'
    event.target.value = ''
    return
  }
  errores[facturaId] = ''
  revisiones[facturaId][detalleId].evidencia = file
  revisiones[facturaId][detalleId].evidenciaNombre = file.name
}

async function subirEvidencias(facturaId, incidenciasCreadas) {
  for (const inc of incidenciasCreadas) {
    const rev = revisiones[facturaId]?.[inc.detalle_factura]
    if (!rev?.evidencia) continue
    const fd = new FormData()
    fd.append('incidencia', inc.id)
    fd.append('nombre', rev.evidencia.name)
    fd.append('archivo', rev.evidencia)
    await api.post('/evidencias-calidad/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  }
}

async function toggleFactura(factura) {
  if (facturaExpandidaId.value === factura.id) {
    facturaExpandidaId.value = null
    return
  }
  facturaExpandidaId.value = factura.id
  errores[factura.id] = ''
  const completa = await asegurarDetalleFactura(factura)
  const idx = facturasAtendidas.value.findIndex(f => f.id === factura.id)
  if (idx >= 0) facturasAtendidas.value[idx] = completa
  initRevision(completa)
}

async function loadResultados() {
  loadingResultados.value = true
  try {
    const { data } = await api.get('/control-calidad/resultados/')
    resultados.value = data
    if (!data.permisos?.aceptados && data.permisos?.rechazados) {
      subTabResultados.value = 'rechazados'
    } else if (data.permisos?.aceptados) {
      subTabResultados.value = 'aceptados'
    }
  } finally {
    loadingResultados.value = false
  }
}

async function load() {
  loading.value = true
  facturaExpandidaId.value = null
  try {
    const ordRes = await api.get('/ordenes-compra/', { params: { control_calidad: 'pendiente' } })
    const base = (ordRes.data.results || ordRes.data).filter(o => o.estado === 'atendido')
    facturasAtendidas.value = await Promise.all(base.map(asegurarDetalleFactura))
    await loadResultados()
  } finally {
    loading.value = false
  }
}

function fmtFecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-PE')
}

function badgeControl(estado) {
  return {
    conforme: 'bg-success',
    con_rechazos: 'bg-warning text-dark',
  }[estado] || 'bg-secondary'
}

function badgeIncidencia(estado) {
  return {
    abierta: 'bg-danger',
    en_seguimiento: 'bg-warning text-dark',
    cerrada: 'bg-secondary',
  }[estado] || 'bg-secondary'
}

function validarRevision(factura) {
  initRevision(factura)
  for (const d of factura.detalles) {
    const r = revisiones[factura.id][d.id]
    if (r.estado === 'rechazado' && !r.motivo?.trim()) {
      return `Indique el motivo del rechazo para: ${d.descripcion}`
    }
    if (r.estado === 'rechazado') {
      const cant = Number(r.cantidad_rechazada)
      if (!cant || cant <= 0 || cant > Number(d.cantidad)) {
        return `Cantidad rechazada inválida para: ${d.descripcion}`
      }
    }
  }
  return ''
}

async function finalizarControlFactura(factura) {
  const msg = validarRevision(factura)
  if (msg) {
    errores[factura.id] = msg
    return
  }
  procesandoFacturaId.value = factura.id
  errores[factura.id] = ''
  try {
    const items = factura.detalles.map(d => {
      const r = revisiones[factura.id][d.id]
      return {
        detalle_factura: d.id,
        estado: r.estado,
        cantidad_rechazada: r.estado === 'rechazado' ? Number(r.cantidad_rechazada) : undefined,
        motivo: r.estado === 'rechazado' ? r.motivo.trim() : '',
        comentarios: r.comentarios || '',
      }
    })
    const { data } = await api.post(`/ordenes-compra/${factura.id}/control-calidad/`, { items })
    if (data.incidencias_creadas?.length) {
      await subirEvidencias(factura.id, data.incidencias_creadas)
    }
    delete revisiones[factura.id]
    facturaExpandidaId.value = null
    await load()
  } catch (err) {
    errores[factura.id] = err.response?.data?.detail || 'Error al finalizar el control.'
  } finally {
    procesandoFacturaId.value = null
  }
}

function importeLinea(d) {
  const precio = Number(d.precio_unitario) || 0
  const cant = Number(d.cantidad) || 0
  if (d.igv_incluido) return precio * cant
  return precio * cant * 1.18
}

onMounted(async () => {
  if (!puedeEjecutarControlCalidad(auth.user)) {
    tab.value = 'resultados'
    await loadResultados()
  } else {
    await load()
  }
})
</script>

<template>
  <div>
    <PageHeader title="Control de calidad" subtitle="Inspección de productos recepcionados" />

    <div v-if="!puedeEjecutar" class="alert alert-light border small mb-3">
      <i class="bi bi-eye me-1"></i>
      Modo consulta: puede revisar resultados del control de calidad. Solo <strong>Control de Calidad</strong> ejecuta inspecciones.
    </div>

    <ul class="nav nav-tabs mb-3">
      <li v-if="puedeEjecutar" class="nav-item">
        <button class="nav-link" :class="{ active: tab === 'control' }" @click="tab = 'control'">
          UC 02 — Control recepción (FEAT 03-04)
        </button>
      </li>
      <li class="nav-item">
        <button
          v-if="puedeVerAceptados || puedeVerRechazados"
          class="nav-link"
          :class="{ active: tab === 'resultados' }"
          @click="tab = 'resultados'; loadResultados()"
        >
          Resultados del control
          <span v-if="resultados.totales?.rechazados" class="badge bg-warning text-dark ms-1">
            {{ resultados.totales.rechazados }} rech.
          </span>
        </button>
      </li>
    </ul>

    <div v-if="tab === 'control' && puedeEjecutar">
      <div class="alert alert-info py-2 small mb-3">
        <i class="bi bi-info-circle me-1"></i>
        <strong>Cómo funciona:</strong> abra una factura, marque cada producto como
        <span class="badge bg-success">Conforme</span> o
        <span class="badge bg-warning text-dark">Rechazado</span>
        y pulse <strong>Finalizar control</strong>.
        En rechazos puede adjuntar evidencia fotográfica (PNG / JPG).
      </div>

      <div class="card mb-3">
        <div class="card-header d-flex justify-content-between align-items-center">
          <span class="fw-semibold">Facturas pendientes de control</span>
          <span v-if="facturasPendientes.length" class="badge bg-primary">{{ facturasPendientes.length }}</span>
        </div>
        <div class="card-body p-0">
          <div v-if="loading" class="text-center py-4"><div class="spinner-border text-primary"></div></div>
          <div v-else-if="!facturasPendientes.length" class="text-center text-muted py-4">
            No hay facturas pendientes de control
          </div>
          <div v-else class="accordion-calidad">
            <article
              v-for="o in facturasPendientes"
              :key="o.id"
              class="accordion-item-calidad"
              :class="{ expanded: facturaExpandidaId === o.id }"
            >
              <!-- Cabecera colapsable -->
              <button type="button" class="accordion-toggle w-100 text-start" @click="toggleFactura(o)">
                <div class="row g-2 align-items-center">
                  <div class="col-auto">
                    <i class="bi chevron" :class="facturaExpandidaId === o.id ? 'bi-chevron-down' : 'bi-chevron-right'"></i>
                  </div>
                  <div class="col-md-2">
                    <span class="fw-bold">{{ o.numero_completo }}</span>
                  </div>
                  <div class="col-md-4 text-truncate" :title="o.proveedor_nombre">
                    {{ o.proveedor_nombre }}
                  </div>
                  <div class="col-md-2 small text-muted">{{ o.fecha_orden }}</div>
                  <div class="col-md-3 text-md-end">
                    <span class="badge bg-light text-dark border me-1">{{ o.total_items || o.detalles?.length || 0 }} ítems</span>
                    <span class="fw-semibold text-primary">S/ {{ formatoMoneda(o.importe_total_factura) }}</span>
                    <template v-if="revisiones[o.id]">
                      <span class="badge bg-success ms-1">{{ resumenFactura(o.id).conformes }} OK</span>
                      <span v-if="resumenFactura(o.id).rechazados" class="badge bg-warning text-dark ms-1">
                        {{ resumenFactura(o.id).rechazados }} rech.
                      </span>
                    </template>
                  </div>
                </div>
              </button>

              <!-- Panel expandido: revisión ítem por ítem -->
              <div v-if="facturaExpandidaId === o.id" class="accordion-panel">
                <div v-if="errores[o.id]" class="alert alert-danger py-2 mx-3 mt-2 mb-0">{{ errores[o.id] }}</div>

                <div class="d-flex flex-wrap gap-2 px-3 pt-3 pb-2">
                  <button type="button" class="btn btn-sm btn-outline-success" @click="marcarTodosConformes(o)">
                    <i class="bi bi-check-all me-1"></i>Todos conformes
                  </button>
                </div>

                <div v-if="!o.detalles?.length" class="alert alert-warning mx-3 small">Sin ítems en esta factura.</div>
                <div v-else class="table-responsive px-3 pb-2">
                  <table class="table table-sm calidad-table mb-0">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Producto</th>
                        <th>Lote</th>
                        <th>Venc.</th>
                        <th class="text-end">Cant.</th>
                        <th>U.M.</th>
                        <th class="text-center" style="min-width:160px">Resultado</th>
                        <th style="min-width:200px">Motivo rechazo</th>
                        <th style="min-width:180px">Evidencia</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="d in o.detalles"
                        :key="d.id"
                        :class="{ 'row-rechazado': revisiones[o.id]?.[d.id]?.estado === 'rechazado' }"
                      >
                        <td class="text-muted">{{ d.numero_item }}</td>
                        <td>
                          <div class="fw-medium">{{ d.descripcion }}</div>
                          <div class="small text-muted">{{ d.marca || '—' }} · {{ d.laboratorio || '—' }}</div>
                        </td>
                        <td class="small">{{ d.lote || '—' }}</td>
                        <td class="small">{{ d.fecha_vencimiento || '—' }}</td>
                        <td class="text-end">{{ d.cantidad }}</td>
                        <td>{{ d.unidad_medida }}</td>
                        <td class="text-center">
                          <div class="btn-group btn-group-sm" role="group">
                            <input
                              :id="`ok-${o.id}-${d.id}`"
                              type="radio"
                              class="btn-check"
                              :checked="revisiones[o.id]?.[d.id]?.estado === 'conforme'"
                              @change="setEstadoItem(o, d, 'conforme')"
                            />
                            <label class="btn btn-outline-success" :for="`ok-${o.id}-${d.id}`">OK</label>
                            <input
                              :id="`no-${o.id}-${d.id}`"
                              type="radio"
                              class="btn-check"
                              :checked="revisiones[o.id]?.[d.id]?.estado === 'rechazado'"
                              @change="setEstadoItem(o, d, 'rechazado')"
                            />
                            <label class="btn btn-outline-warning" :for="`no-${o.id}-${d.id}`">Rech.</label>
                          </div>
                        </td>
                        <td>
                          <template v-if="revisiones[o.id]?.[d.id]?.estado === 'rechazado'">
                            <div class="d-flex gap-1 mb-1">
                              <input
                                v-model="revisiones[o.id][d.id].cantidad_rechazada"
                                type="number"
                                min="0.01"
                                :max="d.cantidad"
                                step="0.01"
                                class="form-control form-control-sm"
                                style="width:72px"
                                title="Cant. rechazada"
                              />
                              <input
                                v-model="revisiones[o.id][d.id].motivo"
                                class="form-control form-control-sm"
                                placeholder="Motivo *"
                              />
                            </div>
                          </template>
                          <span v-else class="text-muted small">—</span>
                        </td>
                        <td>
                          <template v-if="revisiones[o.id]?.[d.id]?.estado === 'rechazado'">
                            <input
                              type="file"
                              class="form-control form-control-sm"
                              accept=".png,.jpg,.jpeg"
                              @change="e => onEvidenciaSelect(o.id, d.id, e)"
                            />
                            <small v-if="revisiones[o.id][d.id].evidenciaNombre" class="text-success d-block mt-1">
                              <i class="bi bi-paperclip"></i> {{ revisiones[o.id][d.id].evidenciaNombre }}
                            </small>
                            <small v-else class="text-muted d-block mt-1">PNG / JPG (opcional)</small>
                          </template>
                          <span v-else class="text-muted small">—</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div class="accordion-panel-footer px-3 pb-3">
                  <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
                    <div class="small text-muted">
                      <span class="badge bg-success">{{ resumenFactura(o.id).conformes }} conformes</span>
                      <span v-if="resumenFactura(o.id).rechazados" class="badge bg-warning text-dark ms-1">
                        {{ resumenFactura(o.id).rechazados }} rechazados
                      </span>
                    </div>
                    <button
                      type="button"
                      class="btn btn-primary"
                      :disabled="procesandoFacturaId === o.id || !o.detalles?.length"
                      @click="finalizarControlFactura(o)"
                    >
                      <span v-if="procesandoFacturaId === o.id" class="spinner-border spinner-border-sm me-1"></span>
                      <i v-else class="bi bi-check2-circle me-1"></i>
                      Finalizar control de factura
                    </button>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </div>
      </div>
    </div>

    <div v-if="tab === 'resultados'">
      <div v-if="esAdmin" class="alert alert-light border py-2 small mb-3">
        <i class="bi bi-shield-check me-1 text-primary"></i>
        Como <strong>administrador</strong> visualiza todos los productos aceptados y rechazados del sistema.
      </div>

      <ul class="nav nav-pills mb-3">
        <li v-if="puedeVerAceptados" class="nav-item">
          <button
            class="nav-link"
            :class="{ active: subTabResultados === 'aceptados' }"
            @click="subTabResultados = 'aceptados'"
          >
            <i class="bi bi-check-circle me-1"></i>Aceptados
            <span class="badge bg-success ms-1">{{ resultados.totales?.aceptados || 0 }}</span>
          </button>
        </li>
        <li v-if="puedeVerRechazados" class="nav-item">
          <button
            class="nav-link"
            :class="{ active: subTabResultados === 'rechazados' }"
            @click="subTabResultados = 'rechazados'"
          >
            <i class="bi bi-x-circle me-1"></i>Rechazados
            <span class="badge bg-danger ms-1">{{ resultados.totales?.rechazados || 0 }}</span>
          </button>
        </li>
      </ul>

      <div v-if="loadingResultados" class="text-center py-4">
        <div class="spinner-border text-primary"></div>
      </div>

      <!-- Aceptados -->
      <div v-else-if="subTabResultados === 'aceptados' && puedeVerAceptados" class="card">
        <div class="card-header fw-semibold bg-success bg-opacity-10 text-success">
          Productos aceptados — listos para almacenamiento
        </div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-hover table-sm mb-0 calidad-table">
              <thead>
                <tr>
                  <th>Factura</th>
                  <th>Fecha control</th>
                  <th>Proveedor</th>
                  <th>#</th>
                  <th>Producto</th>
                  <th>Lote</th>
                  <th>Venc.</th>
                  <th class="text-end">Cant. aceptada</th>
                  <th>U.M.</th>
                  <th>Control</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, idx) in resultados.aceptados" :key="`a-${r.detalle_factura_id}-${idx}`">
                  <td class="fw-semibold">{{ r.numero_factura }}</td>
                  <td class="small">{{ fmtFecha(r.fecha_control) }}</td>
                  <td class="small text-truncate" style="max-width:140px" :title="r.proveedor_nombre">
                    {{ r.proveedor_nombre }}
                  </td>
                  <td>{{ r.numero_item }}</td>
                  <td>
                    <div class="fw-medium">{{ r.descripcion }}</div>
                    <div class="small text-muted">{{ r.marca || '—' }} · {{ r.laboratorio || '—' }}</div>
                  </td>
                  <td>{{ r.lote || '—' }}</td>
                  <td>{{ r.fecha_vencimiento || '—' }}</td>
                  <td class="text-end fw-semibold text-success">{{ r.cantidad_aceptada }}</td>
                  <td>{{ r.unidad_medida }}</td>
                  <td>
                    <span class="badge" :class="badgeControl(r.control_calidad_estado)">
                      {{ r.control_calidad_estado === 'con_rechazos' ? 'Parcial' : 'Conforme' }}
                    </span>
                  </td>
                </tr>
                <tr v-if="!resultados.aceptados?.length">
                  <td colspan="10" class="text-center text-muted py-4">Sin productos aceptados registrados</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Rechazados -->
      <div v-else-if="subTabResultados === 'rechazados' && puedeVerRechazados" class="card">
        <div class="card-header fw-semibold bg-warning bg-opacity-25">
          Productos rechazados — detalle, motivo y evidencia
        </div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-hover table-sm mb-0 calidad-table">
              <thead>
                <tr>
                  <th>Factura</th>
                  <th>Fecha</th>
                  <th>Producto</th>
                  <th>Lote</th>
                  <th class="text-end">Cant. rech.</th>
                  <th>Motivo</th>
                  <th>Comentarios</th>
                  <th>Estado</th>
                  <th>Evidencia</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in resultados.rechazados" :key="`r-${r.incidencia_id}`" class="row-rechazado">
                  <td class="fw-semibold">{{ r.numero_factura }}</td>
                  <td class="small">{{ fmtFecha(r.creado_en) }}</td>
                  <td>
                    <div class="fw-medium">{{ r.descripcion }}</div>
                    <div class="small text-muted">{{ r.proveedor_nombre }}</div>
                  </td>
                  <td>{{ r.lote || '—' }}</td>
                  <td class="text-end fw-semibold text-danger">{{ r.cantidad_rechazada }}</td>
                  <td>
                    <span class="fw-medium">{{ r.motivo }}</span>
                  </td>
                  <td class="small">{{ r.comentarios || '—' }}</td>
                  <td>
                    <span class="badge" :class="badgeIncidencia(r.estado_incidencia)">
                      {{ r.estado_incidencia?.replace('_', ' ') }}
                    </span>
                  </td>
                  <td>
                    <template v-if="r.evidencias?.length">
                      <a
                        v-for="ev in r.evidencias"
                        :key="ev.id"
                        :href="ev.url"
                        target="_blank"
                        rel="noopener"
                        class="btn btn-sm btn-outline-primary me-1 mb-1"
                        :title="ev.nombre"
                      >
                        <i class="bi bi-paperclip"></i>
                        {{ ev.nombre.length > 18 ? ev.nombre.slice(0, 15) + '…' : ev.nombre }}
                      </a>
                    </template>
                    <span v-else class="text-muted small">Sin adjunto</span>
                  </td>
                </tr>
                <tr v-if="!resultados.rechazados?.length">
                  <td colspan="9" class="text-center text-muted py-4">Sin productos rechazados registrados</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div v-else-if="!puedeVerAceptados && !puedeVerRechazados" class="alert alert-warning">
        Su rol no tiene permiso para consultar resultados de control de calidad.
      </div>
    </div>
  </div>
</template>

<style scoped>
.calidad-section-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #64748b;
}

.calidad-table thead th {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  background: #f1f5f9;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.calidad-table tbody td {
  font-size: 0.875rem;
  vertical-align: middle;
}

.row-rechazado {
  background: #fff8e6;
}

.accordion-calidad {
  border-top: 1px solid #e2e8f0;
}

.accordion-item-calidad {
  border-bottom: 1px solid #e2e8f0;
}

.accordion-item-calidad.expanded {
  background: #fafbfc;
}

.accordion-toggle {
  border: none;
  background: #fff;
  padding: 0.85rem 1rem;
  transition: background 0.15s;
}

.accordion-toggle:hover {
  background: #f8fafc;
}

.accordion-item-calidad.expanded .accordion-toggle {
  background: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
}

.accordion-toggle .chevron {
  color: #64748b;
}

.accordion-panel {
  animation: slideDown 0.2s ease;
}

.accordion-panel-footer {
  border-top: 1px solid #e2e8f0;
  padding-top: 0.75rem;
  margin-top: 0.5rem;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
