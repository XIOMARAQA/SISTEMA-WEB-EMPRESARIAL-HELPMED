<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { rutaInicioPorRol } from '../config/roles'

const username = ref('')
const email = ref('')
const password = ref('')
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  const ok = await auth.login(username.value, email.value, password.value)
  if (ok) router.push(rutaInicioPorRol(auth.user))
}
</script>

<template>
  <div class="login-bg d-flex align-items-center justify-content-center p-3">
    <div class="login-card">
      <div class="card shadow-lg border-0">
        <div class="card-body p-4 p-md-5">
          <div class="text-center mb-4">
            <i class="bi bi-heart-pulse-fill text-primary display-4"></i>
            <h1 class="h3 fw-bold mt-2">HelpMed</h1>
            <p class="text-muted">Sistema de Logística Médica — Seguricel S.A.C.</p>
          </div>
          <form @submit.prevent="submit">
            <div v-if="auth.error" class="alert alert-danger py-2">{{ auth.error }}</div>
            <div class="mb-3">
              <label class="form-label">Usuario</label>
              <input v-model="username" type="text" class="form-control form-control-lg" required autofocus autocomplete="username" />
            </div>
            <div class="mb-3">
              <label class="form-label">Correo</label>
              <input v-model="email" type="email" class="form-control form-control-lg" required autocomplete="email" />
            </div>
            <div class="mb-4">
              <label class="form-label">Contraseña</label>
              <input v-model="password" type="password" class="form-control form-control-lg" required autocomplete="current-password" />
            </div>
            <button type="submit" class="btn btn-primary btn-lg w-100" :disabled="auth.loading">
              <span v-if="auth.loading" class="spinner-border spinner-border-sm me-2"></span>
              Ingresar
            </button>
          </form>
          <p class="text-center text-muted small mt-4 mb-0">
            ISO/IEC 27005 · Gestión de Riesgos de Seguridad
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
