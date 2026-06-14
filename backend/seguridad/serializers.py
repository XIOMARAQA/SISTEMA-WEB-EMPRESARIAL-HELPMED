from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from seguridad.models import IntentoLogin, RefreshToken as RefreshTokenModel, Rol, Usuario, UsuarioRol
from seguridad.utils.usuarios import generar_email, generar_password_inicial, generar_username


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ('id', 'codigo', 'nombre')


class UsuarioSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    roles_codigos = serializers.SerializerMethodField()
    modulos_permitidos = serializers.SerializerMethodField()
    es_admin = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            'id', 'username', 'email', 'nombres', 'apellidos',
            'documento', 'telefono', 'estado', 'roles', 'roles_codigos',
            'modulos_permitidos', 'es_admin', 'is_superuser', 'ultimo_acceso',
        )
        read_only_fields = fields

    def get_roles(self, obj):
        roles = Rol.objects.filter(usuarios_asignados__usuario=obj, activo=True)
        return RolSerializer(roles, many=True).data

    def get_roles_codigos(self, obj):
        return list(
            Rol.objects.filter(usuarios_asignados__usuario=obj, activo=True)
            .values_list('codigo', flat=True)
        )

    def get_modulos_permitidos(self, obj):
        from seguridad.modulos import modulos_permitidos
        return modulos_permitidos(obj)

    def get_es_admin(self, obj):
        if obj.is_superuser:
            return True
        return Rol.objects.filter(
            usuarios_asignados__usuario=obj, codigo='admin', activo=True,
        ).exists()


class UsuarioGestionSerializer(UsuarioSerializer):
    rol = serializers.SerializerMethodField()

    class Meta(UsuarioSerializer.Meta):
        fields = UsuarioSerializer.Meta.fields + ('rol',)

    def get_rol(self, obj):
        ur = obj.roles_asignados.select_related('rol').filter(rol__activo=True).first()
        if not ur:
            return None
        return RolSerializer(ur.rol).data


class PerfilUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ('telefono',)

    def validate_telefono(self, value):
        return (value or '').strip()[:20]


