"""
Lambda para análisis de riesgo de deserción con IA
Endpoint: POST /analisis/usuario
Analiza datos del estudiante y calcula riesgo de deserción
Soporta conversación continua usando Gemini Chat
"""
import json
import os
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Attr
from google import genai

# Configuración DynamoDB
dynamodb = boto3.resource('dynamodb')
table_usuarios = dynamodb.Table(os.getenv('TABLE_USUARIOS', 'Usuario'))
table_academicos = dynamodb.Table(os.getenv('TABLE_DATOS_ACADEMICOS', 'DatosAcademicos'))
table_emocionales = dynamodb.Table(os.getenv('TABLE_DATOS_EMOCIONALES', 'DatosEmocionales'))
table_socioeconomicos = dynamodb.Table(os.getenv('TABLE_DATOS_SOCIOECONOMICOS', 'DatosSocioeconomicos'))

# Configuración Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=GEMINI_API_KEY)


def decimal_to_float(obj):
    """Convierte Decimal a float para JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


def obtener_usuario_por_correo(correo):
    """Busca usuario por correo"""
    response = table_usuarios.scan(
        FilterExpression=Attr('correo').eq(correo),
        Limit=1
    )
    items = response.get('Items', [])
    return items[0] if items else None


def obtener_datos_por_usuario_id(table, usuario_id):
    """Obtiene datos de una tabla por usuarioId"""
    try:
        response = table.query(
            KeyConditionExpression='usuarioId = :uid',
            ExpressionAttributeValues={':uid': usuario_id},
            Limit=1,
            ScanIndexForward=False
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        print(f"⚠️ Error obteniendo datos de {table.name}: {str(e)}")
        return None


def construir_prompt_analisis(usuario, datos_acad, datos_emo, datos_socio):
    """Construye el prompt del sistema para análisis de deserción"""
    
    prompt_sistema = """
Eres un analista experto en retención estudiantil y predicción de deserción académica.

Tu misión es evaluar el riesgo de deserción de estudiantes universitarios basándote en sus datos académicos, emocionales y socioeconómicos.

INDICADORES DE RIESGO DE DESERCIÓN:

📚 **Académicos (peso: 40%)**
- Promedio ponderado < 11: ALTO riesgo
- Promedio 11-13: MEDIO riesgo  
- Promedio > 13: BAJO riesgo
- Cursos reprobados > 3: ALTO riesgo
- Créditos desaprobados > 15: ALTO riesgo
- Asistencia < 70%: ALTO riesgo
- Historial de retiros de cursos: MEDIO-ALTO riesgo

🧠 **Emocionales/Conductuales (peso: 30%)**
- Frecuencia de acceso RARA_VEZ o NUNCA: ALTO riesgo
- Horas de estudio < 5/semana: MEDIO-ALTO riesgo
- No usa servicios de tutoría: MEDIO riesgo
- No usa servicios de psicología cuando hay bajo rendimiento: MEDIO riesgo
- No participa en actividades extracurriculares: BAJO-MEDIO riesgo

💰 **Socioeconómicos (peso: 30%)**
- Situación TRABAJA_Y_ESTUDIA: MEDIO-ALTO riesgo
- Financiamiento por CREDITO sin avance adecuado: MEDIO riesgo
- Dependencia económica + bajo rendimiento: ALTO riesgo
- Ingreso estimado muy bajo: MEDIO riesgo

FORMATO DE RESPUESTA:

Debes responder en formato JSON ESTRICTO con esta estructura:
{
  "riesgo_desercion": <número 0-100>,
  "nivel_riesgo": "<BAJO|MEDIO|ALTO>",
  "mensaje": "<análisis detallado en 2-3 párrafos>",
  "factores_riesgo": ["<factor1>", "<factor2>", ...],
  "factores_protectores": ["<factor1>", "<factor2>", ...],
  "recomendaciones": ["<recomendación1>", "<recomendación2>", ...]
}

IMPORTANTE:
- El porcentaje debe ser un número del 0 al 100
- BAJO: 0-33, MEDIO: 34-66, ALTO: 67-100
- Sé específico y basado en datos
- El mensaje debe ser empático pero realista
- Incluye recomendaciones accionables
"""

    # Construir contexto del estudiante
    contexto_estudiante = f"""
=== DATOS DEL ESTUDIANTE ===

**Usuario:**
- Correo: {usuario.get('correo', 'N/A')}
- Autorización de datos: {usuario.get('autorizacion', False)}

"""

    # Datos académicos
    if datos_acad:
        contexto_estudiante += f"""
**Datos Académicos:**
- Carrera: {datos_acad.get('carrera', 'N/A')}
- Ciclo actual: {datos_acad.get('ciclo_actual', 'N/A')}
- Estado de matrícula: {datos_acad.get('estado_matricula', 'N/A')}
- Promedio ponderado: {datos_acad.get('promedio_ponderado', 0):.2f}
- Créditos aprobados: {datos_acad.get('creditos_aprobados', 0)}
- Créditos desaprobados: {datos_acad.get('creditos_desaprobados', 0)}
- Avance de malla: {datos_acad.get('avance_malla', 0):.1f}%
- Asistencia promedio: {datos_acad.get('asistencia_promedio', 0):.1f}%
- Cursos reprobados: {len(datos_acad.get('cursos_reprobados', []))}
- Historial de retiros: {len(datos_acad.get('historial_retirados', []))}
"""
    else:
        contexto_estudiante += "\n**Datos Académicos:** No disponibles\n"

    # Datos emocionales
    if datos_emo:
        contexto_estudiante += f"""
