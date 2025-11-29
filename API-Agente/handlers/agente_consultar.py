"""
Handler principal para consultas a los agentes académicos
"""
import json
import traceback
import uuid
from datetime import datetime

from services.agente_service import AgenteService
from dao.base import DAOFactory
from utils.formatters import formatear_respuesta_exitosa, formatear_respuesta_error
from utils.validators import validar_email, validar_contexto


def handler(event, context):
    """
    Handler para consultas a los agentes especializados
    
    Espera un body JSON con:
    {
        "correo": "estudiante@example.com",
        "contexto": "MentorAcademico" | "OrientadorVocacional" | "Psicologo",
        "mensaje": "¿Cómo puedo mejorar mi promedio?"
    }
    
    Proceso:
    1. Valida el correo y obtiene el usuario
    2. Verifica autorización del usuario
    3. Carga el historial previo automáticamente
    4. Genera respuesta con el agente
    5. Guarda un resumen en el historial
    """
    try:
        # 1. Parsear body
        body = json.loads(event.get('body', '{}'))
        
        # 2. Validar campos requeridos
        correo = body.get('correo')
        contexto = body.get('contexto')
        mensaje = body.get('mensaje')
        
        if not correo or not validar_email(correo):
            return formatear_respuesta_error(
                400,
                'Email inválido',
                'Se requiere un email válido'
            )
        
        if not contexto or not validar_contexto(contexto):
            return formatear_respuesta_error(
                400,
                'Contexto inválido',
                f'El contexto debe ser uno de: MentorAcademico, OrientadorVocacional, Psicologo'
            )
        
        if not mensaje or len(mensaje.strip()) == 0:
            return formatear_respuesta_error(
                400,
                'Mensaje requerido',
                'Se requiere un mensaje no vacío'
            )
        
        if len(mensaje) > 5000:
            return formatear_respuesta_error(
                400,
                'Mensaje muy largo',
                'El mensaje no puede exceder 5000 caracteres'
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
        
        # 4. Verificar autorización
        if not usuario.get('autorizacion', False):
            return formatear_respuesta_error(
                403,
                'Autorización requerida',
                'El usuario no ha autorizado la recopilación de datos. '
                'Debe activar la autorización antes de usar los agentes.'
            )
        
        usuario_id = usuario['id']
        
        # 5. Cargar historial previo automáticamente
        historial_dao = DAOFactory.get_dao('historial')
        historial_previo = historial_dao.get_historial_usuario(correo, limit=10)
        
        # Convertir historial a formato de conversación
        # El historial contiene resúmenes de interacciones previas
        conversacion_previa = []
        for item in historial_previo:
            conversacion_previa.append({
                'role': 'assistant',
                'content': f"[Interacción previa]: {item.get('texto', '')}"
            })
        
        # 6. Procesar consulta con el servicio del agente
        agente_service = AgenteService()
        resultado = agente_service.procesar_consulta(
            correo=correo,
            contexto=contexto,
            mensaje_usuario=mensaje,
            historial_conversacion=conversacion_previa
        )
        
        # 7. Generar resumen de la interacción
        resumen = agente_service.generar_resumen_interaccion(
            mensaje_usuario=mensaje,
            respuesta_agente=resultado['respuesta'],
            contexto=contexto
        )
        
        # 8. Guardar resumen en historial
        registro_historial = {
            'usuarioId': usuario_id,
            'id': str(uuid.uuid4()),
            'texto': resumen
        }
        
        exito_guardado = historial_dao.agregar_interaccion(registro_historial)
        
        if not exito_guardado:
            print(f"⚠️ No se pudo guardar en historial para usuario {correo}")
        
        # 9. Retornar respuesta
        return formatear_respuesta_exitosa({
            'respuesta': resultado['respuesta'],
            'contexto': contexto,
            'timestamp': datetime.now().isoformat(),
            'historial_guardado': exito_guardado,
            'usuario': {
                'correo': correo,
                'id': usuario_id
            }
        })
    
    except json.JSONDecodeError:
        return formatear_respuesta_error(
            400,
            'JSON inválido',
            'El body debe ser JSON válido'
        )
    
    except ValueError as e:
        return formatear_respuesta_error(
            400,
            'Error de validación',
            str(e)
        )
    
    except Exception as e:
        print(f"❌ Error en agente_consultar: {str(e)}")
        print(traceback.format_exc())
        return formatear_respuesta_error(
            500,
            'Error interno del servidor',
            'Ocurrió un error procesando la consulta'
        )