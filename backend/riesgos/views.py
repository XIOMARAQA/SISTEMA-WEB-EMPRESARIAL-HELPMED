from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from riesgos.models import (
    Activo,
    Amenaza,
    ControlISO27001,
    EvaluacionRiesgo,
    Riesgo,
    TratamientoRiesgo,
    Vulnerabilidad,
)


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


class TratamientoRiesgoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TratamientoRiesgo
        fields = '__all__'


class ControlISO27001Serializer(serializers.ModelSerializer):
    class Meta:
        model = ControlISO27001
        fields = '__all__'


class ActivoViewSet(viewsets.ModelViewSet):
    queryset = Activo.objects.filter(activo=True).select_related('propietario')
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


class AmenazaViewSet(viewsets.ModelViewSet):
    queryset = Amenaza.objects.filter(activo=True)
    serializer_class = AmenazaSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='siguiente-codigo')
    def siguiente_codigo(self, request):
        codigo = Amenaza.obtener_siguiente_codigo()
        return Response({
            'prefijo': Amenaza.PREFIJO_CODIGO,
            'codigo': codigo,
        })


class VulnerabilidadViewSet(viewsets.ModelViewSet):
    queryset = Vulnerabilidad.objects.select_related('activo')
    serializer_class = VulnerabilidadSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='siguiente-codigo')
    def siguiente_codigo(self, request):
        codigo = Vulnerabilidad.obtener_siguiente_codigo()
        return Response({
            'prefijo': Vulnerabilidad.PREFIJO_CODIGO,
            'codigo': codigo,
        })


class RiesgoViewSet(viewsets.ModelViewSet):
    queryset = Riesgo.objects.select_related('activo', 'amenaza', 'vulnerabilidad')
    serializer_class = RiesgoSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='siguiente-codigo')
    def siguiente_codigo(self, request):
        codigo = Riesgo.obtener_siguiente_codigo()
        return Response({
            'prefijo': Riesgo.PREFIJO_CODIGO,
            'codigo': codigo,
        })


class EvaluacionRiesgoViewSet(viewsets.ModelViewSet):
    queryset = EvaluacionRiesgo.objects.select_related('riesgo', 'evaluado_por')
    serializer_class = EvaluacionRiesgoSerializer
    permission_classes = [IsAuthenticated]


class TratamientoRiesgoViewSet(viewsets.ModelViewSet):
    queryset = TratamientoRiesgo.objects.select_related('riesgo', 'responsable')
    serializer_class = TratamientoRiesgoSerializer
    permission_classes = [IsAuthenticated]


class ControlISO27001ViewSet(viewsets.ModelViewSet):
    queryset = ControlISO27001.objects.select_related('responsable', 'riesgo')
    serializer_class = ControlISO27001Serializer
    permission_classes = [IsAuthenticated]
