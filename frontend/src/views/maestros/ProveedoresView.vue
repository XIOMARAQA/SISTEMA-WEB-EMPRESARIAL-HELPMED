<script setup>
import { onMounted, ref } from 'vue'
import api from '../../api/client'
import PageHeader from '../../components/PageHeader.vue'

const proveedores = ref([])
const loading = ref(true)
const showModal = ref(false)
const editId = ref(null)
const error = ref('')
const saving = ref(false)
const consultandoRuc = ref(false)
const rucError = ref('')
const sunatInfo = ref(null)

const form = ref({
  ruc: '',
  razon_social: '',
  direccion: '',
  telefono: '',
  email: '',
  contacto: '',
})

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/proveedores/')
    proveedores.value = data.results || data
  } finally {
    loading.value = false
  }
}

function abrirNuevo() {
  editId.value = null
  form.value = { ruc: '', razon_social: '', direccion: '', telefono: '', email: '', contacto: '' }
  sunatInfo.value = null
  rucError.value = ''
  error.value = ''
  showModal.value = true
}

function abrirEditar(p) {
  editId.value = p.id
  form.value = {
    ruc: p.ruc,
    razon_social: p.razon_social,
    direccion: p.direccion || '',
    telefono: p.telefono || '',
    email: p.email || '',
    contacto: p.contacto || '',
  }
  sunatInfo.value = null
  error.value = ''
  showModal.value = true
}

async function consultarRuc() {
  rucError.value = ''
  sunatInfo.value = null
  if (!/^\d{11}$/.test(form.value.ruc)) {
    rucError.value = 'Ingrese un RUC válido de 11 dígitos.'
    return
  }
  consultandoRuc.value = true
  try {
    const { data } = await api.get('/proveedores/consultar-ruc/', { params: { ruc: form.value.ruc } })
    form.value.razon_social = data.razon_social || form.value.razon_social
    form.value.direccion = data.direccion || form.value.direccion
    sunatInfo.value = data
    if (data.ya_registrado) {
      rucError.value = 'Este RUC ya está registrado.'
    }
  } catch (e) {
    rucError.value = e.response?.data?.detail || 'No se pudo consultar SUNAT.'
  } finally {
    consultandoRuc.value = false
  }
}

async function guardar() {
  error.value = ''
  if (!form.value.ruc.trim() || !form.value.razon_social.trim()) {
    error.value = 'RUC y razón social son obligatorios.'
    return
  }
  saving.value = true
  try {
    if (editId.value) {
      await api.patch(`/proveedores/${editId.value}/`, form.value)
    } else {
      await api.post('/proveedores/', form.value)
    }
    showModal.value = false
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.response?.data?.ruc?.[0] || 'No se pudo guardar.'
  } finally {
    saving.value = false
  }
}

async function desactivar(p) {
  if (!confirm(`¿Desactivar "${p.razon_social}"?`)) return
  await api.patch(`/proveedores/${p.id}/`, { activo: false })
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Proveedores"
      subtitle="Registro maestro de proveedores — consulta SUNAT disponible"
    >
      <template #actions>
        <button class="btn btn-primary" @click="abrirNuevo">
          <i class="bi bi-plus-lg me-1"></i>Nuevo proveedor
        </button>
      </template>
    </PageHeader>

    <div class="card">
      <div class="card-body p-0">
        <div v-if="loading" class="p-4 text-center text-muted">Cargando...</div>
        <div v-else-if="!proveedores.length" class="p-4 text-center text-muted">Sin proveedores registrados.</div>
        <div v-else class="table-responsive">
          <table class="table table-hover mb-0 align-middle">
            <thead class="table-light">
              <tr>
                <th>RUC</th>
                <th>Razón social</th>
                <th>Contacto</th>
                <th>Teléfono</th>
                <th>Email</th>
                <th class="text-end">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in proveedores" :key="p.id">
                <td><code>{{ p.ruc }}</code></td>
                <td>{{ p.razon_social }}</td>
                <td>{{ p.contacto || '—' }}</td>
                <td>{{ p.telefono || '—' }}</td>
                <td>{{ p.email || '—' }}</td>
                <td class="text-end">
                  <button class="btn btn-sm btn-outline-secondary me-1" @click="abrirEditar(p)">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger" @click="desactivar(p)">
                    <i class="bi bi-trash"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="showModal" class="modal d-block" tabindex="-1" style="background:rgba(0,0,0,.45)">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ editId ? 'Editar' : 'Nuevo' }} proveedor</h5>
            <button type="button" class="btn-close" @click="showModal = false"></button>
          </div>
          <div class="modal-body">
            <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
            <div class="row g-3">
              <div class="col-md-5">
                <label class="form-label">RUC *</label>
                <div class="input-group">
                  <input v-model="form.ruc" class="form-control" maxlength="11" :readonly="!!editId" />
                  <button
                    v-if="!editId"
                    class="btn btn-outline-primary"
                    type="button"
                    :disabled="consultandoRuc"
                    @click="consultarRuc"
                  >
                    {{ consultandoRuc ? '...' : 'SUNAT' }}
                  </button>
                </div>
                <div v-if="rucError" class="text-danger small mt-1">{{ rucError }}</div>
                <div v-if="sunatInfo?.estado_sunat" class="text-muted small mt-1">
                  Estado: {{ sunatInfo.estado_sunat }} — {{ sunatInfo.condicion_sunat }}
                </div>
              </div>
              <div class="col-md-7">
                <label class="form-label">Razón social *</label>
                <input v-model="form.razon_social" class="form-control" />
              </div>
              <div class="col-12">
                <label class="form-label">Dirección</label>
                <input v-model="form.direccion" class="form-control" />
              </div>
              <div class="col-md-4">
                <label class="form-label">Contacto</label>
                <input v-model="form.contacto" class="form-control" />
              </div>
              <div class="col-md-4">
                <label class="form-label">Teléfono</label>
                <input v-model="form.telefono" class="form-control" />
              </div>
              <div class="col-md-4">
                <label class="form-label">Email</label>
                <input v-model="form.email" type="email" class="form-control" />
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showModal = false">Cancelar</button>
            <button class="btn btn-primary" :disabled="saving" @click="guardar">
              {{ saving ? 'Guardando...' : 'Guardar' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
