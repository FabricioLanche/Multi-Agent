"""
Handler para actualizar memoria contextual
"""
import json
import uuid
import traceback
from datetime import datetime

from dao.base import DAOFactory
from services.auth_service import AuthService
from utils.formatters import formatear_respuesta_exitosa, formatear_respuesta_error
from utils.validators import validar_email


def handler(event, context):
    """
    Handler Lambda para actualizar la memoria contextual
    
    Espera un body JSON con:
    {
        "correo": "usuario@example.com",
        "context_id": "ctx-abc123",  # Opcional, se genera si no existe
        "fecha": "2024-11-23",  # Opcional
        "resumen_conversacion": "...",
        "intencion_detectada": "...",
        "datos_extraidos": {...}
    }
    """
    try:
        # 1. Parsear body
        body = json.loads(event.get('body', '{}'))
        
        # 2. Obtener correo (de body o de token)
        correo = body.get('correo')
        if not correo:
            correo = AuthService.get_user_email_from_event(event)
        
        if not correo or not validar_email(correo):
            return formatear_respuesta_error(
                400,
                'Email inválido',
                'Se requiere un email válido'
            )
        
        # 3. Obtener DAO
        memoria_dao = DAOFactory.get_dao('memoria')
        
        # 4. Preparar registro de memoria
        context_id = body.get('context_id', f"ctx-{uuid.uuid4().hex[:8]}")
        fecha = body.get('fecha', datetime.now().isoformat())
        resumen = body.get('resumen_conversacion', '')
        intencion = body.get('intencion_detectada', 'no_detectada')
        datos_extraidos = body.get('datos_extraidos', {})
        
        if not resumen:
            return formatear_respuesta_error(
                400,
                'Datos faltantes',
                'Se requiere "resumen_conversacion"'
            )
        
        memoria = {
            'correo': correo,
            'context_id': context_id,
            'fecha': fecha,
            'resumen_conversacion': resumen,
            'intencion_detectada': intencion,
            'datos_extraidos': datos_extraidos
        }
        
        # 5. Guardar en DynamoDB
        exito = memoria_dao.guardar_memoria(memoria)
        
        if not exito:
            return formatear_respuesta_error(
                500,
                'Error al guardar',
                'No se pudo guardar la memoria'
            )
        
        # 6. Retornar éxito
        return formatear_respuesta_exitosa({
            'message': 'Memoria actualizada correctamente',
            'correo': correo,
            'context_id': context_id,
            'fecha': fecha
        })
    
    except json.JSONDecodeError:
        return formatear_respuesta_error(
            400,
            'JSON inválido',
            'El body debe ser JSON válido'
        )
    
    except Exception as e:
        print(f"Error actualizando memoria: {str(e)}")
        print(traceback.format_exc())
        return formatear_respuesta_error(
            500,
            'Error interno',
            'Ocurrió un error procesando la solicitud'
        )
