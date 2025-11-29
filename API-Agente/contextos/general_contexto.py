"""
Implementaciones específicas de cada contexto
"""
from typing import Dict, List
from .base_contexto import BaseContexto
from dao.base import DAOFactory

# ===== CONTEXTO GENERAL =====
class GeneralContexto(BaseContexto):
    """Contexto para la pestaña General"""
    
    def __init__(self):
        super().__init__()
        self.recetas_dao = DAOFactory.get_dao('recetas')
        self.historial_dao = DAOFactory.get_dao('historial')
    
    def get_tablas_requeridas(self) -> List[str]:
        return ['usuarios', 'recetas', 'memoria', 'historial']
    
    def build_context_data(self, correo: str) -> Dict:
        """Construye datos para contexto general"""
        datos_base = self.cargar_datos_base(correo)
        
        # Cargar datos adicionales
        recetas = self.recetas_dao.get_recetas_usuario(correo)
        historial = self.historial_dao.get_historial_reciente(correo, dias=7)
        
        return {
            **datos_base,
            'recetas': recetas,
            'historial_reciente': historial
        }
    
    def get_system_prompt(self) -> str:
        return """
Eres un asistente médico de acompañamiento amable y empático. Tu rol es:

- Mantener una comunicación asertiva del tipo paciente-cuidador
- Ofrecer apoyo emocional y orientación general basada en los datos del usuario
- Hacer referencias a información del historial médico y recetas cuando sea relevante
- NUNCA hacer diagnósticos médicos ni prescribir tratamientos
- Analizar datos objetivamente sin hacer suposiciones médicas
- Sugerir consultar con profesionales de salud cuando sea apropiado
- Ser cercano, comprensivo y motivador

Tu objetivo es acompañar al usuario en su proceso de salud, no reemplazar atención médica profesional.
"""
    
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """Formatea datos del contexto general"""
        recetas = datos.get('recetas', [])
        historial = datos.get('historial_reciente', [])
        
        # Formatear recetas
        recetas_texto = "No hay recetas registradas."
        if recetas:
            recetas_lista = []
            for idx, receta in enumerate(recetas[:3], 1):
                institucion = receta.get('institucion', 'Desconocida')
                productos = [r.get('producto') for r in receta.get('recetas', [])]
                recetas_lista.append(f"  {idx}. {institucion}: {', '.join(productos[:3])}")
            recetas_texto = "\n".join(recetas_lista)
        
        # Formatear historial reciente (últimos 3 días)
        historial_texto = "No hay registros recientes de actividad."
        if historial:
            historial_lista = []
            for registro in historial[:3]:
                fecha = registro.get('fecha', 'Desconocida')[:10]
                wearables = registro.get('wearables', {})
                sensores = registro.get('sensores', {})
                
                pasos = wearables.get('pasos') or sensores.get('pasos', 0)
                ritmo = wearables.get('ritmo_cardiaco', 'N/A')
                sueno = wearables.get('horas_de_sueno') or sensores.get('horas_de_sueno', 0)
                
                historial_lista.append(
                    f"  • {fecha}: {pasos} pasos, {sueno}h sueño, FC: {ritmo}"
                )
            historial_texto = "\n".join(historial_lista)
        
        return f"""
RECETAS ACTIVAS:
{recetas_texto}

ACTIVIDAD RECIENTE:
{historial_texto}
"""