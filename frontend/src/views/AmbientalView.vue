<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import { useAuthStore } from '../stores/auth'
import { puedeRegistrarMedicionAmbiental } from '../config/roles'

const auth = useAuthStore()
const mediciones = ref([])
const loading = ref(true)
const form = ref({ temperatura: '', humedad: '', fecha: '', hora: '', ubicacion: 'Almacén principal' })

const puedeRegistrar = computed(() => puedeRegistrarMedicionAmbiental(auth.user))

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/mediciones/')
    mediciones.value = data.results || data
  } finally {
    loading.value = false
  }
}

async function registrar() {
  if (!puedeRegistrar.value) return
  await api.post('/mediciones/', form.value)
  form.value = { temperatura: '', humedad: '', fecha: '', hora: '', ubicacion: 'Almacén principal' }
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader
      title="Control Ambiental"
      subtitle="Temperatura 20–25°C · Alertas automáticas e incidentes"
    />

    <div class="alert alert-info">
      <i class="bi bi-info-circle me-2"></i>
      Si la temperatura supera 20–25°C se genera alerta, incidente y acción correctiva automáticamente.
    </div>

    <div v-if="puedeRegistrar" class="card mb-4">
      <div class="card-body">
        <h6 class="fw-semibold mb-3">Registrar medición</h6>
        <div class="row g-3">
          <div class="col-md-2">
            <label class="form-label small">Temperatura °C</label>
            <input v-model="form.temperatura" type="number" step="0.1" class="form-control" />
          </div>
          <div class="col-md-2">
            <label class="form-label small">Humedad %</label>
            <input v-model="form.humedad" type="number" step="0.1" class="form-control" />
          </div>
          <div class="col-md-2">
            <label class="form-label small">Fecha</label>
            <input v-model="form.fecha" type="date" class="form-control" />
          </div>
          <div class="col-md-2">
            <label class="form-label small">Hora</label>
            <input v-model="form.hora" type="time" class="form-control" />
          </div>
          <div class="col-md-2">
            <label class="form-label small">Ubicación</label>
            <input v-model="form.ubicacion" class="form-control" />
          </div>
          <div class="col-md-2 d-flex align-items-end">
            <button class="btn btn-primary w-100" @click="registrar">Registrar</button>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="alert alert-light border small mb-4">
      <i class="bi bi-eye me-1"></i>
      Modo consulta: su rol puede ver mediciones e incidentes, pero no registrar nuevas mediciones.
    </div>

    <div class="card">
      <div class="card-body p-0">
        <div v-if="loading" class="text-center py-4"><div class="spinner-border text-primary"></div></div>
        <div v-else class="table-responsive">
          <table class="table table-hover mb-0">
            <thead class="table-light">
              <tr>
                <th>Fecha</th>
                <th>Hora</th>
                <th>Ubicación</th>
                <th class="text-end">Temp. °C</th>
                <th class="text-end">Humedad %</th>
                <th>Estado</th>
                <th>Responsable</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in mediciones" :key="m.id" :class="{ 'table-danger': m.fuera_rango }">
                <td>{{ m.fecha }}</td>
                <td>{{ m.hora }}</td>
                <td>{{ m.ubicacion }}</td>
                <td class="text-end">{{ m.temperatura }}</td>
                <td class="text-end">{{ m.humedad ?? '—' }}</td>
                <td>
                  <span class="badge" :class="m.fuera_rango ? 'bg-danger' : 'bg-success'">
                    {{ m.fuera_rango ? 'Fuera de rango' : 'Normal' }}
                  </span>
                </td>
                <td>{{ m.responsable_nombre || '—' }}</td>
              </tr>
              <tr v-if="!mediciones.length">
                <td colspan="7" class="text-center text-muted py-4">Sin mediciones registradas</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
