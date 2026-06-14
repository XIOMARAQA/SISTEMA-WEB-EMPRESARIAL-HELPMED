<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api/client'

const estado = ref({
  sms_habilitado: false,
  telefono: '',
  telefono_configurado: false,
})

const etiqueta = computed(() => {
  if (!estado.value.sms_habilitado) return 'SMS desactivado'
  if (!estado.value.telefono_configurado) return 'SMS: sin teléfono en perfil'
  return `SMS activo → ${estado.value.telefono}`
})

const clase = computed(() => {
  if (estado.value.sms_habilitado && estado.value.telefono_configurado) return 'sms-status--ok'
  if (estado.value.sms_habilitado) return 'sms-status--warn'
  return 'sms-status--muted'
})

onMounted(async () => {
  try {
    const { data } = await api.get('/notificaciones/sms-estado/')
    estado.value = data
  } catch {
    /* ignore */
  }
})
</script>

<template>
  <span class="sms-status-badge small" :class="clase" :title="etiqueta">
    <i class="bi bi-chat-dots"></i>
    {{ etiqueta }}
  </span>
</template>

<style scoped>
.sms-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-weight: 500;
  white-space: nowrap;
}

.sms-status--ok {
  background: #dcfce7;
  color: #166534;
}

.sms-status--warn {
  background: #fef9c3;
  color: #854d0e;
}

.sms-status--muted {
  background: #f1f5f9;
  color: #64748b;
}
</style>
