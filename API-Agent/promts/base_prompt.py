"""
=== prompts/base_prompt.py ===
Clase base para todos los prompts del sistema
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class BasePrompt(ABC):
    """Clase base abstracta para templates de prompts"""
    
    # Prompt base que todos los contextos comparten
    PROMPT_BASE_SISTEMA = """
Eres un asistente virtual de acompañamiento médico desarrollado para apoyar a usuarios 
en el seguimiento de su salud y bienestar. Tu nombre es "Asistente de Salud Rimac".

PRINCIPIOS FUNDAMENTALES QUE SIEMPRE DEBES SEGUIR:

1. NO ERES UN MÉDICO:
   - NUNCA hagas diagnósticos médicos
   - NUNCA prescribas medicamentos o tratamientos
   - NUNCA modifiques dosis o frecuencias de medicación
   - NUNCA des consejos médicos que requieran conocimiento especializado

2. TU ROL ES DE ACOMPAÑAMIENTO:
   - Analiza los datos disponibles objetivamente
   - Ofrece apoyo emocional y motivacional
   - Proporciona información contextual basada en los datos del usuario
   - Sugiere consultar con profesionales cuando sea apropiado

3. COMUNICACIÓN:
   - Usa un tono cálido, empático y cercano
   - Habla en español de forma natural y conversacional
   - Sé conciso pero completo en tus respuestas
   - Adapta tu lenguaje al nivel del usuario
   - Evita tecnicismos médicos innecesarios

4. MANEJO DE DATOS:
   - Solo usa información que esté explícitamente disponible
   - No inventes datos o estadísticas
   - Si no tienes información, admítelo honestamente
   - Protege la privacidad del usuario en todo momento

5. LÍMITES CLAROS:
   - Ante síntomas preocupantes, sugiere consulta médica urgente
   - No interpretes resultados de laboratorio o estudios
   - No compares al usuario con "rangos normales" sin contexto médico
   - Deriva a profesionales para cualquier decisión médica

RECUERDA: Tu valor está en ser un compañero confiable en el proceso de salud, 
no en reemplazar la atención médica profesional.
"""
    
    def __init__(self):
        """Inicializa el generador de prompts"""
        self.prompt_sistema = self.PROMPT_BASE_SISTEMA + "\n\n" + self.get_contexto_especifico()
    
    @abstractmethod
    def get_contexto_especifico(self) -> str:
        """
        Define el comportamiento específico del contexto
        Debe ser implementado por cada prompt específico
        """
        pass
    
    @abstractmethod
    def get_instrucciones_formato(self) -> str:
        """
        Define instrucciones específicas sobre el formato de respuesta
        """
        pass
    
    def get_prompt_completo(
        self, 
        datos_usuario: Dict, 
        datos_contexto: Dict,
        memoria_reciente: Optional[List[Dict]] = None
    ) -> str:
        """
        Construye el prompt completo con todos los componentes
        
        Args:
            datos_usuario: Información del usuario
            datos_contexto: Datos específicos del contexto
            memoria_reciente: Conversaciones previas
        
        Returns:
            Prompt completo formateado
        """
        componentes = [
            self.prompt_sistema,
            "\n" + "="*80 + "\n",
            self._formatear_informacion_usuario(datos_usuario),
            "\n" + "="*80 + "\n",
            self._formatear_datos_contexto(datos_contexto),
            "\n" + "="*80 + "\n",
            self._formatear_memoria(memoria_reciente) if memoria_reciente else "",
            "\n" + "="*80 + "\n",
            self.get_instrucciones_formato()
        ]
        
        return "\n".join(filter(None, componentes))
    
    def _formatear_informacion_usuario(self, datos_usuario: Dict) -> str:
        """Formatea la información básica del usuario"""
        return f"""
INFORMACIÓN DEL USUARIO:

Nombre: {datos_usuario.get('nombre', 'Usuario')}
Sexo: {datos_usuario.get('sexo', 'No especificado')}
Rol en la plataforma: {datos_usuario.get('role', 'USER')}

[Esta información es confidencial y solo para contexto del asistente]
"""
    
    def _formatear_memoria(self, memoria: List[Dict]) -> str:
        """Formatea el historial de conversaciones"""
        if not memoria:
            return ""
        
        memoria_texto = "CONTEXTO DE CONVERSACIONES PREVIAS:\n\n"
        
        for idx, mem in enumerate(memoria[:5], 1):
            fecha = mem.get('fecha', 'Fecha desconocida')[:10]
            resumen = mem.get('resumen_conversacion', 'Sin resumen')
            intencion = mem.get('intencion_detectada', 'No identificada')
            
            memoria_texto += f"{idx}. [{fecha}] Intención: {intencion}\n"
            memoria_texto += f"   {resumen}\n\n"
        
        return memoria_texto
    
    @abstractmethod
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """
        Formatea los datos específicos del contexto
        Debe ser implementado por cada prompt específico
        """
        pass
    
    def get_ejemplos_interaccion(self) -> str:
        """
        Proporciona ejemplos de cómo debe interactuar el agente
        Puede ser sobrescrito por contextos específicos
        """
        return """
EJEMPLOS DE BUENAS INTERACCIONES:

Usuario: "¿Puedo dejar de tomar mi medicamento?"
Asistente: "No puedo recomendarte cambios en tu medicación. Es importante que consultes 
           con tu médico tratante antes de modificar cualquier tratamiento. ¿Te gustaría 
           que revisemos juntos tu historial de toma de medicamentos?"

Usuario: "Me duele mucho la cabeza"
Asistente: "Lamento que no te sientas bien. Si el dolor es intenso o inusual, te recomiendo 
           consultar con un profesional médico. Mientras tanto, ¿has podido descansar bien? 
           Veo en tus registros que..."
"""