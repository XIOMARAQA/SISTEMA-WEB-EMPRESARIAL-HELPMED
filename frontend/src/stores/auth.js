import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('access_token'))
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const loading = ref(false)
  const error = ref('')

  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(username, email, password) {
    loading.value = true
    error.value = ''
    try {
      const { data } = await api.post('/auth/login/', { username, email, password })
      accessToken.value = data.access
      localStorage.setItem('access_token', data.access)
      localStorage.setItem('refresh_token', data.refresh)
      localStorage.setItem('user', JSON.stringify(data.user))
      user.value = data.user
      await fetchProfile()
      return true
    } catch (err) {
      if (!err.response) {
        error.value = 'No se pudo conectar con el servidor. Verifique que el backend esté en ejecución.'
        return false
      }
      const detail = err.response?.data?.detail
      error.value = (Array.isArray(detail) ? detail[0] : detail)
        || err.response?.data?.non_field_errors?.[0]
        || Object.values(err.response?.data || {})?.flat()?.[0]
        || 'Credenciales inválidas'
      return false
    } finally {
      loading.value = false
    }
  }

  function logout() {
    accessToken.value = null
    user.value = null
    localStorage.clear()
  }

  function syncFromStorage() {
    accessToken.value = localStorage.getItem('access_token')
    user.value = JSON.parse(localStorage.getItem('user') || 'null')
  }

  async function fetchProfile() {
    const { data } = await api.get('/auth/perfil/')
    user.value = data
    localStorage.setItem('user', JSON.stringify(data))
  }

  return {
    user, loading, error, accessToken, isAuthenticated,
    login, logout, fetchProfile, syncFromStorage,
  }
})
