"""
DAOs específicos para cada tabla
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from .base import BaseDAO
from config import Config

# ===== SERVICIOS DAO =====
class ServiciosDAO(BaseDAO):
    """DAO para la tabla de servicios"""
    
    def __init__(self):
        super().__init__(Config.TABLE_SERVICIOS)
    
    def get_todos_servicios(self, limit: Optional[int] = None) -> List[Dict]:
        """Obtiene todos los servicios disponibles"""
        return self.scan_all(limit=limit or Config.LIMITE_SERVICIOS)
    
    def get_servicios_por_categoria(self, categoria: str, limit: Optional[int] = None) -> List[Dict]:
        """Obtiene servicios filtrados por categoría"""
        from boto3.dynamodb.conditions import Attr
        return self.scan_all(
            limit=limit or Config.LIMITE_SERVICIOS,
            filter_expression=Attr('categoria').eq(categoria)
        )
    
    def get_servicio(self, nombre: str) -> Optional[Dict]:
        """Obtiene un servicio específico por nombre"""
        return self.get_by_key(nombre)
