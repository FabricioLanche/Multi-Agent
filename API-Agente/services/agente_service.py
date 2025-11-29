"""
Servicio principal del sistema de agentes académicos
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


class AutorizacionRequeridaError(Exception):
    """Usuario no ha autorizado la recopilación de datos"""
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
            historial_conversacion: Historial previo de conversaciones (ya cargado)
        
        Returns:
            Diccionario con la respuesta del agente
        
        Raises:
            UsuarioNoEncontradoError: Si el usuario no existe
            ContextoInvalidoError: Si el contexto no es válido
            AutorizacionRequeridaError: Si el usuario no ha autorizado
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
        
        # 3. Verificar autorización
        if not usuario.get('autorizacion', False):
            raise AutorizacionRequeridaError(
                f"Usuario {correo} no ha autorizado la recopilación de datos"
            )
        
        # 4. Obtener procesador de contexto
        procesador = ContextoFactory.get_contexto(contexto)
        
        # 5. Construir datos del contexto
        datos_contexto = procesador.build_context_data(correo)
        
        # 6. Construir prompt completo
        usuario_data = datos_contexto.get('usuario', usuario)
        historial_data = datos_contexto.get('historial', [])
        
        prompt_sistema = procesador.get_prompt_instructions(
            usuario=usuario_data,
            historial=historial_data,
            datos_contexto=datos_contexto
        )
        
        # 7. Construir mensajes para Gemini
        mensajes = [
            {'role': 'system', 'content': prompt_sistema}
        ]
        
        # Agregar historial de conversaciones previas si existe
        if historial_conversacion:
            # Limitar a las últimas 5-10 interacciones para no saturar el contexto
            for msg in historial_conversacion[-5:]:
                mensajes.append({
                    'role': msg.get('role', 'assistant'),
                    'content': msg.get('content', '')
                })
        
        # Agregar mensaje actual del usuario
        mensajes.append({
            'role': 'user',
            'content': mensaje_usuario
        })
        
        # 8. Generar respuesta con Gemini
        respuesta_agente = self.gemini_service.generar_respuesta(mensajes)
        
        # 9. Retornar resultado
        return {
            'respuesta': respuesta_agente,
            'contexto': contexto,
            'timestamp': datetime.now().isoformat(),
            'usuario': {
                'correo': correo,
                'id': usuario.get('id')
            }
        }
    
    def generar_resumen_interaccion(
        self,
        mensaje_usuario: str,
        respuesta_agente: str,
        contexto: str
    ) -> str:
        """
        Genera un resumen conciso de la interacción para guardar en historial
        
        Args:
            mensaje_usuario: Mensaje original del usuario
            respuesta_agente: Respuesta generada por el agente
            contexto: Contexto del agente utilizado
        
        Returns:
            String con el resumen de la interacción
        """
        try:
            # Construir prompt para generar resumen
            prompt_resumen = f"""
Genera un resumen muy conciso (máximo 150 caracteres) de esta interacción:

Contexto del agente: {contexto}
Usuario preguntó: {mensaje_usuario[:200]}
Agente respondió: {respuesta_agente[:300]}

Resumen debe capturar:
1. La intención principal del usuario
2. El tipo de orientación o ayuda brindada
3. Ser breve y claro

Formato del resumen: "[{contexto}] Usuario consultó sobre X. Se orientó sobre Y."

Resumen:
"""
            
            # Generar resumen con Gemini
            mensajes_resumen = [
                {'role': 'user', 'content': prompt_resumen}
            ]
            
            resumen = self.gemini_service.generar_respuesta(mensajes_resumen)
            
            # Limpiar y limitar longitud
            resumen = resumen.strip().replace('\n', ' ')
            if len(resumen) > 250:
                resumen = resumen[:247] + "..."
            
            return resumen
        
        except Exception as e:
            print(f"⚠️ Error generando resumen: {str(e)}")
            # Fallback: crear resumen manual simple
            contexto_emoji = {
                'MentorAcademico': '🎓',
                'OrientadorVocacional': '🧭',
                'Psicologo': '🧠'
            }.get(contexto, '💬')
            
            mensaje_corto = mensaje_usuario[:50].strip()
            return f"{contexto_emoji} [{contexto}] Usuario: {mensaje_corto}..."
    
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
                limit=limite or Config.LIMITE_HISTORIAL
            )
        except Exception as e:
            print(f"Error obteniendo historial: {str(e)}")
            return []