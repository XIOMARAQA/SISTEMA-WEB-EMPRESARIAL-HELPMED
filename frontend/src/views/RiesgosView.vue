<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'

const tab = ref('activos')
const activos = ref([])
const amenazas = ref([])
const vulnerabilidades = ref([])
const riesgos = ref([])
const evaluaciones = ref([])
const tratamientos = ref([])
const loading = ref(true)
const errorCarga = ref('')
const exportandoExcel = ref(false)
const errorExport = ref('')

function extraerLista(respuesta) {
  const data = respuesta?.data
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}
const codigoActivoPreview = ref('')
const cargandoCodigoActivo = ref(false)
const guardandoActivo = ref(false)
const errorActivo = ref('')

const CLASIFICACIONES_ACTIVO = [
  { value: 'informacion', label: 'Información' },
  { value: 'software', label: 'Software' },
  { value: 'hardware', label: 'Hardware' },
  { value: 'personal', label: 'Personal' },
  { value: 'servicios', label: 'Servicios' },
  { value: 'infraestructura', label: 'Infraestructura' },
]

const formActivo = ref({ nombre: '', clasificacion: 'informacion', criticidad: 'media', descripcion: '' })
const formAmenaza = ref({ tipo: 'phishing', nombre: '', descripcion: '' })
const codigoAmenazaPreview = ref('')
const guardandoAmenaza = ref(false)
const errorAmenaza = ref('')

const TIPOS_AMENAZA = [
  { value: 'phishing', label: 'Phishing' },
  { value: 'malware', label: 'Malware' },
  { value: 'ransomware', label: 'Ransomware' },
  { value: 'sql_injection', label: 'SQL Injection' },
  { value: 'xss', label: 'XSS' },
  { value: 'fuerza_bruta', label: 'Fuerza bruta' },
  { value: 'error_humano', label: 'Error humano' },
  { value: 'robo_equipos', label: 'Robo de equipos' },
  { value: 'acceso_no_autorizado', label: 'Acceso no autorizado' },
]
const formVuln = ref({ activo: '', nombre: '', descripcion: '', severidad: 'media' })
const codigoVulnPreview = ref('')
const guardandoVuln = ref(false)
const errorVuln = ref('')
const formRiesgo = ref({ activo: '', amenaza: '', vulnerabilidad: '', descripcion: '' })
const codigoRiesgoPreview = ref('')
const guardandoRiesgo = ref(false)
const errorRiesgo = ref('')
const formEval = ref({ riesgo: '', tipo: 'inherente', probabilidad: 3, impacto: 3, fecha_evaluacion: new Date().toISOString().slice(0, 10) })
const formTrat = ref({ riesgo: '', estrategia: 'mitigar', control_aplicado: '', fecha_inicio: new Date().toISOString().slice(0, 10) })

const showEditModal = ref(false)
const editTipo = ref('')
const editId = ref(null)
const editCodigo = ref('')
const editForm = ref({})
const guardandoEdicion = ref(false)
const errorEdicion = ref('')
const eliminandoId = ref(null)

const BAJA_CONFIG = {
  activos: { endpoint: 'activos', campo: 'activo', valor: false, etiqueta: 'activo' },
  amenazas: { endpoint: 'amenazas', campo: 'activo', valor: false, etiqueta: 'amenaza' },
  vulnerabilidades: { endpoint: 'vulnerabilidades', campo: 'estado', valor: 'cerrada', etiqueta: 'vulnerabilidad' },
  riesgos: { endpoint: 'riesgos', campo: 'eliminado', valor: true, etiqueta: 'riesgo' },
  evaluaciones: { endpoint: 'evaluaciones-riesgo', campo: 'activo', valor: false, etiqueta: 'evaluación' },
  tratamientos: { endpoint: 'tratamientos-riesgo', campo: 'activo', valor: false, etiqueta: 'tratamiento' },
}

const TITULO_EDICION = {
  activos: 'Editar activo',
  amenazas: 'Editar amenaza',
  vulnerabilidades: 'Editar vulnerabilidad',
  riesgos: 'Editar riesgo',
  evaluaciones: 'Editar evaluación',
  tratamientos: 'Editar tratamiento',
}

const vulnsPorActivo = computed(() => {
  if (!formRiesgo.value.activo) return []
  return vulnerabilidades.value.filter(v => v.activo === formRiesgo.value.activo)
})

const PROB_LABELS = ['Muy baja', 'Baja', 'Media', 'Alta', 'Muy alta']
const IMP_LABELS = ['Insignificante', 'Menor', 'Moderado', 'Mayor', 'Crítico']

const evaluacionesInherentes = computed(() =>
  evaluaciones.value.filter(e => e.tipo === 'inherente')
)

const evalPreview = computed(() => {
  const prob = formEval.value.probabilidad
  const imp = formEval.value.impacto
  const valor = prob * imp
  return {
    valor,
    nivel: valorANivel(valor),
    celda: `I${imp} × P${prob}`,
  }
})

const matrizDetalle = computed(() => {
  const grid = Array.from({ length: 5 }, () =>
    Array.from({ length: 5 }, () => ({ riesgos: [] }))
  )
  evaluacionesInherentes.value.forEach(e => {
    grid[e.impacto - 1][e.probabilidad - 1].riesgos.push({
      codigo: e.riesgo_codigo,
      valor: e.valor_riesgo,
      nivel: e.nivel,
    })
  })
  return grid
})

function valorANivel(valor) {
  if (valor <= 5) return 'bajo'
  if (valor <= 10) return 'medio'
  if (valor <= 15) return 'alto'
  return 'critico'
}

function celdaBg(impacto, probabilidad, tieneRiesgos) {
  const nivel = valorANivel(impacto * probabilidad)
  const tonos = {
    bajo: { con: '#bbf7d0', sin: '#f0fdf4' },
    medio: { con: '#fde68a', sin: '#fffbeb' },
    alto: { con: '#fdba74', sin: '#fff7ed' },
    critico: { con: '#fca5a5', sin: '#fef2f2' },
  }
  return tonos[nivel][tieneRiesgos ? 'con' : 'sin']
}

