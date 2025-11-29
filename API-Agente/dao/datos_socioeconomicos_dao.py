"""
DAOs específicos para cada tabla del sistema académico
"""
from typing import Dict, List, Optional
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from .base import BaseDAO
from config import Config

# ===== DATOS SOCIOECONÓMICOS DAO =====
class DatosSocioeconomicosDAO(BaseDAO):
    """DAO para la tabla de datos socioeconómicos"""
    
    def __init__(self):
        super().__init__(Config.TABLE_DATOS_SOCIOECONOMICOS)
    
    def get_datos_por_usuario(self, usuario_id: str) -> Optional[Dict]:
        """Obtiene los datos socioeconómicos de un usuario"""
        try:
            datos_list = self.query_by_partition(
                usuario_id,
                limit=1,
                scan_index_forward=False
            )
            return datos_list[0] if datos_list else None
        except Exception as e:
            print(f"Error obteniendo datos socioeconómicos: {str(e)}")
            return None
    
    def actualizar_datos_socioeconomicos(self, datos: Dict) -> bool:
        """Actualiza o inserta datos socioeconómicos"""
        return self.put_item(datos)