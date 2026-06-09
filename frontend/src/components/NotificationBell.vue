<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/client'

const router = useRouter()
const abierto = ref(false)
const cargando = ref(false)
const noLeidas = ref(0)
const notificaciones = ref([])
const panelRef = ref(null)
const btnRef = ref(null)
const detalleAbierto = ref(false)
const notificacionSeleccionada = ref(null)

let intervalo = null

const prioridadClase = {
  baja: 'text-secondary',
  media: 'text-primary',
  alta: 'text-warning',
  critica: 'text-danger fw-bold',
}

const tipoIcono = {
  inventario: 'bi-boxes',
  ambiental: 'bi-thermometer-half',
  calidad: 'bi-clipboard2-check',
  riesgo: 'bi-shield-exclamation',
  seguridad: 'bi-shield-lock',
  sistema: 'bi-bell',
}

async function cargar() {
  try {
    const { data } = await api.get('/notificaciones/resumen/')
    noLeidas.value = data.no_leidas
    notificaciones.value = data.notificaciones || []
  } catch {
    /* sesión expirada u offline */
  }
}

async function marcarLeida(n, ir = false) {
  if (!n.leida) {
    try {
      await api.post(`/notificaciones/${n.id}/marcar-leida/`)
      n.leida = true
      noLeidas.value = Math.max(0, noLeidas.value - 1)
    } catch { /* ignore */ }
  }
  if (ir && n.enlace) {
    abierto.value = false
    cerrarDetalle()
    router.push(n.enlace)
  }
}

async function abrirDetalle(n) {
  await marcarLeida(n, false)
  notificacionSeleccionada.value = n
  detalleAbierto.value = true
}

function cerrarDetalle() {
  detalleAbierto.value = false
  notificacionSeleccionada.value = null
}

function irDesdeDetalle() {
  const n = notificacionSeleccionada.value
  if (!n?.enlace) return
  abierto.value = false
  cerrarDetalle()
  router.push(n.enlace)
}

async function marcarTodas() {
  cargando.value = true
  try {
    await api.post('/notificaciones/marcar-todas-leidas/')
    notificaciones.value.forEach(n => { n.leida = true })
    noLeidas.value = 0
  } finally {
    cargando.value = false
  }
}

function togglePanel() {
  abierto.value = !abierto.value
  if (abierto.value) cargar()
}

function cerrarSiClickFuera(e) {
  if (!abierto.value) return
  if (panelRef.value?.contains(e.target) || btnRef.value?.contains(e.target)) return
  abierto.value = false
}

