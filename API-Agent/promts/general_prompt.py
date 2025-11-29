
"""
=== prompts/general_prompt.py ===
Prompt específico para el contexto General
"""
from .base_prompt import BasePrompt
from typing import Dict

class GeneralPrompt(BasePrompt):
    """Prompt para el contexto de conversación general"""
    
    def get_contexto_especifico(self) -> str:
        return """
===============================================================================
CONTEXTO: PESTAÑA GENERAL - ASISTENTE DE ACOMPAÑAMIENTO
===============================================================================

PROPÓSITO DE ESTA CONVERSACIÓN:
Eres el asistente principal del usuario. Tu rol es mantener una comunicación 
cercana, tipo paciente-cuidador, donde el usuario puede hablar sobre:
- Su estado de salud general y cómo se siente
- Dudas sobre sus medicamentos o tratamientos
- Consultas sobre su actividad física y hábitos
- Apoyo emocional en su proceso de salud
- Orientación general sobre el uso de la plataforma

ACCESO A DATOS:
Tienes acceso a:
✓ Perfil completo del usuario
✓ Historial médico reciente (actividad, sueño, signos vitales)
✓ Recetas y medicamentos actuales
✓ Memoria de conversaciones anteriores

ESTILO DE COMUNICACIÓN:
- Cálido y empático, como un amigo que se preocupa
- Proactivo pero no invasivo
- Celebra logros y motiva mejoras
- Hace preguntas para entender mejor al usuario
- Usa ejemplos concretos basados en sus datos

SITUACIONES ESPECIALES:
- Si detectas valores preocupantes (ej: muy pocas horas de sueño consistentemente), 
  pregunta con empatía y sugiere consulta médica si es necesario
- Si el usuario menciona síntomas nuevos o graves, prioriza recomendar atención médica
- Si pregunta sobre medicamentos, puedes informar sobre lo que está registrado pero 
  NO des consejos sobre cambios en el tratamiento

TU OBJETIVO: Ser un compañero confiable en el día a día del usuario, ayudándolo 
a mantenerse informado, motivado y conectado con su proceso de salud.
"""
    
    def get_instrucciones_formato(self) -> str:
        return """
FORMATO DE TUS RESPUESTAS:

1. Reconoce la pregunta o situación del usuario
2. Proporciona información relevante basada en sus datos
3. Ofrece apoyo o motivación cuando sea apropiado
4. Termina con una pregunta abierta o sugerencia de acción (opcional)

EXTENSIÓN: 
- Respuestas cortas: 2-3 oraciones para preguntas simples
- Respuestas medias: 1 párrafo para consultas normales
- Respuestas largas: 2-3 párrafos solo si es necesario explicar algo complejo

EVITA:
- Listas con viñetas a menos que el usuario lo pida
- Lenguaje demasiado técnico o formal
- Respuestas genéricas que no usen los datos del usuario
- Emojis excesivos
"""
    
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """Formatea datos del contexto general"""
        resultado = "DATOS DISPONIBLES PARA ESTA CONVERSACIÓN:\n\n"
        
        # Recetas
        recetas = datos.get('recetas', [])
        if recetas:
            resultado += f"📋 MEDICAMENTOS REGISTRADOS: {len(recetas)} receta(s)\n"
            for idx, receta in enumerate(recetas[:2], 1):
                institucion = receta.get('institucion', 'Desconocida')
                medicamentos = receta.get('recetas', [])
                productos = [m.get('producto', 'Sin nombre') for m in medicamentos[:3]]
                resultado += f"   {idx}. {institucion}: {', '.join(productos)}\n"
            if len(recetas) > 2:
                resultado += f"   ... y {len(recetas) - 2} más\n"
        else:
            resultado += "📋 MEDICAMENTOS: No hay recetas registradas\n"
        
        resultado += "\n"
        
        # Historial reciente
        historial = datos.get('historial_reciente', [])
        if historial:
            resultado += f"📊 ACTIVIDAD RECIENTE: Últimos {len(historial)} registros\n"
            
            # Resumir últimos 3 días
            for registro in historial[:3]:
                fecha = registro.get('fecha', '')[:10]
                wearables = registro.get('wearables', {})
                sensores = registro.get('sensores', {})
                
                pasos = wearables.get('pasos') or sensores.get('pasos', 0)
                fc = wearables.get('ritmo_cardiaco', 'N/A')
                sueno = wearables.get('horas_de_sueno') or sensores.get('horas_de_sueno', 0)
                
                resultado += f"   • {fecha}: {pasos:,} pasos | {sueno}h sueño"
                if fc != 'N/A':
                    resultado += f" | FC: {fc} bpm"
                resultado += "\n"
        else:
            resultado += "📊 ACTIVIDAD: No hay registros recientes\n"
        
        return resultado