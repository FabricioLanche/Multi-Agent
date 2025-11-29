"""
DAOs específicos para cada tabla
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from .base import BaseDAO
from config import Config

# ===== MEMORIA CONTEXTUAL DAO =====
class MemoriaDAO(BaseDAO):
    """DAO para la tabla de memoria contextual"""
    
    def __init__(self):
        super().__init__(Config.TABLE_MEMORIA)
    
    def get_memoria_reciente(self, correo: str, limite: Optional[int] = None) -> List[Dict]:
        """
        Obtiene las conversaciones más recientes
        
        Args:
            correo: Email del usuario
            limite: Número máximo de registros
        
        Returns:
            Lista de memorias contextuales ordenadas por fecha descendente
        """
        return self.query_by_partition(
            correo,
            limit=limite or Config.LIMITE_MEMORIA,
            scan_index_forward=False
        )
    
    def get_memoria_por_contexto(self, correo: str, context_id: str) -> Optional[Dict]:
        """Obtiene una memoria específica por context_id"""
        return self.get_by_key(correo, context_id)
    
    def guardar_memoria(self, memoria: Dict) -> bool:
        """Guarda una nueva memoria contextual"""
        if 'fecha' not in memoria:
            memoria['fecha'] = datetime.now().isoformat()
        return self.put_item(memoria)
    
    def get_intenciones_detectadas(self, correo: str, limite: int = 10) -> List[str]:
        """Obtiene las últimas intenciones detectadas del usuario"""
        memorias = self.get_memoria_reciente(correo, limite)
        return [m.get('intencion_detectada') for m in memorias if m.get('intencion_detectada')]

