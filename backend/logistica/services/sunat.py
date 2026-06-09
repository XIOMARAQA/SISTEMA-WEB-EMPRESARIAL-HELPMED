import re

import requests
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError


class SunatServiceError(APIException):
    status_code = 502
    default_detail = 'No se pudo consultar SUNAT en este momento.'


def validar_ruc(ruc: str) -> str:
    ruc = re.sub(r'\D', '', ruc or '')
    if len(ruc) != 11:
        raise ValidationError({'ruc': 'El RUC debe tener 11 dígitos.'})
    return ruc


def validar_dni(dni: str) -> str:
    dni = re.sub(r'\D', '', dni or '')
    if len(dni) != 8:
        raise ValidationError({'dni': 'El DNI debe tener 8 dígitos.'})
    return dni


def consultar_dni_reniec(dni: str) -> dict:
    """Consulta DNI en RENIEC vía Decolecta (apis.net.pe)."""
    dni = validar_dni(dni)
    token = getattr(settings, 'APIS_NET_PE_TOKEN', '') or ''
    if not token:
        raise ValidationError({'detail': 'Token APIS_NET_PE_TOKEN no configurado en .env'})

    base_url = getattr(settings, 'DECOLECTA_API_URL', 'https://api.decolecta.com/v1')
    url = f'{base_url.rstrip("/")}/reniec/dni'

    try:
        response = requests.get(
            url,
            params={'numero': dni},
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
            },
            timeout=getattr(settings, 'DECOLECTA_API_TIMEOUT', 15),
        )
    except requests.RequestException as exc:
        raise SunatServiceError(detail=f'Error de conexión con RENIEC: {exc}') from exc

    if response.status_code == 404:
        raise ValidationError({'dni': 'DNI no encontrado en RENIEC.'})
    if response.status_code == 401:
        raise ValidationError({'detail': 'Token de Decolecta inválido o expirado.'})
    if response.status_code != 200:
        raise SunatServiceError(detail=f'RENIEC respondió con código {response.status_code}.')

    data = response.json()
    nombres = (data.get('nombres') or '').strip()
    apellido_paterno = (data.get('apellido_paterno') or data.get('apellidoPaterno') or '').strip()
    apellido_materno = (data.get('apellido_materno') or data.get('apellidoMaterno') or '').strip()
    nombre_completo = ' '.join(p for p in (nombres, apellido_paterno, apellido_materno) if p).strip()

    return {
        'dni': data.get('numero_documento') or dni,
        'nombres': nombres,
        'apellido_paterno': apellido_paterno,
        'apellido_materno': apellido_materno,
        'nombre_completo': nombre_completo or data.get('nombre_completo', ''),
        'reniec_raw': data,
    }


def consultar_ruc_sunat(ruc: str) -> dict:
    """Consulta RUC en Decolecta (apis.net.pe / api.decolecta.com)."""
    ruc = validar_ruc(ruc)
    token = getattr(settings, 'APIS_NET_PE_TOKEN', '') or ''
    if not token:
        raise ValidationError({'detail': 'Token APIS_NET_PE_TOKEN no configurado en .env'})

    base_url = getattr(settings, 'DECOLECTA_API_URL', 'https://api.decolecta.com/v1')
    url = f'{base_url.rstrip("/")}/sunat/ruc'

    try:
        response = requests.get(
            url,
            params={'numero': ruc},
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
            },
            timeout=getattr(settings, 'DECOLECTA_API_TIMEOUT', 15),
        )
    except requests.RequestException as exc:
        raise SunatServiceError(detail=f'Error de conexión con SUNAT: {exc}') from exc

    if response.status_code == 404:
        raise ValidationError({'ruc': 'RUC no encontrado en SUNAT.'})
    if response.status_code == 401:
        raise ValidationError({'detail': 'Token de Decolecta inválido o expirado.'})
    if response.status_code != 200:
        raise SunatServiceError(detail=f'SUNAT respondió con código {response.status_code}.')

    data = response.json()
    direccion = data.get('direccion') or data.get('dirección') or ''
    if not direccion.strip():
        partes = [
            data.get('via_tipo'), data.get('via_nombre'), data.get('numero'),
            data.get('interior'), data.get('distrito'), data.get('provincia'),
            data.get('departamento'),
        ]
        direccion = ' '.join(p for p in partes if p and str(p) != '-')

    return {
        'ruc': data.get('numero_documento') or ruc,
        'razon_social': data.get('razon_social', ''),
        'direccion': direccion.strip(),
        'estado_sunat': data.get('estado', ''),
        'condicion_sunat': data.get('condicion', ''),
        'ubigeo': data.get('ubigeo', ''),
        'distrito': data.get('distrito', ''),
        'provincia': data.get('provincia', ''),
        'departamento': data.get('departamento', ''),
        'es_agente_retencion': data.get('es_agente_retencion', False),
        'es_buen_contribuyente': data.get('es_buen_contribuyente', False),
        'sunat_raw': data,
    }
