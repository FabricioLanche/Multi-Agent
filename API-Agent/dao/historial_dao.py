"""
DAOs específicos para cada tabla
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from .base import BaseDAO
from config import Config

# ===== HISTORIAL MÉDICO DAO =====
class HistorialDAO(BaseDAO):
    """DAO para la tabla de historial médico"""
    
    def __init__(self):
        super().__init__(Config.TABLE_HISTORIAL)
    
    def get_historial_reciente(self, correo: str, dias: int = 30) -> List[Dict]:
        """
        Obtiene el historial médico reciente del usuario
        
        Args:
            correo: Email del usuario
            dias: Número de días hacia atrás
        
        Returns:
            Lista de registros ordenados por fecha descendente
        """
        fecha_limite = (datetime.now() - timedelta(days=dias)).isoformat()
        
        return self.query_by_partition(
            correo,
            sort_key_condition=Key('fecha').gte(fecha_limite),
            scan_index_forward=False,
            limit=Config.LIMITE_HISTORIAL
        )
    
    def get_historial_rango(self, correo: str, fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """Obtiene historial en un rango de fechas específico"""
        return self.query_by_partition(
            correo,
            sort_key_condition=Key('fecha').between(fecha_inicio, fecha_fin),
            scan_index_forward=False
        )
    
    def get_ultimo_registro(self, correo: str) -> Optional[Dict]:
        """Obtiene el registro más reciente"""
        registros = self.query_by_partition(
            correo,
            limit=1,
            scan_index_forward=False
        )
        return registros[0] if registros else None
    
    def agregar_registro(self, registro: Dict) -> bool:
        """Agrega un nuevo registro de historial"""
        if 'fecha' not in registro:
            registro['fecha'] = datetime.now().isoformat()
        return self.put_item(registro)
