from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    IntentoLogin,
    Permiso,
    RefreshToken,
    Rol,
    RolPermiso,
    SesionUsuario,
    TokenRecuperacion,
    Usuario,
    UsuarioRol,
)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'nombres', 'apellidos', 'estado', 'is_staff')
    list_filter = ('estado', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('HelpMed', {'fields': ('nombres', 'apellidos', 'documento', 'telefono', 'estado')}),
    )


admin.site.register(Rol)
admin.site.register(Permiso)
admin.site.register(RolPermiso)
admin.site.register(UsuarioRol)
admin.site.register(SesionUsuario)
admin.site.register(RefreshToken)
admin.site.register(IntentoLogin)
admin.site.register(TokenRecuperacion)
