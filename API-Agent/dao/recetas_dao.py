"""
DAOs específicos para cada tabla
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from .base import BaseDAO
from config import Config

# ===== RECETAS DAO =====
class RecetasDAO(BaseDAO):
    """DAO para la tabla de recetas"""
    
    def __init__(self):
        super().__init__(Config.TABLE_RECETAS)
    
    def get_recetas_usuario(self, correo: str) -> List[Dict]:
        """Obtiene todas las recetas de un usuario"""
        return self.query_by_partition(correo)
    
    def get_receta(self, correo: str, receta_id: str) -> Optional[Dict]:
        """Obtiene una receta específica"""
        return self.get_by_key(correo, receta_id)
    
    def get_recetas_activas(self, correo: str) -> List[Dict]:
        """
        Obtiene recetas que probablemente estén activas
        (esto es una simplificación, necesitarías lógica para determinar vigencia)
        """
        return self.get_recetas_usuario(correo)