function fmtFecha(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const hoy = new Date()
  if (d.toDateString() === hoy.toDateString()) {
    return d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('es-PE', { day: '2-digit', month: 'short' })
}

function fmtFechaCompleta(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('es-PE', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const etiquetaModulo = {
  recepcion: 'Recepción de insumos',
  calidad: 'Control de calidad',
  inventario: 'Inventario',
  ambiental: 'Control ambiental',
  reportes: 'Reportes',
}

const hayNotificaciones = computed(() => notificaciones.value.length > 0)

onMounted(() => {
  cargar()
  intervalo = setInterval(cargar, 45000)
  document.addEventListener('click', cerrarSiClickFuera)
})

onUnmounted(() => {
  if (intervalo) clearInterval(intervalo)
  document.removeEventListener('click', cerrarSiClickFuera)
})
</script>

<template>
  <div class="notif-bell position-relative">
    <button
      ref="btnRef"
      type="button"
      class="btn btn-light btn-notif position-relative"
      title="Notificaciones"
      aria-label="Notificaciones"
      @click.stop="togglePanel"
    >
      <i class="bi bi-bell fs-5"></i>
      <span
        v-if="noLeidas > 0"
        class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger notif-badge"
      >
        {{ noLeidas > 99 ? '99+' : noLeidas }}
      </span>
    </button>

    <div
      v-show="abierto"
      ref="panelRef"
      class="notif-panel shadow-lg"
      @click.stop
    >
      <div class="notif-panel-header d-flex align-items-center justify-content-between">
        <span class="fw-semibold">Notificaciones</span>
        <button
          v-if="noLeidas > 0"
          type="button"
          class="btn btn-link btn-sm p-0 text-decoration-none"
          :disabled="cargando"
          @click="marcarTodas"
        >
          Marcar todas leídas
        </button>
      </div>

      <div class="notif-panel-body">
        <div v-if="!hayNotificaciones" class="text-center text-muted py-4 small">
          <i class="bi bi-bell-slash d-block fs-3 mb-2 opacity-50"></i>
          Sin notificaciones
        </div>
        <button
          v-for="n in notificaciones"
          :key="n.id"
          type="button"
          class="notif-item w-100 text-start border-0"
          :class="{ 'notif-item--unread': !n.leida }"
          @click="abrirDetalle(n)"
        >
          <div class="d-flex gap-2">
            <i :class="['bi', tipoIcono[n.tipo] || 'bi-bell', 'notif-item-icon', prioridadClase[n.prioridad]]"></i>
            <div class="flex-grow-1 min-w-0">
              <div class="d-flex justify-content-between gap-2">
                <span class="notif-item-title">{{ n.titulo }}</span>
                <span class="notif-item-time text-muted">{{ fmtFecha(n.creado_en) }}</span>
              </div>
              <p class="notif-item-msg mb-0">{{ n.mensaje }}</p>
            </div>
          </div>
        </button>
      </div>
    </div>

    <div
      v-if="detalleAbierto && notificacionSeleccionada"
      class="notif-detalle-backdrop"
      @click.self="cerrarDetalle"
    >
      <div class="notif-detalle-modal shadow-lg" role="dialog" aria-modal="true">
        <div class="notif-detalle-header d-flex align-items-start gap-2">
          <i
            :class="[
              'bi',
              tipoIcono[notificacionSeleccionada.tipo] || 'bi-bell',
              'notif-detalle-icon',
              prioridadClase[notificacionSeleccionada.prioridad],
            ]"
          ></i>
          <div class="flex-grow-1 min-w-0">
            <h6 class="notif-detalle-title mb-1">{{ notificacionSeleccionada.titulo }}</h6>
            <span class="notif-detalle-time text-muted">{{ fmtFechaCompleta(notificacionSeleccionada.creado_en) }}</span>
          </div>
          <button
            type="button"
            class="btn-close btn-close-sm"
            aria-label="Cerrar"
            @click="cerrarDetalle"
          ></button>
        </div>
        <div class="notif-detalle-body">
          <p class="notif-detalle-msg mb-0">{{ notificacionSeleccionada.mensaje }}</p>
        </div>
        <div class="notif-detalle-footer d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-sm btn-outline-secondary" @click="cerrarDetalle">
            Cerrar
          </button>
          <button
            v-if="notificacionSeleccionada.enlace"
            type="button"
            class="btn btn-sm btn-primary"
            @click="irDesdeDetalle"
          >
            Ir a {{ etiquetaModulo[notificacionSeleccionada.referencia_modulo] || 'módulo' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.btn-notif {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.notif-badge {
  font-size: 0.65rem;
  min-width: 1.1rem;
}

.notif-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: min(380px, calc(100vw - 2rem));
  background: #fff;
  border-radius: 0.75rem;
  border: 1px solid #e2e8f0;
  z-index: 1050;
  overflow: hidden;
}

.notif-panel-header {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
}

.notif-panel-body {
  max-height: 420px;
  overflow-y: auto;
}

.notif-item {
  padding: 0.75rem 1rem;
  background: transparent;
  border-bottom: 1px solid #f1f5f9 !important;
  cursor: pointer;
  transition: background 0.15s;
}

.notif-item:hover {
  background: #f8fafc;
}

.notif-item--unread {
  background: #eff6ff;
}

.notif-item--unread:hover {
  background: #dbeafe;
}

.notif-item-icon {
  font-size: 1.1rem;
  margin-top: 0.15rem;
  flex-shrink: 0;
}

.notif-item-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #1e293b;
}

.notif-item-time {
  font-size: 0.7rem;
  white-space: nowrap;
}

.notif-item-msg {
  font-size: 0.78rem;
  color: #64748b;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notif-detalle-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 1060;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.notif-detalle-modal {
  width: min(480px, 100%);
  background: #fff;
  border-radius: 0.75rem;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.notif-detalle-header {
  padding: 1rem 1rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
}

.notif-detalle-icon {
  font-size: 1.35rem;
  margin-top: 0.1rem;
  flex-shrink: 0;
}

.notif-detalle-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1e293b;
}

.notif-detalle-time {
  font-size: 0.75rem;
}

.notif-detalle-body {
  padding: 1rem;
  max-height: min(50vh, 320px);
  overflow-y: auto;
}

.notif-detalle-msg {
  font-size: 0.9rem;
  color: #475569;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.notif-detalle-footer {
  padding: 0.75rem 1rem;
  border-top: 1px solid #f1f5f9;
  background: #fafafa;
}
</style>
