<script setup>
import { ref, watch } from 'vue'
import api from '../api/client'

const props = defineProps({
  show: { type: Boolean, default: false },
  initialRuc: { type: String, default: '' },
  initialRazonSocial: { type: String, default: '' },
  initialDireccion: { type: String, default: '' },
  autoConsultarSunat: { type: Boolean, default: true },
})

const emit = defineEmits(['close', 'created'])

const error = ref('')
const saving = ref(false)
const consultandoRuc = ref(false)
const rucError = ref('')
const sunatInfo = ref(null)

const form = ref({
  ruc: '',
  razon_social: '',
  direccion: '',
  telefono: '',
  email: '',
  contacto: '',
})

function resetForm() {
  form.value = {
    ruc: props.initialRuc || '',
    razon_social: props.initialRazonSocial || '',
    direccion: props.initialDireccion || '',
    telefono: '',
    email: '',
    contacto: '',
  }
  error.value = ''
  rucError.value = ''
  sunatInfo.value = null
}

watch(() => props.show, async (v) => {
  if (!v) return
  resetForm()
  if (props.autoConsultarSunat && /^\d{11}$/.test(form.value.ruc)) {
    await consultarRuc(true)
  }
})

async function consultarRuc(silent = false) {
  rucError.value = ''
  sunatInfo.value = null
  if (!/^\d{11}$/.test(form.value.ruc)) {
    if (!silent) rucError.value = 'Ingrese un RUC válido de 11 dígitos.'
    return
  }
  consultandoRuc.value = true
  try {
    const { data } = await api.get('/proveedores/consultar-ruc/', { params: { ruc: form.value.ruc } })
    form.value.razon_social = data.razon_social || form.value.razon_social
    form.value.direccion = data.direccion || form.value.direccion
    sunatInfo.value = data
    if (data.ya_registrado && data.proveedor_id) {
      emit('created', {
        id: data.proveedor_id,
        ruc: data.ruc,
        razon_social: data.razon_social,
      })
      emit('close')
    }
  } catch (e) {
    if (!silent) rucError.value = e.response?.data?.detail || 'No se pudo consultar SUNAT.'
  } finally {
    consultandoRuc.value = false
  }
}

async function guardar() {
  error.value = ''
  if (!form.value.ruc.trim() || !form.value.razon_social.trim()) {
    error.value = 'RUC y razón social son obligatorios.'
    return
  }
  saving.value = true
  try {
    const { data } = await api.post('/proveedores/', form.value)
    emit('created', data)
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || e.response?.data?.ruc?.[0] || 'No se pudo guardar.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="show" class="modal d-block" tabindex="-1" style="background:rgba(0,0,0,.55); z-index:1060">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title"><i class="bi bi-building me-2"></i>Nuevo proveedor</h5>
          <button type="button" class="btn-close" @click="emit('close')"></button>
        </div>
        <div class="modal-body">
          <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>
          <div class="row g-3">
            <div class="col-md-5">
              <label class="form-label">RUC *</label>
              <div class="input-group">
                <input v-model="form.ruc" class="form-control" maxlength="11" />
                <button
                  class="btn btn-outline-primary"
                  type="button"
                  :disabled="consultandoRuc"
                  @click="consultarRuc(false)"
                >
                  {{ consultandoRuc ? '...' : 'SUNAT' }}
                </button>
              </div>
              <div v-if="rucError" class="text-danger small mt-1">{{ rucError }}</div>
              <div v-if="sunatInfo?.estado_sunat" class="text-muted small mt-1">
                Estado: {{ sunatInfo.estado_sunat }} — {{ sunatInfo.condicion_sunat }}
              </div>
            </div>
            <div class="col-md-7">
              <label class="form-label">Razón social *</label>
              <input v-model="form.razon_social" class="form-control" />
            </div>
            <div class="col-12">
              <label class="form-label">Dirección</label>
              <input v-model="form.direccion" class="form-control" />
            </div>
            <div class="col-md-4">
              <label class="form-label">Contacto</label>
              <input v-model="form.contacto" class="form-control" />
            </div>
            <div class="col-md-4">
              <label class="form-label">Teléfono</label>
              <input v-model="form.telefono" class="form-control" />
            </div>
            <div class="col-md-4">
              <label class="form-label">Email</label>
              <input v-model="form.email" type="email" class="form-control" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="emit('close')">Cancelar</button>
          <button class="btn btn-primary" :disabled="saving" @click="guardar">
            {{ saving ? 'Guardando...' : 'Guardar proveedor' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
