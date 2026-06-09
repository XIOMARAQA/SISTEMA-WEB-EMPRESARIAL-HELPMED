import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'
import './assets/main.css'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const pinia = createPinia()
const app = createApp(App)
app.use(pinia)

async function bootstrap() {
  const auth = useAuthStore()
  if (auth.isAuthenticated) {
    try {
      await auth.fetchProfile()
    } catch {
      auth.logout()
    }
  }
  app.use(router)
  await router.isReady()
  app.mount('#app')
}

bootstrap()
