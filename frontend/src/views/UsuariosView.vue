<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'

const usuarios = ref([])
const roles = ref([])
const loading = ref(true)
const showModal = ref(false)
const editId = ref(null)
const error = ref('')
const saving = ref(false)
const usernamePreview = ref('')
const showConfirmDesactivar = ref(false)
const usuarioDesactivar = ref(null)
const desactivando = ref(false)
const errorDesactivar = ref('')

const form = ref({
  nombres: '',
  apellidos: '',
  documento: '',
  email: '',
  telefono: '',
  rol: '',
  password: '',
  estado: 'activo',
})

const estados = [
  { value: 'activo', label: 'Activo' },
  { value: 'inactivo', label: 'Inactivo' },
  { value: 'bloqueado', label: 'Bloqueado' },
]

const esEdicion = computed(() => !!editId.value)

function extraerErrorApi(err, fallback) {
  const d = err.response?.data
  if (typeof d === 'string') {
    if (d.includes('usuarios_pkey') || d.includes('llave duplicada')) {
      return 'Conflicto de identificador en la base de datos. Contacte al administrador del sistema.'
    }
    return fallback
  }
  if (!d || typeof d !== 'object') return fallback
  return d.detail
    || d.documento?.[0]
    || d.email?.[0]
    || d.password?.[0]
    || d.nombres?.[0]
    || d.apellidos?.[0]
    || d.rol?.[0]
    || Object.values(d).flat().find((v) => typeof v === 'string')
    || fallback
}

async function load() {
  loading.value = true
  try {
    const [uRes, rRes] = await Promise.all([
      api.get('/usuarios/'),
      api.get('/roles/'),
    ])
    usuarios.value = uRes.data.results || uRes.data
    roles.value = rRes.data.results || rRes.data
  } finally {
    loading.value = false
  }
}

function abrirNuevo() {
  editId.value = null
  form.value = {
    nombres: '', apellidos: '', documento: '', email: '',
    telefono: '', rol: roles.value[0]?.id || '', password: '', estado: 'activo',
  }
  usernamePreview.value = ''
  error.value = ''
  showModal.value = true
}

function abrirEditar(u) {
  editId.value = u.id
  form.value = {
    nombres: u.nombres || '',
    apellidos: u.apellidos || '',
    documento: u.documento || '',
    email: u.email || '',
    telefono: u.telefono || '',
    rol: u.rol?.id || '',
    password: '',
    estado: u.estado || 'activo',
  }
  usernamePreview.value = u.username
  error.value = ''
  showModal.value = true
}

function credencialesLocales(username, documento) {
  const user = (username || '').trim().toLowerCase()
  if (!user) return { email: '', password: '' }
  const digitos = String(documento || '').replace(/\D/g, '')
  const sufijo = digitos.length >= 2 ? digitos.slice(-2) : digitos
  return {
    email: `${user}@seguricel.com`,
    password: `${user}${sufijo}`,
  }
}

async function actualizarCredencialesAuto() {
  if (esEdicion.value) return
  if (!form.value.nombres.trim() || !form.value.apellidos.trim()) {
    usernamePreview.value = ''
    form.value.email = ''
    form.value.password = ''
    return
  }
  try {
    const params = {
      nombres: form.value.nombres,
      apellidos: form.value.apellidos,
    }
    if (form.value.documento.trim()) params.documento = form.value.documento.trim()
    const { data } = await api.get('/usuarios/sugerir-username/', { params })
    usernamePreview.value = data.username
    form.value.email = data.email || credencialesLocales(data.username, form.value.documento).email
    form.value.password = data.password || credencialesLocales(data.username, form.value.documento).password
  } catch {
    usernamePreview.value = ''
    form.value.email = ''
    form.value.password = ''
  }
}

let previewTimer = null
watch(
  () => [form.value.nombres, form.value.apellidos, form.value.documento],
  () => {
    clearTimeout(previewTimer)
    previewTimer = setTimeout(actualizarCredencialesAuto, 350)
  },
)

