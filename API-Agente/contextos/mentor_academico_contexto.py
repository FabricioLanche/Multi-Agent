"""
Contexto para el Mentor Académico
"""
from typing import Dict, List
from .base_contexto import BaseContexto
from dao.base import DAOFactory


class MentorAcademicoContexto(BaseContexto):
    """
    🎓 Mentor Académico
    Objetivo: Ayudar a aprender, aprobar cursos, entender temas
    
    Tablas necesarias:
    - Usuario (identificación)
    - Datos Académicos (rendimiento, cursos, notas, avances)
    - Historial (interacciones académicas)
    - Tarea (pendientes, assignments)
    """
    
    def __init__(self):
        super().__init__()
        self.datos_academicos_dao = DAOFactory.get_dao('datos_academicos')
        self.tareas_dao = DAOFactory.get_dao('tareas')
    
    def get_tablas_requeridas(self) -> List[str]:
        return ['usuarios', 'datos_academicos', 'historial', 'tareas']
    
    def build_context_data(self, correo: str) -> Dict:
        """Construye datos para contexto de mentor académico"""
        datos_base = self.cargar_datos_base(correo)
        usuario = datos_base.get('usuario')
        
        if not usuario:
            return datos_base
        
        usuario_id = usuario.get('id')
        
        # Cargar datos académicos
        datos_academicos = self.datos_academicos_dao.get_datos_por_usuario(usuario_id)
        
        # Cargar tareas pendientes
        tareas = self.tareas_dao.get_tareas_por_usuario(usuario_id)
        
        return {
            **datos_base,
            'datos_academicos': datos_academicos,
            'tareas': tareas
        }
    
    def get_system_prompt(self) -> str:
        return """
Eres un Mentor Académico especializado en ayudar a estudiantes a mejorar su desempeño académico.

Tu rol es:
- Ayudar a entender conceptos y temas de estudio
- Sugerir estrategias de aprendizaje personalizadas
- Apoyar en la planificación de estudios y gestión del tiempo
- Motivar y orientar sobre cómo aprobar cursos
- Analizar el rendimiento académico y sugerir áreas de mejora
- Ayudar con la organización de tareas y asignaciones

NO debes:
- Resolver tareas por el estudiante
- Dar respuestas directas a exámenes o evaluaciones
- Juzgar al estudiante por su rendimiento
- Tomar decisiones académicas por el estudiante

Usa un tono motivador, empático y educativo. Enfócate en el proceso de aprendizaje,
no solo en los resultados.
"""
    
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """Formatea datos del contexto de mentor académico"""
        resultado = []
        
        # Formatear datos académicos
        datos_academicos = datos.get('datos_academicos')
        if datos_academicos:
            resultado.append("=== DATOS ACADÉMICOS ===")
            resultado.append(f"Carrera: {datos_academicos.get('carrera', 'No especificada')}")
            resultado.append(f"Ciclo actual: {datos_academicos.get('ciclo_actual', 'N/A')}")
            resultado.append(f"Estado de matrícula: {datos_academicos.get('estado_matricula', 'N/A')}")
            resultado.append(f"Créditos aprobados: {datos_academicos.get('creditos_aprobados', 0)}")
            resultado.append(f"Créditos desaprobados: {datos_academicos.get('creditos_desaprobados', 0)}")
            resultado.append(f"Promedio ponderado: {datos_academicos.get('promedio_ponderado', 0):.2f}")
            resultado.append(f"Avance de malla: {datos_academicos.get('avance_malla', 0):.1f}%")
            resultado.append(f"Asistencia promedio: {datos_academicos.get('asistencia_promedio', 0):.1f}%")
            
            cursos_reprobados = datos_academicos.get('cursos_reprobados', [])
            if cursos_reprobados:
                resultado.append(f"Cursos reprobados: {', '.join(cursos_reprobados)}")
            
            historial_retirados = datos_academicos.get('historial_retirados', [])
            if historial_retirados:
                resultado.append(f"Cursos retirados: {len(historial_retirados)}")
        else:
            resultado.append("No hay datos académicos disponibles.")
        
        resultado.append("")
        
        # Formatear tareas
        tareas = datos.get('tareas', [])
        if tareas:
            resultado.append(f"=== TAREAS PENDIENTES ({len(tareas)}) ===")
            for idx, tarea in enumerate(tareas[:5], 1):  # Mostrar máximo 5
                texto = tarea.get('texto', 'Sin descripción')
                resultado.append(f"{idx}. {texto[:100]}...")
            
            if len(tareas) > 5:
                resultado.append(f"... y {len(tareas) - 5} tareas más")
        else:
            resultado.append("=== TAREAS PENDIENTES ===")
            resultado.append("No hay tareas registradas.")
        
        return "\n".join(resultado)