**Datos Emocionales:**
- Frecuencia acceso plataforma: {datos_emo.get('frecuencia_acceso_plataforma', 'N/A')}
- Horas de estudio semanales: {datos_emo.get('horas_estudio_estimadas', 'N/A')}
- Uso de tutoría: {datos_emo.get('uso_servicios_tutoria', 'N/A')}
- Uso de psicología: {datos_emo.get('uso_servicios_psicologia', 'N/A')}
- Actividades extracurriculares: {'Sí' if datos_emo.get('actividades_extracurriculares') else 'No'}
"""
    else:
        contexto_estudiante += "\n**Datos Emocionales:** No disponibles\n"

    # Datos socioeconómicos
    if datos_socio:
        contexto_estudiante += f"""
**Datos Socioeconómicos:**
- Tipo de financiamiento: {datos_socio.get('tipo_financiamiento', 'N/A')}
- Situación laboral: {datos_socio.get('situacion_laboral', 'N/A')}
- Ingreso estimado mensual: {datos_socio.get('ingreso_estimado', 0):.2f}
- Dependencia económica: {'Sí' if datos_socio.get('dependencia_economica') else 'No'}
"""
    else:
        contexto_estudiante += "\n**Datos Socioeconómicos:** No disponibles\n"

    return prompt_sistema, contexto_estudiante


def handler(event, context):
    """
    Analiza riesgo de deserción de un estudiante
    
    Body JSON:
    {
        "correo": "estudiante@utec.edu.pe",
        "mensaje": "opcional, para conversación"
    }
    
    Returns:
        {
            "correo": "...",
            "riesgo_desercion": 0-100,
            "nivel_riesgo": "BAJO|MEDIO|ALTO",
            "mensaje": "análisis detallado",
            "factores_riesgo": [...],
            "factores_protectores": [...],
            "recomendaciones": [...]
        }
    """
    try:
        # Parsear body
        body = json.loads(event.get('body', '{}'))
        correo = body.get('correo')
        mensaje_usuario = body.get('mensaje', '')
        
        if not correo:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': True,
                    'message': 'Se requiere el campo "correo"'
                }, ensure_ascii=False)
            }
        
        # 1. Obtener todos los datos del usuario
        usuario = obtener_usuario_por_correo(correo)
        
        if not usuario:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': True,
                    'message': f'Usuario con correo {correo} no encontrado'
                }, ensure_ascii=False)
            }
        
        usuario_id = usuario.get('id')
        
        # Obtener datos de las 3 tablas adicionales
        datos_acad = obtener_datos_por_usuario_id(table_academicos, usuario_id)
        datos_emo = obtener_datos_por_usuario_id(table_emocionales, usuario_id)
        datos_socio = obtener_datos_por_usuario_id(table_socioeconomicos, usuario_id)
        
        # Convertir Decimals para serialización
        usuario = decimal_to_float(usuario)
        datos_acad = decimal_to_float(datos_acad) if datos_acad else None
        datos_emo = decimal_to_float(datos_emo) if datos_emo else None
        datos_socio = decimal_to_float(datos_socio) if datos_socio else None
        
        # 2. Construir prompt de análisis
        prompt_sistema, contexto_estudiante = construir_prompt_analisis(
            usuario, datos_acad, datos_emo, datos_socio
        )
        
        # 3. Crear chat de Gemini
        chat = client.chats.create(model="gemini-2.0-flash-exp")
        
        # Enviar contexto del sistema y datos del estudiante
        instruccion_inicial = f"{prompt_sistema}\n\n{contexto_estudiante}\n\nAnaliza estos datos y proporciona tu evaluación en formato JSON."
        
        if mensaje_usuario:
            # Si hay mensaje del usuario, agregarlo al contexto
            instruccion_inicial += f"\n\nPregunta del analista: {mensaje_usuario}"
        
        # Generar análisis
        response = chat.send_message(instruccion_inicial)
        respuesta_texto = response.text
        
        # 4. Parsear respuesta JSON
        try:
            # Intentar extraer JSON de la respuesta
            # Gemini a veces incluye markdown, necesitamos extraer el JSON puro
            inicio_json = respuesta_texto.find('{')
            fin_json = respuesta_texto.rfind('}') + 1
            
            if inicio_json != -1 and fin_json > inicio_json:
                json_str = respuesta_texto[inicio_json:fin_json]
                analisis = json.loads(json_str)
            else:
                # Si no hay JSON válido, crear respuesta por defecto
                analisis = {
                    'riesgo_desercion': 50,
                    'nivel_riesgo': 'MEDIO',
                    'mensaje': respuesta_texto,
                    'factores_riesgo': [],
                    'factores_protectores': [],
                    'recomendaciones': []
                }
        
        except json.JSONDecodeError as e:
            print(f"⚠️ Error parseando JSON de Gemini: {str(e)}")
            print(f"Respuesta original: {respuesta_texto}")
            # Respuesta de fallback
            analisis = {
                'riesgo_desercion': 50,
                'nivel_riesgo': 'MEDIO',
                'mensaje': respuesta_texto,
                'factores_riesgo': [],
                'factores_protectores': [],
                'recomendaciones': []
            }
        
        # 5. Agregar correo a la respuesta
        analisis['correo'] = correo
        analisis['usuario_id'] = usuario_id
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps(analisis, ensure_ascii=False)
        }
    
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': True,
                'message': 'El body debe ser JSON válido'
            }, ensure_ascii=False)
        }
    
    except Exception as e:
        print(f"❌ Error en análisis de deserción: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': True,
                'message': 'Error interno al analizar usuario',
                'detalle': str(e)
            }, ensure_ascii=False)
        }
