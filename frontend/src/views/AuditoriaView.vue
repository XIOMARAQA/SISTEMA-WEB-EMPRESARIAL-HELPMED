<script setup>
import { onMounted, ref, watch } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'

const registros = ref([])
const auditorias = ref([])
const tab = ref('registros')
const loading = ref(true)
const guardando = ref(false)
const errorForm = ref('')
const codigoPreview = ref('')
const showModal = ref(false)
const editando = ref(null)

const TIPOS = [
  { value: 'interna', label: 'Interna' },
  { value: 'externa', label: 'Externa' },
  { value: 'seguridad', label: 'Seguridad de la información' },
  { value: 'iso27001', label: 'ISO 27001' },
]

const ESTADOS = [
  { value: 'programada', label: 'Programada' },
  { value: 'en_curso', label: 'En curso' },
  { value: 'finalizada', label: 'Finalizada' },
]

const form = ref({
  titulo: '',
  tipo: 'interna',
  fecha_inicio: new Date().toISOString().slice(0, 10),
  fecha_fin: '',
  alcance: '',
  hallazgos: '',
  estado: 'programada',
})

const estadoBadge = {
  programada: 'bg-warning text-dark',
  en_curso: 'bg-primary',
  finalizada: 'bg-success',
}

const tipoLabel = Object.fromEntries(TIPOS.map(t => [t.value, t.label]))
const estadoLabel = Object.fromEntries(ESTADOS.map(e => [e.value, e.label]))

async function load() {
  loading.value = true
  try {
    const [regRes, audRes] = await Promise.all([
      api.get('/registros-auditoria/'),
      api.get('/auditorias/'),
    ])
    registros.value = regRes.data.results || regRes.data
    auditorias.value = audRes.data.results || audRes.data
  } finally {
    loading.value = false
  }
}

async function actualizarCodigo() {
  try {
    const { data } = await api.get('/auditorias/siguiente-codigo/')
    codigoPreview.value = data.codigo
  } catch {
    codigoPreview.value = ''
  }
}

function resetForm() {
  form.value = {
    titulo: '',
    tipo: 'interna',
    fecha_inicio: new Date().toISOString().slice(0, 10),
    fecha_fin: '',
    alcance: '',
    hallazgos: '',
    estado: 'programada',
  }
  editando.value = null
  errorForm.value = ''
}

function abrirNueva() {
  resetForm()
  showModal.value = true
  actualizarCodigo()
}

function abrirEditar(a) {
  editando.value = a.id
  form.value = {
    titulo: a.titulo,
    tipo: a.tipo,
    fecha_inicio: a.fecha_inicio,
    fecha_fin: a.fecha_fin || '',
    alcance: a.alcance,
    hallazgos: a.hallazgos || '',
    estado: a.estado,
  }
  codigoPreview.value = a.codigo
  errorForm.value = ''
  showModal.value = true
}

function cerrarModal() {
  showModal.value = false
  resetForm()
}

async function guardar() {
  if (!form.value.titulo.trim()) {
    errorForm.value = 'Indique el título de la auditoría.'
    return
  }
  if (!form.value.fecha_inicio) {
    errorForm.value = 'Indique la fecha de inicio.'
    return
  }
  guardando.value = true
  errorForm.value = ''
  try {
    const payload = {
      titulo: form.value.titulo.trim(),
      tipo: form.value.tipo,
      fecha_inicio: form.value.fecha_inicio,
      estado: form.value.estado,
      alcance: form.value.alcance?.trim() || form.value.titulo.trim(),
      hallazgos: form.value.hallazgos?.trim() || '',
    }
    if (form.value.fecha_fin) payload.fecha_fin = form.value.fecha_fin

    if (editando.value) {
      await api.patch(`/auditorias/${editando.value}/`, payload)
    } else {
      await api.post('/auditorias/', payload)
    }
    cerrarModal()
    await load()
    if (tab.value === 'auditorias') await actualizarCodigo()
  } catch (e) {
    const d = e.response?.data
    errorForm.value = d?.detail
      || d?.titulo?.[0]
      || Object.values(d || {}).flat().find(v => typeof v === 'string')
      || 'No se pudo guardar la auditoría.'
  } finally {
    guardando.value = false
  }
}

onMounted(async () => {
  await load()
  await actualizarCodigo()
})

watch(tab, (t) => {
  if (t === 'auditorias') actualizarCodigo()
})
</script>