async function guardar() {
  error.value = ''
  if (!form.value.nombres.trim() || !form.value.apellidos.trim()) {
    error.value = 'Nombres y apellidos son obligatorios.'
    return
  }
  if (!form.value.documento.trim()) {
    error.value = 'El DNI es obligatorio.'
    return
  }
  if (!form.value.rol) {
    error.value = 'Seleccione un rol.'
    return
  }
  if (!esEdicion.value) {
    if (!usernamePreview.value) {
      error.value = 'Complete nombres y apellidos para generar el código de usuario.'
      return
    }
    const cred = credencialesLocales(usernamePreview.value, form.value.documento)
    form.value.email = cred.email
    form.value.password = cred.password
  }

  saving.value = true
  try {
    const payload = {
      nombres: form.value.nombres.trim(),
      apellidos: form.value.apellidos.trim(),
      documento: form.value.documento.trim(),
      email: form.value.email.trim(),
      telefono: form.value.telefono.trim(),
      rol: form.value.rol,
    }
    if (esEdicion.value) {
      payload.estado = form.value.estado
      if (form.value.password) payload.password = form.value.password
      await api.patch(`/usuarios/${editId.value}/`, payload)
    } else {
      payload.password = form.value.password
      await api.post('/usuarios/', payload)
    }
    showModal.value = false
    await load()
  } catch (e) {
    error.value = extraerErrorApi(e, 'No se pudo guardar el usuario.')
  } finally {
    saving.value = false
  }
}

function abrirConfirmDesactivar(u) {
  if (u.is_superuser) {
    error.value = 'No puede desactivar un superusuario desde esta pantalla.'
    return
  }
  usuarioDesactivar.value = u
  errorDesactivar.value = ''
  showConfirmDesactivar.value = true
}

function cerrarConfirmDesactivar() {
  showConfirmDesactivar.value = false
  usuarioDesactivar.value = null
  errorDesactivar.value = ''
}

async function confirmarDesactivar() {
  const u = usuarioDesactivar.value
  if (!u) return
  desactivando.value = true
  errorDesactivar.value = ''
  try {
    await api.delete(`/usuarios/${u.id}/`)
    cerrarConfirmDesactivar()
    await load()
  } catch (e) {
    errorDesactivar.value = extraerErrorApi(e, 'No se pudo desactivar el usuario.')
  } finally {
    desactivando.value = false
  }
}

