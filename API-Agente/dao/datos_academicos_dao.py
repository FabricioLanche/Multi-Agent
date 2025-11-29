"""
DAOs específicos para cada tabla del sistema académico
"""
from typing import Dict, List, Optional
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from .base import BaseDAO
from config import Config

# ===== DATOS ACADÉMICOS DAO =====
class DatosAcademicosDAO(BaseDAO):
    """DAO para la tabla de datos académicos"""
    
    def __init__(self):
        super().__init__(Config.TABLE_DATOS_ACADEMICOS)
    
    def get_datos_por_usuario(self, usuario_id: str) -> Optional[Dict]:
        """
        Obtiene los datos académicos de un usuario
        
        Args:
            usuario_id: ID del usuario
        
        Returns:
            Diccionario con datos académicos o None
        """
        try:
            datos_list = self.query_by_partition(
                usuario_id,
                limit=1,
                scan_index_forward=False  # Más reciente primero
            )
            return datos_list[0] if datos_list else None
        except Exception as e:
            print(f"Error obteniendo datos académicos: {str(e)}")
            return None
    
    def actualizar_datos_academicos(self, datos: Dict) -> bool:
        """Actualiza o inserta datos académicos"""
        return self.put_item(datos)