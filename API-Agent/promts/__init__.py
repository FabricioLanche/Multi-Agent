"""
Prompts package - Prompt templates for different contexts
"""
from .base_prompt import BasePrompt
from .general_prompt import GeneralPrompt
from .servicios_prompt import ServiciosPrompt
from .estadisticas_prompt import EstadisticasPrompt
from .recetas_prompt import RecetasPrompt

__all__ = [
    'BasePrompt',
    'GeneralPrompt',
    'ServiciosPrompt',
    'EstadisticasPrompt',
    'RecetasPrompt'
]