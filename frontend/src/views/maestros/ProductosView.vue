<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '../../api/client'
import PageHeader from '../../components/PageHeader.vue'

const productos = ref([])
const categorias = ref([])
const subcategorias = ref([])
const marcas = ref([])
const unidades = ref([])
const loading = ref(true)
const showModal = ref(false)
const editId = ref(null)
const error = ref('')
const saving = ref(false)
const cargandoCodigo = ref(false)

const form = ref({
  codigo: '',
  nombre: '',
  descripcion: '',
  tipo: 'producto',
  categoria: '',
  subcategoria: '',
  marca: '',
  unidad: '',
  stock_minimo: 0,
  stock_maximo: 0,
  requiere_cadena_frio: false,
  laboratorio: '',
})

const subcategoriasFiltradas = computed(() =>
  subcategorias.value.filter(s => s.categoria === form.value.categoria)
)

const requiereSubcategoria = computed(() => subcategoriasFiltradas.value.length > 0)

const codigoAutoGenerado = computed(() => !editId.value)

watch(() => form.value.categoria, () => {
  form.value.subcategoria = ''
  if (!editId.value) form.value.codigo = ''
})

watch(() => form.value.subcategoria, async (subId) => {
  if (editId.value) return
  if (subId) {
    await cargarSiguienteCodigo({ subcategoria: subId })
  } else if (form.value.categoria && !requiereSubcategoria.value) {
    await cargarSiguienteCodigo({ categoria: form.value.categoria })
  } else {
    form.value.codigo = ''
  }
})

async function cargarSiguienteCodigo(params) {
  cargandoCodigo.value = true
  try {
    const { data } = await api.get('/productos/siguiente-codigo/', { params })
    form.value.codigo = data.codigo
  } catch {
    form.value.codigo = ''
  } finally {
    cargandoCodigo.value = false
  }
}

