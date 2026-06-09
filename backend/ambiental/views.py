from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ambiental.models import AccionCorrectiva, Medicion
from seguridad.actores import puede_registrar_medicion_ambiental


class MedicionSerializer(serializers.ModelSerializer):
    responsable_nombre = serializers.CharField(source='responsable.username', read_only=True)

    class Meta:
        model = Medicion
        fields = '__all__'
        read_only_fields = ('responsable', 'fuera_rango')


class AccionCorrectivaSerializer(serializers.ModelSerializer):
    responsable_nombre = serializers.CharField(source='responsable.username', read_only=True)

    class Meta:
        model = AccionCorrectiva
        fields = '__all__'


class MedicionViewSet(viewsets.ModelViewSet):
    queryset = Medicion.objects.select_related('responsable').order_by('-fecha', '-hora')
    serializer_class = MedicionSerializer
    permission_classes = [IsAuthenticated]

    http_method_names = ['get', 'post', 'head', 'options']

    def create(self, request, *args, **kwargs):
        if not puede_registrar_medicion_ambiental(request.user):
            return Response(
                {'detail': 'Solo personal de almacén puede registrar mediciones ambientales.'},
                status=403,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        medicion = serializer.save(responsable=self.request.user)
        fuera = not medicion.evaluar_rango()
        if fuera != medicion.fuera_rango:
            medicion.fuera_rango = fuera
            medicion.save(update_fields=['fuera_rango'])
        if fuera:
            from ambiental.models import IncidenteAmbiental
            accion = AccionCorrectiva.objects.create(
                origen='ambiental',
                referencia_id=medicion.id,
                descripcion=f'Temperatura fuera de rango: {medicion.temperatura}°C',
                responsable=self.request.user,
            )
            IncidenteAmbiental.objects.create(
                medicion=medicion,
                descripcion=f'Alerta: temperatura {medicion.temperatura}°C fuera del rango 20-25°C',
                accion_correctiva=accion,
            )
            from notificaciones.flujos import notificar_incidente_ambiental
            notificar_incidente_ambiental(medicion, actor=self.request.user)


class AccionCorrectivaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AccionCorrectiva.objects.select_related('responsable').order_by('-creado_en')
    serializer_class = AccionCorrectivaSerializer
    permission_classes = [IsAuthenticated]
