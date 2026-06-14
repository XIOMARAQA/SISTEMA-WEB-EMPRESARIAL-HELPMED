import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Longitud máxima razonable para SMS concatenado (varios segmentos GSM)
SMS_MAX_CARACTERES = 480


def _normalizar_telefono_peru(telefono):
    """Convierte 972677418 → +51972677418."""
    digits = re.sub(r'\D', '', telefono or '')
    if not digits:
        return ''
    if digits.startswith('51') and len(digits) >= 11:
        return f'+{digits}'
    if len(digits) == 9:
        return f'+51{digits}'
    if len(digits) == 10 and digits.startswith('9'):
        return f'+51{digits[-9:]}'
    if len(digits) >= 10:
        return f'+{digits}'
    return ''


def texto_sms_notificacion(notificacion):
    """Mismo contenido que la campana in-app: título + mensaje."""
    titulo = (notificacion.titulo or '').strip()
    mensaje = (notificacion.mensaje or '').strip()
    if titulo and mensaje:
        texto = f'{titulo}\n{mensaje}'
    else:
        texto = titulo or mensaje
    if len(texto) > SMS_MAX_CARACTERES:
        return texto[: SMS_MAX_CARACTERES - 1] + '…'
    return texto


def _debe_enviar_sms(notificacion):
    if not getattr(settings, 'MYSMSGATE_ENABLED', False):
        return False
    if not (notificacion.usuario.telefono or '').strip():
        return False
    if getattr(settings, 'MYSMSGATE_SMS_TODAS', True):
        return True
    from notificaciones.models import Notificacion

    if notificacion.tipo == Notificacion.Tipo.SEGURIDAD:
        return True
    return notificacion.prioridad in (
        Notificacion.Prioridad.ALTA,
        Notificacion.Prioridad.CRITICA,
    )


def _enviar_sms_a_numero(destino, texto, notificacion_id=None, usuario_id=None):
    api_key = getattr(settings, 'MYSMSGATE_API_KEY', '')
    if not api_key:
        logger.warning('MySMSGate habilitado pero MYSMSGATE_API_KEY no está configurado.')
        return False

    url = getattr(settings, 'MYSMSGATE_API_URL', 'https://mysmsgate.net/api/v1/send')
    payload = {'to': destino, 'message': texto}
    device_id = getattr(settings, 'MYSMSGATE_DEVICE_ID', '')
    if device_id:
        payload['device_id'] = device_id

    try:
        response = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=getattr(settings, 'MYSMSGATE_TIMEOUT', 15),
        )
        if response.status_code in (200, 201, 202):
            logger.info(
                'SMS MySMSGate encolado → %s (usuario %s, notif %s): %s',
                destino,
                usuario_id,
                notificacion_id,
                response.text[:120],
            )
            return True
        logger.warning(
            'MySMSGate respondió %s para %s: %s',
            response.status_code,
            destino,
            response.text[:300],
        )
        return False
    except requests.RequestException as exc:
        logger.exception('Error al enviar SMS MySMSGate a %s: %s', destino, exc)
        return False


def enviar_sms_mysmsgate(notificacion):
    """Envía SMS al teléfono del usuario con el mismo texto que la notificación in-app."""
    if not _debe_enviar_sms(notificacion):
        return False

    destino = _normalizar_telefono_peru(notificacion.usuario.telefono)
    if not destino:
        logger.warning('SMS omitido: teléfono inválido para usuario %s', notificacion.usuario.pk)
        return False

    texto = texto_sms_notificacion(notificacion)
    return _enviar_sms_a_numero(
        destino,
        texto,
        notificacion_id=notificacion.pk,
        usuario_id=notificacion.usuario.pk,
    )
