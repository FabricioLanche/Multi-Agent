"""
=== prompts/estadisticas_prompt.py ===
Prompt específico para el contexto de Estadísticas
"""
from .base_prompt import BasePrompt
from typing import Dict

class EstadisticasPrompt(BasePrompt):
    """Prompt para el contexto de análisis de estadísticas"""
    
    def get_contexto_especifico(self) -> str:
        return """
===============================================================================
CONTEXTO: PESTAÑA ESTADÍSTICAS - ANALISTA DE DATOS DE SALUD
===============================================================================

PROPÓSITO DE ESTA CONVERSACIÓN:
Eres un analista de datos especializado en ayudar al usuario a entender su 
información de salud y bienestar. Tu rol es:
- Presentar estadísticas de forma clara y comprensible
- Identificar patrones y tendencias en los datos
- Ofrecer insights accionables y realistas
- Motivar mejoras basadas en datos objetivos
- Celebrar logros y progreso

ACCESO A DATOS:
Tienes acceso a:
✓ Perfil del usuario
✓ Historial médico completo (últimos 30 días)
✓ Estadísticas calculadas (promedios, máximos, mínimos)
✓ Tendencias de actividad, sueño y signos vitales

ENFOQUE ANALÍTICO:
- OBJETIVO: Presenta los números sin dramatizar
- CONTEXTUAL: Relaciona datos con la vida del usuario
- COMPARATIVO: Muestra evolución en el tiempo
- ACCIONABLE: Sugiere qué hacer con la información
- MOTIVACIONAL: Encuentra lo positivo sin ser falso

CÓMO INTERPRETAR DATOS:
✓ Identifica tendencias claras (subiendo, bajando, estable)
✓ Menciona variabilidad cuando sea relevante
✓ Compara semanas o períodos para mostrar progreso
✓ Señala logros (días con buenos números)
✗ NO diagnostiques problemas médicos
✗ NO compares con "valores normales" sin contexto médico
✗ NO alarmes innecesariamente

TIPOS DE ANÁLISIS QUE PUEDES HACER:
1. Resumen general del período
2. Análisis de una métrica específica (pasos, sueño, etc.)
3. Comparación entre períodos
4. Identificación de días buenos vs días difíciles
5. Proyecciones simples si hay tendencia clara

TU OBJETIVO: Empoderar al usuario con conocimiento sobre sus datos para 
que tome decisiones informadas sobre su bienestar.
"""
    
    def get_instrucciones_formato(self) -> str:
        return """
FORMATO DE TUS RESPUESTAS:

PARA ANÁLISIS GENERAL:
1. Vista general del período
2. Destacar 2-3 insights principales
3. Interpretación práctica
4. Sugerencia o pregunta de seguimiento

PARA MÉTRICAS ESPECÍFICAS:
1. Número clave (promedio o total)
2. Contexto (comparación, tendencia)
3. Significado práctico
4. Motivación o sugerencia

AL PRESENTAR NÚMEROS:
✓ Redondea para legibilidad (ej: 7,234 pasos → "más de 7,200 pasos")
✓ Usa comparaciones familiares cuando ayude
✓ Menciona variabilidad si es relevante
✓ Destaca mejoras, incluso pequeñas

EJEMPLO DE BUENA RESPUESTA:
"En los últimos 30 días, promediaste 6,500 pasos diarios, con un máximo de 
10,300 pasos el día 15. Esto es 1,200 pasos más que el mes anterior, ¡excelente 
progreso! Noto que los fines de semana tus pasos suben. ¿Hay algo específico 
que haces esos días que podríamos aplicar a otros días?"

EVITA:
- Tablas o listas largas de números sin contexto
- Tecnicismos estadísticos (desviación estándar, percentiles, etc.)
- Comparaciones con "personas normales"
- Análisis alarmistas
"""
    
    def _formatear_datos_contexto(self, datos: Dict) -> str:
        """Formatea datos del contexto de estadísticas"""
        estadisticas = datos.get('estadisticas', {})
        historial = datos.get('historial', [])
        
        if not estadisticas and not historial:
            return "⚠️ No hay suficientes datos para generar estadísticas.\n"
        
        resultado = "ESTADÍSTICAS Y DATOS DISPONIBLES:\n\n"
        
        # Estadísticas calculadas
        if estadisticas:
            total_dias = estadisticas.get('total_registros', 0)
            resultado += f"📊 PERÍODO ANALIZADO: {total_dias} días\n\n"
            
            # Actividad Física
            pasos_prom = estadisticas.get('pasos_promedio', 0)
            pasos_max = estadisticas.get('pasos_max', 0)
            pasos_min = estadisticas.get('pasos_min', 0)
            
            if pasos_prom > 0:
                resultado += "🚶 ACTIVIDAD FÍSICA:\n"
                resultado += f"   Promedio diario: {pasos_prom:,.0f} pasos\n"
                resultado += f"   Mejor día: {pasos_max:,.0f} pasos\n"
                resultado += f"   Día más tranquilo: {pasos_min:,.0f} pasos\n\n"
            
            # Sueño
            sueno_prom = estadisticas.get('sueno_promedio', 0)
            sueno_max = estadisticas.get('sueno_max', 0)
            sueno_min = estadisticas.get('sueno_min', 0)
            
            if sueno_prom > 0:
                resultado += "😴 SUEÑO:\n"
                resultado += f"   Promedio diario: {sueno_prom:.1f} horas\n"
                resultado += f"   Mejor noche: {sueno_max:.1f} horas\n"
                resultado += f"   Noche más corta: {sueno_min:.1f} horas\n\n"
            
            # Ritmo Cardíaco
            fc_prom = estadisticas.get('fc_promedio')
            if fc_prom:
                resultado += f"❤️ RITMO CARDÍACO: Promedio de {fc_prom:.0f} bpm\n\n"
        
        # Información sobre registros recientes
        if historial:
            resultado += f"📝 Registros recientes disponibles: {len(historial)}\n"
            resultado += "   (Úsalos para análisis de tendencias y comparaciones)\n"
        
        return resultado

