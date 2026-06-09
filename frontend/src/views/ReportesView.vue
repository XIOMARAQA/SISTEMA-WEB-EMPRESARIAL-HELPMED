<script setup>
import { ref } from 'vue'
import api from '../api/client'
import PageHeader from '../components/PageHeader.vue'

const reportes = [
  {
    id: 'matriz-riesgos',
    titulo: 'Matriz de Riesgos ISO 27005',
    desc: 'Mapa de calor y clasificación por nivel',
    icon: 'bi-grid-3x3-gap',
    pdf: true,
    excel: true,
  },
  {
    id: 'inventario',
    titulo: 'Inventario y Kardex',
    desc: 'Stock, movimientos y productos por vencer',
    icon: 'bi-boxes',
    pdf: false,
    excel: true,
  },
  {
    id: 'ambiental',
    titulo: 'Control Ambiental',
    desc: 'Mediciones, alertas e incidentes',
    icon: 'bi-thermometer-half',
    pdf: true,
    excel: true,
  },
  {
    id: 'auditoria',
    titulo: 'Auditoría del Sistema',
    desc: 'Registro de acciones y trazabilidad',
    icon: 'bi-journal-text',
    pdf: true,
    excel: true,
  },
]

const exportando = ref('')
const error = ref('')

async function exportar(id, formato) {
  const key = `${id}-${formato}`
  exportando.value = key
  error.value = ''
  try {
    const { data, headers } = await api.get(`/reportes/${id}/`, {
      params: { formato },
      responseType: 'blob',
    })
    const disposition = headers['content-disposition'] || ''
    const match = disposition.match(/filename="?([^"]+)"?/)
    const nombre = match?.[1] || `helpmed_${id}.${formato === 'pdf' ? 'pdf' : 'xlsx'}`
    const url = window.URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = nombre
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    if (e.response?.data instanceof Blob) {
      try {
        const texto = await e.response.data.text()
        const json = JSON.parse(texto)
        error.value = json.detail || 'No se pudo exportar el reporte.'
      } catch {
        error.value = 'No se pudo exportar el reporte.'
      }
    } else {
      error.value = e.response?.data?.detail || 'No se pudo exportar el reporte.'
    }
  } finally {
    exportando.value = ''
  }
}

function estaExportando(id, formato) {
  return exportando.value === `${id}-${formato}`
}
</script>

<template>
  <div>
    <PageHeader title="Reportes" subtitle="Exportación PDF y Excel — indicadores gerenciales" />

    <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>

    <div class="row g-3">
      <div v-for="r in reportes" :key="r.id" class="col-md-6 col-lg-4">
        <div class="card h-100">
          <div class="card-body">
            <div class="d-flex align-items-start gap-3">
              <div class="text-primary fs-3"><i :class="['bi', r.icon]"></i></div>
              <div class="flex-grow-1">
                <h6 class="fw-semibold">{{ r.titulo }}</h6>
                <p class="text-muted small mb-2">{{ r.desc }}</p>
                <span class="badge bg-light text-dark">
                  {{ [r.pdf && 'PDF', r.excel && 'Excel'].filter(Boolean).join(' / ') }}
                </span>
              </div>
            </div>
            <div class="mt-3 d-flex gap-2">
              <button
                v-if="r.pdf"
                class="btn btn-sm btn-outline-danger"
                :disabled="!!exportando"
                @click="exportar(r.id, 'pdf')"
              >
                <span v-if="estaExportando(r.id, 'pdf')" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-file-pdf me-1"></i>PDF
              </button>
              <button
                v-if="r.excel"
                class="btn btn-sm btn-outline-success"
                :disabled="!!exportando"
                @click="exportar(r.id, 'excel')"
              >
                <span v-if="estaExportando(r.id, 'excel')" class="spinner-border spinner-border-sm me-1"></span>
                <i v-else class="bi bi-file-earmark-excel me-1"></i>Excel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
