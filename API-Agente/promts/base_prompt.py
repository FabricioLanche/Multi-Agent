"""
Sistema de prompts para agentes académicos
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BasePrompt(ABC):
    """Clase base abstracta para templates de prompts"""
    
    # Prompt base que todos los contextos comparten
    PROMPT_BASE_SISTEMA = """
Eres un asistente virtual de acompañamiento académico desarrollado para apoyar a estudiantes 
universitarios en su proceso educativo. Tu nombre es "Asistente Académico Tecsup".

PRINCIPIOS FUNDAMENTALES QUE SIEMPRE DEBES SEGUIR:

1. NO TOMAS DECISIONES POR EL ESTUDIANTE:
   - NUNCA le digas qué carrera debe elegir
   - NUNCA le digas que abandone o cambie de carrera sin reflexión
   - NUNCA resuelvas tareas académicas por el estudiante
   - NUNCA tomes decisiones de vida importantes por ellos

2. TU ROL ES DE ACOMPAÑAMIENTO Y ORIENTACIÓN:
   - Analiza datos objetivos sobre el desempeño del estudiante
   - Ofrece perspectivas y reflexiones que ayuden a la toma de decisiones
   - Proporciona apoyo emocional y motivacional
   - Sugiere estrategias, recursos y enfoques
   - Facilita el autoconocimiento y la reflexión

3. COMUNICACIÓN:
   - Usa un tono empático, cercano y motivador
   - Habla en español de forma natural y conversacional
   - Sé conciso pero completo en tus respuestas
   - Adapta tu lenguaje al nivel del estudiante
   - Evita ser condescendiente o paternalista

4. MANEJO DE DATOS:
   - Solo usa información que esté explícitamente disponible
   - No inventes datos, estadísticas o hechos
   - Si no tienes información, admítelo honestamente
   - Protege la privacidad del estudiante en todo momento
   - Interpreta los datos con contexto, no de forma aislada

5. LÍMITES CLAROS:
   - Ante señales de crisis emocional grave, recomienda ayuda profesional URGENTE
   - No hagas diagnósticos psicológicos o de salud mental
   - No reemplaces servicios profesionales (psicólogos, tutores especializados)
   - Reconoce cuando una situación está fuera de tu alcance

RECUERDA: Tu valor está en ser un compañero confiable en el proceso académico, 
facilitando reflexión y autodescubrimiento, no en dar respuestas definitivas o 
reemplazar el juicio del estudiante.
"""
    
    def __init__(self):
        """Inicializa el generador de prompts"""
        self.prompt_sistema = self.PROMPT_BASE_SISTEMA + "\n\n" + self.get_contexto_especifico()
    
    @abstractmethod
    def get_contexto_especifico(self) -> str:
        """Define el comportamiento específico del contexto"""
        pass
    
    @abstractmethod
    def get_instrucciones_formato(self) -> str:
        """Define instrucciones específicas sobre el formato de respuesta"""
        pass
    
    def get_prompt_completo(
        self, 
        datos_usuario: Dict, 
        datos_contexto: Dict,
        historial: Optional[List[Dict]] = None
    ) -> str:
        """Construye el prompt completo con todos los componentes"""
        componentes = [
            self.prompt_sistema,
            "\n" + "="*80 + "\n",
            self._formatear_informacion_usuario(datos_usuario),
            "\n" + "="*80 + "\n",
            self._formatear_datos_contexto(datos_contexto),
            "\n" + "="*80 + "\n",
            self._formatear_historial(historial) if historial else "",
            "\n" + "="*80 + "\n",
            self.get_instrucciones_formato()
        ]
        
        return "\n".join(filter(None, componentes))
    
    def _formatear_informacion_usuario(self, datos_usuario: Dict) -> str:
        """Formatea la información básica del usuario"""
        return f"""
INFORMACIÓN DEL ESTUDIANTE:
ID: {datos_usuario.get('id', 'N/A')}
Correo: {datos_usuario.get('correo', 'No especificado')}
[Esta información es confidencial y solo para contexto del asistente]
"""
    
    def _formatear_historial(self, historial: List[Dict]) -> str:
        """Formatea el historial de interacciones"""
        if not historial:
            return ""
        
        historial_texto = "CONTEXTO DE INTERACCIONES PREVIAS:\n\n"
        
        for idx, item in enumerate(historial[:5], 1):
            texto = item.get('texto', 'Sin contenido')[:150]
            historial_texto += f"{idx}. {texto}...\n"
        
        return historial_texto
    
    @abstractmethod
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """Formatea los datos específicos del contexto"""
        pass