"""
Contexto para el Orientador Vocacional
"""
from typing import Dict, List
from .base_contexto import BaseContexto
from dao.base import DAOFactory


class OrientadorVocacionalContexto(BaseContexto):
    """
    🧭 Orientador Vocacional
    Objetivo: Ayudar al estudiante a entender si está en la carrera correcta,
              explorar sus intereses profesionales
    
    Tablas necesarias:
    - Usuario
    - Datos Académicos (para ver avance en carrera, repitencias, preferencias)
    - Datos Socioeconómicos (si trabaja, ingresos, motivaciones económicas)
    - Historial (versión resumida de intervenciones previas)
    """
    
    def __init__(self):
        super().__init__()
        self.datos_academicos_dao = DAOFactory.get_dao('datos_academicos')
        self.datos_socioeconomicos_dao = DAOFactory.get_dao('datos_socioeconomicos')
    
    def get_tablas_requeridas(self) -> List[str]:
        return ['usuarios', 'datos_academicos', 'datos_socioeconomicos', 'historial']
    
    def build_context_data(self, correo: str) -> Dict:
        """Construye datos para contexto de orientador vocacional"""
        datos_base = self.cargar_datos_base(correo)
        usuario = datos_base.get('usuario')
        
        if not usuario:
            return datos_base
        
        usuario_id = usuario.get('id')
        
        # Cargar datos académicos (enfoque en carrera y rendimiento general)
        datos_academicos = self.datos_academicos_dao.get_datos_por_usuario(usuario_id)
        
        # Cargar datos socioeconómicos
        datos_socioeconomicos = self.datos_socioeconomicos_dao.get_datos_por_usuario(usuario_id)
        
        return {
            **datos_base,
            'datos_academicos': datos_academicos,
            'datos_socioeconomicos': datos_socioeconomicos
        }
    
    def get_system_prompt(self) -> str:
        return """
Eres un Orientador Vocacional especializado en ayudar a estudiantes a descubrir 
su camino profesional y validar sus elecciones académicas.

Tu rol es:
- Ayudar al estudiante a reflexionar sobre su elección de carrera
- Explorar intereses, habilidades y valores profesionales
- Analizar la congruencia entre carrera actual y perfil del estudiante
- Considerar factores socioeconómicos que influyen en decisiones académicas
- Sugerir alternativas o ajustes de ruta profesional si es apropiado
- Proporcionar información sobre el mercado laboral y oportunidades

NO debes:
- Decirle al estudiante que cambie de carrera sin una reflexión profunda
- Ignorar el contexto socioeconómico del estudiante
- Imponer tu visión sobre lo que es "correcto"
- Desestimar las aspiraciones del estudiante

Usa un tono reflexivo, empático y constructivo. Haz preguntas que promuevan 
la autoexploración y el autoconocimiento.
"""
    
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """Formatea datos del contexto de orientador vocacional"""
        resultado = []
        
        # Formatear datos académicos (enfoque vocacional)
        datos_academicos = datos.get('datos_academicos')
        if datos_academicos:
            resultado.append("=== PERFIL ACADÉMICO ===")
            resultado.append(f"Carrera elegida: {datos_academicos.get('carrera', 'No especificada')}")
            resultado.append(f"Ciclo actual: {datos_academicos.get('ciclo_actual', 'N/A')}")
            resultado.append(f"Avance en la malla: {datos_academicos.get('avance_malla', 0):.1f}%")
            resultado.append(f"Promedio ponderado: {datos_academicos.get('promedio_ponderado', 0):.2f}")
            resultado.append(f"Estado: {datos_academicos.get('estado_matricula', 'N/A')}")
            
            # Indicadores de posible desajuste vocacional
            cursos_reprobados = datos_academicos.get('cursos_reprobados', [])
            historial_retirados = datos_academicos.get('historial_retirados', [])
            
            if cursos_reprobados:
                resultado.append(f"Cursos con dificultades: {len(cursos_reprobados)}")
            
            if historial_retirados:
                resultado.append(f"Retiros de cursos: {len(historial_retirados)}")
        else:
            resultado.append("No hay datos académicos disponibles.")
        
        resultado.append("")
        
        # Formatear datos socioeconómicos
        datos_socio = datos.get('datos_socioeconomicos')
        if datos_socio:
            resultado.append("=== CONTEXTO SOCIOECONÓMICO ===")
            resultado.append(f"Tipo de financiamiento: {datos_socio.get('tipo_financiamiento', 'N/A')}")
            resultado.append(f"Situación laboral: {datos_socio.get('situacion_laboral', 'N/A')}")
            
            if datos_socio.get('ingreso_estimado'):
                resultado.append(f"Ingreso mensual estimado: {datos_socio.get('ingreso_estimado', 0):.2f}")
            
            dependencia = datos_socio.get('dependencia_economica', None)
            if dependencia is not None:
                dep_texto = "Sí" if dependencia else "No"
                resultado.append(f"Dependencia económica: {dep_texto}")
        else:
            resultado.append("=== CONTEXTO SOCIOECONÓMICO ===")
            resultado.append("No hay datos socioeconómicos disponibles.")
        
        return "\n".join(resultado)