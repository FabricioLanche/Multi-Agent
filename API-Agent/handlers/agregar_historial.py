"""
Handler para actualizar historial médico
"""
import json
import traceback
from datetime import datetime

from dao.base import DAOFactory
from services.auth_service import AuthService
from utils.formatters import formatear_respuesta_exitosa, formatear_respuesta_error
from utils.validators import validar_email


def handler(event, context):
    """
    Handler Lambda para actualizar el historial médico del usuario
    
    Espera un body JSON con:
    {
        "correo": "usuario@example.com",
        "fecha": "2024-11-23",  # Opcional
        "sensores": {...},
        "wearables": {...}
    }
    
    O alternativamente puede obtener el correo del token si no viene en body
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
                'Se require un email válido'
            )
        
        # 3. Obtener DAO
        historial_dao = DAOFactory.get_dao('historial')
        
        # 4. Preparar registro
        fecha = body.get('fecha', datetime.now().strftime('%Y-%m-%d'))
        sensores = body.get('sensores', {})
        wearables = body.get('wearables', {})
        
        if not sensores and not wearables:
            return formatear_respuesta_error(
                400,
                'Datos faltantes',
                'Se requiere al menos "sensores" o "wearables"'
            )
        
        registro = {
            'correo': correo,
            'fecha': fecha,
            'sensores': sensores,
            'wearables': wearables
        }
        
        # 5. Guardar en DynamoDB
        exito = historial_dao.agregar_registro(registro)
        
        if not exito:
            return formatear_respuesta_error(
                500,
                'Error al guardar',
                'No se pudo guardar el registro'
            )
        
        # 6. Retornar éxito
        return formatear_respuesta_exitosa({
            'message': 'Historial actualizado correctamente',
            'correo': correo,
            'fecha': fecha
        })
    
    except json.JSONDecodeError:
        return formatear_respuesta_error(
            400,
            'JSON inválido',
            'El body debe ser JSON válido'
        )
    
    except Exception as e:
        print(f"Error actualizando historial: {str(e)}")
        print(traceback.format_exc())
        return formatear_respuesta_error(
            500,
            'Error interno',
            'Ocurrió un error procesando la solicitud'
        )
