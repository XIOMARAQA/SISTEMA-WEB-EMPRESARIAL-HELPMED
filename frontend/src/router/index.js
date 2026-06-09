import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { puedeVerRuta, rutaInicioPorRol, esSuperAdmin } from '../config/roles'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
      { path: 'datos-maestros', redirect: '/datos-maestros/productos' },
      { path: 'datos-maestros/productos', name: 'maestros-productos', component: () => import('../views/maestros/ProductosView.vue') },
      {
        path: 'datos-maestros/categorias',
        name: 'maestros-categorias',
        component: () => import('../views/maestros/CategoriasView.vue'),
      },
      {
        path: 'datos-maestros/subcategorias',
        name: 'maestros-subcategorias',
        component: () => import('../views/maestros/SubcategoriasView.vue'),
      },
      {
        path: 'datos-maestros/marcas',
        name: 'maestros-marcas',
        component: () => import('../views/maestros/SimpleMaestroView.vue'),
        meta: { maestroKey: 'marcas' },
      },
      {
        path: 'datos-maestros/unidades',
        name: 'maestros-unidades',
        component: () => import('../views/maestros/SimpleMaestroView.vue'),
        meta: { maestroKey: 'unidades' },
      },
      { path: 'datos-maestros/proveedores', name: 'maestros-proveedores', component: () => import('../views/maestros/ProveedoresView.vue') },
      { path: 'recepcion', name: 'recepcion', component: () => import('../views/RecepcionView.vue') },
      { path: 'calidad', name: 'calidad', component: () => import('../views/CalidadView.vue') },
      { path: 'ambiental', name: 'ambiental', component: () => import('../views/AmbientalView.vue') },
      { path: 'inventario', name: 'inventario', component: () => import('../views/InventarioView.vue') },
      { path: 'riesgos', name: 'riesgos', component: () => import('../views/RiesgosView.vue') },
      { path: 'reportes', name: 'reportes', component: () => import('../views/ReportesView.vue') },
      { path: 'auditoria', name: 'auditoria', component: () => import('../views/AuditoriaView.vue') },
      {
        path: 'usuarios',
        name: 'usuarios',
        component: () => import('../views/UsuariosView.vue'),
        meta: { requiresAdmin: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return rutaInicioPorRol(auth.user)
  }
  if (to.meta.requiresAdmin && !esSuperAdmin(auth.user)) {
    return { name: 'dashboard' }
  }
  if (to.meta.requiresAuth && auth.user && !puedeVerRuta(auth.user, to.path)) {
    return rutaInicioPorRol(auth.user)
  }
})

export default router
