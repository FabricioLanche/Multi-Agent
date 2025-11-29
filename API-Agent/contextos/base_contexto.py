"""
Clase base abstracta para todos los contextos del agente
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dao.base import DAOFactory


class BaseContexto(ABC):
    """Clase base para procesadores de contexto"""
    
    def __init__(self):
        # Inicializar DAOs necesarios
        self.usuarios_dao = DAOFactory.get_dao('usuarios')
        self.memoria_dao = DAOFactory.get_dao('memoria')
    
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
        memoria: List[Dict], 
        datos_contexto: Dict
    ) -> str:
        """
        Construye las instrucciones completas del prompt incluyendo datos del usuario
        
        Args:
            usuario: Datos del usuario
            memoria: Historial de conversaciones
            datos_contexto: Datos específicos del contexto
        
        Returns:
            Prompt completo formateado
        """
        system_prompt = self.get_system_prompt()
        
        # Construir contexto del usuario
        contexto_usuario = self._formatear_contexto_usuario(usuario)
        
        # Construir memoria contextual
        contexto_memoria = self._formatear_memoria(memoria)
        
        # Construir datos específicos del contexto  
        contexto_datos = self._formatear_datos_contexto(datos_contexto)
        
        # Ensamblar prompt completo
        prompt_completo = f"""
{system_prompt}

--- INFORMACIÓN DEL USUARIO ---
{contexto_usuario}

--- MEMORIA DE CONVERSACIONES ANTERIORES ---
{contexto_memoria}

--- DATOS DEL CONTEXTO ACTUAL ---
{contexto_datos}

Recuerda: Eres un asistente de acompañamiento médico. NO hagas diagnósticos ni prescripciones.
Analiza los datos disponibles y ofrece información contextual, apoyo emocional y orientación general.
"""
        return prompt_completo
    
    def _formatear_contexto_usuario(self, usuario: Dict) -> str:
        """Formatea la información básica del usuario"""
        if not usuario:
            return "No hay información del usuario disponible."
        
        return f"""
Nombre: {usuario.get('nombre', 'No especificado')}
Sexo: {usuario.get('sexo', 'No especificado')}
Rol: {usuario.get('role', 'USER')}
"""
    
    def _formatear_memoria(self, memoria: List[Dict]) -> str:
        """Formatea el historial de memoria contextual"""
        if not memoria:
            return "No hay conversaciones previas registradas."
        
        memorias_formateadas = []
        for idx, mem in enumerate(memoria[:5], 1):  # Últimas 5 conversaciones
            fecha = mem.get('fecha', 'Fecha desconocida')
            resumen = mem.get('resumen_conversacion', 'Sin resumen')
            intencion = mem.get('intencion_detectada', 'No detectada')
            
            memorias_formateadas.append(
                f"{idx}. [{fecha}] - Intención: {intencion}\n   Resumen: {resumen}"
            )
        
        return "\n".join(memorias_formateadas)
    
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
            Diccionario con usuario y memoria
        """
        usuario = self.usuarios_dao.get_usuario(correo)
        memoria = self.memoria_dao.get_memoria_reciente(correo)
        
        return {
            'usuario': usuario,
            'memoria': memoria
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
            from .general_contexto import GeneralContexto
            from .servicios_contexto import ServiciosContexto
            from .estadisticas_contexto import EstadisticasContexto
            from .recetas_contexto import RecetasContexto
            
            cls._contextos = {
                'General': GeneralContexto,
                'Servicios': ServiciosContexto,
                'Estadisticas': EstadisticasContexto,
                'Recetas': RecetasContexto
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