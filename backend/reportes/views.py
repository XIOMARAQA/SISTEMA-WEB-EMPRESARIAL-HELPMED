import logging

from django.http import HttpResponse
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from reportes.builders import EXPORTADORES
from seguridad.modulos import puede_acceder_modulo

logger = logging.getLogger(__name__)

class PuedeExportarReportes(BasePermission):
    def has_permission(self, request, view):
        return puede_acceder_modulo(request.user, 'reportes')


class ExportarReporteView(APIView):
    permission_classes = [IsAuthenticated, PuedeExportarReportes]

    def get(self, request, tipo):
        formato = (request.query_params.get('formato') or '').lower()
        if formato not in ('pdf', 'excel'):
            return Response({'detail': 'Indique formato=pdf o formato=excel.'}, status=400)

        exportadores = EXPORTADORES.get(tipo)
        if not exportadores:
            return Response({'detail': 'Tipo de reporte no válido.'}, status=404)

        generador = exportadores.get(formato)
        if not generador:
            return Response(
                {'detail': f'Este reporte no admite exportación en {formato.upper()}.'},
                status=400,
            )

        try:
            resultado = generador()
            if isinstance(resultado, HttpResponse):
                return resultado
            return resultado
        except Exception as exc:
            logger.exception('Error exportando reporte %s (%s)', tipo, formato)
            return Response(
                {'detail': f'Error al generar el reporte: {exc}'},
                status=500,
            )