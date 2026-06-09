<script setup>
import { onMounted, ref } from 'vue'
import api from '../../api/client'
import PageHeader from '../../components/PageHeader.vue'

const items = ref([])
const categorias = ref([])
const loading = ref(true)
const showModal = ref(false)
const editId = ref(null)
const form = ref({ categoria: '', codigo: '', nombre: '', descripcion: '' })
const error = ref('')
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    const [sc, cat] = await Promise.all([api.get('/subcategorias/'), api.get('/categorias/')])
    items.value = sc.data.results || sc.data
    categorias.value = cat.data.results || cat.data
  } finally {
    loading.value = false
  }
}

function abrirNuevo() {
  editId.value = null
  form.value = {
    categoria: categorias.value[0]?.id || '',
    codigo: '',
    nombre: '',
    descripcion: '',
  }
  error.value = ''
  showModal.value = true
}

function abrirEditar(item) {
  editId.value = item.id
  form.value = {
    categoria: item.categoria,
    codigo: item.codigo,
    nombre: item.nombre,
    descripcion: item.descripcion || '',
  }
  error.value = ''
  showModal.value = true
}

async function guardar() {
  error.value = ''
  if (!form.value.categoria || !form.value.codigo.trim() || !form.value.nombre.trim()) {
    error.value = 'Categoría padre, código y nombre son obligatorios.'
    return
  }
  saving.value = true
  try {
    if (editId.value) {
      await api.patch(`/subcategorias/${editId.value}/`, form.value)
    } else {
      await api.post('/subcategorias/', form.value)
    }
    showModal.value = false
    await load()
  } catch (e) {
    const d = e.response?.data
    error.value = d?.detail || d?.codigo?.[0] || 'No se pudo guardar.'
  } finally {
    saving.value = false
  }
}

async function desactivar(item) {
  if (!confirm(`¿Desactivar "${item.nombre}"?`)) return
  await api.patch(`/subcategorias/${item.id}/`, { activo: false })
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Subcategorías"
      subtitle="Detalle bajo cada categoría padre (ej. Analgésicos dentro de Medicinas)"
    >
      <template #actions>
        <button class="btn btn-primary" @click="abrirNuevo">
          <i class="bi bi-plus-lg me-1"></i>Nueva subcategoría
        </button>
      </template>
    </PageHeader>

    <div class="card">
      <div class="card-body p-0">
        <div v-if="loading" class="p-4 text-center text-muted">Cargando...</div>
        <div v-else-if="!items.length" class="p-4 text-center text-muted">Sin subcategorías. Créelas bajo una categoría padre.</div>
        <div v-else class="table-responsive">
          <table class="table table-hover mb-0 align-middle">
            <thead class="table-light">
              <tr>
                <th>Categoría padre</th>
                <th>Código</th>
                <th>Nombre</th>
                <th>Descripción</th>
                <th class="text-end">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.id">
                <td><span class="badge bg-primary">{{ item.categoria_nombre }}</span></td>
                <td><code>{{ item.codigo }}</code></td>
                <td>{{ item.nombre }}</td>
                <td>{{ item.descripcion || '—' }}</td>
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
            <h5 class="modal-title">{{ editId ? 'Editar' : 'Nueva' }} subcategoría</h5>
            <button type="button" class="btn-close" @click="showModal = false"></button>
          </div>
          <div class="modal-body">
            <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
            <div class="row g-3">
              <div class="col-12">
                <label class="form-label">Categoría padre *</label>
                <select v-model="form.categoria" class="form-select">
                  <option value="">Seleccione categoría...</option>
                  <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
                </select>
              </div>
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
