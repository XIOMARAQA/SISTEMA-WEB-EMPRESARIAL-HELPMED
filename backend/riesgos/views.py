from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from reportes.builders import exportar_gestion_riesgos_excel

from riesgos.models import (
    Activo,
    Amenaza,
    ControlISO27001,
    EvaluacionRiesgo,
    Riesgo,
    TratamientoRiesgo,
    Vulnerabilidad,
)


class RiesgosViewSetMixin:
    """Catálogos ISO 27005: listas completas sin paginar (volúmenes pequeños)."""
    pagination_class = None


class BajaLogicaMixin:
    """DELETE vía API también aplica baja lógica (no borrado físico)."""
    baja_logica_campos: tuple[str, object] = ('activo', False)

    def perform_destroy(self, instance):
        campo, valor = self.baja_logica_campos
        setattr(instance, campo, valor)
        instance.save(update_fields=[campo])


class ActivoSerializer(serializers.ModelSerializer):
    propietario_nombre = serializers.CharField(source='propietario.username', read_only=True)

    class Meta:
        model = Activo
        fields = '__all__'
        read_only_fields = ('codigo', 'propietario')

    def create(self, validated_data):
        clasificacion = validated_data['clasificacion']
        validated_data['codigo'] = Activo.obtener_siguiente_codigo(clasificacion)
        if 'propietario' not in validated_data:
            validated_data['propietario'] = self.context['request'].user
        return super().create(validated_data)


class AmenazaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenaza
        fields = '__all__'
        read_only_fields = ('codigo',)

    def create(self, validated_data):
        validated_data['codigo'] = Amenaza.obtener_siguiente_codigo()
        return super().create(validated_data)


class VulnerabilidadSerializer(serializers.ModelSerializer):
    activo_nombre = serializers.CharField(source='activo.nombre', read_only=True)
    descripcion = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Vulnerabilidad
        fields = '__all__'
        read_only_fields = ('codigo',)

    def create(self, validated_data):
        validated_data['codigo'] = Vulnerabilidad.obtener_siguiente_codigo()
        descripcion = (validated_data.get('descripcion') or '').strip()
        if not descripcion:
            validated_data['descripcion'] = validated_data['nombre']
        return super().create(validated_data)


class RiesgoSerializer(serializers.ModelSerializer):
    activo_nombre = serializers.CharField(source='activo.nombre', read_only=True)
    amenaza_nombre = serializers.CharField(source='amenaza.nombre', read_only=True)
    descripcion = serializers.CharField(required=False, allow_blank=True)
    vulnerabilidad = serializers.PrimaryKeyRelatedField(
        queryset=Vulnerabilidad.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Riesgo
        fields = '__all__'
        read_only_fields = ('codigo',)

    def create(self, validated_data):
        validated_data['codigo'] = Riesgo.obtener_siguiente_codigo()
        descripcion = (validated_data.get('descripcion') or '').strip()
        if not descripcion:
            activo = validated_data['activo']
            amenaza = validated_data['amenaza']
            validated_data['descripcion'] = f'{amenaza.nombre} sobre {activo.nombre}'
        return super().create(validated_data)


class EvaluacionRiesgoSerializer(serializers.ModelSerializer):
    riesgo_codigo = serializers.CharField(source='riesgo.codigo', read_only=True)

    class Meta:
        model = EvaluacionRiesgo
        fields = '__all__'
        read_only_fields = ('valor_riesgo', 'nivel', 'evaluado_por')

    def create(self, validated_data):
        prob = validated_data['probabilidad']
        imp = validated_data['impacto']
        valor = prob * imp
        validated_data['valor_riesgo'] = valor
        validated_data['nivel'] = EvaluacionRiesgo.calcular_nivel(valor)
        validated_data['evaluado_por'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        prob = validated_data.get('probabilidad', instance.probabilidad)
        imp = validated_data.get('impacto', instance.impacto)
        if 'probabilidad' in validated_data or 'impacto' in validated_data:
            valor = prob * imp
            validated_data['valor_riesgo'] = valor
            validated_data['nivel'] = EvaluacionRiesgo.calcular_nivel(valor)
        return super().update(instance, validated_data)


class TratamientoRiesgoSerializer(serializers.ModelSerializer):
    riesgo_codigo = serializers.CharField(source='riesgo.codigo', read_only=True)
    riesgo_residual_valor = serializers.SerializerMethodField()
    riesgo_residual_nivel = serializers.SerializerMethodField()

    class Meta:
        model = TratamientoRiesgo
        fields = '__all__'
        read_only_fields = ('riesgo_residual', 'evaluacion_residual')

    def _evaluacion_residual(self, obj):
        if obj.evaluacion_residual_id:
            return obj.evaluacion_residual
        return (
            EvaluacionRiesgo.objects
            .filter(
                riesgo_id=obj.riesgo_id,
                tipo=EvaluacionRiesgo.Tipo.RESIDUAL,
                activo=True,
            )
            .order_by('-fecha_evaluacion', '-creado_en')
            .first()
        )

    def get_riesgo_residual_valor(self, obj):
        if obj.riesgo_residual is not None:
            return obj.riesgo_residual
        ev = self._evaluacion_residual(obj)
        return ev.valor_riesgo if ev else None

    def get_riesgo_residual_nivel(self, obj):
        ev = self._evaluacion_residual(obj)
        return ev.nivel if ev else None

    def create(self, validated_data):
        if 'responsable' not in validated_data:
            validated_data['responsable'] = self.context['request'].user
        ev = (
            EvaluacionRiesgo.objects
            .filter(riesgo=validated_data['riesgo'], tipo=EvaluacionRiesgo.Tipo.RESIDUAL, activo=True)
            .order_by('-fecha_evaluacion', '-creado_en')
            .first()
        )
        if ev:
            validated_data['evaluacion_residual'] = ev
            validated_data['riesgo_residual'] = ev.valor_riesgo
        return super().create(validated_data)


class ControlISO27001Serializer(serializers.ModelSerializer):
    class Meta:
        model = ControlISO27001
        fields = '__all__'


class ActivoViewSet(BajaLogicaMixin, RiesgosViewSetMixin, viewsets.ModelViewSet):
    queryset = Activo.objects.filter(activo=True).select_related('propietario').order_by('codigo')
    serializer_class = ActivoSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='siguiente-codigo')
    def siguiente_codigo(self, request):
        clasificacion = request.query_params.get('clasificacion', '')
        if clasificacion not in dict(Activo.Clasificacion.choices):
            return Response({'detail': 'Clasificación no válida.'}, status=400)
        codigo = Activo.obtener_siguiente_codigo(clasificacion)
        return Response({
            'clasificacion': clasificacion,
            'prefijo': Activo.prefijo_codigo(clasificacion),
            'codigo': codigo,
        })


class AmenazaViewSet(BajaLogicaMixin, RiesgosViewSetMixin, viewsets.ModelViewSet):
    queryset = Amenaza.objects.filter(activo=True).order_by('codigo')
    serializer_class = AmenazaSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='siguiente-codigo')
    def siguiente_codigo(self, request):
        codigo = Amenaza.obtener_siguiente_codigo()
        return Response({
            'prefijo': Amenaza.PREFIJO_CODIGO,
            'codigo': codigo,
        })