async function load() {
  loading.value = true
  try {
    const [p, c, sc, m, u] = await Promise.all([
      api.get('/productos/'),
      api.get('/categorias/'),
      api.get('/subcategorias/'),
      api.get('/marcas/'),
      api.get('/unidades-medida/'),
    ])
    productos.value = p.data.results || p.data
    categorias.value = c.data.results || c.data
    subcategorias.value = sc.data.results || sc.data
    marcas.value = m.data.results || m.data
    unidades.value = u.data.results || u.data
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.value = {
    codigo: '',
    nombre: '',
    descripcion: '',
    tipo: 'producto',
    categoria: '',
    subcategoria: '',
    marca: '',
    unidad: unidades.value.find(u => u.codigo === 'UND')?.id || unidades.value[0]?.id || '',
    stock_minimo: 0,
    stock_maximo: 0,
    requiere_cadena_frio: false,
    laboratorio: '',
  }
}

function abrirNuevo() {
  editId.value = null
  resetForm()
  error.value = ''
  showModal.value = true
}

function abrirEditar(p) {
  editId.value = p.id
  form.value = {
    codigo: p.codigo,
    nombre: p.nombre,
    descripcion: p.descripcion || '',
    tipo: p.tipo || 'producto',
    categoria: p.categoria,
    subcategoria: p.subcategoria || '',
    marca: p.marca || '',
    unidad: p.unidad || '',
    stock_minimo: p.stock_minimo,
    stock_maximo: p.stock_maximo,
    requiere_cadena_frio: p.requiere_cadena_frio,
    laboratorio: p.laboratorio || '',
  }
  error.value = ''
  showModal.value = true
}

async function guardar() {
  error.value = ''
  if (!form.value.categoria || !form.value.nombre.trim()) {
    error.value = 'Categoría y nombre son obligatorios.'
    return
  }
  if (requiereSubcategoria.value && !form.value.subcategoria) {
    error.value = 'Seleccione una subcategoría para generar el código del producto.'
    return
  }
  if (!form.value.codigo.trim()) {
    error.value = 'Seleccione categoría y subcategoría para obtener el código automático.'
    return
  }
  saving.value = true
  const payload = {
    ...form.value,
    marca: form.value.marca || null,
    unidad: form.value.unidad || null,
    subcategoria: form.value.subcategoria || null,
  }
  try {
    if (editId.value) {
      await api.patch(`/productos/${editId.value}/`, payload)
    } else {
      await api.post('/productos/', payload)
    }
    showModal.value = false
    await load()
  } catch (e) {
    const d = e.response?.data
    error.value = d?.subcategoria?.[0] || d?.codigo?.[0] || d?.detail || 'No se pudo guardar.'
  } finally {
    saving.value = false
  }
}

async function desactivar(p) {
  if (!confirm(`¿Desactivar "${p.nombre}"?`)) return
  await api.patch(`/productos/${p.id}/`, { activo: false })
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Productos y servicios"
      subtitle="El código se genera automáticamente: código subcategoría + correlativo (ej. ANALG000001)"
    >
      <template #actions>
        <button class="btn btn-primary" @click="abrirNuevo">
          <i class="bi bi-plus-lg me-1"></i>Nuevo producto
        </button>
      </template>
    </PageHeader>

    <div class="card">
      <div class="card-body p-0">
        <div v-if="loading" class="p-4 text-center text-muted">Cargando...</div>
        <div v-else-if="!productos.length" class="p-4 text-center text-muted">Sin productos registrados.</div>
        <div v-else class="table-responsive">
          <table class="table table-hover mb-0 align-middle">
            <thead class="table-light">
              <tr>
                <th>Código</th>
                <th>Nombre</th>
                <th>Categoría</th>
                <th>Subcategoría</th>
                <th>Marca</th>
                <th>Laboratorio</th>
                <th>Unidad</th>
                <th class="text-end">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in productos" :key="p.id">
                <td><code>{{ p.codigo }}</code></td>
                <td>{{ p.nombre }}</td>
                <td>{{ p.categoria_nombre || '—' }}</td>
                <td>{{ p.subcategoria_nombre || '—' }}</td>
                <td>{{ p.marca_nombre || '—' }}</td>
                <td>{{ p.laboratorio || '—' }}</td>
                <td>{{ p.unidad_codigo || 'UND' }}</td>
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
            <h5 class="modal-title">{{ editId ? 'Editar' : 'Nuevo' }} producto</h5>
            <button type="button" class="btn-close" @click="showModal = false"></button>
          </div>
          <div class="modal-body">
            <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
            <div class="row g-3">
              <div class="col-md-4">
                <label class="form-label">Tipo</label>
                <select v-model="form.tipo" class="form-select">
                  <option value="producto">Producto</option>
                  <option value="servicio">Servicio</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label">Categoría *</label>
                <select v-model="form.categoria" class="form-select">
                  <option value="">Seleccione primero...</option>
                  <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label">
                  Subcategoría
                  <span v-if="requiereSubcategoria" class="text-danger">*</span>
                </label>
                <select
                  v-model="form.subcategoria"
                  class="form-select"
                  :disabled="!form.categoria || !subcategoriasFiltradas.length"
                >
                  <option value="">
                    {{ !form.categoria ? 'Seleccione categoría...' : subcategoriasFiltradas.length ? 'Seleccione...' : 'Sin subcategorías' }}
                  </option>
                  <option v-for="s in subcategoriasFiltradas" :key="s.id" :value="s.id">
                    {{ s.nombre }} ({{ s.codigo }})
                  </option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label">Código *</label>
                <input
                  v-model="form.codigo"
                  class="form-control font-monospace"
                  readonly
                  :placeholder="cargandoCodigo ? 'Generando...' : 'Seleccione subcategoría'"
                />
                <div v-if="codigoAutoGenerado" class="form-text">
                  Auto: código subcategoría + 6 dígitos (ej. ANALG000001).
                </div>
              </div>
              <div class="col-md-8">
                <label class="form-label">Nombre *</label>
                <input v-model="form.nombre" class="form-control" />
              </div>
              <div class="col-md-4">
                <label class="form-label">Marca</label>
                <select v-model="form.marca" class="form-select">
                  <option value="">Sin marca</option>
                  <option v-for="m in marcas" :key="m.id" :value="m.id">{{ m.nombre }}</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label">Unidad de medida</label>
                <select v-model="form.unidad" class="form-select">
                  <option v-for="u in unidades" :key="u.id" :value="u.id">{{ u.codigo }} — {{ u.nombre }}</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label">Laboratorio</label>
                <input v-model="form.laboratorio" class="form-control" />
              </div>
              <div class="col-md-4">
                <label class="form-label">Stock mínimo</label>
                <input v-model.number="form.stock_minimo" type="number" min="0" step="0.01" class="form-control" />
              </div>
              <div class="col-md-4">
                <label class="form-label">Stock máximo</label>
                <input v-model.number="form.stock_maximo" type="number" min="0" step="0.01" class="form-control" />
              </div>
              <div class="col-12">
                <label class="form-label">Descripción</label>
                <textarea v-model="form.descripcion" class="form-control" rows="2"></textarea>
              </div>
              <div class="col-12">
                <div class="form-check">
                  <input id="frio" v-model="form.requiere_cadena_frio" class="form-check-input" type="checkbox" />
                  <label class="form-check-label" for="frio">Requiere cadena de frío</label>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showModal = false">Cancelar</button>
            <button class="btn btn-primary" :disabled="saving || cargandoCodigo" @click="guardar">
              {{ saving ? 'Guardando...' : 'Guardar' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