function celdaTooltip(impacto, probabilidad) {
  const celda = matrizDetalle.value[impacto - 1][probabilidad - 1]
  const valor = impacto * probabilidad
  const nivel = valorANivel(valor)
  if (!celda.riesgos.length) {
    return `Celda I${impacto} × P${probabilidad} · Valor ${valor} (${nivel}) · Sin riesgos`
  }
  const lista = celda.riesgos.map(r => `${r.codigo} (valor ${r.valor})`).join(', ')
  return `I${impacto} × P${probabilidad} · Valor ${valor} (${nivel}) · ${lista}`
}

function nivelClass(nivel) {
  return { critico: 'riesgo-critico', alto: 'riesgo-alto', medio: 'riesgo-medio', bajo: 'riesgo-bajo' }[nivel] || ''
}

function nivelBadgeClass(nivel) {
  return `matriz-badge-${nivel || 'bajo'}`
}

async function load() {
  loading.value = true
  errorCarga.value = ''
  try {
    const [a, am, v, r, e, t] = await Promise.all([
      api.get('/activos/'), api.get('/amenazas/'), api.get('/vulnerabilidades/'),
      api.get('/riesgos/'), api.get('/evaluaciones-riesgo/'), api.get('/tratamientos-riesgo/'),
    ])
    activos.value = extraerLista(a)
    amenazas.value = extraerLista(am)
    vulnerabilidades.value = extraerLista(v)
    riesgos.value = extraerLista(r)
    evaluaciones.value = extraerLista(e)
    tratamientos.value = extraerLista(t)
  } catch {
    errorCarga.value = 'No se pudieron cargar los datos. Compruebe que el backend esté en ejecución (puerto 8000) y pulse Reintentar.'
  } finally {
    loading.value = false
  }
}

async function actualizarCodigoActivo() {
  cargandoCodigoActivo.value = true
  try {
    const { data } = await api.get('/activos/siguiente-codigo/', {
      params: { clasificacion: formActivo.value.clasificacion },
    })
    codigoActivoPreview.value = data.codigo
  } catch {
    codigoActivoPreview.value = ''
  } finally {
    cargandoCodigoActivo.value = false
  }
}

async function crearActivo() {
  if (!formActivo.value.nombre.trim()) {
    errorActivo.value = 'Indique el nombre del activo.'
    return
  }
  guardandoActivo.value = true
  errorActivo.value = ''
  try {
    await api.post('/activos/', {
      nombre: formActivo.value.nombre.trim(),
      clasificacion: formActivo.value.clasificacion,
      criticidad: formActivo.value.criticidad,
      descripcion: formActivo.value.descripcion?.trim() || '',
    })
    formActivo.value.nombre = ''
    formActivo.value.descripcion = ''
    await load()
    await actualizarCodigoActivo()
  } catch (e) {
    const d = e.response?.data
    errorActivo.value = d?.detail
      || d?.nombre?.[0]
      || Object.values(d || {}).flat().find(v => typeof v === 'string')
      || 'No se pudo registrar el activo.'
  } finally {
    guardandoActivo.value = false
  }
}
async function actualizarCodigoAmenaza() {
  try {
    const { data } = await api.get('/amenazas/siguiente-codigo/')
    codigoAmenazaPreview.value = data.codigo
  } catch {
    codigoAmenazaPreview.value = ''
  }
}

async function crearAmenaza() {
  if (!formAmenaza.value.nombre.trim()) {
    errorAmenaza.value = 'Indique el nombre de la amenaza.'
    return
  }
  guardandoAmenaza.value = true
  errorAmenaza.value = ''
  try {
    await api.post('/amenazas/', {
      tipo: formAmenaza.value.tipo,
      nombre: formAmenaza.value.nombre.trim(),
      descripcion: formAmenaza.value.descripcion?.trim() || '',
    })
    formAmenaza.value.nombre = ''
    formAmenaza.value.descripcion = ''
    await load()
    await actualizarCodigoAmenaza()
  } catch (e) {
    const d = e.response?.data
    errorAmenaza.value = d?.detail
      || d?.nombre?.[0]
      || Object.values(d || {}).flat().find(v => typeof v === 'string')
      || 'No se pudo registrar la amenaza.'
  } finally {
    guardandoAmenaza.value = false
  }
}
async function actualizarCodigoVuln() {
  try {
    const { data } = await api.get('/vulnerabilidades/siguiente-codigo/')
    codigoVulnPreview.value = data.codigo
  } catch {
    codigoVulnPreview.value = ''
  }
}

async function crearVuln() {
  if (!formVuln.value.activo) {
    errorVuln.value = 'Seleccione el activo afectado.'
    return
  }
  if (!formVuln.value.nombre.trim()) {
    errorVuln.value = 'Indique el nombre de la vulnerabilidad.'
    return
  }
  guardandoVuln.value = true
  errorVuln.value = ''
  try {
    await api.post('/vulnerabilidades/', {
      activo: formVuln.value.activo,
      nombre: formVuln.value.nombre.trim(),
      descripcion: formVuln.value.descripcion?.trim() || formVuln.value.nombre.trim(),
      severidad: formVuln.value.severidad,
    })
    formVuln.value.nombre = ''
    formVuln.value.descripcion = ''
    await load()
    await actualizarCodigoVuln()
  } catch (e) {
    const d = e.response?.data
    errorVuln.value = d?.detail
      || d?.activo?.[0]
      || d?.nombre?.[0]
      || Object.values(d || {}).flat().find(v => typeof v === 'string')
      || 'No se pudo registrar la vulnerabilidad.'
  } finally {
    guardandoVuln.value = false
  }
}
async function actualizarCodigoRiesgo() {
  try {
    const { data } = await api.get('/riesgos/siguiente-codigo/')
    codigoRiesgoPreview.value = data.codigo
  } catch {
    codigoRiesgoPreview.value = ''
  }
}

