"""
DAOs específicos para cada tabla del sistema académico
"""
from typing import Dict, List, Optional
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from .base import BaseDAO
from config import Config

# ===== HISTORIAL DAO =====
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
        Primero busca el usuarioId por correo, luego hace query
        
        Args:
            correo: Email del usuario
            limit: Límite de registros
        
        Returns:
            Lista de registros del historial
        """
        try:
            # Primero obtener el usuario para conseguir su ID
            from .usuarios_dao import UsuariosDAO
            usuarios_dao = UsuariosDAO()
            usuario = usuarios_dao.get_usuario_por_correo(correo)
            
            if not usuario:
                return []
            
            usuario_id = usuario.get('id')
            
            return self.query_by_partition(
                usuario_id,
                limit=limit or Config.LIMITE_HISTORIAL,
                scan_index_forward=False  # Más recientes primero
            )
        except Exception as e:
            print(f"Error obteniendo historial: {str(e)}")
            return []
    
    def agregar_interaccion(self, registro: Dict) -> bool:
        """
        Agrega una nueva interacción al historial
        
        Args:
            registro: Diccionario con usuarioId, id, texto
        
        Returns:
            True si fue exitoso
        """
        return self.put_item(registro)