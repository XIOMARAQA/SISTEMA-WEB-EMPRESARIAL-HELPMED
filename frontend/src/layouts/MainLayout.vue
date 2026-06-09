<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { MAESTROS_MENU, maestrosVisibles } from '../config/maestros'
import { etiquetaRoles, esSuperAdmin, puedeVerRuta, tieneModulo } from '../config/roles'
import NotificationBell from '../components/NotificationBell.vue'



const route = useRoute()

const router = useRouter()

const auth = useAuthStore()



const maestrosOpen = ref(false)



const menu = [

  { to: '/', icon: 'bi-speedometer2', label: 'Dashboard', exact: true },

  { to: '/recepcion', icon: 'bi-box-seam', label: 'Recepción de Insumos' },

  { to: '/calidad', icon: 'bi-clipboard2-check', label: 'Control de Calidad' },

  { to: '/ambiental', icon: 'bi-thermometer-half', label: 'Control Ambiental' },

  { to: '/inventario', icon: 'bi-boxes', label: 'Control de Inventario' },

  { to: '/riesgos', icon: 'bi-shield-exclamation', label: 'Gestión ISO 27005' },

  { to: '/reportes', icon: 'bi-file-earmark-bar-graph', label: 'Reportes' },

  { to: '/auditoria', icon: 'bi-journal-text', label: 'Auditoría' },

]

const menuAdmin = [
  { to: '/usuarios', icon: 'bi-people', label: 'Usuarios' },
]



const userName = computed(() => {
  const u = auth.user
  if (!u) return ''
  return u.nombres ? `${u.nombres} ${u.apellidos || ''}`.trim() : u.username
})

const userRoleLabel = computed(() => etiquetaRoles(auth.user))

const showDashboard = computed(() => tieneModulo(auth.user, 'dashboard'))

const esAdmin = computed(() => esSuperAdmin(auth.user))

const menuVisible = computed(() =>
  menu.filter(item => item.exact || puedeVerRuta(auth.user, item.to))
)

const showMaestros = computed(() =>
  (esAdmin.value || (auth.user?.modulos_permitidos || []).includes('maestros'))
  && maestrosVisibles(auth.user).length > 0
)

const maestrosMenu = computed(() => maestrosVisibles(auth.user))



const isMaestrosActive = computed(() => route.path.startsWith('/datos-maestros'))



watch(isMaestrosActive, (active) => {

  if (active) maestrosOpen.value = true

}, { immediate: true })



function isActive(item) {

  if (item.exact) return route.path === item.to

  return route.path.startsWith(item.to)

}



function isSubActive(sub) {

  return route.path === sub.to

}



function toggleMaestros() {

  const willOpen = !maestrosOpen.value

  maestrosOpen.value = willOpen

  if (willOpen && !isMaestrosActive.value) {

    router.push(maestrosMenu.value[0]?.to || MAESTROS_MENU[0].to)

  }

}



function logout() {

  auth.logout()

  router.push({ name: 'login' })

}

onMounted(() => {
  if (auth.isAuthenticated) auth.fetchProfile().catch(() => {})
})

</script>



<template>

  <div class="d-flex">

    <aside class="sidebar d-flex flex-column">

      <div class="brand">

        <i class="bi bi-heart-pulse-fill text-info me-2"></i>

        HelpMed

        <div class="small text-muted fw-normal mt-1">Seguricel S.A.C.</div>

      </div>

      <nav class="nav flex-column py-2 flex-grow-1">

        <RouterLink
          v-if="showDashboard"
          :to="menu[0].to"
          class="nav-link"
          :class="{ active: isActive(menu[0]) }"
        >
          <i :class="['bi', menu[0].icon, 'me-2']"></i>{{ menu[0].label }}
        </RouterLink>



        <div v-if="showMaestros" class="nav-group">

          <button

            type="button"

            class="nav-link nav-toggle w-100"

            :class="{ active: isMaestrosActive, open: maestrosOpen }"

            @click="toggleMaestros"

          >

            <i class="bi bi-database me-2"></i>

            <span class="flex-grow-1 text-start">Datos Maestros</span>

            <i class="bi bi-chevron-down nav-chevron"></i>

          </button>

          <div v-show="maestrosOpen" class="nav-submenu">

            <RouterLink

              v-for="sub in maestrosMenu"

              :key="sub.to"

              :to="sub.to"

              class="nav-link nav-sublink"

              :class="{ active: isSubActive(sub) }"

            >

              <span class="sub-dot"></span>

              {{ sub.label }}

            </RouterLink>

          </div>

        </div>



        <RouterLink

          v-for="item in menuVisible.filter(i => !i.exact)"

          :key="item.to"

          :to="item.to"

          class="nav-link"

          :class="{ active: isActive(item) }"

        >

          <i :class="['bi', item.icon, 'me-2']"></i>{{ item.label }}

        </RouterLink>

        <template v-if="esAdmin">
          <div class="nav-divider my-2 mx-3 border-top border-secondary border-opacity-25"></div>
          <RouterLink
            v-for="item in menuAdmin"
            :key="item.to"
            :to="item.to"
            class="nav-link"
            :class="{ active: isActive(item) }"
          >
            <i :class="['bi', item.icon, 'me-2']"></i>{{ item.label }}
          </RouterLink>
        </template>

      </nav>

      <div class="p-3 border-top border-secondary border-opacity-25">
        <div class="small text-white fw-semibold mb-1">{{ userName }}</div>
        <div class="small text-white-50 mb-2 text-truncate" :title="userRoleLabel">{{ userRoleLabel }}</div>
        <button class="btn btn-outline-light btn-sm w-100" @click="logout">

          <i class="bi bi-box-arrow-right me-1"></i>Cerrar sesión

        </button>

      </div>

    </aside>

    <main class="main-content d-flex flex-column">
      <header class="app-topbar d-flex align-items-center justify-content-between px-4 py-2 gap-3">
        <div class="welcome-panel d-flex align-items-center gap-3 min-w-0">
          <div class="welcome-avatar">
            <i class="bi bi-person-fill"></i>
          </div>
          <div class="min-w-0">
            <div class="welcome-line text-truncate">
              Bienvenido, <strong>{{ userName }}</strong>
            </div>
            <div class="welcome-role text-truncate" :title="userRoleLabel">
              <i class="bi bi-shield-check me-1"></i>{{ userRoleLabel }}
            </div>
          </div>
        </div>
        <NotificationBell />
      </header>
      <div class="flex-grow-1 p-4 pt-2">
        <RouterView />
      </div>
    </main>

  </div>

</template>