async function crearRiesgo() {
  if (!formRiesgo.value.activo) {
    errorRiesgo.value = 'Seleccione el activo.'
    return
  }
  if (!formRiesgo.value.amenaza) {
    errorRiesgo.value = 'Seleccione la amenaza.'
    return
  }
  guardandoRiesgo.value = true
  errorRiesgo.value = ''
  try {
    const payload = {
      activo: formRiesgo.value.activo,
      amenaza: formRiesgo.value.amenaza,
    }
    if (formRiesgo.value.vulnerabilidad) {
      payload.vulnerabilidad = formRiesgo.value.vulnerabilidad
    }
    if (formRiesgo.value.descripcion?.trim()) {
      payload.descripcion = formRiesgo.value.descripcion.trim()
    }
    await api.post('/riesgos/', payload)
    formRiesgo.value.vulnerabilidad = ''
    formRiesgo.value.descripcion = ''
    await load()
    await actualizarCodigoRiesgo()
  } catch (e) {
    const d = e.response?.data
    errorRiesgo.value = d?.detail
      || d?.activo?.[0]
      || d?.amenaza?.[0]
      || Object.values(d || {}).flat().find(v => typeof v === 'string')
      || 'No se pudo registrar el riesgo.'
  } finally {
    guardandoRiesgo.value = false
  }
}
async function crearEval() { await api.post('/evaluaciones-riesgo/', formEval.value); await load() }
async function crearTrat() { await api.post('/tratamientos-riesgo/', formTrat.value); await load() }

function cerrarEditar() {
  showEditModal.value = false
  editTipo.value = ''
  editId.value = null
  editCodigo.value = ''
  editForm.value = {}
  errorEdicion.value = ''
}

function abrirEditar(tipo, item) {
  editTipo.value = tipo
  editId.value = item.id
  editCodigo.value = item.codigo || item.riesgo_codigo || ''
  errorEdicion.value = ''
  if (tipo === 'activos') {
    editForm.value = {
      nombre: item.nombre,
      clasificacion: item.clasificacion,
      criticidad: item.criticidad,
      descripcion: item.descripcion || '',
    }
  } else if (tipo === 'amenazas') {
    editForm.value = { tipo: item.tipo, nombre: item.nombre, descripcion: item.descripcion || '' }
  } else if (tipo === 'vulnerabilidades') {
    editForm.value = {
      activo: item.activo,
      nombre: item.nombre,
      severidad: item.severidad,
      estado: item.estado,
      descripcion: item.descripcion || '',
    }
  } else if (tipo === 'riesgos') {
    editForm.value = {
      activo: item.activo,
      amenaza: item.amenaza,
      vulnerabilidad: item.vulnerabilidad || '',
      descripcion: item.descripcion || '',
    }
  } else if (tipo === 'evaluaciones') {
    editForm.value = {
      riesgo: item.riesgo,
      tipo: item.tipo,
      probabilidad: item.probabilidad,
      impacto: item.impacto,
      fecha_evaluacion: item.fecha_evaluacion,
      observaciones: item.observaciones || '',
    }
  } else if (tipo === 'tratamientos') {
    editForm.value = {
      riesgo: item.riesgo,
      estrategia: item.estrategia,
      control_aplicado: item.control_aplicado,
      fecha_inicio: item.fecha_inicio,
      observaciones: item.observaciones || '',
    }
  }
  showEditModal.value = true
}

async function guardarEdicion() {
  const cfg = BAJA_CONFIG[editTipo.value]
  if (!cfg || !editId.value) return
  guardandoEdicion.value = true
  errorEdicion.value = ''
  try {
    const payload = { ...editForm.value }
    if (editTipo.value === 'riesgos' && !payload.vulnerabilidad) {
      payload.vulnerabilidad = null
    }
    await api.patch(`/${cfg.endpoint}/${editId.value}/`, payload)
    cerrarEditar()
    await load()
  } catch (e) {
    const d = e.response?.data
    errorEdicion.value = d?.detail
      || Object.values(d || {}).flat().find(v => typeof v === 'string')
      || 'No se pudo guardar los cambios.'
  } finally {
    guardandoEdicion.value = false
  }
}

async function eliminarRegistro(tipo, item) {
  const cfg = BAJA_CONFIG[tipo]
  if (!cfg) return
  const nombre = item.codigo || item.riesgo_codigo || item.nombre || 'registro'
  if (!confirm(`¿Eliminar lógicamente ${cfg.etiqueta} "${nombre}"?`)) return
  eliminandoId.value = item.id
  try {
    await api.patch(`/${cfg.endpoint}/${item.id}/`, { [cfg.campo]: cfg.valor })
    await load()
  } catch (e) {
    alert(e.response?.data?.detail || 'No se pudo eliminar el registro.')
  } finally {
    eliminandoId.value = null
  }
}

function estaEliminando(id) {
  return eliminandoId.value === id
}

async function exportarExcel() {
  exportandoExcel.value = true
  errorExport.value = ''
  try {
    const { data, headers } = await api.get('/riesgos/exportar-excel/', { responseType: 'blob' })
    const disposition = headers['content-disposition'] || ''
    const match = disposition.match(/filename="?([^"]+)"?/)
    const nombre = match?.[1] || 'helpmed_gestion-riesgos.xlsx'
    const url = window.URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = nombre
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    if (e.response?.data instanceof Blob) {
      try {
        const texto = await e.response.data.text()
        const json = JSON.parse(texto)
        errorExport.value = json.detail || 'No se pudo exportar el archivo.'
      } catch {
        errorExport.value = 'No se pudo exportar el archivo.'
      }
    } else {
      errorExport.value = e.response?.data?.detail || 'No se pudo exportar el archivo.'
    }
  } finally {
    exportandoExcel.value = false
  }
}

onMounted(async () => {
  await load()
  await actualizarCodigoActivo()
  await actualizarCodigoAmenaza()
  await actualizarCodigoVuln()
  await actualizarCodigoRiesgo()
})

watch(() => formActivo.value.clasificacion, () => {
  actualizarCodigoActivo()
})

watch(tab, (t) => {
  if (t === 'activos') actualizarCodigoActivo()
  if (t === 'amenazas') actualizarCodigoAmenaza()
  if (t === 'vulnerabilidades') actualizarCodigoVuln()
  if (t === 'riesgos') actualizarCodigoRiesgo()
})
</script>

