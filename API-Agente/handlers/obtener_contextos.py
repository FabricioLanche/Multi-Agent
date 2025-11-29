"""
Handlers Lambda para los agentes académicos
"""
import json
import traceback
import uuid
from datetime import datetime

# ===== HANDLER: OBTENER CONTEXTOS DISPONIBLES =====
def obtener_contextos_handler(event, context):
    """
    Handler simple para obtener la lista de contextos disponibles
    
    No requiere body, solo retorna la lista de agentes especializados
    """
    try:
        from contextos.base_contexto import ContextoFactory
        
        contextos = ContextoFactory.get_contextos_disponibles()
        
        return formatear_respuesta_exitosa({
            'contextos': contextos,
            'total': len(contextos),
            'descripciones': {
                'MentorAcademico': 'Ayuda con estrategias de estudio y rendimiento académico',
                'OrientadorVocacional': 'Orientación sobre carrera y decisiones profesionales',
                'Psicologo': 'Apoyo emocional y bienestar psicológico'
            }
        })
    
    except Exception as e:
        print(f"Error obteniendo contextos: {str(e)}")
        return formatear_respuesta_error(
            500,
            'Error interno',
            'No se pudieron obtener los contextos'
        )