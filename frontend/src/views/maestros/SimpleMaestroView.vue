<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api/client'
import PageHeader from '../../components/PageHeader.vue'
import { MAESTROS_ENTIDADES } from '../../config/maestros'

const route = useRoute()
const config = computed(() => MAESTROS_ENTIDADES[route.meta.maestroKey])
const items = ref([])
const loading = ref(true)
const showModal = ref(false)
const editId = ref(null)
const form = ref({})
const error = ref('')
const saving = ref(false)

async function load() {
  if (!config.value) return
  loading.value = true
  try {
    const { data } = await api.get(config.value.endpoint)
    items.value = data.results || data
  } finally {
    loading.value = false
  }
}

function abrirNuevo() {
  editId.value = null
  form.value = { ...config.value.empty }
  error.value = ''
  showModal.value = true
}

function abrirEditar(item) {
  editId.value = item.id
  form.value = { ...config.value.empty }
  config.value.fields.forEach(f => {
    form.value[f.key] = item[f.key] ?? ''
  })
  error.value = ''
  showModal.value = true
}

async function guardar() {
  error.value = ''
  for (const f of config.value.fields) {
    if (f.required && !String(form.value[f.key] ?? '').trim()) {
      error.value = `Complete el campo "${f.label}".`
      return
    }
  }
  saving.value = true
  try {
    if (editId.value) {
      await api.patch(`${config.value.endpoint}${editId.value}/`, form.value)
    } else {
      await api.post(config.value.endpoint, form.value)
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
  if (!confirm(`¿Desactivar "${item.nombre || item.codigo}"?`)) return
  await api.patch(`${config.value.endpoint}${item.id}/`, { activo: false })
  await load()
}

watch(() => route.meta.maestroKey, load, { immediate: true })
onMounted(load)
</script>

<template>
  <div v-if="config">
    <PageHeader :title="config.title" :subtitle="config.subtitle">
      <template #actions>
        <button class="btn btn-primary" @click="abrirNuevo">
          <i class="bi bi-plus-lg me-1"></i>Nuevo
        </button>
      </template>
    </PageHeader>

    <div class="card">
      <div class="card-body p-0">
        <div v-if="loading" class="p-4 text-center text-muted">Cargando...</div>
        <div v-else-if="!items.length" class="p-4 text-center text-muted">Sin registros. Agregue el primero.</div>
        <div v-else class="table-responsive">
          <table class="table table-hover mb-0 align-middle">
            <thead class="table-light">
              <tr>
                <th v-for="col in config.columns" :key="col.key">{{ col.label }}</th>
                <th class="text-end" style="width:120px">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.id">
                <td v-for="col in config.columns" :key="col.key">{{ item[col.key] || '—' }}</td>
                <td class="text-end">
                  <button class="btn btn-sm btn-outline-secondary me-1" title="Editar" @click="abrirEditar(item)">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-sm btn-outline-danger" title="Desactivar" @click="desactivar(item)">
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
            <h5 class="modal-title">{{ editId ? 'Editar' : 'Nuevo' }} registro</h5>
            <button type="button" class="btn-close" @click="showModal = false"></button>
          </div>
          <div class="modal-body">
            <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
            <div class="row g-3">
              <div v-for="f in config.fields" :key="f.key" :class="`col-md-${f.col || 12}`">
                <label class="form-label">{{ f.label }}<span v-if="f.required" class="text-danger"> *</span></label>
                <textarea
                  v-if="f.type === 'textarea'"
                  v-model="form[f.key]"
                  class="form-control"
                  rows="2"
                ></textarea>
                <input v-else v-model="form[f.key]" :type="f.type || 'text'" class="form-control" />
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
