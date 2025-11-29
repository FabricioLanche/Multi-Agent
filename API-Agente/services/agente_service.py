"""
Servicio principal del agente - Orquestador
"""
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from dao.base import DAOFactory
from contextos.base_contexto import ContextoFactory
from services.gemini_service import GeminiService
from utils.exceptions import UsuarioNoEncontradoError, ContextoInvalidoError
from config import Config


class AgenteService:
    """Servicio principal que orquesta la lógica del agente"""
    
    def __init__(self):
        """Inicializa el servicio y sus dependencias"""
        self.gemini_service = GeminiService()
        self.usuarios_dao = DAOFactory.get_dao('usuarios')
        self.memoria_dao = DAOFactory.get_dao('memoria')
    
    def procesar_consulta(
        self,
        correo: str,
        contexto: str,
        mensaje_usuario: str,
        historial_conversacion: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Procesa una consulta del usuario
        
        Args:
            correo: Email del usuario
            contexto: Tipo de contexto (General, Servicios, etc.)
            mensaje_usuario: Mensaje del usuario
            historial_conversacion: Historial previo de la conversación
        
        Returns:
            Diccionario con la respuesta del agente
        
        Raises:
            UsuarioNoEncontradoError: Si el usuario no existe
            ContextoInvalidoError: Si el contexto no es válido
        """
        # 1. Validar contexto
        if contexto not in Config.CONTEXTOS_DISPONIBLES:
            raise ContextoInvalidoError(
                f"Contexto '{contexto}' no válido. "
                f"Disponibles: {Config.CONTEXTOS_DISPONIBLES}"
            )
        
        # 2. Validar usuario existe
        usuario = self.usuarios_dao.get_usuario(correo)
        if not usuario:
            raise UsuarioNoEncontradoError(f"Usuario con correo '{correo}' no encontrado")
        
        # 3. Obtener procesador de contexto
        procesador = ContextoFactory.get_contexto(contexto)
        
        # 4. Construir datos del contexto
        datos_contexto = procesador.build_context_data(correo)
        
        # 5. Construir prompt completo
        usuario_data = datos_contexto.get('usuario', usuario)
        memoria_data = datos_contexto.get('memoria', [])
        
        prompt_sistema = procesador.get_prompt_instructions(
            usuario=usuario_data,
            memoria=memoria_data,
            datos_contexto=datos_contexto
        )
        
        # 6. Construir mensajes para Gemini
        mensajes = [
            {'role': 'system', 'content': prompt_sistema}
        ]
        
        # Agregar historial si existe
        if historial_conversacion:
            for msg in historial_conversacion[-5:]:  # Últimos 5 mensajes
                mensajes.append({
                    'role': msg.get('role', 'user'),
                    'content': msg.get('content', '')
                })
        
        # Agregar mensaje actual del usuario
        mensajes.append({
            'role': 'user',
            'content': mensaje_usuario
        })
        
        # 7. Generar respuesta con Gemini
        respuesta_agente = self.gemini_service.generar_respuesta(mensajes)
        
        # 8. Retornar resultado
        return {
            'respuesta': respuesta_agente,
            'contexto': contexto,
            'timestamp': datetime.now().isoformat(),
            'usuario': {
                'correo': correo,
                'nombre': usuario.get('nombre', 'Usuario')
            }
        }
    
    def guardar_memoria_conversacion(
        self,
        correo: str,
        mensaje_usuario: str,
        respuesta_agente: str,
        intencion_detectada: Optional[str] = None
    ) -> bool:
        """
        Guarda el registro de una conversación en la memoria contextual
        
        Args:
            correo: Email del usuario
            mensaje_usuario: Mensaje original del usuario
            respuesta_agente: Respuesta generada
            intencion_detectada: Intención detectada (opcional)
        
        Returns:
            True si se guardó exitosamente
        """
        try:
            memoria = {
                'correo': correo,
                'context_id': f"ctx-{uuid.uuid4().hex[:8]}",
                'fecha': datetime.now().isoformat(),
                'resumen_conversacion': f"Usuario: {mensaje_usuario[:100]}... | Agente: {respuesta_agente[:100]}...",
                'intencion_detectada': intencion_detectada or 'consulta_general',
                'datos_extraidos': {
                    'mensaje_usuario': mensaje_usuario,
                    'respuesta_agente': respuesta_agente
                }
            }
            
            return self.memoria_dao.guardar_memoria(memoria)
        
        except Exception as e:
            print(f"Error guardando memoria: {str(e)}")
            return False
    
    def obtener_sugerencias_contexto(
        self,
        correo: str,
        contexto: str
    ) -> Dict:
        """
        Genera sugerencias proactivas basadas en el contexto
        
        Args:
            correo: Email del usuario
            contexto: Tipo de contexto
        
        Returns:
            Diccionario con sugerencias
        """
        try:
            # Validar usuario
            usuario = self.usuarios_dao.get_usuario(correo)
            if not usuario:
                return {'sugerencias': []}
            
            # Obtener procesador de contexto
            procesador = ContextoFactory.get_contexto(contexto)
            datos_contexto = procesador.build_context_data(correo)
            
            # Generar sugerencias según el contexto
            sugerencias = self._generar_sugerencias_para_contexto(
                contexto, 
                datos_contexto
            )
            
            return {
                'sugerencias': sugerencias,
                'contexto': contexto,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"Error obteniendo sugerencias: {str(e)}")
            return {'sugerencias': []}
    
    def _generar_sugerencias_para_contexto(
        self,
        contexto: str,
        datos: Dict
    ) -> List[str]:
        """
        Genera sugerencias específicas por contexto
        
        Args:
            contexto: Nombre del contexto
            datos: Datos del contexto
        
        Returns:
            Lista de sugerencias
        """
        sugerencias = []
        
        if contexto == 'General':
            # Sugerencias basadas en actividad reciente
            historial = datos.get('historial_reciente', [])
            if historial:
                sugerencias.append("¿Cómo te has sentido últimamente?")
                sugerencias.append("¿Quieres revisar tu progreso de la semana?")
        
        elif contexto == 'Recetas':
            recetas = datos.get('recetas', [])
            if recetas:
                sugerencias.append("¿Necesitas ayuda con tus medicamentos?")
                sugerencias.append("¿Quieres que revise tus recetas activas?")
        
        elif contexto == 'Servicios':
            sugerencias.append("¿Te gustaría conocer servicios disponibles?")
            sugerencias.append("¿Hay algún evento o taller que te interese?")
        
        elif contexto == 'Estadisticas':
            historial = datos.get('historial', [])
            if historial:
                sugerencias.append("¿Quieres ver tu resumen del mes?")
                sugerencias.append("¿Te interesa conocer tus tendencias de actividad?")
        
        return sugerencias
