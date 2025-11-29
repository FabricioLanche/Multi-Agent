"""
Servicios principales del sistema de agentes académicos
"""
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from dao.base import DAOFactory
from contextos.base_contexto import ContextoFactory
from services.gemini_service import GeminiService
from config import Config


# ===== EXCEPCIONES PERSONALIZADAS =====
class UsuarioNoEncontradoError(Exception):
    """Usuario no existe en la base de datos"""
    pass


class ContextoInvalidoError(Exception):
    """Contexto solicitado no es válido"""
    pass


# ===== SERVICIO PRINCIPAL DEL AGENTE =====
class AgenteService:
    """Servicio principal que orquesta la lógica del agente académico"""
    
    def __init__(self):
        """Inicializa el servicio y sus dependencias"""
        self.gemini_service = GeminiService()
        self.usuarios_dao = DAOFactory.get_dao('usuarios')
        self.historial_dao = DAOFactory.get_dao('historial')
    
    def procesar_consulta(
        self,
        correo: str,
        contexto: str,
        mensaje_usuario: str,
        historial_conversacion: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Procesa una consulta del usuario con el agente especializado
        
        Args:
            correo: Email del usuario
            contexto: Tipo de contexto (MentorAcademico, OrientadorVocacional, Psicologo)
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
        
        # 2. Validar que usuario existe
        usuario = self.usuarios_dao.get_usuario_por_correo(correo)
        if not usuario:
            raise UsuarioNoEncontradoError(
                f"Usuario con correo '{correo}' no encontrado"
            )
        
        # 3. Obtener procesador de contexto
        procesador = ContextoFactory.get_contexto(contexto)
        
        # 4. Construir datos del contexto
        datos_contexto = procesador.build_context_data(correo)
        
        # 5. Construir prompt completo
        usuario_data = datos_contexto.get('usuario', usuario)
        historial_data = datos_contexto.get('historial', [])
        
        prompt_sistema = procesador.get_prompt_instructions(
            usuario=usuario_data,
            historial=historial_data,
            datos_contexto=datos_contexto
        )
        
        # 6. Construir mensajes para Gemini
        mensajes = [
            {'role': 'system', 'content': prompt_sistema}
        ]
        
        # Agregar historial de la conversación actual si existe
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
                'id': usuario.get('id')
            }
        }
    
    def guardar_interaccion(
        self,
        correo: str,
        texto: str
    ) -> bool:
        """
        Guarda una interacción en el historial del usuario
        
        Args:
            correo: Email del usuario
            texto: Texto de la interacción a guardar
        
        Returns:
            True si se guardó exitosamente
        """
        try:
            # Obtener usuario
            usuario = self.usuarios_dao.get_usuario_por_correo(correo)
            if not usuario:
                print(f"Usuario {correo} no encontrado para guardar historial")
                return False
            
            # Preparar registro
            registro = {
                'usuarioId': usuario['id'],
                'id': str(uuid.uuid4()),
                'texto': texto
            }
            
            return self.historial_dao.agregar_interaccion(registro)
        
        except Exception as e:
            print(f"Error guardando interacción: {str(e)}")
            return False
    
    def obtener_historial_usuario(
        self,
        correo: str,
        limite: Optional[int] = None
    ) -> List[Dict]:
        """
        Obtiene el historial de interacciones de un usuario
        
        Args:
            correo: Email del usuario
            limite: Número máximo de registros a retornar
        
        Returns:
            Lista de interacciones
        """
        try:
            return self.historial_dao.get_historial_usuario(
                correo,
                limit=limite
            )
        except Exception as e:
            print(f"Error obteniendo historial: {str(e)}")
            return []