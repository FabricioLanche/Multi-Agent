"""
Handler principal para iniciar conversación con el agente
"""
import json
import traceback
from services.agente_service import AgenteService
from services.auth_service import AuthService
from utils.exceptions import UsuarioNoEncontradoError, ContextoInvalidoError
from utils.formatters import formatear_respuesta_exitosa, formatear_respuesta_error

# Instancia global del servicio (reutilizada entre invocaciones Lambda)
agente_service = None

def get_agente_service():
    """Lazy loading del servicio para reutilizar conexiones"""
    global agente_service
    if agente_service is None:
        agente_service = AgenteService()
    return agente_service


def handler(event, context):
    """
    Handler Lambda para procesar consultas del agente
    
    Espera un body JSON con:
    {
        "mensaje": "¿Cómo estoy con mis medicamentos?",
        "contexto": "General|Servicios|Estadisticas|Recetas"
    }
    
    El correo del usuario se extrae automáticamente del token de Authorization
    
    Returns:
        Response JSON con la respuesta del agente
    """
    try:
        # 1. Obtener usuario desde token (igual que API-REGISTRO)
        usuario = AuthService.get_user_from_token(event)
        
        if not usuario:
            return formatear_respuesta_error(
                401,
                'No autorizado',
                'Token inválido o usuario no encontrado'
            )
        
        correo = usuario['correo']
        print(f"✅ Usuario autenticado: {correo}")
        
        # 2. Parsear body
        body = json.loads(event.get('body', '{}'))
        
        # 3. Validar campos requeridos
        mensaje = body.get('mensaje')
        contexto = body.get('contexto', 'General')
        
        if not mensaje:
            return formatear_respuesta_error(
                400,
                'Campo requerido',
                'El campo "mensaje" es obligatorio'
            )
        
        # Validar contexto
        contextos_validos = ['General', 'Servicios', 'Estadisticas', 'Recetas']
        if contexto not in contextos_validos:
            return formatear_respuesta_error(
                400,
                'Contexto inválido',
                f'El contexto debe ser uno de: {", ".join(contextos_validos)}'
            )
        
        # 4. Procesar consulta
        service = get_agente_service()
        resultado = service.procesar_consulta(
            correo=correo,
            contexto=contexto,
            mensaje_usuario=mensaje,
            historial_conversacion=None  # Por ahora sin historial
        )
        
        # 5. Guardar en memoria automáticamente
        service.guardar_memoria_conversacion(
            correo=correo,
            mensaje_usuario=mensaje,
            respuesta_agente=resultado['respuesta']
        )
        
        # 6. Retornar respuesta exitosa
        return formatear_respuesta_exitosa(resultado)
    
    except UsuarioNoEncontradoError as e:
        return formatear_respuesta_error(404, 'Usuario no encontrado', str(e))
    
    except ContextoInvalidoError as e:
        return formatear_respuesta_error(400, 'Contexto inválido', str(e))
    
    except json.JSONDecodeError:
        return formatear_respuesta_error(400, 'JSON inválido', 'El body debe ser JSON válido')
    
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        print(traceback.format_exc())
        return formatear_respuesta_error(
            500,
            'Error interno del servidor',
            'Ocurrió un error procesando tu solicitud'
        )