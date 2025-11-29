"""
Contextos package - Context processors for different conversation contexts
"""
# Import context implementations after base to avoid circular imports
from .base_contexto import BaseContexto, ContextoFactory
from .general_contexto import GeneralContexto
from .servicios_contexto import ServiciosContexto
from .estadisticas_contexto import EstadisticasContexto
from .recetas_contexto import RecetasContexto

__all__ = [
    'BaseContexto',
    'ContextoFactory',
    'GeneralContexto',
    'ServiciosContexto',
    'EstadisticasContexto',
    'RecetasContexto'
]
