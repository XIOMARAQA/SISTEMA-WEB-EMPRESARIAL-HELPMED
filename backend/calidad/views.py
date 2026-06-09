from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from calidad.models import EvidenciaCalidad, IncidenciaCalidad
from calidad.services.permisos import permisos_vista_resultados
from calidad.services.resultados import obtener_resultados_control_calidad
from seguridad.actores import puede_ejecutar_control_calidad


class EvidenciaCalidadListSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = EvidenciaCalidad
        fields = ('id', 'nombre', 'url', 'descripcion', 'creado_en')

    def get_url(self, obj):
        request = self.context.get('request')
        if obj.archivo and request:
            return request.build_absolute_uri(obj.archivo.url)
        return ''


class IncidenciaCalidadSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True, default=None)
    detalle_descripcion = serializers.CharField(source='detalle_factura.descripcion', read_only=True, default=None)
    numero_factura = serializers.SerializerMethodField()
    evidencias = EvidenciaCalidadListSerializer(many=True, read_only=True)

    class Meta:
        model = IncidenciaCalidad
        fields = '__all__'
        read_only_fields = ('registrado_por',)

    def get_numero_factura(self, obj):
        if obj.orden_id:
            return obj.orden.numero_completo
        return None

    def validate(self, attrs):
        if not attrs.get('producto') and not attrs.get('detalle_factura'):
            raise serializers.ValidationError('Indique producto o ítem de la orden.')
        return attrs


class EvidenciaCalidadSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = EvidenciaCalidad
        fields = '__all__'
        read_only_fields = ('subido_por',)

    def get_url(self, obj):
        request = self.context.get('request')
        if obj.archivo and request:
            return request.build_absolute_uri(obj.archivo.url)
        return ''


class ResultadosControlCalidadView(APIView):
    """Productos aceptados y rechazados tras control de calidad, filtrado por rol."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        permisos = permisos_vista_resultados(request.user)
        aceptados, rechazados = obtener_resultados_control_calidad(request)

        if not permisos['aceptados']:
            aceptados = []
        if not permisos['rechazados']:
            rechazados = []

        return Response({
            'permisos': permisos,
            'aceptados': aceptados,
            'rechazados': rechazados,
            'totales': {
                'aceptados': len(aceptados),
                'rechazados': len(rechazados),
            },
        })


class IncidenciaCalidadViewSet(viewsets.ModelViewSet):
    queryset = IncidenciaCalidad.objects.select_related(
        'producto', 'registrado_por', 'orden', 'detalle_factura',
    ).prefetch_related('evidencias').order_by('-creado_en')
    serializer_class = IncidenciaCalidadSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        permisos = permisos_vista_resultados(self.request.user)
        if not permisos['rechazados']:
            return qs.none()
        return qs

    def create(self, request, *args, **kwargs):
        if not puede_ejecutar_control_calidad(request.user):
            return Response(
                {'detail': 'Solo control de calidad puede registrar incidencias.'},
                status=403,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)


class EvidenciaCalidadViewSet(viewsets.ModelViewSet):
    queryset = EvidenciaCalidad.objects.select_related('incidencia')
    serializer_class = EvidenciaCalidadSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def create(self, request, *args, **kwargs):
        if not puede_ejecutar_control_calidad(request.user):
            return Response(
                {'detail': 'Solo control de calidad puede adjuntar evidencias.'},
                status=403,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(subido_por=self.request.user)
