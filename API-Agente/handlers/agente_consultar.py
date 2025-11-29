"""
Handlers Lambda para los agentes académicos
"""
import json
import traceback
import uuid
from datetime import datetime

from services.agente_service import AgenteService
from dao.base import DAOFactory
from utils.formatters import formatear_respuesta_exitosa, formatear_respuesta_error
from utils.validators import validar_email, validar_request_agente


# ===== HANDLER: CONSULTA AL AGENTE =====
def agente_consultar_handler(event, context):
    """
    Handler para consultas a los agentes especializados
    
    Espera un body JSON con:
    {
        "correo": "estudiante@example.com",
        "contexto": "MentorAcademico" | "OrientadorVocacional" | "Psicologo",
        "mensaje": "¿Cómo puedo mejorar mi promedio?",
        "historial": [...]  # Opcional
    }
    """
    try:
        # 1. Parsear body
        body = json.loads(event.get('body', '{}'))
        
        # 2. Validar request
        errores = validar_request_agente(body)
        if errores:
            return formatear_respuesta_error(
                400,
                'Datos inválidos',
                {'errores': errores}
            )
        
        # 3. Extraer datos
        correo = body['correo']
        contexto = body['contexto']
        mensaje = body['mensaje']
        historial = body.get('historial', [])
        
        # 4. Procesar con el servicio del agente
        agente_service = AgenteService()
        resultado = agente_service.procesar_consulta(
            correo=correo,
            contexto=contexto,
            mensaje_usuario=mensaje,
            historial_conversacion=historial
        )
        
        # 5. Guardar en historial
        texto_historial = f"[{contexto}] Usuario: {mensaje[:100]}... | Agente: {resultado['respuesta'][:100]}..."
        agente_service.guardar_interaccion(
            correo=correo,
            texto=texto_historial
        )
        
        # 6. Retornar respuesta
        return formatear_respuesta_exitosa(resultado)
    
    except ValueError as e:
        # Errores de validación o contexto
        return formatear_respuesta_error(
            400,
            'Error de validación',
            str(e)
        )
    
    except json.JSONDecodeError:
        return formatear_respuesta_error(
            400,
            'JSON inválido',
            'El body debe ser JSON válido'
        )
    
    except Exception as e:
        print(f"Error en agente_consultar: {str(e)}")
        print(traceback.format_exc())
        return formatear_respuesta_error(
            500,
            'Error interno del servidor',
            'Ocurrió un error procesando la consulta'
        )
