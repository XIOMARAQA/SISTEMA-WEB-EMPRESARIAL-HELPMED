from django.db.models import Count, F
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ambiental.models import Medicion
from inventario.models import Inventario
from logistica.models import OrdenCompra
from riesgos.models import Activo, EvaluacionRiesgo, Vulnerabilidad
from seguridad.serializers import UsuarioSerializer


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        hoy = timezone.now().date()
        evaluaciones = EvaluacionRiesgo.objects.filter(tipo='inherente')
        riesgos_por_nivel = evaluaciones.values('nivel').annotate(total=Count('id'))
        niveles = {item['nivel']: item['total'] for item in riesgos_por_nivel}

        total_evaluados = evaluaciones.count()
        criticos = niveles.get('critico', 0)
        pct_criticos = round((criticos / total_evaluados * 100), 1) if total_evaluados else 0

        alertas = Inventario.objects.filter(
            cantidad__gt=0,
            producto__stock_minimo__gt=0,
            cantidad__lte=F('producto__stock_minimo'),
        ).select_related('producto')[:10]

        return Response({
            'usuario': UsuarioSerializer(request.user).data,
            'riesgos': {
                'criticos': criticos,
                'altos': niveles.get('alto', 0),
                'medios': niveles.get('medio', 0),
                'bajos': niveles.get('bajo', 0),
                'porcentaje_criticos': pct_criticos,
            },
            'activos_criticos': Activo.objects.filter(criticidad='critica', activo=True).count(),
            'vulnerabilidades_abiertas': Vulnerabilidad.objects.filter(
                estado__in=['abierta', 'en_tratamiento']
            ).count(),
            'ordenes_pendientes': OrdenCompra.objects.filter(estado='pendiente').count(),
            'mediciones_fuera_rango': Medicion.objects.filter(fuera_rango=True).count(),
            'productos_por_vencer': Inventario.objects.filter(
                fecha_vencimiento__lte=hoy + timezone.timedelta(days=30),
                fecha_vencimiento__gte=hoy,
                cantidad__gt=0,
            ).count(),
            'alertas_inventario': [
                {
                    'codigo': a.producto.codigo,
                    'nombre': a.producto.nombre,
                    'cantidad': float(a.cantidad),
                    'clasificacion': a.clasificacion,
                }
                for a in alertas
            ],
        })
