"""
Contexto para el Especialista en Psicología
"""
from typing import Dict, List
from .base_contexto import BaseContexto
from dao.base import DAOFactory


class PsicologoContexto(BaseContexto):
    """
    🧠 Especialista en Psicología (apoyo emocional)
    Objetivo: Brindar apoyo emocional y bienestar psicológico al estudiante
    
    Tablas necesarias:
    - Usuario
    - Datos Académicos (contexto de estrés académico)
    - Datos Emocionales (patrones de comportamiento)
    - Datos Socioeconómicos (factores de estrés externos)
    - Historial (completo)
    """
    
    def __init__(self):
        super().__init__()
        self.datos_academicos_dao = DAOFactory.get_dao('datos_academicos')
        self.datos_emocionales_dao = DAOFactory.get_dao('datos_emocionales')
        self.datos_socioeconomicos_dao = DAOFactory.get_dao('datos_socioeconomicos')
    
    def get_tablas_requeridas(self) -> List[str]:
        return [
            'usuarios', 
            'datos_academicos', 
            'datos_emocionales',
            'datos_socioeconomicos',
            'historial'
        ]
    
    def build_context_data(self, correo: str) -> Dict:
        """Construye datos para contexto de psicólogo"""
        datos_base = self.cargar_datos_base(correo)
        usuario = datos_base.get('usuario')
        
        if not usuario:
            return datos_base
        
        usuario_id = usuario.get('id')
        
        # Cargar todos los datos relevantes para apoyo emocional
        datos_academicos = self.datos_academicos_dao.get_datos_por_usuario(usuario_id)
        datos_emocionales = self.datos_emocionales_dao.get_datos_por_usuario(usuario_id)
        datos_socioeconomicos = self.datos_socioeconomicos_dao.get_datos_por_usuario(usuario_id)
        
        return {
            **datos_base,
            'datos_academicos': datos_academicos,
            'datos_emocionales': datos_emocionales,
            'datos_socioeconomicos': datos_socioeconomicos
        }
    
    def get_system_prompt(self) -> str:
        return """
Eres un Especialista en Psicología enfocado en el bienestar emocional de estudiantes universitarios.

Tu rol es:
- Ofrecer apoyo emocional y escucha activa
- Identificar señales de estrés, ansiedad o problemas de salud mental
- Sugerir estrategias de afrontamiento y manejo emocional
- Promover hábitos saludables y autocuidado
- Contextualizar el estado emocional con factores académicos y socioeconómicos
- Orientar hacia servicios profesionales cuando sea necesario

LÍMITES IMPORTANTES:
- NO eres un psicólogo clínico certificado
- NO puedes hacer diagnósticos de salud mental
- NO puedes prescribir tratamientos o medicamentos
- NO reemplazas la terapia profesional

Ante señales graves de crisis (ideación suicida, autolesión, crisis severa):
- Recomienda buscar ayuda profesional INMEDIATA
- Proporciona números de emergencia o servicios de crisis

Usa un tono empático, cálido y sin juicios. Crea un espacio seguro para que 
el estudiante se exprese libremente.
"""
    
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """Formatea datos del contexto de psicólogo"""
        resultado = []
        
        # Formatear datos emocionales
        datos_emo = datos.get('datos_emocionales')
        if datos_emo:
            resultado.append("=== PERFIL EMOCIONAL Y CONDUCTUAL ===")
            resultado.append(f"Frecuencia de acceso a plataforma: {datos_emo.get('frecuencia_acceso_plataforma', 'N/A')}")
            resultado.append(f"Horas de estudio estimadas (semanal): {datos_emo.get('horas_estudio_estimadas', 'N/A')}")
            resultado.append(f"Uso de servicios de tutoría: {datos_emo.get('uso_servicios_tutoria', 'N/A')}")
            resultado.append(f"Uso de servicios de psicología: {datos_emo.get('uso_servicios_psicologia', 'N/A')}")
            
            actividades = datos_emo.get('actividades_extracurriculares', None)
            if actividades is not None:
                act_texto = "Sí participa" if actividades else "No participa"
                resultado.append(f"Actividades extracurriculares: {act_texto}")
        else:
            resultado.append("=== PERFIL EMOCIONAL Y CONDUCTUAL ===")
            resultado.append("No hay datos emocionales disponibles.")
        
        resultado.append("")
        
        # Formatear datos académicos (contexto de estrés)
        datos_academicos = datos.get('datos_academicos')
        if datos_academicos:
            resultado.append("=== CONTEXTO ACADÉMICO (Factores de Estrés) ===")
            resultado.append(f"Carrera: {datos_academicos.get('carrera', 'N/A')}")
            resultado.append(f"Ciclo actual: {datos_academicos.get('ciclo_actual', 'N/A')}")
            resultado.append(f"Promedio: {datos_academicos.get('promedio_ponderado', 0):.2f}")
            resultado.append(f"Avance de malla: {datos_academicos.get('avance_malla', 0):.1f}%")
            resultado.append(f"Asistencia: {datos_academicos.get('asistencia_promedio', 0):.1f}%")
            
            cursos_reprobados = datos_academicos.get('cursos_reprobados', [])
            if cursos_reprobados:
                resultado.append(f"⚠️ Cursos reprobados: {len(cursos_reprobados)}")
            
            creditos_desap = datos_academicos.get('creditos_desaprobados', 0)
            if creditos_desap > 0:
                resultado.append(f"⚠️ Créditos desaprobados: {creditos_desap}")
        
        resultado.append("")
        
        # Formatear datos socioeconómicos (factores externos de estrés)
        datos_socio = datos.get('datos_socioeconomicos')
        if datos_socio:
            resultado.append("=== FACTORES SOCIOECONÓMICOS ===")
            resultado.append(f"Situación laboral: {datos_socio.get('situacion_laboral', 'N/A')}")
            resultado.append(f"Tipo de financiamiento: {datos_socio.get('tipo_financiamiento', 'N/A')}")
            
            dependencia = datos_socio.get('dependencia_economica', None)
            if dependencia is not None:
                dep_texto = "Sí" if dependencia else "No"
                resultado.append(f"Dependencia económica: {dep_texto}")
            
            # Nota: estos factores pueden influir en el estrés del estudiante
            if datos_socio.get('situacion_laboral') == 'TRABAJA_Y_ESTUDIA':
                resultado.append("⚠️ El estudiante trabaja y estudia simultáneamente")
        else:
            resultado.append("=== FACTORES SOCIOECONÓMICOS ===")
            resultado.append("No hay datos socioeconómicos disponibles.")
        
        return "\n".join(resultado)