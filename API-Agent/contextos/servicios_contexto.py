"""
Implementaciones específicas de cada contexto
"""
from typing import Dict, List
from .base_contexto import BaseContexto
from dao.base import DAOFactory

# ===== CONTEXTO SERVICIOS =====
class ServiciosContexto(BaseContexto):
    """Contexto para la pestaña de Servicios"""
    
    def __init__(self):
        super().__init__()
        self.servicios_dao = DAOFactory.get_dao('servicios')
    
    def get_tablas_requeridas(self) -> List[str]:
        return ['usuarios', 'memoria', 'servicios']
    
    def build_context_data(self, correo: str) -> Dict:
        """Construye datos para contexto de servicios"""
        datos_base = self.cargar_datos_base(correo)
        
        # Cargar todos los servicios disponibles
        servicios = self.servicios_dao.get_todos_servicios()
        
        return {
            **datos_base,
            'servicios': servicios
        }
    
    def get_system_prompt(self) -> str:
        return """
Eres un asistente especializado en informar y motivar sobre servicios de salud y bienestar.

Tu rol es:
- Sugerir servicios relevantes según el perfil e intereses del usuario
- Informar sobre eventos, talleres y actividades disponibles
- Incentivar la participación del usuario de manera positiva
- Explicar beneficios de cada servicio de forma clara y atractiva
- Personalizar recomendaciones según el historial del usuario

Usa un tono entusiasta pero no agresivo. Enfócate en cómo los servicios pueden mejorar 
la calidad de vida del usuario de manera concreta.
"""
    
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """Formatea datos del contexto de servicios"""
        servicios = datos.get('servicios', [])
        
        if not servicios:
            return "No hay servicios disponibles actualmente."
        
        # Agrupar por categoría
        por_categoria = {}
        for servicio in servicios:
            cat = servicio.get('categoria', 'otros')
            if cat not in por_categoria:
                por_categoria[cat] = []
            por_categoria[cat].append(servicio)
        
        # Formatear salida
        texto_servicios = []
        for categoria, lista_servicios in por_categoria.items():
            texto_servicios.append(f"\n{categoria.upper()}:")
            for serv in lista_servicios[:5]:  # Máximo 5 por categoría
                nombre = serv.get('nombre', 'Sin nombre')
                desc = serv.get('descripcion', 'Sin descripción')
                texto_servicios.append(f"  • {nombre}: {desc[:100]}...")
        
        return "\n".join(texto_servicios)

