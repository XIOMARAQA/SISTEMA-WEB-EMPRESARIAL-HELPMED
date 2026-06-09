from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auditoria.models import Auditoria, RegistroAuditoria


class AuditoriaSerializer(serializers.ModelSerializer):
    auditor_nombre = serializers.CharField(source='auditor.username', read_only=True)
    alcance = serializers.CharField(required=False, allow_blank=True)
    hallazgos = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Auditoria
        fields = '__all__'
        read_only_fields = ('codigo', 'auditor', 'creado_en')

    def create(self, validated_data):
        validated_data['codigo'] = Auditoria.obtener_siguiente_codigo()
        validated_data['auditor'] = self.context['request'].user
        alcance = (validated_data.get('alcance') or '').strip()
        if not alcance:
            validated_data['alcance'] = validated_data['titulo']
        return super().create(validated_data)


class RegistroAuditoriaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = RegistroAuditoria
        fields = '__all__'


class AuditoriaViewSet(viewsets.ModelViewSet):
    queryset = Auditoria.objects.select_related('auditor').order_by('-creado_en')
    serializer_class = AuditoriaSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='siguiente-codigo')
    def siguiente_codigo(self, request):
        codigo = Auditoria.obtener_siguiente_codigo()
        return Response({
            'prefijo': Auditoria.PREFIJO_CODIGO,
            'codigo': codigo,
        })


class RegistroAuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RegistroAuditoria.objects.select_related('usuario').order_by('-creado_en')
    serializer_class = RegistroAuditoriaSerializer
    permission_classes = [IsAuthenticated]
