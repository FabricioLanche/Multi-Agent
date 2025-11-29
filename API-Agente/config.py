"""
Configuración centralizada para el microservicio API-AGENTE
Sistema de Agentes Académicos
"""
import os
from typing import Dict, List


class Config:
    """Configuración centralizada del microservicio"""
    
    # ===== TABLAS DYNAMODB =====
    TABLE_USUARIOS = os.getenv('TABLE_USUARIOS', 'Usuario')
    TABLE_DATOS_ACADEMICOS = os.getenv('TABLE_DATOS_ACADEMICOS', 'DatosAcademicos')
    TABLE_DATOS_EMOCIONALES = os.getenv('TABLE_DATOS_EMOCIONALES', 'DatosEmocionales')
    TABLE_DATOS_SOCIOECONOMICOS = os.getenv('TABLE_DATOS_SOCIOECONOMICOS', 'DatosSocioeconomicos')
    TABLE_HISTORIAL = os.getenv('TABLE_HISTORIAL', 'Historial')
    TABLE_TAREAS = os.getenv('TABLE_TAREAS', 'Tarea')
    
    # ===== API CONFIGURATION =====
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = "gemini-2.0-flash-exp"
    
    # ===== LÍMITES DE CONSULTA =====
    LIMITE_HISTORIAL = int(os.getenv('LIMITE_HISTORIAL', '10'))
    LIMITE_TAREAS = int(os.getenv('LIMITE_TAREAS', '20'))
    
    # ===== CONFIGURACIÓN DE CONTEXTOS =====
    CONTEXTOS_DISPONIBLES = [
        'MentorAcademico',
        'OrientadorVocacional',
        'Psicologo'
    ]
    
    # Mapeo de contextos a tablas requeridas
    CONTEXTO_TABLAS_MAP: Dict[str, List[str]] = {
        'MentorAcademico': [
            TABLE_USUARIOS,
            TABLE_DATOS_ACADEMICOS,
            TABLE_HISTORIAL,
            TABLE_TAREAS
        ],
        'OrientadorVocacional': [
            TABLE_USUARIOS,
            TABLE_DATOS_ACADEMICOS,
            TABLE_DATOS_SOCIOECONOMICOS,
            TABLE_HISTORIAL
        ],
        'Psicologo': [
            TABLE_USUARIOS,
            TABLE_DATOS_ACADEMICOS,
            TABLE_DATOS_EMOCIONALES,
            TABLE_DATOS_SOCIOECONOMICOS,
            TABLE_HISTORIAL
        ]
    }
    
    # ===== DESCRIPCIÓN DE CONTEXTOS =====
    CONTEXTOS_DESCRIPCIONES = {
        'MentorAcademico': {
            'nombre': 'Mentor Académico',
            'emoji': '🎓',
            'descripcion': 'Ayuda con estrategias de estudio, organización y rendimiento académico',
            'objetivo': 'Mejorar el desempeño académico del estudiante',
            'tablas': ['Usuario', 'DatosAcademicos', 'Historial', 'Tarea']
        },
        'OrientadorVocacional': {
            'nombre': 'Orientador Vocacional',
            'emoji': '🧭',
            'descripcion': 'Orientación sobre elección de carrera e intereses profesionales',
            'objetivo': 'Facilitar la reflexión sobre el camino profesional',
            'tablas': ['Usuario', 'DatosAcademicos', 'DatosSocioeconomicos', 'Historial']
        },
        'Psicologo': {
            'nombre': 'Especialista en Psicología',
            'emoji': '🧠',
            'descripcion': 'Apoyo emocional y bienestar psicológico del estudiante',
            'objetivo': 'Brindar contención emocional y promover el bienestar mental',
            'tablas': ['Usuario', 'DatosAcademicos', 'DatosEmocionales', 'DatosSocioeconomicos', 'Historial']
        }
    }
    
    # ===== AWS CONFIGURATION =====
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID')
    
    # ===== ORGANIZATION =====
    ORG_NAME = os.getenv('ORG_NAME', 'Tecsup')
    
    @classmethod
    def validar_configuracion(cls):
        """Valida que las configuraciones críticas estén presentes"""
        errores = []
        
        if not cls.GEMINI_API_KEY:
            errores.append("GEMINI_API_KEY no está configurada")
        
        if not cls.AWS_ACCOUNT_ID:
            errores.append("AWS_ACCOUNT_ID no está configurada")
        
        if errores:
            raise ValueError(
                f"Configuración inválida: {', '.join(errores)}"
            )
        
        return True
    
    @classmethod
    def get_info_contexto(cls, nombre_contexto: str) -> Dict:
        """
        Obtiene información detallada sobre un contexto
        
        Args:
            nombre_contexto: Nombre del contexto
        
        Returns:
            Diccionario con información del contexto
        """
        return cls.CONTEXTOS_DESCRIPCIONES.get(
            nombre_contexto,
            {'nombre': 'Desconocido', 'descripcion': 'Contexto no encontrado'}
        )
    
    @classmethod
    def get_tablas_por_contexto(cls, nombre_contexto: str) -> List[str]:
        """
        Obtiene las tablas requeridas por un contexto específico
        
        Args:
            nombre_contexto: Nombre del contexto
        
        Returns:
            Lista de nombres de tablas
        """
        return cls.CONTEXTO_TABLAS_MAP.get(nombre_contexto, [])