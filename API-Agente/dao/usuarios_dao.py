"""
DAOs específicos para cada tabla del sistema académico
"""
from typing import Dict, List, Optional
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from .base import BaseDAO
from config import Config


# ===== USUARIOS DAO =====
class UsuariosDAO(BaseDAO):
    """DAO para la tabla de usuarios"""
    
    def __init__(self):
        super().__init__(Config.TABLE_USUARIOS)
    
    def get_usuario_por_correo(self, correo: str) -> Optional[Dict]:
        """
        Busca usuario por correo electrónico usando scan
        
        Args:
            correo: Email del usuario
        
        Returns:
            Diccionario con datos del usuario o None
        """
        try:
            response = self.scan_all(
                filter_expression=Attr('correo').eq(correo),
                limit=1
            )
            return response[0] if response else None
        except Exception as e:
            print(f"Error buscando usuario por correo: {str(e)}")
            return None
    
    def existe_usuario(self, correo: str) -> bool:
        """Verifica si un usuario existe por correo"""
        return self.get_usuario_por_correo(correo) is not None
    
    def get_usuario_por_id(self, usuario_id: str) -> Optional[Dict]:
        """Obtiene usuario por ID (partition key)"""
        return self.get_by_key(usuario_id)