<template>
  <div>
    <PageHeader
      title="Gestión de Riesgos ISO/IEC 27005"
      subtitle="Activos · Amenazas · Vulnerabilidades · Evaluación · Tratamiento"
    >
      <template #actions>
        <button
          class="btn btn-sm btn-outline-success"
          :disabled="loading || exportandoExcel"
          title="Descarga un Excel con las 7 pestañas del módulo"
          @click="exportarExcel"
        >
          <span v-if="exportandoExcel" class="spinner-border spinner-border-sm me-1"></span>
          <i v-else class="bi bi-file-earmark-excel me-1"></i>
          Exportar Excel
        </button>
      </template>
    </PageHeader>

    <div v-if="errorExport" class="alert alert-danger py-2 small">{{ errorExport }}</div>

    <div v-if="errorCarga" class="alert alert-warning py-2 small d-flex align-items-center justify-content-between flex-wrap gap-2">
      <span>{{ errorCarga }}</span>
      <button class="btn btn-sm btn-outline-dark" :disabled="loading" @click="load">Reintentar</button>
    </div>

    <ul class="nav nav-pills mb-4 flex-wrap gap-1">
      <li v-for="t in ['activos','amenazas','vulnerabilidades','riesgos','evaluacion','matriz','tratamiento']" :key="t">
        <button class="nav-link text-capitalize" :class="{ active: tab === t }" @click="tab = t">{{ t === 'evaluacion' ? 'Evaluación' : t }}</button>
      </li>
    </ul>

    <div v-if="loading" class="text-center py-5"><div class="spinner-border text-primary"></div></div>

    <!-- ACTIVOS -->
    <template v-else-if="tab === 'activos'">
      <div class="card mb-3"><div class="card-body">
        <div v-if="errorActivo" class="alert alert-danger py-2 small mb-2">{{ errorActivo }}</div>
        <div class="row g-2 align-items-end">
        <div class="col-md-2">
          <label class="small text-muted mb-1">Código</label>
          <input
            :value="codigoActivoPreview"
            class="form-control form-control-sm bg-light"
            readonly
            placeholder="Auto"
          />
        </div>
        <div class="col-md-3">
          <label class="small text-muted mb-1">Nombre</label>
          <input v-model="formActivo.nombre" class="form-control form-control-sm" placeholder="Nombre del activo" />
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Clasificación</label>
          <select v-model="formActivo.clasificacion" class="form-select form-select-sm">
            <option v-for="c in CLASIFICACIONES_ACTIVO" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Criticidad</label>
          <select v-model="formActivo.criticidad" class="form-select form-select-sm">
            <option v-for="c in ['baja','media','alta','critica']" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <button
            class="btn btn-sm btn-primary w-100"
            :disabled="!formActivo.nombre.trim() || cargandoCodigoActivo || guardandoActivo"
            @click="crearActivo"
          >
            <span v-if="guardandoActivo" class="spinner-border spinner-border-sm"></span>
            <span v-else>Agregar</span>
          </button>
        </div>
        </div>
      </div></div>
      <div class="card"><div class="table-responsive"><table class="table table-hover mb-0">
        <thead class="table-light"><tr><th>Código</th><th>Nombre</th><th>Clasificación</th><th>Criticidad</th><th class="text-end">Acciones</th></tr></thead>
        <tbody>
          <tr v-if="!activos.length">
            <td colspan="5" class="text-center text-muted py-4 small">
              No hay activos en pantalla.
              <span v-if="!errorCarga"> Si acaba de abrir la página, espere un momento o pulse <button class="btn btn-link btn-sm p-0 align-baseline" @click="load">recargar</button>.</span>
            </td>
          </tr>
          <tr v-for="a in activos" :key="a.id">
            <td>{{ a.codigo }}</td><td>{{ a.nombre }}</td><td>{{ a.clasificacion }}</td><td>{{ a.criticidad }}</td>
            <td class="text-end text-nowrap">
              <button class="btn btn-sm btn-outline-primary" title="Editar" @click="abrirEditar('activos', a)"><i class="bi bi-pencil"></i></button>
              <button class="btn btn-sm btn-outline-danger ms-1" title="Eliminar" :disabled="estaEliminando(a.id)" @click="eliminarRegistro('activos', a)">
                <span v-if="estaEliminando(a.id)" class="spinner-border spinner-border-sm"></span>
                <i v-else class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table></div></div>
    </template>

    <!-- AMENAZAS -->
    <template v-else-if="tab === 'amenazas'">
      <div class="card mb-3"><div class="card-body">
        <div v-if="errorAmenaza" class="alert alert-danger py-2 small mb-2">{{ errorAmenaza }}</div>
        <div class="row g-2 align-items-end">
        <div class="col-md-2">
          <label class="small text-muted mb-1">Código</label>
          <input
            :value="codigoAmenazaPreview"
            class="form-control form-control-sm bg-light"
            readonly
            placeholder="Auto"
          />
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Tipo</label>
          <select v-model="formAmenaza.tipo" class="form-select form-select-sm">
            <option v-for="t in TIPOS_AMENAZA" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="small text-muted mb-1">Nombre</label>
          <input v-model="formAmenaza.nombre" class="form-control form-control-sm" placeholder="Nombre de la amenaza" />
        </div>
        <div class="col-md-2">
          <button
            class="btn btn-sm btn-primary w-100"
            :disabled="!formAmenaza.nombre.trim() || guardandoAmenaza"
            @click="crearAmenaza"
          >
            <span v-if="guardandoAmenaza" class="spinner-border spinner-border-sm"></span>
            <span v-else>Agregar</span>
          </button>
        </div>
        </div>
      </div></div>
      <div class="card"><div class="table-responsive"><table class="table table-hover mb-0">
        <thead class="table-light"><tr><th>Código</th><th>Tipo</th><th>Nombre</th><th class="text-end">Acciones</th></tr></thead>
        <tbody>
          <tr v-for="a in amenazas" :key="a.id">
            <td>{{ a.codigo }}</td><td>{{ a.tipo }}</td><td>{{ a.nombre }}</td>
            <td class="text-end text-nowrap">
              <button class="btn btn-sm btn-outline-primary" title="Editar" @click="abrirEditar('amenazas', a)"><i class="bi bi-pencil"></i></button>
              <button class="btn btn-sm btn-outline-danger ms-1" title="Eliminar" :disabled="estaEliminando(a.id)" @click="eliminarRegistro('amenazas', a)">
                <span v-if="estaEliminando(a.id)" class="spinner-border spinner-border-sm"></span>
                <i v-else class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table></div></div>
    </template>

    <!-- VULNERABILIDADES -->
    <template v-else-if="tab === 'vulnerabilidades'">
      <div class="card mb-3"><div class="card-body">
        <div v-if="errorVuln" class="alert alert-danger py-2 small mb-2">{{ errorVuln }}</div>
        <div class="row g-2 align-items-end">
        <div class="col-md-2">
          <label class="small text-muted mb-1">Código</label>
          <input
            :value="codigoVulnPreview"
            class="form-control form-control-sm bg-light"
            readonly
            placeholder="Auto"
          />
        </div>
        <div class="col-md-3">
          <label class="small text-muted mb-1">Activo *</label>
          <select v-model="formVuln.activo" class="form-select form-select-sm">
            <option value="">— Seleccione —</option>
            <option v-for="a in activos" :key="a.id" :value="a.id">{{ a.codigo }} — {{ a.nombre }}</option>
          </select>
        </div>
        <div class="col-md-3">
          <label class="small text-muted mb-1">Vulnerabilidad *</label>
          <input v-model="formVuln.nombre" class="form-control form-control-sm" placeholder="Nombre de la vulnerabilidad" />
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Severidad</label>
          <select v-model="formVuln.severidad" class="form-select form-select-sm">
            <option v-for="s in ['baja','media','alta','critica']" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <button
            class="btn btn-sm btn-primary w-100"
            :disabled="!formVuln.activo || !formVuln.nombre.trim() || guardandoVuln"
            @click="crearVuln"
          >
            <span v-if="guardandoVuln" class="spinner-border spinner-border-sm"></span>
            <span v-else>Agregar</span>
          </button>
        </div>
        </div>
      </div></div>
      <div class="card"><div class="table-responsive"><table class="table table-hover mb-0">
        <thead class="table-light"><tr><th>Código</th><th>Activo</th><th>Vulnerabilidad</th><th>Severidad</th><th>Estado</th><th class="text-end">Acciones</th></tr></thead>
        <tbody>
          <tr v-for="v in vulnerabilidades" :key="v.id">
            <td>{{ v.codigo }}</td><td>{{ v.activo_nombre }}</td><td>{{ v.nombre }}</td><td>{{ v.severidad }}</td><td>{{ v.estado }}</td>
            <td class="text-end text-nowrap">
              <button class="btn btn-sm btn-outline-primary" title="Editar" @click="abrirEditar('vulnerabilidades', v)"><i class="bi bi-pencil"></i></button>
              <button class="btn btn-sm btn-outline-danger ms-1" title="Eliminar" :disabled="estaEliminando(v.id)" @click="eliminarRegistro('vulnerabilidades', v)">
                <span v-if="estaEliminando(v.id)" class="spinner-border spinner-border-sm"></span>
                <i v-else class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table></div></div>
    </template>

    <!-- RIESGOS -->
    <template v-else-if="tab === 'riesgos'">
      <div class="card mb-3"><div class="card-body">
        <div v-if="errorRiesgo" class="alert alert-danger py-2 small mb-2">{{ errorRiesgo }}</div>
        <div class="row g-2 align-items-end">
        <div class="col-md-2">
          <label class="small text-muted mb-1">Código</label>
          <input
            :value="codigoRiesgoPreview"
            class="form-control form-control-sm bg-light"
            readonly
            placeholder="Auto"
          />
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Activo *</label>
          <select v-model="formRiesgo.activo" class="form-select form-select-sm" @change="formRiesgo.vulnerabilidad = ''">
            <option value="">— Seleccione —</option>
            <option v-for="a in activos" :key="a.id" :value="a.id">{{ a.codigo }} — {{ a.nombre }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Amenaza *</label>
          <select v-model="formRiesgo.amenaza" class="form-select form-select-sm">
            <option value="">— Seleccione —</option>
            <option v-for="a in amenazas" :key="a.id" :value="a.id">{{ a.codigo }} — {{ a.nombre }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Vulnerabilidad</label>
          <select v-model="formRiesgo.vulnerabilidad" class="form-select form-select-sm" :disabled="!formRiesgo.activo">
            <option value="">— Opcional —</option>
            <option v-for="v in vulnsPorActivo" :key="v.id" :value="v.id">{{ v.codigo }} — {{ v.nombre }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Descripción</label>
          <input v-model="formRiesgo.descripcion" class="form-control form-control-sm" placeholder="Opcional" />
        </div>
        <div class="col-md-2">
          <button
            class="btn btn-sm btn-primary w-100"
            :disabled="!formRiesgo.activo || !formRiesgo.amenaza || guardandoRiesgo"
            @click="crearRiesgo"
          >
            <span v-if="guardandoRiesgo" class="spinner-border spinner-border-sm"></span>
            <span v-else>Agregar</span>
          </button>
        </div>
        </div>
      </div></div>
      <div class="card"><div class="table-responsive"><table class="table table-hover mb-0">
        <thead class="table-light"><tr><th>Código</th><th>Activo</th><th>Amenaza</th><th>Descripción</th><th class="text-end">Acciones</th></tr></thead>
        <tbody>
          <tr v-for="r in riesgos" :key="r.id">
            <td>{{ r.codigo }}</td><td>{{ r.activo_nombre }}</td><td>{{ r.amenaza_nombre }}</td><td>{{ r.descripcion }}</td>
            <td class="text-end text-nowrap">
              <button class="btn btn-sm btn-outline-primary" title="Editar" @click="abrirEditar('riesgos', r)"><i class="bi bi-pencil"></i></button>
              <button class="btn btn-sm btn-outline-danger ms-1" title="Eliminar" :disabled="estaEliminando(r.id)" @click="eliminarRegistro('riesgos', r)">
                <span v-if="estaEliminando(r.id)" class="spinner-border spinner-border-sm"></span>
                <i v-else class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table></div></div>
    </template>

    <!-- EVALUACIÓN -->
    <template v-else-if="tab === 'evaluacion'">
      <div class="alert alert-secondary small">
        <strong>Fórmula:</strong> VALOR = PROBABILIDAD × IMPACTO ·
        Bajo (1-5) · Medio (6-10) · Alto (11-15) · Crítico (16-25).
        Si el tipo es <strong>inherente</strong>, el riesgo aparecerá en la pestaña <strong>Matriz</strong>.
      </div>
      <div class="card mb-3"><div class="card-body">
        <div class="row g-2 align-items-end">
        <div class="col-md-3">
          <label class="small text-muted mb-1">Riesgo *</label>
          <select v-model="formEval.riesgo" class="form-select form-select-sm">
            <option value="">— Seleccione —</option>
            <option v-for="r in riesgos" :key="r.id" :value="r.id">{{ r.codigo }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Tipo</label>
          <select v-model="formEval.tipo" class="form-select form-select-sm">
            <option value="inherente">Inherente (va a Matriz)</option>
            <option value="residual">Residual</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Probabilidad</label>
          <select v-model="formEval.probabilidad" class="form-select form-select-sm">
            <option v-for="n in 5" :key="n" :value="n">P{{ n }} — {{ PROB_LABELS[n - 1] }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="small text-muted mb-1">Impacto</label>
          <select v-model="formEval.impacto" class="form-select form-select-sm">
            <option v-for="n in 5" :key="n" :value="n">I{{ n }} — {{ IMP_LABELS[n - 1] }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <button class="btn btn-sm btn-primary w-100" @click="crearEval">Evaluar</button>
        </div>
        </div>
        <div class="mt-2 small">
          Vista previa:
          <strong>{{ evalPreview.celda }}</strong> →
          valor <strong>{{ evalPreview.valor }}</strong>
          (<span :class="nivelClass(evalPreview.nivel)" class="text-capitalize">{{ evalPreview.nivel }}</span>)
        </div>
      </div></div>
      <div class="card"><div class="table-responsive"><table class="table table-hover mb-0">
        <thead class="table-light"><tr><th>Riesgo</th><th>Tipo</th><th>Prob.</th><th>Imp.</th><th>Valor</th><th>Nivel</th><th class="text-end">Acciones</th></tr></thead>
        <tbody>
          <tr v-for="e in evaluaciones" :key="e.id">
            <td>{{ e.riesgo_codigo }}</td><td>{{ e.tipo }}</td><td>{{ e.probabilidad }}</td><td>{{ e.impacto }}</td>
            <td class="fw-bold">{{ e.valor_riesgo }}</td>
            <td :class="nivelClass(e.nivel)">{{ e.nivel }}</td>
            <td class="text-end text-nowrap">
              <button class="btn btn-sm btn-outline-primary" title="Editar" @click="abrirEditar('evaluaciones', e)"><i class="bi bi-pencil"></i></button>
              <button class="btn btn-sm btn-outline-danger ms-1" title="Eliminar" :disabled="estaEliminando(e.id)" @click="eliminarRegistro('evaluaciones', e)">
                <span v-if="estaEliminando(e.id)" class="spinner-border spinner-border-sm"></span>
                <i v-else class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table></div></div>
    </template>

    <!-- MATRIZ / MAPA DE CALOR -->
    <template v-else-if="tab === 'matriz'">
      <div class="alert alert-info small mb-3">
        <strong>¿Cómo leerla?</strong>
        Cada celda es <strong>Impacto × Probabilidad</strong>.
        El número grande es el <strong>valor del riesgo</strong> (ej. 4×4 = 16).
        Los badges muestran qué <strong>RSG-000x</strong> está en esa celda.
        Solo aparecen evaluaciones de tipo <strong>inherente</strong>.
      </div>

      <div class="row g-3 mb-3">
        <div class="col-auto" v-for="n in [
          { k: 'bajo', l: 'Bajo (1-5)', c: '#bbf7d0' },
          { k: 'medio', l: 'Medio (6-10)', c: '#fde68a' },
          { k: 'alto', l: 'Alto (11-15)', c: '#fdba74' },
          { k: 'critico', l: 'Crítico (16-25)', c: '#fca5a5' },
        ]" :key="n.k">
          <span class="matriz-leyenda-item">
            <span class="matriz-leyenda-color" :style="{ background: n.c }"></span>
            {{ n.l }}
          </span>
        </div>
      </div>

      <div class="card mb-3">
        <div class="card-header fw-semibold">Matriz de Riesgos — Mapa de Calor</div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-bordered text-center mb-0 matriz-tabla">
              <thead>
                <tr>
                  <th class="matriz-esquina">
                    <div class="small text-muted">Impacto ↓</div>
                    <div class="small text-muted">Probabilidad →</div>
                  </th>
                  <th v-for="p in 5" :key="p" class="matriz-header-col">
                    <div class="fw-semibold">P{{ p }}</div>
                    <div class="small text-muted">{{ PROB_LABELS[p - 1] }}</div>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="imp in [5, 4, 3, 2, 1]" :key="imp">
                  <th class="matriz-header-row">
                    <div class="fw-semibold">I{{ imp }}</div>
                    <div class="small text-muted">{{ IMP_LABELS[imp - 1] }}</div>
                  </th>
                  <td
                    v-for="prob in 5"
                    :key="prob"
                    class="matriz-celda"
                    :style="{ background: celdaBg(imp, prob, matrizDetalle[imp - 1][prob - 1].riesgos.length > 0) }"
                    :title="celdaTooltip(imp, prob)"
                  >
                    <div class="matriz-valor">{{ imp * prob }}</div>
                    <div v-if="matrizDetalle[imp - 1][prob - 1].riesgos.length" class="matriz-badges">
                      <span
                        v-for="r in matrizDetalle[imp - 1][prob - 1].riesgos"
                        :key="r.codigo"
                        class="matriz-badge"
                        :class="nivelBadgeClass(r.nivel)"
                      >{{ r.codigo }}</span>
                    </div>
                    <div v-else class="matriz-sin-riesgo small text-muted">—</div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header fw-semibold">Ubicación de cada riesgo en la matriz</div>
        <div class="card-body p-0">
          <div v-if="!evaluacionesInherentes.length" class="p-4 text-muted text-center small">
            Aún no hay evaluaciones inherentes. Regístralas en la pestaña <strong>Evaluación</strong>.
          </div>
          <div v-else class="table-responsive">
            <table class="table table-hover mb-0">
              <thead class="table-light">
                <tr>
                  <th>Riesgo</th>
                  <th>Probabilidad</th>
                  <th>Impacto</th>
                  <th>Celda</th>
                  <th>Valor</th>
                  <th>Nivel</th>
                  <th class="text-end">Acciones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="e in evaluacionesInherentes" :key="e.id">
                  <td class="fw-semibold">{{ e.riesgo_codigo }}</td>
                  <td>P{{ e.probabilidad }} — {{ PROB_LABELS[e.probabilidad - 1] }}</td>
                  <td>I{{ e.impacto }} — {{ IMP_LABELS[e.impacto - 1] }}</td>
                  <td><span class="badge bg-secondary">I{{ e.impacto }} × P{{ e.probabilidad }}</span></td>
                  <td class="fw-bold">{{ e.valor_riesgo }}</td>
                  <td :class="nivelClass(e.nivel)" class="text-capitalize">{{ e.nivel }}</td>
                  <td class="text-end text-nowrap">
                    <button class="btn btn-sm btn-outline-primary" title="Editar" @click="abrirEditar('evaluaciones', e)"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-sm btn-outline-danger ms-1" title="Eliminar" :disabled="estaEliminando(e.id)" @click="eliminarRegistro('evaluaciones', e)">
                      <span v-if="estaEliminando(e.id)" class="spinner-border spinner-border-sm"></span>
                      <i v-else class="bi bi-trash"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <!-- TRATAMIENTO -->
    <template v-else-if="tab === 'tratamiento'">
      <div class="alert alert-secondary small mb-3">
        El <strong>riesgo residual</strong> se obtiene de la evaluación tipo
        <strong>residual</strong> del mismo riesgo en la pestaña <strong>Evaluación</strong>.
        Si aparece «—», registra primero esa evaluación (después de aplicar el control).
      </div>
      <div class="card mb-3"><div class="card-body row g-2">
        <div class="col-md-2"><select v-model="formTrat.riesgo" class="form-select form-select-sm"><option value="">Riesgo</option><option v-for="r in riesgos" :key="r.id" :value="r.id">{{ r.codigo }}</option></select></div>
        <div class="col-md-2"><select v-model="formTrat.estrategia" class="form-select form-select-sm"><option v-for="s in ['mitigar','transferir','evitar','aceptar']" :key="s" :value="s">{{ s }}</option></select></div>
        <div class="col-md-4"><input v-model="formTrat.control_aplicado" class="form-control form-control-sm" placeholder="Control aplicado" /></div>
        <div class="col-md-2"><button class="btn btn-sm btn-primary w-100" @click="crearTrat">Registrar</button></div>
      </div></div>
      <div class="card"><div class="table-responsive"><table class="table table-hover mb-0">
        <thead class="table-light"><tr><th>Riesgo</th><th>Estrategia</th><th>Control</th><th>Riesgo residual</th><th class="text-end">Acciones</th></tr></thead>
        <tbody>
          <tr v-for="t in tratamientos" :key="t.id">
            <td>{{ t.riesgo_codigo }}</td>
            <td>{{ t.estrategia }}</td>
            <td>{{ t.control_aplicado }}</td>
            <td>
              <template v-if="t.riesgo_residual_valor != null">
                <span class="fw-bold">{{ t.riesgo_residual_valor }}</span>
                <span v-if="t.riesgo_residual_nivel" :class="nivelClass(t.riesgo_residual_nivel)" class="text-capitalize ms-1">
                  ({{ t.riesgo_residual_nivel }})
                </span>
              </template>
              <span v-else class="text-muted">—</span>
            </td>
            <td class="text-end text-nowrap">
              <button class="btn btn-sm btn-outline-primary" title="Editar" @click="abrirEditar('tratamientos', t)"><i class="bi bi-pencil"></i></button>
              <button class="btn btn-sm btn-outline-danger ms-1" title="Eliminar" :disabled="estaEliminando(t.id)" @click="eliminarRegistro('tratamientos', t)">
                <span v-if="estaEliminando(t.id)" class="spinner-border spinner-border-sm"></span>
                <i v-else class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table></div></div>
    </template>

    <!-- Modal editar -->
    <div v-if="showEditModal" class="modal d-block" tabindex="-1" style="background:rgba(0,0,0,.45)">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              {{ TITULO_EDICION[editTipo] || 'Editar' }}
              <span v-if="editCodigo" class="text-muted small ms-2">{{ editCodigo }}</span>
            </h5>
            <button type="button" class="btn-close" @click="cerrarEditar"></button>
          </div>
          <div class="modal-body">
            <div v-if="errorEdicion" class="alert alert-danger py-2 small">{{ errorEdicion }}</div>

            <template v-if="editTipo === 'activos'">
              <div class="row g-2">
                <div class="col-md-6"><label class="small text-muted">Nombre</label><input v-model="editForm.nombre" class="form-control form-control-sm" /></div>
                <div class="col-md-3"><label class="small text-muted">Clasificación</label><select v-model="editForm.clasificacion" class="form-select form-select-sm"><option v-for="c in CLASIFICACIONES_ACTIVO" :key="c.value" :value="c.value">{{ c.label }}</option></select></div>
                <div class="col-md-3"><label class="small text-muted">Criticidad</label><select v-model="editForm.criticidad" class="form-select form-select-sm"><option v-for="c in ['baja','media','alta','critica']" :key="c" :value="c">{{ c }}</option></select></div>
                <div class="col-12"><label class="small text-muted">Descripción</label><textarea v-model="editForm.descripcion" class="form-control form-control-sm" rows="2"></textarea></div>
              </div>
            </template>

            <template v-else-if="editTipo === 'amenazas'">
              <div class="row g-2">
                <div class="col-md-4"><label class="small text-muted">Tipo</label><select v-model="editForm.tipo" class="form-select form-select-sm"><option v-for="t in TIPOS_AMENAZA" :key="t.value" :value="t.value">{{ t.label }}</option></select></div>
                <div class="col-md-8"><label class="small text-muted">Nombre</label><input v-model="editForm.nombre" class="form-control form-control-sm" /></div>
                <div class="col-12"><label class="small text-muted">Descripción</label><textarea v-model="editForm.descripcion" class="form-control form-control-sm" rows="2"></textarea></div>
              </div>
            </template>

            <template v-else-if="editTipo === 'vulnerabilidades'">
              <div class="row g-2">
                <div class="col-md-6"><label class="small text-muted">Activo</label><select v-model="editForm.activo" class="form-select form-select-sm"><option v-for="a in activos" :key="a.id" :value="a.id">{{ a.codigo }} — {{ a.nombre }}</option></select></div>
                <div class="col-md-3"><label class="small text-muted">Severidad</label><select v-model="editForm.severidad" class="form-select form-select-sm"><option v-for="s in ['baja','media','alta','critica']" :key="s" :value="s">{{ s }}</option></select></div>
                <div class="col-md-3"><label class="small text-muted">Estado</label><select v-model="editForm.estado" class="form-select form-select-sm"><option v-for="s in ['abierta','en_tratamiento','mitigada','cerrada']" :key="s" :value="s">{{ s }}</option></select></div>
                <div class="col-12"><label class="small text-muted">Vulnerabilidad</label><input v-model="editForm.nombre" class="form-control form-control-sm" /></div>
                <div class="col-12"><label class="small text-muted">Descripción</label><textarea v-model="editForm.descripcion" class="form-control form-control-sm" rows="2"></textarea></div>
              </div>
            </template>

            <template v-else-if="editTipo === 'riesgos'">
              <div class="row g-2">
                <div class="col-md-4"><label class="small text-muted">Activo</label><select v-model="editForm.activo" class="form-select form-select-sm"><option v-for="a in activos" :key="a.id" :value="a.id">{{ a.codigo }} — {{ a.nombre }}</option></select></div>
                <div class="col-md-4"><label class="small text-muted">Amenaza</label><select v-model="editForm.amenaza" class="form-select form-select-sm"><option v-for="a in amenazas" :key="a.id" :value="a.id">{{ a.codigo }} — {{ a.nombre }}</option></select></div>
                <div class="col-md-4"><label class="small text-muted">Vulnerabilidad</label><select v-model="editForm.vulnerabilidad" class="form-select form-select-sm"><option value="">— Ninguna —</option><option v-for="v in vulnerabilidades.filter(v => v.activo === editForm.activo)" :key="v.id" :value="v.id">{{ v.codigo }} — {{ v.nombre }}</option></select></div>
                <div class="col-12"><label class="small text-muted">Descripción</label><textarea v-model="editForm.descripcion" class="form-control form-control-sm" rows="2"></textarea></div>
              </div>
            </template>

            <template v-else-if="editTipo === 'evaluaciones'">
              <div class="row g-2">
                <div class="col-md-4"><label class="small text-muted">Riesgo</label><select v-model="editForm.riesgo" class="form-select form-select-sm"><option v-for="r in riesgos" :key="r.id" :value="r.id">{{ r.codigo }}</option></select></div>
                <div class="col-md-3"><label class="small text-muted">Tipo</label><select v-model="editForm.tipo" class="form-select form-select-sm"><option value="inherente">Inherente</option><option value="residual">Residual</option></select></div>
                <div class="col-md-2"><label class="small text-muted">Probabilidad</label><select v-model="editForm.probabilidad" class="form-select form-select-sm"><option v-for="n in 5" :key="n" :value="n">P{{ n }}</option></select></div>
                <div class="col-md-2"><label class="small text-muted">Impacto</label><select v-model="editForm.impacto" class="form-select form-select-sm"><option v-for="n in 5" :key="n" :value="n">I{{ n }}</option></select></div>
                <div class="col-md-3"><label class="small text-muted">Fecha</label><input v-model="editForm.fecha_evaluacion" type="date" class="form-control form-control-sm" /></div>
                <div class="col-12"><label class="small text-muted">Observaciones</label><textarea v-model="editForm.observaciones" class="form-control form-control-sm" rows="2"></textarea></div>
              </div>
            </template>

            <template v-else-if="editTipo === 'tratamientos'">
              <div class="row g-2">
                <div class="col-md-4"><label class="small text-muted">Riesgo</label><select v-model="editForm.riesgo" class="form-select form-select-sm"><option v-for="r in riesgos" :key="r.id" :value="r.id">{{ r.codigo }}</option></select></div>
                <div class="col-md-3"><label class="small text-muted">Estrategia</label><select v-model="editForm.estrategia" class="form-select form-select-sm"><option v-for="s in ['mitigar','transferir','evitar','aceptar']" :key="s" :value="s">{{ s }}</option></select></div>
                <div class="col-md-3"><label class="small text-muted">Fecha inicio</label><input v-model="editForm.fecha_inicio" type="date" class="form-control form-control-sm" /></div>
                <div class="col-12"><label class="small text-muted">Control aplicado</label><textarea v-model="editForm.control_aplicado" class="form-control form-control-sm" rows="2"></textarea></div>
                <div class="col-12"><label class="small text-muted">Observaciones</label><textarea v-model="editForm.observaciones" class="form-control form-control-sm" rows="2"></textarea></div>
              </div>
            </template>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="cerrarEditar">Cancelar</button>
            <button class="btn btn-primary" :disabled="guardandoEdicion" @click="guardarEdicion">
              <span v-if="guardandoEdicion" class="spinner-border spinner-border-sm me-1"></span>
              Guardar
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
