"""
DAO para la tabla de Historial
"""
from typing import Dict, List, Optional
from .base import BaseDAO
from config import Config


class HistorialDAO(BaseDAO):
    """DAO para la tabla de historial de interacciones"""
    
    def __init__(self):
        super().__init__(Config.TABLE_HISTORIAL)
    
    def get_historial_usuario(
        self, 
        correo: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Obtiene el historial de interacciones de un usuario
        
        Args:
            correo: Email del usuario
            limit: Límite de registros (default desde Config)
        
        Returns:
            Lista de registros del historial ordenados del más reciente al más antiguo
        """
        try:
            # Primero obtener el usuario para conseguir su ID
            from dao.usuarios_dao import UsuariosDAO
            usuarios_dao = UsuariosDAO()
            usuario = usuarios_dao.get_usuario_por_correo(correo)
            
            if not usuario:
                print(f"Usuario con correo {correo} no encontrado")
                return []
            
            usuario_id = usuario.get('id')
            
            # Query por partition key (usuarioId)
            return self.query_by_partition(
                usuario_id,
                limit=limit or Config.LIMITE_HISTORIAL,
                scan_index_forward=False  # False = más recientes primero
            )
        except Exception as e:
            print(f"Error obteniendo historial: {str(e)}")
            return []
    
    def get_historial_por_usuario_id(
        self,
        usuario_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Obtiene el historial directamente por usuarioId (más eficiente si ya tienes el ID)
        
        Args:
            usuario_id: ID del usuario
            limit: Límite de registros
        
        Returns:
            Lista de registros del historial
        """
        try:
            return self.query_by_partition(
                usuario_id,
                limit=limit or Config.LIMITE_HISTORIAL,
                scan_index_forward=False
            )
        except Exception as e:
            print(f"Error obteniendo historial por ID: {str(e)}")
            return []
    
    def agregar_interaccion(self, registro: Dict) -> bool:
        """
        Agrega una nueva interacción al historial
        
        Args:
            registro: Diccionario con usuarioId, id, texto
                     {
                         "usuarioId": "uuid-del-usuario",
                         "id": "uuid-de-la-interaccion",
                         "texto": "Resumen de la interacción"
                     }
        
        Returns:
            True si fue exitoso
        """
        # Validar campos requeridos
        campos_requeridos = ['usuarioId', 'id', 'texto']
        for campo in campos_requeridos:
            if campo not in registro:
                print(f"Error: Campo requerido '{campo}' faltante en historial")
                return False
        
        return self.put_item(registro)
    
    def limpiar_historial_antiguo(
        self,
        usuario_id: str,
        mantener_ultimos: int = 50
    ) -> int:
        """
        Limpia el historial antiguo de un usuario, manteniendo solo los últimos N registros
        
        Args:
            usuario_id: ID del usuario
            mantener_ultimos: Cantidad de registros más recientes a mantener
        
        Returns:
            Número de registros eliminados
        """
        try:
            # Obtener todo el historial del usuario
            historial_completo = self.query_by_partition(
                usuario_id,
                scan_index_forward=False  # Más recientes primero
            )
            
            # Si hay menos registros que el límite, no hacer nada
            if len(historial_completo) <= mantener_ultimos:
                return 0
            
            # Identificar registros a eliminar (los más antiguos)
            registros_a_eliminar = historial_completo[mantener_ultimos:]
            
            # Eliminar uno por uno
            eliminados = 0
            for registro in registros_a_eliminar:
                if self.delete_item(usuario_id, registro['id']):
                    eliminados += 1
            
            print(f"Limpieza de historial: {eliminados} registros eliminados de usuario {usuario_id}")
            return eliminados
        
        except Exception as e:
            print(f"Error limpiando historial: {str(e)}")
            return 0
    
    def obtener_ultimo_registro(self, usuario_id: str) -> Optional[Dict]:
        """
        Obtiene el registro más reciente del historial de un usuario
        
        Args:
            usuario_id: ID del usuario
        
        Returns:
            Diccionario con el último registro o None
        """
        try:
            registros = self.query_by_partition(
                usuario_id,
                limit=1,
                scan_index_forward=False  # Más reciente
            )
            return registros[0] if registros else None
        except Exception as e:
            print(f"Error obteniendo último registro: {str(e)}")
            return None