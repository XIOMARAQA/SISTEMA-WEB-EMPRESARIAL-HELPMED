from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from config.views import DashboardView
from reportes.views import ExportarReporteView
from seguridad.views import PerfilView, RolViewSet, UsuarioViewSet
from seguridad.serializers import CustomTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


router = DefaultRouter()
from logistica.views import (
    CategoriaViewSet, DetalleFacturaViewSet, DocumentoViewSet, MarcaViewSet,
    OrdenCompraViewSet, ProductoViewSet, ProveedorViewSet, SubcategoriaViewSet, UnidadMedidaViewSet,
)
from calidad.views import EvidenciaCalidadViewSet, IncidenciaCalidadViewSet, ResultadosControlCalidadView
from ambiental.views import AccionCorrectivaViewSet, MedicionViewSet
from inventario.views import InventarioViewSet, MovimientoInventarioViewSet
from riesgos.views import (
    ActivoViewSet, AmenazaViewSet, ControlISO27001ViewSet,
    EvaluacionRiesgoViewSet, RiesgoViewSet, TratamientoRiesgoViewSet, VulnerabilidadViewSet,
)
from auditoria.views import AuditoriaViewSet, RegistroAuditoriaViewSet
from notificaciones.views import NotificacionViewSet

router.register('marcas', MarcaViewSet)
router.register('unidades-medida', UnidadMedidaViewSet)
router.register('proveedores', ProveedorViewSet)
router.register('subcategorias', SubcategoriaViewSet)
router.register('categorias', CategoriaViewSet)
router.register('productos', ProductoViewSet)
router.register('ordenes-compra', OrdenCompraViewSet)
router.register('detalle-factura', DetalleFacturaViewSet)
router.register('documentos', DocumentoViewSet)
router.register('incidencias-calidad', IncidenciaCalidadViewSet)
router.register('evidencias-calidad', EvidenciaCalidadViewSet)
router.register('mediciones', MedicionViewSet)
router.register('acciones-correctivas', AccionCorrectivaViewSet)
router.register('inventarios', InventarioViewSet)
router.register('movimientos-inventario', MovimientoInventarioViewSet)
router.register('activos', ActivoViewSet)
router.register('amenazas', AmenazaViewSet)
router.register('vulnerabilidades', VulnerabilidadViewSet)
router.register('riesgos', RiesgoViewSet)
router.register('evaluaciones-riesgo', EvaluacionRiesgoViewSet)
router.register('tratamientos-riesgo', TratamientoRiesgoViewSet)
router.register('controles-iso27001', ControlISO27001ViewSet)
router.register('auditorias', AuditoriaViewSet)
router.register('registros-auditoria', RegistroAuditoriaViewSet)
router.register('usuarios', UsuarioViewSet)
router.register('roles', RolViewSet)
router.register('notificaciones', NotificacionViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/perfil/', PerfilView.as_view(), name='perfil'),
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('api/reportes/<str:tipo>/', ExportarReporteView.as_view(), name='exportar_reporte'),
    path('api/control-calidad/resultados/', ResultadosControlCalidadView.as_view(), name='control_calidad_resultados'),
    path('api/', include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
