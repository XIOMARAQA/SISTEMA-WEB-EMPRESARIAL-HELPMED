import re
import unicodedata

from django.contrib.auth import get_user_model

User = get_user_model()


def _normalizar_texto(texto):
    texto = (texto or '').strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', texto)


def generar_username(nombres, apellidos):
    """
    Código de usuario: primera letra del nombre + apellido paterno.
    Ej.: Juan Pérez García → jperez
    """
    partes_nombre = (nombres or '').strip().split()
    partes_apellido = (apellidos or '').strip().split()
    if not partes_nombre or not partes_apellido:
        raise ValueError('Indique nombres y apellido paterno.')

    inicial = _normalizar_texto(partes_nombre[0][:1])
    apellido_paterno = _normalizar_texto(partes_apellido[0])
    if not inicial or not apellido_paterno:
        raise ValueError('No se pudo generar el código de usuario.')

    base = f'{inicial}{apellido_paterno}'
    candidato = base
    n = 2
    while User.objects.filter(username=candidato).exists():
        candidato = f'{base}{n}'
        n += 1
    return candidato


DOMINIO_CORREO = 'seguricel.com'


def generar_email(username):
    """Correo: codigo_usuario@seguricel.com"""
    return f'{(username or "").strip().lower()}@{DOMINIO_CORREO}'


def generar_password_inicial(username, documento):
    """Contraseña inicial: codigo_usuario + 2 últimos dígitos del DNI."""
    user = (username or '').strip().lower()
    digitos = re.sub(r'\D', '', str(documento or ''))
    sufijo = digitos[-2:] if len(digitos) >= 2 else digitos
    return f'{user}{sufijo}'
