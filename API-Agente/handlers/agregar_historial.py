"""
Handlers Lambda para los agentes académicos
"""
import json
import traceback
import uuid
from datetime import datetime

from dao.base import DAOFactory
from utils.formatters import formatear_respuesta_exitosa, formatear_respuesta_error
from utils.validators import validar_email

# ===== HANDLER: AGREGAR AL HISTORIAL =====
def agregar_historial_handler(event, context):
    """
    Handler para agregar manualmente una entrada al historial
    
    Espera un body JSON con:
    {
        "correo": "estudiante@example.com",
        "texto": "Descripción de la interacción"
    }
    """
    try:
        # 1. Parsear body
        body = json.loads(event.get('body', '{}'))
        
        # 2. Validar campos
        correo = body.get('correo')
        texto = body.get('texto')
        
        if not correo or not validar_email(correo):
            return formatear_respuesta_error(
                400,
                'Email inválido',
                'Se requiere un email válido'
            )
        
        if not texto:
            return formatear_respuesta_error(
                400,
                'Texto requerido',
                'Se requiere el campo "texto"'
            )
        
        # 3. Obtener ID del usuario
        usuarios_dao = DAOFactory.get_dao('usuarios')
        usuario = usuarios_dao.get_usuario_por_correo(correo)
        
        if not usuario:
            return formatear_respuesta_error(
                404,
                'Usuario no encontrado',
                f'No existe usuario con correo {correo}'
            )
        
        # 4. Preparar registro
        historial_dao = DAOFactory.get_dao('historial')
        registro = {
            'usuarioId': usuario['id'],
            'id': str(uuid.uuid4()),
            'texto': texto
        }
        
        # 5. Guardar
        exito = historial_dao.agregar_interaccion(registro)
        
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
            'id': registro['id']
        })
    
    except json.JSONDecodeError:
        return formatear_respuesta_error(
            400,
            'JSON inválido',
            'El body debe ser JSON válido'
        )
    
    except Exception as e:
        print(f"Error agregando historial: {str(e)}")
        print(traceback.format_exc())
        return formatear_respuesta_error(
            500,
            'Error interno',
            'Ocurrió un error procesando la solicitud'
        )