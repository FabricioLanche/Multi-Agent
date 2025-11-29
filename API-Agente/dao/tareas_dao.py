"""
DAOs específicos para cada tabla del sistema académico
"""
from typing import Dict, List, Optional
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from .base import BaseDAO
from config import Config

# ===== TAREAS DAO =====
class TareasDAO(BaseDAO):
    """DAO para la tabla de tareas"""
    
    def __init__(self):
        super().__init__(Config.TABLE_TAREAS)
    
    def get_tareas_por_usuario(
        self,
        usuario_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Obtiene las tareas de un usuario
        
        Args:
            usuario_id: ID del usuario
            limit: Límite de registros
        
        Returns:
            Lista de tareas
        """
        return self.query_by_partition(
            usuario_id,
            limit=limit or Config.LIMITE_TAREAS,
            scan_index_forward=False
        )
    
    def agregar_tarea(self, tarea: Dict) -> bool:
        """Agrega una nueva tarea"""
        return self.put_item(tarea)
    
    def actualizar_tarea(self, tarea: Dict) -> bool:
        """Actualiza una tarea existente"""
        return self.put_item(tarea)
    
    def eliminar_tarea(self, usuario_id: str, tarea_id: str) -> bool:
        """Elimina una tarea"""
        return self.delete_item(usuario_id, tarea_id)