function estadoBadge(estado) {
  return {
    activo: 'bg-success',
    inactivo: 'bg-secondary',
    bloqueado: 'bg-danger',
  }[estado] || 'bg-secondary'
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Usuarios del sistema"
      subtitle="Mantenimiento de usuarios · Solo administrador"
    >
      <template #actions>
        <button class="btn btn-primary" @click="abrirNuevo">
          <i class="bi bi-person-plus me-1"></i>Nuevo usuario
        </button>
      </template>
    </PageHeader>

    <div class="alert alert-light border small mb-3">
      <i class="bi bi-info-circle me-1"></i>
      El <strong>código de usuario</strong> se genera automáticamente:
      primera letra del nombre + apellido paterno (ej. Emir García → <code>egarcia</code>).
      El <strong>correo</strong> será <code>codigo@seguricel.com</code> y la
      <strong>contraseña inicial</strong> <code>codigo + 2 últimos dígitos del DNI</code>
      (ej. DNI 50023442 → <code>egarcia42</code>).
    </div>

    <div class="card">
      <div class="card-body p-0">
        <div v-if="loading" class="text-center py-4">
          <div class="spinner-border text-primary"></div>
        </div>
        <div v-else class="table-responsive">
          <table class="table table-hover table-sm mb-0">
            <thead class="table-light">
              <tr>
                <th>Usuario</th>
                <th>Nombres</th>
                <th>DNI</th>
                <th>Correo</th>
                <th>Rol</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in usuarios" :key="u.id">
                <td class="fw-semibold">
                  {{ u.username }}
                  <span v-if="u.is_superuser" class="badge bg-dark ms-1">Super</span>
                  <span v-else-if="u.es_admin" class="badge bg-primary ms-1">Admin</span>
                </td>
                <td>{{ u.nombres }} {{ u.apellidos }}</td>
                <td>{{ u.documento || '—' }}</td>
                <td class="small">{{ u.email || '—' }}</td>
                <td><span class="badge bg-info text-dark">{{ u.rol?.nombre || '—' }}</span></td>
                <td><span class="badge" :class="estadoBadge(u.estado)">{{ u.estado }}</span></td>
                <td class="text-end text-nowrap">
                  <button class="btn btn-sm btn-outline-primary me-1" @click="abrirEditar(u)">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button
                    v-if="u.estado === 'activo' && !u.is_superuser"
                    class="btn btn-sm btn-outline-danger"
                    @click="abrirConfirmDesactivar(u)"
                  >
                    <i class="bi bi-person-x"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="showModal" class="modal fade show d-block" style="background:rgba(0,0,0,.5)">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header bg-primary text-white">
            <h5 class="modal-title">{{ esEdicion ? 'Editar usuario' : 'Nuevo usuario' }}</h5>
            <button type="button" class="btn-close btn-close-white" @click="showModal = false"></button>
          </div>
          <div class="modal-body">
            <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label small">Nombres *</label>
                <input v-model="form.nombres" class="form-control form-control-sm" placeholder="Juan Carlos" />
              </div>
              <div class="col-md-6">
                <label class="form-label small">Apellidos * <span class="text-muted">(paterno primero)</span></label>
                <input v-model="form.apellidos" class="form-control form-control-sm" placeholder="Pérez García" />
              </div>
              <div class="col-md-4">
                <label class="form-label small">Código de usuario</label>
                <input
                  class="form-control form-control-sm bg-light"
                  :value="esEdicion ? usernamePreview : (usernamePreview || '—')"
                  readonly
                />
              </div>
              <div class="col-md-4">
                <label class="form-label small">DNI *</label>
                <input v-model="form.documento" class="form-control form-control-sm" maxlength="20" />
              </div>
              <div class="col-md-4">
                <label class="form-label small">Rol *</label>
                <select v-model="form.rol" class="form-select form-select-sm">
                  <option value="">— Seleccione —</option>
                  <option v-for="r in roles" :key="r.id" :value="r.id">{{ r.nombre }}</option>
                </select>
              </div>
              <div class="col-md-6">
                <label class="form-label small">Correo electrónico</label>
                <input
                  v-model="form.email"
                  type="email"
                  class="form-control form-control-sm"
                  :class="{ 'bg-light': !esEdicion }"
                  :readonly="!esEdicion"
                />
                <div v-if="!esEdicion" class="form-text">Generado: codigo@seguricel.com</div>
              </div>
              <div class="col-md-6">
                <label class="form-label small">Teléfono</label>
                <input v-model="form.telefono" class="form-control form-control-sm" />
              </div>
              <div class="col-md-6">
                <label class="form-label small">
                  {{ esEdicion ? 'Nueva contraseña (opcional)' : 'Contraseña inicial' }}
                </label>
                <input
                  v-model="form.password"
                  :type="esEdicion ? 'password' : 'text'"
                  class="form-control form-control-sm"
                  :class="{ 'bg-light': !esEdicion }"
                  :readonly="!esEdicion"
                  autocomplete="new-password"
                />
                <div v-if="!esEdicion" class="form-text">Generada: codigo + 2 últimos dígitos del DNI</div>
              </div>
              <div v-if="esEdicion" class="col-md-6">
                <label class="form-label small">Estado</label>
                <select v-model="form.estado" class="form-select form-select-sm">
                  <option v-for="e in estados" :key="e.value" :value="e.value">{{ e.label }}</option>
                </select>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showModal = false">Cancelar</button>
            <button class="btn btn-primary" :disabled="saving" @click="guardar">
              {{ saving ? 'Guardando…' : 'Guardar' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showConfirmDesactivar && usuarioDesactivar" class="modal fade show d-block" style="background:rgba(0,0,0,.5); z-index:1060">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header bg-danger text-white">
            <h5 class="modal-title">
              <i class="bi bi-person-x me-2"></i>Desactivar usuario
            </h5>
            <button type="button" class="btn-close btn-close-white" @click="cerrarConfirmDesactivar"></button>
          </div>
          <div class="modal-body">
            <div v-if="errorDesactivar" class="alert alert-danger py-2 small">{{ errorDesactivar }}</div>
            <p class="mb-2">
              ¿Confirma desactivar la cuenta de
              <strong>{{ usuarioDesactivar.nombres }} {{ usuarioDesactivar.apellidos }}</strong>?
            </p>
            <ul class="small text-muted mb-0 ps-3">
              <li>Usuario: <code>{{ usuarioDesactivar.username }}</code></li>
              <li>Rol: {{ usuarioDesactivar.rol?.nombre || '—' }}</li>
              <li>No podrá iniciar sesión en HelpMed.</li>
              <li>El registro se conserva; puede reactivarlo editando el usuario y cambiando el estado a <strong>Activo</strong>.</li>
            </ul>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" :disabled="desactivando" @click="cerrarConfirmDesactivar">
              Cancelar
            </button>
            <button class="btn btn-danger" :disabled="desactivando" @click="confirmarDesactivar">
              <span v-if="desactivando" class="spinner-border spinner-border-sm me-1"></span>
              Sí, desactivar
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
