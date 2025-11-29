"""
DAOs específicos para cada tabla
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from .base import BaseDAO
from config import Config

# ===== USUARIOS DAO =====
class UsuariosDAO(BaseDAO):
    """DAO para la tabla de usuarios"""
    
    def __init__(self):
        super().__init__(Config.TABLE_USUARIOS)
    
    def get_usuario(self, correo: str) -> Optional[Dict]:
        """Obtiene un usuario por correo"""
        return self.get_by_key(correo)
    
    def existe_usuario(self, correo: str) -> bool:
        """Verifica si un usuario existe"""
        return self.get_usuario(correo) is not None
