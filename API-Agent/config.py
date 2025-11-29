"""
Configuración centralizada para el microservicio API-AGENTE
"""
import os
from typing import Dict, List

class Config:
    """Configuración centralizada del microservicio"""
    
    # DynamoDB Tables
    TABLE_USUARIOS = os.getenv('TABLE_USUARIOS', 'usuarios')
    TABLE_RECETAS = os.getenv('TABLE_RECETAS', 'recetas')
    TABLE_SERVICIOS = os.getenv('TABLE_SERVICIOS', 'servicios')
    TABLE_HISTORIAL = os.getenv('TABLE_HISTORIAL_MEDICO', 'historial_medico')
    TABLE_MEMORIA = os.getenv('TABLE_MEMORIA_CONTEXTUAL', 'memoria_contextual')
    
    # API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    
    # Límites de consulta
    LIMITE_HISTORIAL = int(os.getenv('LIMITE_HISTORIAL', '30'))
    LIMITE_MEMORIA = int(os.getenv('LIMITE_MEMORIA', '10'))
    LIMITE_SERVICIOS = int(os.getenv('LIMITE_SERVICIOS', '20'))
    
    # Configuración de contextos
    CONTEXTOS_DISPONIBLES = ['General', 'Servicios', 'Estadisticas', 'Recetas']
    
    # Mapeo de contextos a tablas requeridas
    CONTEXTO_TABLAS_MAP: Dict[str, List[str]] = {
        'General': [TABLE_USUARIOS, TABLE_RECETAS, TABLE_MEMORIA, TABLE_HISTORIAL],
        'Servicios': [TABLE_USUARIOS, TABLE_MEMORIA, TABLE_SERVICIOS],
        'Estadisticas': [TABLE_USUARIOS, TABLE_MEMORIA, TABLE_HISTORIAL],
        'Recetas': [TABLE_USUARIOS, TABLE_MEMORIA, TABLE_HISTORIAL, TABLE_RECETAS]
    }
    
    @classmethod
    def validar_configuracion(cls):
        """Valida que las configuraciones críticas estén presentes"""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY no está configurada")
        
        return True