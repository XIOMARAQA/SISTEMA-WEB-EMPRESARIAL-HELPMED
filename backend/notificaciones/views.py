from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notificaciones.models import Notificacion

ENLACES_MODULO = {
    'recepcion': '/recepcion',
    'calidad': '/calidad',
    'inventario': '/inventario',
    'ambiental': '/ambiental',
    'reportes': '/reportes',
    'auditoria': '/auditoria',
    'seguridad': '/auditoria',
}


class NotificacionSerializer(serializers.ModelSerializer):
    enlace = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = (
            'id', 'tipo', 'prioridad', 'titulo', 'mensaje', 'leida',
            'referencia_modulo', 'referencia_id', 'enlace', 'creado_en',
        )
        read_only_fields = fields

    def get_enlace(self, obj):
        return ENLACES_MODULO.get(obj.referencia_modulo, '/')


class NotificacionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user).order_by('-creado_en')

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        qs = self.get_queryset()
        no_leidas = qs.filter(leida=False).count()
        ultimas = qs[:20]
        return Response({
            'no_leidas': no_leidas,
            'notificaciones': NotificacionSerializer(ultimas, many=True).data,
        })

    @action(detail=True, methods=['post'], url_path='marcar-leida')
    def marcar_leida(self, request, pk=None):
        notif = self.get_object()
        if not notif.leida:
            notif.leida = True
            notif.save(update_fields=['leida'])
        return Response(NotificacionSerializer(notif).data)

    @action(detail=False, methods=['post'], url_path='marcar-todas-leidas')
    def marcar_todas_leidas(self, request):
        actualizadas = self.get_queryset().filter(leida=False).update(leida=True)
        return Response({'marcadas': actualizadas})