class VulnerabilidadViewSet(RiesgosViewSetMixin, viewsets.ModelViewSet):
    queryset = (
        Vulnerabilidad.objects
        .select_related('activo')
        .exclude(estado=Vulnerabilidad.Estado.CERRADA)
        .order_by('codigo')
    )
    serializer_class = VulnerabilidadSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='siguiente-codigo')
    def siguiente_codigo(self, request):
        codigo = Vulnerabilidad.obtener_siguiente_codigo()
        return Response({
            'prefijo': Vulnerabilidad.PREFIJO_CODIGO,
            'codigo': codigo,
        })

    def perform_destroy(self, instance):
        instance.estado = Vulnerabilidad.Estado.CERRADA
        instance.save(update_fields=['estado'])


class RiesgoViewSet(RiesgosViewSetMixin, viewsets.ModelViewSet):
    queryset = (
        Riesgo.objects
        .filter(eliminado=False)
        .select_related('activo', 'amenaza', 'vulnerabilidad')
        .order_by('codigo')
    )
    serializer_class = RiesgoSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='exportar-excel')
    def exportar_excel(self, request):
        return exportar_gestion_riesgos_excel()

    @action(detail=False, methods=['get'], url_path='siguiente-codigo')
    def siguiente_codigo(self, request):
        codigo = Riesgo.obtener_siguiente_codigo()
        return Response({
            'prefijo': Riesgo.PREFIJO_CODIGO,
            'codigo': codigo,
        })

    def perform_destroy(self, instance):
        instance.eliminado = True
        instance.save(update_fields=['eliminado'])


class EvaluacionRiesgoViewSet(BajaLogicaMixin, RiesgosViewSetMixin, viewsets.ModelViewSet):
    queryset = (
        EvaluacionRiesgo.objects
        .filter(activo=True)
        .select_related('riesgo', 'evaluado_por')
        .order_by('-fecha_evaluacion', 'riesgo__codigo')
    )
    serializer_class = EvaluacionRiesgoSerializer
    permission_classes = [IsAuthenticated]


class TratamientoRiesgoViewSet(BajaLogicaMixin, RiesgosViewSetMixin, viewsets.ModelViewSet):
    queryset = (
        TratamientoRiesgo.objects
        .filter(activo=True)
        .select_related('riesgo', 'responsable', 'evaluacion_residual')
        .order_by('-fecha_inicio', 'riesgo__codigo')
    )
    serializer_class = TratamientoRiesgoSerializer
    permission_classes = [IsAuthenticated]


class ControlISO27001ViewSet(viewsets.ModelViewSet):
    queryset = ControlISO27001.objects.select_related('responsable', 'riesgo')
    serializer_class = ControlISO27001Serializer
    permission_classes = [IsAuthenticated]
