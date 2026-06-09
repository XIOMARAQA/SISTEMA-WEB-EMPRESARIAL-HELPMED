<script setup>

import { computed, onMounted, ref } from 'vue'

import api from '../api/client'

import PageHeader from '../components/PageHeader.vue'

import { puedeCuadreFisico, puedeMovimientoInventario, inventarioSoloLectura } from '../config/roles'

import { useAuthStore } from '../stores/auth'



const auth = useAuthStore()

const inventarios = ref([])

const movimientos = ref([])

const tab = ref('stock')

const loading = ref(true)

const showModalMov = ref(false)

const guardando = ref(false)

const guardandoCuadre = ref(null)

const buscandoCliente = ref(false)

const clienteHint = ref('')



const formMov = ref({

  inventario: '', tipo: 'entrada', cantidad: '',

  tercero_tipo: 'proveedor', tercero_documento: '', tercero_nombre: '',

  doc_fecha: '', doc_tipo: 'FACTURA', doc_serie: '', doc_numero: '',

  motivo: '', observaciones: '',

})



const clasificacionBadge = {

  conforme: 'bg-success', reposicion: 'bg-warning text-dark',

  alta_prioridad: 'bg-orange', retiro_inmediato: 'bg-danger',

}

const cuadreBadge = {

  pendiente: 'bg-secondary',

  conforme: 'bg-success',

  discrepancia: 'bg-danger',

}

const user = computed(() => auth.user)

const puedeCuadre = computed(() => puedeCuadreFisico(user.value))

const puedeMov = computed(() => puedeMovimientoInventario(user.value))

const soloLectura = computed(() => inventarioSoloLectura(user.value))



const alertasStock = computed(() =>

  inventarios.value.filter(i => i.stock_minimo > 0 && i.cantidad <= i.stock_minimo)

)

const discrepancias = computed(() =>

  inventarios.value.filter(i => i.cuadre_estado === 'discrepancia')

)



async function load() {

  loading.value = true

  try {

    const [invRes, movRes] = await Promise.all([

      api.get('/inventarios/'),

      api.get('/movimientos-inventario/'),

    ])

    inventarios.value = invRes.data.results || invRes.data

    movimientos.value = movRes.data.results || movRes.data

  } finally {

    loading.value = false

  }

}



function abrirMovimiento(tipo) {

  formMov.value = {

    inventario: '', tipo, cantidad: '',

    tercero_tipo: tipo === 'entrada' ? 'proveedor' : 'cliente',

    tercero_documento: '', tercero_nombre: '',

    doc_fecha: new Date().toISOString().slice(0, 10),

    doc_tipo: tipo === 'entrada' ? 'FACTURA' : 'GUIA',

    doc_serie: '', doc_numero: '', motivo: '', observaciones: '',

  }

  showModalMov.value = true

  clienteHint.value = ''

}



async function buscarClienteDocumento() {

  const doc = (formMov.value.tercero_documento || '').replace(/\D/g, '')

  if (!doc) {

    clienteHint.value = 'Ingrese el RUC (11 dígitos) o DNI (8 dígitos) del cliente.'

    return

  }

  if (doc.length !== 8 && doc.length !== 11) {

    clienteHint.value = 'Use RUC de 11 dígitos o DNI de 8 dígitos.'

    return

  }

  buscandoCliente.value = true

  clienteHint.value = ''

  try {

    const { data } = await api.get('/movimientos-inventario/consultar-tercero/', {

      params: { documento: doc },

    })

    formMov.value.tercero_documento = data.documento || doc

    formMov.value.tercero_nombre = data.nombre || ''

    if (!formMov.value.tercero_nombre) {

      clienteHint.value = 'Documento encontrado sin nombre. Complete manualmente.'

    }

  } catch (e) {

    const d = e.response?.data

    clienteHint.value = d?.detail || d?.dni?.[0] || d?.ruc?.[0]

      || 'No se encontró el documento. Ingrese el nombre manualmente.'

  } finally {

    buscandoCliente.value = false

  }

}



async function registrarMovimiento() {

  guardando.value = true

  try {

    await api.post('/movimientos-inventario/', formMov.value)

    showModalMov.value = false

    await load()

  } finally {

    guardando.value = false

  }

}



