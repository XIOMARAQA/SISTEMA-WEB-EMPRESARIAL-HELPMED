<script setup>
import { onMounted, ref } from 'vue'
import api from '../../api/client'
import PageHeader from '../../components/PageHeader.vue'

const items = ref([])
const loading = ref(true)
const showModal = ref(false)
const editId = ref(null)
const form = ref({ codigo: '', nombre: '', descripcion: '', requiere_fecha_vencimiento: false })
const error = ref('')
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/categorias/')
    items.value = data.results || data
  } finally {
    loading.value = false
  }
}

function abrirNuevo() {
  editId.value = null
  form.value = { codigo: '', nombre: '', descripcion: '', requiere_fecha_vencimiento: false }
  error.value = ''
  showModal.value = true
}

function abrirEditar(item) {
  editId.value = item.id
  form.value = {
    codigo: item.codigo,
    nombre: item.nombre,
    descripcion: item.descripcion || '',
    requiere_fecha_vencimiento: !!item.requiere_fecha_vencimiento,
  }
  error.value = ''
  showModal.value = true
}

async function guardar() {
  error.value = ''
  if (!form.value.codigo.trim() || !form.value.nombre.trim()) {
    error.value = 'Código y nombre son obligatorios.'
    return
  }
  saving.value = true
  try {
    if (editId.value) {
      await api.patch(`/categorias/${editId.value}/`, form.value)
    } else {
      await api.post('/categorias/', form.value)
    }
    showModal.value = false
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || e.response?.data?.codigo?.[0] || 'No se pudo guardar.'
  } finally {
    saving.value = false
  }
}

async function desactivar(item) {
  if (!confirm(`¿Desactivar "${item.nombre}"?`)) return
  await api.patch(`/categorias/${item.id}/`, { activo: false })
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Categorías de producto"
      subtitle="Clasificación principal. Marque vencimiento obligatorio para medicinas y similares."
    >
      <template #actions>
        <button class="btn btn-primary" @click="abrirNuevo">
          <i class="bi bi-plus-lg me-1"></i>Nuevo
        </button>
      </template>
    </PageHeader>

    <div class="card">
      <div class="card-body p-0">
        <div v-if="loading" class="p-4 text-center text-muted">Cargando...</div>
        <div v-else-if="!items.length" class="p-4 text-center text-muted">Sin categorías registradas.</div>
        <div v-else class="table-responsive">
          <table class="table table-hover mb-0 align-middle">
            <thead class="table-light">
              <tr>
                <th>Código</th>
                <th>Nombre</th>
                <th>Descripción</th>
                <th>Subcategorías</th>
                <th>Vencimiento</th>
                <th class="text-end">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.id">
                <td><code>{{ item.codigo }}</code></td>
                <td>{{ item.nombre }}</td>
                <td>{{ item.descripcion || '—' }}</td>
                <td><span class="badge bg-secondary">{{ item.subcategorias_count || 0 }}</span></td>
                <td>
                  <span
                    v-if="item.requiere_fecha_vencimiento"
                    class="badge bg-warning text-dark"
                    title="Los productos deben tener fecha de vencimiento"
                  >
                    Obligatorio
                  </span>
                  <span v-else class="text-muted small">Opcional</span>
                </td>
                <td class="text-end">
                  <button class="btn btn-sm btn-outline-secondary me-1" @click="abrirEditar(item)">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger" @click="desactivar(item)">
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
            <h5 class="modal-title">{{ editId ? 'Editar' : 'Nueva' }} categoría</h5>
            <button type="button" class="btn-close" @click="showModal = false"></button>
          </div>
          <div class="modal-body">
            <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
            <div class="row g-3">
              <div class="col-md-4">
                <label class="form-label">Código *</label>
                <input v-model="form.codigo" class="form-control" :readonly="!!editId" />
              </div>
              <div class="col-md-8">
                <label class="form-label">Nombre *</label>
                <input v-model="form.nombre" class="form-control" />
              </div>
              <div class="col-12">
                <label class="form-label">Descripción</label>
                <textarea v-model="form.descripcion" class="form-control" rows="2"></textarea>
              </div>
              <div class="col-12">
                <div class="form-check">
                  <input
                    id="req-vcto"
                    v-model="form.requiere_fecha_vencimiento"
                    class="form-check-input"
                    type="checkbox"
                  />
                  <label class="form-check-label" for="req-vcto">
                    Exige fecha de vencimiento en productos (ej. medicinas)
                  </label>
                </div>
                <div class="form-text">
                  Si está activo, al registrar un producto de esta categoría la fecha de vencimiento será obligatoria.
                  Para EPP (guantes, mascarillas) déjelo desmarcado.
                </div>
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
