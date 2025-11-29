"""
Implementaciones específicas de cada contexto
"""
from typing import Dict, List
from .base_contexto import BaseContexto
from dao.base import DAOFactory

# ===== CONTEXTO RECETAS =====
class RecetasContexto(BaseContexto):
    """Contexto para la pestaña de Recetas"""
    
    def __init__(self):
        super().__init__()
        self.recetas_dao = DAOFactory.get_dao('recetas')
        self.historial_dao = DAOFactory.get_dao('historial')
    
    def get_tablas_requeridas(self) -> List[str]:
        return ['usuarios', 'memoria', 'historial', 'recetas']
    
    def build_context_data(self, correo: str) -> Dict:
        """Construye datos para contexto de recetas"""
        datos_base = self.cargar_datos_base(correo)
        
        recetas = self.recetas_dao.get_recetas_usuario(correo)
        historial = self.historial_dao.get_historial_reciente(correo, dias=7)
        
        return {
            **datos_base,
            'recetas': recetas,
            'historial_reciente': historial
        }
    
    def get_system_prompt(self) -> str:
        return """
Eres un asistente especializado en el manejo de recetas médicas y adherencia al tratamiento.

Tu rol es:
- Ayudar al usuario a comprender sus recetas médicas
- Recordar de manera amena los horarios y frecuencias de medicación
- Hacer seguimiento del consumo regular dentro del aplicativo
- Motivar la adherencia al tratamiento de forma positiva
- Aclarar dudas sobre las recetas sin hacer recomendaciones médicas
- Celebrar la constancia en el cumplimiento del tratamiento

IMPORTANTE: NUNCA modifiques dosis ni sugieras cambios en el tratamiento.
Siempre refiere al médico tratante para cualquier modificación.

Usa un tono amable, cercano y de acompañamiento.
"""
    
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """Formatea datos del contexto de recetas"""
        recetas = datos.get('recetas', [])
        
        if not recetas:
            return "No hay recetas registradas en el sistema."
        
        recetas_detalle = []
        for idx, receta in enumerate(recetas, 1):
            institucion = receta.get('institucion', 'Desconocida')
            paciente = receta.get('paciente', 'No especificado')
            
            recetas_detalle.append(f"\nRECETA #{idx} - {institucion}")
            if paciente:
                recetas_detalle.append(f"Paciente: {paciente}")
            
            medicamentos = receta.get('recetas', [])
            for med in medicamentos:
                producto = med.get('producto', 'Sin nombre')
                dosis = med.get('dosis', 'No especificada')
                frecuencia = f"{med.get('frecuencia_valor', '?')} {med.get('frecuencia_unidad', 'veces')}"
                duracion = med.get('duracion', 'No especificada')
                
                recetas_detalle.append(
                    f"  • {producto}: {dosis}, cada {frecuencia}, por {duracion}"
                )
        
        return "\n".join(recetas_detalle)