async function guardarCuadre(item) {

  if (!puedeCuadre.value) return

  guardandoCuadre.value = item.id

  try {

    await api.patch(`/inventarios/${item.id}/`, {

      cantidad_fisica: item.cantidad_fisica === '' || item.cantidad_fisica == null

        ? null

        : Number(item.cantidad_fisica),

      cuadre_observaciones: item.cuadre_observaciones || '',

    })

    await load()

  } catch (e) {

    alert(e.response?.data?.detail || 'No se pudo guardar el cuadre.')

  } finally {

    guardandoCuadre.value = null

  }

}



onMounted(load)

function fmtFechaKardex(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-PE')
}

function fmtVencimiento(fecha) {
  if (!fecha) return '—'
  return new Date(fecha + 'T12:00:00').toLocaleDateString('es-PE')
}

</script>



<template>

  <div>

    <PageHeader title="Control de inventario" subtitle="Stock, movimientos y cuadre físico" />

    <div v-if="soloLectura" class="alert alert-light border small mb-3">
      <i class="bi bi-eye me-1"></i>
      Modo supervisión: puede consultar stock, kardex y discrepancias. No puede registrar movimientos ni cuadre físico.
    </div>

    <div v-if="puedeMov" class="d-flex gap-2 mb-3">

      <button class="btn btn-success btn-sm" @click="abrirMovimiento('entrada')">

        <i class="bi bi-box-arrow-in-down me-1"></i>FEAT 09 — Entrada

      </button>

      <button class="btn btn-warning btn-sm" @click="abrirMovimiento('salida')">

        <i class="bi bi-box-arrow-up me-1"></i>FEAT 10 — Salida

      </button>

    </div>



    <div v-if="alertasStock.length" class="alert alert-warning py-2 small">

      <i class="bi bi-exclamation-triangle me-1"></i>

      <strong>FEAT 11:</strong> {{ alertasStock.length }} producto(s) en stock mínimo.

    </div>



    <div v-if="discrepancias.length" class="alert alert-danger py-2 small">

      <i class="bi bi-exclamation-octagon me-1"></i>

      <strong>Cuadre físico:</strong> {{ discrepancias.length }} discrepancia(s).

      El área administrativa fue notificada para evaluación.

    </div>



    <ul class="nav nav-tabs mb-3">

      <li class="nav-item"><button class="nav-link" :class="{ active: tab === 'stock' }" @click="tab = 'stock'">Stock (FEAT 11)</button></li>

      <li class="nav-item"><button class="nav-link" :class="{ active: tab === 'kardex' }" @click="tab = 'kardex'">Kardex (UC 06)</button></li>

    </ul>



    <div class="card">

      <div class="card-body p-0">

        <div v-if="loading" class="text-center py-4"><div class="spinner-border text-primary"></div></div>

        <div v-else-if="tab === 'stock'" class="table-responsive">

          <table class="table table-hover table-sm mb-0 align-middle">

            <thead class="table-light">

              <tr>

                <th>Producto</th>

                <th>Lote</th>

                <th class="text-end">Stock sist.</th>

                <th class="text-end">Cant. física</th>

                <th class="text-end">Dif.</th>

                <th>Cuadre</th>

                <th>Obs. cuadre</th>

                <th v-if="puedeCuadre"></th>

                <th>Stock mín.</th>

                <th>Venc.</th>

                <th>Clasif.</th>

              </tr>

            </thead>

            <tbody>

              <tr

                v-for="i in inventarios"

                :key="i.id"

                :class="{

                  'table-warning': alertasStock.some(a => a.id === i.id),

                  'table-danger': i.cuadre_estado === 'discrepancia',

                }"

              >

                <td>

                  <div class="small text-muted">{{ i.producto_codigo }}</div>

                  {{ i.producto_nombre }}

                </td>

                <td>{{ i.lote }}</td>

                <td class="text-end fw-semibold">{{ i.cantidad }}</td>

                <td class="text-end" style="min-width:90px">

                  <input

                    v-if="puedeCuadre"

                    v-model="i.cantidad_fisica"

                    type="number"

                    step="0.01"

                    min="0"

                    class="form-control form-control-sm text-end"

                    placeholder="Conteo"

                  />

                  <span v-else>{{ i.cantidad_fisica ?? '—' }}</span>

                </td>

                <td class="text-end small" :class="{ 'text-danger fw-bold': i.diferencia_cuadre && i.diferencia_cuadre !== 0 }">

                  {{ i.diferencia_cuadre != null ? i.diferencia_cuadre : '—' }}

                </td>

                <td>

                  <span class="badge" :class="cuadreBadge[i.cuadre_estado] || 'bg-secondary'">

                    {{ i.cuadre_estado || 'pendiente' }}

                  </span>

                </td>

                <td style="min-width:120px">

                  <input

                    v-if="puedeCuadre"

                    v-model="i.cuadre_observaciones"

                    class="form-control form-control-sm"

                    placeholder="Opcional"

                  />

                  <span v-else class="small">{{ i.cuadre_observaciones || '—' }}</span>

                </td>

                <td v-if="puedeCuadre">

                  <button

                    class="btn btn-sm btn-outline-primary"

                    :disabled="guardandoCuadre === i.id"

                    title="Guardar cuadre"

                    @click="guardarCuadre(i)"

                  >

                    <span v-if="guardandoCuadre === i.id" class="spinner-border spinner-border-sm"></span>

                    <i v-else class="bi bi-check2"></i>

                  </button>

                </td>

                <td>{{ i.stock_minimo ?? '—' }}</td>

                <td class="small">{{ i.fecha_vencimiento || '—' }}</td>

                <td>

                  <span class="badge" :class="clasificacionBadge[i.clasificacion] || 'bg-secondary'">

                    {{ i.clasificacion?.replace('_', ' ') || '—' }}

                  </span>

                </td>

              </tr>

            </tbody>

          </table>

          <p v-if="puedeCuadre" class="small text-muted px-3 py-2 mb-0">

            <i class="bi bi-info-circle me-1"></i>

            Ingrese la cantidad contada en almacén y pulse ✓. Si coincide con el sistema → <strong>Conforme</strong>;

            si no → <strong>Discrepancia</strong> (notifica al área administrativa).

          </p>

        </div>

        <div v-else class="table-responsive">

          <table class="table table-hover table-sm mb-0">

            <thead class="table-light">

              <tr>
                <th>Fecha</th>
                <th>Código</th>
                <th>Producto</th>
                <th>Lote</th>
                <th>Venc.</th>
                <th>Categoría</th>
                <th>Marca</th>
                <th>Tipo</th>
                <th class="text-end">Cant.</th>
                <th class="text-end">Saldo</th>
                <th>Tercero</th>
                <th>Doc.</th>
                <th>Motivo</th>
              </tr>

            </thead>

            <tbody>

              <tr v-for="m in movimientos" :key="m.id">

                <td class="small text-nowrap">{{ fmtFechaKardex(m.creado_en) }}</td>

                <td class="fw-semibold small">{{ m.producto_codigo || '—' }}</td>

                <td style="min-width:160px">
                  <div>{{ m.producto_nombre }}</div>
                  <div v-if="m.producto_laboratorio" class="small text-muted">{{ m.producto_laboratorio }}</div>
                  <div v-if="m.inventario_ubicacion" class="small text-muted">
                    <i class="bi bi-geo-alt"></i> {{ m.inventario_ubicacion }}
                  </div>
                </td>

                <td class="small">{{ m.inventario_lote || '—' }}</td>

                <td class="small text-nowrap">{{ fmtVencimiento(m.inventario_vencimiento) }}</td>

                <td class="small">{{ m.producto_categoria || '—' }}</td>

                <td class="small">{{ m.producto_marca || '—' }}</td>

                <td><span class="badge" :class="m.tipo === 'entrada' ? 'bg-success' : 'bg-warning text-dark'">{{ m.tipo }}</span></td>

                <td class="text-end text-nowrap small">
                  {{ m.cantidad }} <span class="text-muted">{{ m.unidad_medida }}</span>
                </td>

                <td class="text-end small fw-semibold">{{ m.stock_posterior ?? '—' }}</td>

                <td class="small">{{ m.tercero_nombre || '—' }}</td>

                <td class="small text-nowrap">{{ m.doc_tipo }} {{ m.doc_serie }}-{{ m.doc_numero }}</td>

                <td class="small" style="min-width:140px">{{ m.motivo || '—' }}</td>

              </tr>

            </tbody>

          </table>

        </div>

      </div>

    </div>



    <div v-if="showModalMov" class="modal fade show d-block" style="background:rgba(0,0,0,.5)">

      <div class="modal-dialog modal-lg">

        <div class="modal-content">

          <div class="modal-header" :class="formMov.tipo === 'entrada' ? 'bg-success text-white' : 'bg-warning'">

            <h5 class="modal-title">{{ formMov.tipo === 'entrada' ? 'FEAT 09 — Entrada' : 'FEAT 10 — Salida' }}</h5>

            <button class="btn-close" :class="{ 'btn-close-white': formMov.tipo === 'entrada' }" @click="showModalMov = false"></button>

          </div>

          <div class="modal-body">

            <div class="row g-2">

              <div class="col-md-6">

                <label class="small">Inventario / Lote *</label>

                <select v-model="formMov.inventario" class="form-select form-select-sm">

                  <option value="">—</option>

                  <option v-for="i in inventarios" :key="i.id" :value="i.id">{{ i.producto_nombre }} — Lote {{ i.lote }}</option>

                </select>

              </div>

              <div class="col-md-3"><label class="small">Cantidad *</label><input v-model="formMov.cantidad" type="number" class="form-control form-control-sm" /></div>

              <div class="col-md-3"><label class="small">Motivo</label><input v-model="formMov.motivo" class="form-control form-control-sm" /></div>

              <div class="col-md-3">
                <label class="small">{{ formMov.tipo === 'entrada' ? 'RUC Proveedor' : 'Doc. Cliente' }}</label>
                <div v-if="formMov.tipo === 'salida'" class="input-group input-group-sm">
                  <input
                    v-model="formMov.tercero_documento"
                    class="form-control"
                    maxlength="11"
                    placeholder="RUC o DNI"
                    @keyup.enter="buscarClienteDocumento"
                  />
                  <button
                    type="button"
                    class="btn btn-outline-secondary"
                    title="Buscar razón social o nombres"
                    :disabled="buscandoCliente"
                    @click="buscarClienteDocumento"
                  >
                    <span v-if="buscandoCliente" class="spinner-border spinner-border-sm"></span>
                    <i v-else class="bi bi-search"></i>
                  </button>
                </div>
                <input
                  v-else
                  v-model="formMov.tercero_documento"
                  class="form-control form-control-sm"
                />
                <div v-if="formMov.tipo === 'salida' && clienteHint" class="text-danger small mt-1">
                  {{ clienteHint }}
                </div>
              </div>

              <div class="col-md-5"><label class="small">Nombre / Razón social</label>

                <input v-model="formMov.tercero_nombre" class="form-control form-control-sm" /></div>

              <div class="col-md-4"><label class="small">Fecha documento</label>

                <input v-model="formMov.doc_fecha" type="date" class="form-control form-control-sm" /></div>

              <div class="col-md-2"><label class="small">Tipo doc.</label>

                <input v-model="formMov.doc_tipo" class="form-control form-control-sm" /></div>

              <div class="col-md-2"><label class="small">Serie</label>

                <input v-model="formMov.doc_serie" class="form-control form-control-sm" /></div>

              <div class="col-md-2"><label class="small">Número</label>

                <input v-model="formMov.doc_numero" class="form-control form-control-sm" /></div>

              <div class="col-12"><label class="small">Observaciones</label>

                <textarea v-model="formMov.observaciones" class="form-control form-control-sm" rows="2"></textarea></div>

            </div>

          </div>

          <div class="modal-footer">

            <button class="btn btn-secondary" @click="showModalMov = false">Cancelar</button>

            <button class="btn btn-primary" :disabled="guardando" @click="registrarMovimiento">Registrar movimiento</button>

          </div>

        </div>

      </div>

    </div>

  </div>

</template>



<style scoped>

.bg-orange { background-color: #fd7e14; color: #fff; }

</style>