<template>
  <div>
    <PageHeader title="Auditoría" subtitle="Registro de acciones y auditorías de seguridad de la información">
      <template #actions>
        <button v-if="tab === 'auditorias'" class="btn btn-primary btn-sm" @click="abrirNueva">
          <i class="bi bi-plus-lg me-1"></i>Nueva auditoría
        </button>
      </template>
    </PageHeader>

    <ul class="nav nav-tabs mb-4">
      <li class="nav-item">
        <button class="nav-link" :class="{ active: tab === 'registros' }" @click="tab = 'registros'">
          Registro de acciones
        </button>
      </li>
      <li class="nav-item">
        <button class="nav-link" :class="{ active: tab === 'auditorias' }" @click="tab = 'auditorias'">
          Auditorías formales
        </button>
      </li>
    </ul>

    <div v-if="tab === 'registros'" class="alert alert-light border small mb-3">
      <i class="bi bi-info-circle me-1"></i>
      Registro <strong>automático</strong>: cada inicio de sesión y cada creación, actualización o eliminación
      en los módulos del sistema se guarda aquí. No requiere ingreso manual.
    </div>

    <div class="card">
      <div class="card-body p-0">
        <div v-if="loading" class="text-center py-4"><div class="spinner-border text-primary"></div></div>
        <div v-else-if="tab === 'registros'" class="table-responsive">
          <table class="table table-hover mb-0 table-sm">
            <thead class="table-light">
              <tr>
                <th>Fecha</th>
                <th>Usuario</th>
                <th>Acción</th>
                <th>Módulo</th>
                <th>Descripción</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in registros" :key="r.id">
                <td>{{ new Date(r.creado_en).toLocaleString('es-PE') }}</td>
                <td>{{ r.usuario_nombre || '—' }}</td>
                <td>{{ r.accion }}</td>
                <td>{{ r.modulo }}</td>
                <td>{{ r.descripcion || '—' }}</td>
              </tr>
              <tr v-if="!registros.length">
                <td colspan="5" class="text-center text-muted py-4">
                  Aún no hay registros. Inicie sesión o realice cambios en el sistema para generarlos automáticamente.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="table-responsive">
          <table class="table table-hover mb-0">
            <thead class="table-light">
              <tr>
                <th>Código</th>
                <th>Título</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Inicio</th>
                <th>Fin</th>
                <th>Auditor</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in auditorias" :key="a.id">
                <td class="fw-semibold">{{ a.codigo }}</td>
                <td>{{ a.titulo }}</td>
                <td>{{ tipoLabel[a.tipo] || a.tipo }}</td>
                <td><span class="badge" :class="estadoBadge[a.estado] || 'bg-secondary'">{{ estadoLabel[a.estado] || a.estado }}</span></td>
                <td>{{ a.fecha_inicio }}</td>
                <td>{{ a.fecha_fin || '—' }}</td>
                <td>{{ a.auditor_nombre }}</td>
                <td>
                  <button class="btn btn-sm btn-outline-primary" title="Editar" @click="abrirEditar(a)">
                    <i class="bi bi-pencil"></i>
                  </button>
                </td>
              </tr>
              <tr v-if="!auditorias.length">
                <td colspan="8" class="text-center text-muted py-4">
                  No hay auditorías registradas. Use <strong>Nueva auditoría</strong> para agregar una.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Modal nueva / editar auditoría -->
    <div
      v-if="showModal"
      class="modal d-block"
      tabindex="-1"
      style="background: rgba(0,0,0,.5); z-index: 1050"
      @click.self="cerrarModal"
    >
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title fw-semibold">
              {{ editando ? 'Editar auditoría' : 'Nueva auditoría formal' }}
            </h5>
            <button type="button" class="btn-close" @click="cerrarModal"></button>
          </div>
          <div class="modal-body">
            <div v-if="errorForm" class="alert alert-danger py-2 small">{{ errorForm }}</div>
            <div class="row g-3">
              <div class="col-md-3">
                <label class="form-label small">Código</label>
                <input :value="codigoPreview" class="form-control bg-light" readonly />
              </div>
              <div class="col-md-9">
                <label class="form-label small">Título *</label>
                <input v-model="form.titulo" class="form-control" placeholder="Ej. Auditoría ISO 27001 — Q2 2026" />
              </div>
              <div class="col-md-4">
                <label class="form-label small">Tipo</label>
                <select v-model="form.tipo" class="form-select">
                  <option v-for="t in TIPOS" :key="t.value" :value="t.value">{{ t.label }}</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label small">Estado</label>
                <select v-model="form.estado" class="form-select">
                  <option v-for="e in ESTADOS" :key="e.value" :value="e.value">{{ e.label }}</option>
                </select>
              </div>
              <div class="col-md-2">
                <label class="form-label small">Fecha inicio *</label>
                <input v-model="form.fecha_inicio" type="date" class="form-control" />
              </div>
              <div class="col-md-2">
                <label class="form-label small">Fecha fin</label>
                <input v-model="form.fecha_fin" type="date" class="form-control" />
              </div>
              <div class="col-12">
                <label class="form-label small">Alcance</label>
                <textarea v-model="form.alcance" class="form-control" rows="2" placeholder="Áreas, procesos o activos auditados"></textarea>
              </div>
              <div class="col-12">
                <label class="form-label small">Hallazgos</label>
                <textarea v-model="form.hallazgos" class="form-control" rows="3" placeholder="Observaciones, no conformidades, recomendaciones"></textarea>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="cerrarModal">Cancelar</button>
            <button type="button" class="btn btn-primary" :disabled="guardando" @click="guardar">
              <span v-if="guardando" class="spinner-border spinner-border-sm me-1"></span>
              {{ editando ? 'Guardar cambios' : 'Registrar auditoría' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
