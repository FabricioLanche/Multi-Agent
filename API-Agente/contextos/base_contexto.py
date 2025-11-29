"""
Clase base abstracta para todos los contextos del agente académico
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dao.base import DAOFactory


class BaseContexto(ABC):
    """Clase base para procesadores de contexto académico"""
    
    def __init__(self):
        # Inicializar DAOs necesarios
        self.usuarios_dao = DAOFactory.get_dao('usuarios')
        self.historial_dao = DAOFactory.get_dao('historial')
    
    @abstractmethod
    def get_tablas_requeridas(self) -> List[str]:
        """
        Define qué tablas necesita este contexto
        
        Returns:
            Lista de nombres de tablas requeridas
        """
        pass
    
    @abstractmethod
    def build_context_data(self, correo: str) -> Dict:
        """
        Construye el diccionario de datos del contexto
        
        Args:
            correo: Email del usuario
        
        Returns:
            Diccionario con todos los datos necesarios para el contexto
        """
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Obtiene el prompt base del sistema para este contexto
        
        Returns:
            String con el prompt del sistema
        """
        pass
    
    def get_prompt_instructions(
        self, 
        usuario: Dict, 
        historial: List[Dict], 
        datos_contexto: Dict
    ) -> str:
        """
        Construye las instrucciones completas del prompt incluyendo datos del usuario
        
        Args:
            usuario: Datos del usuario
            historial: Historial de interacciones
            datos_contexto: Datos específicos del contexto
        
        Returns:
            Prompt completo formateado
        """
        system_prompt = self.get_system_prompt()
        
        # Construir contexto del usuario
        contexto_usuario = self._formatear_contexto_usuario(usuario)
        
        # Construir historial
        contexto_historial = self._formatear_historial(historial)
        
        # Construir datos específicos del contexto  
        contexto_datos = self._formatear_datos_contexto(datos_contexto)
        
        # Ensamblar prompt completo
        prompt_completo = f"""
{system_prompt}

--- INFORMACIÓN DEL USUARIO ---
{contexto_usuario}

--- HISTORIAL DE INTERACCIONES PREVIAS ---
{contexto_historial}

--- DATOS DEL CONTEXTO ACTUAL ---
{contexto_datos}

Recuerda: Eres un asistente de acompañamiento académico. NO tomes decisiones por el estudiante.
Analiza los datos disponibles y ofrece orientación, apoyo y sugerencias basadas en información objetiva.
"""
        return prompt_completo
    
    def _formatear_contexto_usuario(self, usuario: Dict) -> str:
        """Formatea la información básica del usuario"""
        if not usuario:
            return "No hay información del usuario disponible."
        
        return f"""
ID: {usuario.get('id', 'No especificado')}
Correo: {usuario.get('correo', 'No especificado')}
Autorización de datos: {usuario.get('autorizacion', False)}
"""
    
    def _formatear_historial(self, historial: List[Dict]) -> str:
        """Formatea el historial de interacciones"""
        if not historial:
            return "No hay interacciones previas registradas."
        
        historial_formateado = []
        for idx, item in enumerate(historial[:5], 1):  # Últimas 5 interacciones
            texto = item.get('texto', 'Sin contenido')
            historial_formateado.append(f"{idx}. {texto[:150]}...")
        
        return "\n".join(historial_formateado)
    
    @abstractmethod
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """
        Formatea los datos específicos del contexto
        Debe ser implementado por cada contexto específico
        
        Args:
            datos: Diccionario con datos del contexto
        
        Returns:
            String formateado con los datos
        """
        pass
    
    def cargar_datos_base(self, correo: str) -> Dict:
        """
        Carga los datos base que todos los contextos necesitan
        
        Args:
            correo: Email del usuario
        
        Returns:
            Diccionario con usuario e historial
        """
        usuario = self.usuarios_dao.get_usuario_por_correo(correo)
        historial = self.historial_dao.get_historial_usuario(correo) if usuario else []
        
        return {
            'usuario': usuario,
            'historial': historial
        }
    
    def validar_usuario(self, correo: str) -> bool:
        """
        Valida que el usuario exista en la base de datos
        
        Args:
            correo: Email del usuario
        
        Returns:
            True si el usuario existe, False en caso contrario
        """
        return self.usuarios_dao.existe_usuario(correo)


# ===== FACTORY PARA CONTEXTOS =====
class ContextoFactory:
    """Factory para crear instancias de contextos"""
    
    _contextos = {}  # Will be populated lazily
    
    @classmethod
    def _lazy_load_contextos(cls):
        """Lazy load contexto classes to avoid circular imports"""
        if not cls._contextos:
            from .mentor_academico_contexto import MentorAcademicoContexto
            from .orientador_vocacional_contexto import OrientadorVocacionalContexto
            from .psicologo_contexto import PsicologoContexto
            
            cls._contextos = {
                'MentorAcademico': MentorAcademicoContexto,
                'OrientadorVocacional': OrientadorVocacionalContexto,
                'Psicologo': PsicologoContexto
            }
    
    @classmethod
    def get_contexto(cls, nombre_contexto: str) -> BaseContexto:
        """
        Obtiene una instancia del contexto solicitado
        
        Args:
            nombre_contexto: Nombre del contexto
        
        Returns:
            Instancia del contexto
        
        Raises:
            ValueError: Si el contexto no existe
        """
        cls._lazy_load_contextos()
        
        if nombre_contexto not in cls._contextos:
            raise ValueError(
                f"Contexto '{nombre_contexto}' no existe. "
                f"Contextos disponibles: {list(cls._contextos.keys())}"
            )
        
        return cls._contextos[nombre_contexto]()
    
    @classmethod
    def get_contextos_disponibles(cls) -> List[str]:
        """Retorna lista de contextos disponibles"""
        cls._lazy_load_contextos()
        return list(cls._contextos.keys())