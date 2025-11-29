"""
Handler para activar/desactivar la autorización de recopilación de datos
"""
import json
import traceback
from datetime import datetime

from dao.base import DAOFactory
from utils.formatters import formatear_respuesta_exitosa, formatear_respuesta_error
from utils.validators import validar_email


def handler(event, context):
    """
    Handler para togglear la autorización de un usuario
    
    Espera un body JSON con:
    {
        "correo": "estudiante@example.com",
        "autorizacion": true | false
    }
    
    Proceso:
    1. Busca el usuario por correo
    2. Actualiza el campo autorizacion
    3. Retorna el nuevo estado
    """
    try:
        # 1. Parsear body
        body = json.loads(event.get('body', '{}'))
        
        # 2. Validar campos requeridos
        correo = body.get('correo')
        autorizacion = body.get('autorizacion')
        
        if not correo or not validar_email(correo):
            return formatear_respuesta_error(
                400,
                'Email inválido',
                'Se requiere un email válido'
            )
        
        if autorizacion is None or not isinstance(autorizacion, bool):
            return formatear_respuesta_error(
                400,
                'Campo autorizacion inválido',
                'El campo "autorizacion" debe ser true o false'
            )
        
        # 3. Obtener usuario por correo
        usuarios_dao = DAOFactory.get_dao('usuarios')
        usuario = usuarios_dao.get_usuario_por_correo(correo)
        
        if not usuario:
            return formatear_respuesta_error(
                404,
                'Usuario no encontrado',
                f'No existe usuario con correo {correo}'
            )
        
        # 4. Actualizar autorización
        usuario['autorizacion'] = autorizacion
        
        exito = usuarios_dao.actualizar_usuario(usuario)
        
        if not exito:
            return formatear_respuesta_error(
                500,
                'Error al actualizar',
                'No se pudo actualizar el estado de autorización'
            )
        
        # 5. Retornar éxito
        mensaje = (
            'Autorización activada. Ahora puedes usar los agentes académicos.'
            if autorizacion else
            'Autorización desactivada. No podrás usar los agentes hasta reactivarla.'
        )
        
        return formatear_respuesta_exitosa({
            'message': mensaje,
            'correo': correo,
            'autorizacion': autorizacion,
            'timestamp': datetime.now().isoformat(),
            'usuario': {
                'id': usuario['id'],
                'correo': usuario['correo']
            }
        })
    
    except json.JSONDecodeError:
        return formatear_respuesta_error(
            400,
            'JSON inválido',
            'El body debe ser JSON válido'
        )
    
    except Exception as e:
        print(f"❌ Error en toggle_autorizacion: {str(e)}")
        print(traceback.format_exc())
        return formatear_respuesta_error(
            500,
            'Error interno del servidor',
            'Ocurrió un error procesando la solicitud'
        )