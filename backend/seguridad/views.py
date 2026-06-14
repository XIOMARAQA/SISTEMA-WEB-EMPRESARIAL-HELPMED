from django.db import IntegrityError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from seguridad.models import Rol, Usuario
from seguridad.permissions import EsAdminOSuperusuario
from seguridad.serializers import (
    PerfilUpdateSerializer,
    RolSerializer,
    UsuarioCreateSerializer,
    UsuarioGestionSerializer,
    UsuarioSerializer,
    UsuarioUpdateSerializer,
)
from seguridad.utils.usuarios import generar_email, generar_password_inicial, generar_username


class PerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)

    def patch(self, request):
        serializer = PerfilUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UsuarioSerializer(request.user).data)


class RolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Rol.objects.filter(activo=True).order_by('nombre')
    serializer_class = RolSerializer
    permission_classes = [IsAuthenticated, EsAdminOSuperusuario]


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.prefetch_related('roles_asignados__rol').order_by('username')
    permission_classes = [IsAuthenticated, EsAdminOSuperusuario]

    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UsuarioUpdateSerializer
        return UsuarioGestionSerializer

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as exc:
            if 'usuarios_pkey' in str(exc):
                return Response(
                    {
                        'detail': (
                            'No se pudo asignar un identificador al usuario. '
                            'Ejecute: python manage.py fix_db_sequences'
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            raise

    def perform_destroy(self, instance):
        instance.estado = Usuario.Estado.INACTIVO
        instance.is_active = False
        instance.save(update_fields=['estado', 'is_active'])

    @action(detail=False, methods=['get'], url_path='sugerir-username')
    def sugerir_username(self, request):
        nombres = request.query_params.get('nombres', '')
        apellidos = request.query_params.get('apellidos', '')
        try:
            username = generar_username(nombres, apellidos)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        documento = request.query_params.get('documento', '')
        return Response({
            'username': username,
            'email': generar_email(username),
            'password': generar_password_inicial(username, documento) if documento else '',
        })