class UsuarioCreateSerializer(serializers.ModelSerializer):
    rol = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.filter(activo=True))
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=128)
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = Usuario
        fields = ('nombres', 'apellidos', 'documento', 'email', 'telefono', 'rol', 'password')

    def validate_documento(self, value):
        doc = (value or '').strip()
        if not doc:
            raise serializers.ValidationError('El DNI es obligatorio.')
        if Usuario.objects.filter(documento=doc).exists():
            raise serializers.ValidationError('Ya existe un usuario con este DNI.')
        return doc

    def validate_email(self, value):
        email = (value or '').strip()
        if email and Usuario.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Ya existe un usuario con este correo.')
        return email

    def create(self, validated_data):
        rol = validated_data.pop('rol')
        password = (validated_data.pop('password', '') or '').strip()
        username = generar_username(validated_data['nombres'], validated_data['apellidos'])
        email = (validated_data.get('email') or '').strip() or generar_email(username)
        if not password:
            password = generar_password_inicial(username, validated_data['documento'])
        user = Usuario.objects.create_user(
            username=username,
            password=password,
            email=email,
            nombres=validated_data['nombres'].strip(),
            apellidos=validated_data.get('apellidos', '').strip(),
            documento=validated_data['documento'],
            telefono=validated_data.get('telefono', ''),
            estado=Usuario.Estado.ACTIVO,
            is_active=True,
        )
        UsuarioRol.objects.create(usuario=user, rol=rol)
        return user

    def to_representation(self, instance):
        return UsuarioGestionSerializer(instance, context=self.context).data


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    rol = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.filter(activo=True), required=False)
    password = serializers.CharField(write_only=True, min_length=8, max_length=128, required=False)

    class Meta:
        model = Usuario
        fields = ('nombres', 'apellidos', 'documento', 'email', 'telefono', 'estado', 'rol', 'password')

    def validate_documento(self, value):
        doc = (value or '').strip()
        if not doc:
            raise serializers.ValidationError('El DNI es obligatorio.')
        qs = Usuario.objects.filter(documento=doc)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un usuario con este DNI.')
        return doc

    def update(self, instance, validated_data):
        rol = validated_data.pop('rol', None)
        password = validated_data.pop('password', None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        if password:
            instance.set_password(password)

        if instance.estado == Usuario.Estado.INACTIVO:
            instance.is_active = False
        elif instance.estado == Usuario.Estado.ACTIVO:
            instance.is_active = True
            instance.intentos_fallidos = 0
            instance.bloqueado_hasta = None

        instance.save()

        if rol is not None:
            UsuarioRol.objects.filter(usuario=instance).delete()
            UsuarioRol.objects.create(usuario=instance, rol=rol)

        return instance

    def to_representation(self, instance):
        return UsuarioGestionSerializer(instance, context=self.context).data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(required=True, write_only=True)

    MSG_CUENTA_BLOQUEADA = 'Su cuenta fue bloqueada. Consulte al administrador.'
    MSG_CREDENCIALES = 'Usuario, correo o contraseña incorrectos.'

    def _registrar_fallo(self, username, ip, motivo, user=None):
        IntentoLogin.objects.create(
            username=username,
            ip_address=ip,
            exitoso=False,
            motivo=motivo,
        )
        from auditoria.services import registrar_accion
        request = self.context.get('request')
        registrar_accion(
            request=request,
            usuario=user,
            accion='Login fallido',
            modulo='seguridad',
            descripcion=f'Usuario: {username} — {motivo}',
            ip_address=ip,
        )
        from django.conf import settings
        from notificaciones.flujos import notificar_alerta_login
        notificar_alerta_login(
            username,
            ip,
            motivo,
            max_attempts=getattr(settings, 'MAX_LOGIN_ATTEMPTS', 3),
        )

    def _bloquear_usuario(self, user):
        user.is_active = False
        user.estado = Usuario.Estado.INACTIVO
        user.bloqueado_hasta = None
        user.save(update_fields=['intentos_fallidos', 'is_active', 'estado', 'bloqueado_hasta'])

    def _fallo_credenciales(self, user, username, ip, max_attempts):
        if user:
            user.intentos_fallidos += 1
            if user.intentos_fallidos >= max_attempts:
                self._bloquear_usuario(user)
                self._registrar_fallo(username, ip, 'Cuenta bloqueada por intentos fallidos')
                raise serializers.ValidationError({'detail': self.MSG_CUENTA_BLOQUEADA})

            user.save(update_fields=['intentos_fallidos'])
            restantes = max_attempts - user.intentos_fallidos
            self._registrar_fallo(username, ip, 'Credenciales inválidas', user=user)
            raise serializers.ValidationError({
                'detail': f'{self.MSG_CREDENCIALES} Intentos restantes: {restantes}.',
            })

        self._registrar_fallo(username, ip, 'Credenciales inválidas', user=user)
        raise serializers.ValidationError({'detail': self.MSG_CREDENCIALES})

    def validate(self, attrs):
        from django.conf import settings
        from django.contrib.auth import authenticate

        username = (attrs.get('username') or '').strip()
        email = (attrs.get('email') or '').strip().lower()
        password = attrs.get('password') or ''
        request = self.context.get('request')
        ip = request.META.get('REMOTE_ADDR') if request else None
        max_attempts = settings.MAX_LOGIN_ATTEMPTS

        user = Usuario.objects.filter(username__iexact=username).first()

        if user and (
            not user.is_active
            or user.estado in (Usuario.Estado.INACTIVO, Usuario.Estado.BLOQUEADO)
        ):
            self._registrar_fallo(username, ip, 'Cuenta inactiva o bloqueada', user=user)
            raise serializers.ValidationError({'detail': self.MSG_CUENTA_BLOQUEADA})

        if not user or (user.email or '').strip().lower() != email:
            self._fallo_credenciales(user, username, ip, max_attempts)

        auth_user = authenticate(request=request, username=user.username, password=password)
        if not auth_user:
            self._fallo_credenciales(user, username, ip, max_attempts)

        user = auth_user
        user.intentos_fallidos = 0
        user.ultimo_acceso = timezone.now()
        user.save(update_fields=['intentos_fallidos', 'ultimo_acceso'])
        IntentoLogin.objects.create(username=username, ip_address=ip, exitoso=True)
        from auditoria.services import registrar_accion
        registrar_accion(
            request=request,
            usuario=user,
            accion='Inicio de sesión',
            modulo='seguridad',
            descripcion=f'Acceso exitoso — {user.username}',
            ip_address=ip,
        )

        refresh = RefreshToken.for_user(user)
        RefreshTokenModel.objects.create(
            usuario=user,
            token=str(refresh),
            expira_en=timezone.now() + timedelta(days=7),
        )

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UsuarioSerializer(user).data,
        }
