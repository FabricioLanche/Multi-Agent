"""
Implementaciones específicas de cada contexto
"""
from typing import Dict, List
from .base_contexto import BaseContexto
from dao.base import DAOFactory

# ===== CONTEXTO ESTADÍSTICAS =====
class EstadisticasContexto(BaseContexto):
    """Contexto para la pestaña de Estadísticas"""
    
    def __init__(self):
        super().__init__()
        self.historial_dao = DAOFactory.get_dao('historial')
    
    def get_tablas_requeridas(self) -> List[str]:
        return ['usuarios', 'memoria', 'historial']
    
    def build_context_data(self, correo: str) -> Dict:
        """Construye datos para contexto de estadísticas"""
        datos_base = self.cargar_datos_base(correo)
        
        # Cargar historial del último mes
        historial = self.historial_dao.get_historial_reciente(correo, dias=30)
        
        # Calcular estadísticas básicas
        estadisticas = self._calcular_estadisticas(historial)
        
        return {
            **datos_base,
            'historial': historial,
            'estadisticas': estadisticas
        }
    
    def get_system_prompt(self) -> str:
        return """
Eres un asistente especializado en análisis de datos de salud y bienestar.

Tu rol es:
- Analizar tendencias en los datos del usuario de forma objetiva
- Presentar estadísticas de manera clara y comprensible
- Identificar patrones interesantes en la actividad del usuario
- Ofrecer insights realistas y aterrizados basados en los números
- Evitar alarmismos o interpretaciones médicas
- Celebrar logros y motivar mejoras de manera positiva

Usa un tono analítico pero accesible. Ayuda al usuario a entender sus datos 
y a tomar decisiones informadas sobre su bienestar.
"""
    
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """Formatea datos del contexto de estadísticas"""
        estadisticas = datos.get('estadisticas', {})
        
        if not estadisticas:
            return "No hay suficientes datos para generar estadísticas."
        
        return f"""
ESTADÍSTICAS DEL ÚLTIMO MES:

Actividad Física:
  • Promedio de pasos diarios: {estadisticas.get('pasos_promedio', 0):,.0f}
  • Máximo de pasos en un día: {estadisticas.get('pasos_max', 0):,.0f}
  • Mínimo de pasos en un día: {estadisticas.get('pasos_min', 0):,.0f}

Sueño:
  • Promedio de horas de sueño: {estadisticas.get('sueno_promedio', 0):.1f}h
  • Mejor noche: {estadisticas.get('sueno_max', 0):.1f}h
  • Peor noche: {estadisticas.get('sueno_min', 0):.1f}h

Ritmo Cardíaco (cuando disponible):
  • Promedio: {estadisticas.get('fc_promedio', 'N/A')} bpm
  
Registros totales: {estadisticas.get('total_registros', 0)} días
"""
    
    def _calcular_estadisticas(self, historial: List[Dict]) -> Dict:
        """Calcula estadísticas del historial"""
        if not historial:
            return {}
        
        pasos_list = []
        sueno_list = []
        fc_list = []
        
        for registro in historial:
            wearables = registro.get('wearables', {})
            sensores = registro.get('sensores', {})
            
            # Pasos
            pasos = wearables.get('pasos') or sensores.get('pasos')
            if pasos:
                pasos_list.append(pasos)
            
            # Sueño
            sueno = wearables.get('horas_de_sueno') or sensores.get('horas_de_sueno')
            if sueno:
                sueno_list.append(sueno)
            
            # Ritmo cardíaco
            fc = wearables.get('ritmo_cardiaco')
            if fc:
                fc_list.append(fc)
        
        estadisticas = {
            'total_registros': len(historial),
            'pasos_promedio': sum(pasos_list) / len(pasos_list) if pasos_list else 0,
            'pasos_max': max(pasos_list) if pasos_list else 0,
            'pasos_min': min(pasos_list) if pasos_list else 0,
            'sueno_promedio': sum(sueno_list) / len(sueno_list) if sueno_list else 0,
            'sueno_max': max(sueno_list) if sueno_list else 0,
            'sueno_min': min(sueno_list) if sueno_list else 0,
            'fc_promedio': sum(fc_list) / len(fc_list) if fc_list else None
        }
        
        return estadisticas
