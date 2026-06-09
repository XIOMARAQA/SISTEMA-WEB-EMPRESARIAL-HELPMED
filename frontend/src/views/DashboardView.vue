<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
import { useAuthStore } from '../stores/auth'
import { verSeccionLogistica, verSeccionRiesgos } from '../config/roles'

const auth = useAuthStore()
const data = ref(null)
const loading = ref(true)

const mostrarLogistica = computed(() => verSeccionLogistica(auth.user))
const mostrarRiesgos = computed(() => verSeccionRiesgos(auth.user))

const subtitulo = computed(() => {
  if (mostrarLogistica.value && mostrarRiesgos.value) {
    return 'Indicadores de logística médica y seguridad de la información'
  }
  if (mostrarRiesgos.value) return 'Indicadores de seguridad de la información — ISO/IEC 27005'
  return 'Indicadores de logística médica — Seguricel S.A.C.'
})

onMounted(async () => {
  try {
    const { data: res } = await api.get('/dashboard/')
    data.value = res
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <PageHeader title="Dashboard Gerencial" :subtitle="subtitulo" />

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <template v-else-if="data">
      <template v-if="mostrarRiesgos">
        <h5 class="fw-semibold mb-1">Matriz de Riesgos ISO/IEC 27005</h5>
        <p class="text-muted small mb-3">
          Riesgos <strong>inherentes</strong> por nivel (Probabilidad × Impacto).
        </p>
        <div class="row g-3 mb-4">
          <div class="col-6 col-md-3">
            <StatCard label="Críticos" hint="Valor 16–25" :value="data.riesgos.criticos" icon="bi-exclamation-octagon-fill" variant="critico" />
          </div>
          <div class="col-6 col-md-3">
            <StatCard label="Altos" hint="Valor 11–15" :value="data.riesgos.altos" icon="bi-exclamation-triangle-fill" variant="alto" />
          </div>
          <div class="col-6 col-md-3">
            <StatCard label="Medios" hint="Valor 6–10" :value="data.riesgos.medios" icon="bi-exclamation-circle" variant="medio" />
          </div>
          <div class="col-6 col-md-3">
            <StatCard label="Bajos" hint="Valor 1–5" :value="data.riesgos.bajos" icon="bi-check-circle" variant="bajo" />
          </div>
        </div>
      </template>

      <div v-if="mostrarLogistica || mostrarRiesgos" class="row g-3 mb-4">
        <div v-if="mostrarRiesgos" class="col-md-3">
          <StatCard label="Activos críticos" hint="Criticidad máxima" :value="data.activos_criticos" icon="bi-hdd-stack" />
        </div>
        <div v-if="mostrarRiesgos" class="col-md-3">
          <StatCard label="Vulnerabilidades abiertas" hint="Abiertas o en tratamiento" :value="data.vulnerabilidades_abiertas" icon="bi-bug" />
        </div>
        <div v-if="mostrarLogistica" class="col-md-3">
          <StatCard label="Órdenes pendientes" hint="Estado P" :value="data.ordenes_pendientes" icon="bi-box-seam" />
        </div>
        <div v-if="mostrarLogistica" class="col-md-3">
          <StatCard label="Por vencer (30 días)" hint="Vencimiento próximo" :value="data.productos_por_vencer" icon="bi-calendar-x" />
        </div>
      </div>

      <div v-if="mostrarLogistica && !mostrarRiesgos" class="row g-3">
        <div class="col-12">
          <div class="card">
            <div class="card-body text-center text-muted py-5">
              <i class="bi bi-box-seam display-6 d-block mb-2"></i>
              Use el menú lateral para acceder a los módulos de logística asignados a su rol.
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
