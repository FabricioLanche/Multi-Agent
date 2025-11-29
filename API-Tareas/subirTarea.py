import os
import json
import base64
import boto3
import time
import uuid
from io import BytesIO
import cgi

# ===============================
# 0. Configuración y Clientes AWS
# ===============================
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

TABLE_TAREAS = os.environ.get('TABLE_TAREAS', 'Tareas')
S3_BUCKET = os.environ.get('S3_BUCKET_TAREAS')

table_tareas = dynamodb.Table(TABLE_TAREAS)

# ===============================
# 1. Inicializar cliente Gemini
# ===============================
try:
    from google import genai
    from google.genai import types
    _IMPORT_ERROR = None
except Exception as e:
    genai = None
    types = None
    _IMPORT_ERROR = str(e)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = None
_INIT_ERROR = None

if genai is not None and GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        _INIT_ERROR = str(e)
else:
    if genai is None:
        _INIT_ERROR = f"Dependencia faltante: {_IMPORT_ERROR}"
    elif not GEMINI_API_KEY:
        _INIT_ERROR = "GEMINI_API_KEY no configurada en el entorno"

# ===============================
# 2. Helpers
# ===============================
def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }

def decode_jwt_payload(token):
    """Decodifica el payload de un JWT sin verificar firma"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        payload = parts[1]
        padding = '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding).decode('utf-8')
        return json.loads(decoded)
    except Exception:
        return None

def get_user_id(event, fs=None):
    """Obtiene el ID del usuario desde el token"""
    token = None
    
    # Buscar en Header Authorization
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    auth_header = headers.get('authorization')
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    
    # Buscar en multipart body
    if not token and fs and 'token' in fs:
        token = fs['token'].value
        
    if not token:
        return None
        
    payload = decode_jwt_payload(token)
    if payload:
        # Buscar el campo 'sub' (subject) o 'id' que típicamente contiene el UUID del usuario
        return payload.get('sub') or payload.get('id') or payload.get('user_id')
    return None

# ===============================
# 3. Lambda Handler
# ===============================
def lambda_handler(event, context):
    try:
        # Validaciones tempranas
        if client is None:
            return _response(500, {
                "message": "Dependencia o inicialización faltante",
                "detail": _INIT_ERROR
            })

        # ===============================
        # 3a. Procesar Multipart
        # ===============================
        headers_raw = event.get('headers') or {}
        headers = {k.lower(): v for k, v in headers_raw.items()}
        content_type = headers.get('content-type')
        
        if not content_type:
            return _response(400, {"message": "Content-Type header faltante"})
        
        if event.get('isBase64Encoded'):
            body_bytes = base64.b64decode(event.get('body') or "")
        else:
            body = event.get('body') or ""
            if isinstance(body, str):
                body_bytes = body.encode('utf-8')
            else:
                body_bytes = body
        
        env = {'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type}
        fs = cgi.FieldStorage(fp=BytesIO(body_bytes), environ=env, keep_blank_values=True)
        
        if 'file' not in fs:
            return _response(400, {"message": "No se encontró archivo 'file' en la request"})
        
        file_item = fs['file']
        image_bytes = file_item.file.read()
        
        # ===============================
        # 3b. Autenticación
        # ===============================
        usuario_id = get_user_id(event, fs)
        if not usuario_id:
            return _response(401, {"message": "No autorizado. Token faltante o inválido."})
        
        # ===============================
        # 3c. Generar ID temprano
        # ===============================
        tarea_id = str(uuid.uuid4())
        
        # ===============================
        # 3d. Análisis con Gemini
        # ===============================
        prompt = """
        Eres un analizador especializado en extraer texto de imágenes de tareas o documentos.
        A partir de la imagen dada, extrae TODO el texto visible y devuélvelo 
        exclusivamente como un JSON válido.
        
        Estructura obligatoria:
        {
          "texto": "Todo el texto extraído de la imagen"
        }
        
        Reglas:
        - Extrae todo el texto visible en la imagen
        - Preserva saltos de línea importantes con \\n
        - No agregues explicaciones fuera del JSON
        - Si no hay texto legible, devuelve "texto": ""
        - Mantén la estructura y formato del texto original en lo posible
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt
            ]
        )
        
        # Extracción robusta de JSON
        import re
        raw_text = ""
        if hasattr(response, 'text') and response.text:
            raw_text = response.text
        else:
            raw_text = str(response)
        
        def _extract_json_candidate(text):
            if not text: return None
            t = text.strip()
            t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
            t = re.sub(r"\s*```$", "", t, flags=re.IGNORECASE)
            start = t.find('{')
            end = t.rfind('}')
            if start != -1 and end != -1 and end > start:
                return t[start:end+1].strip()
            return t
        
        candidate = _extract_json_candidate(raw_text)
        
        try:
            data = json.loads(candidate)
        except Exception:
            return _response(500, {
                "message": "Error al parsear respuesta de Gemini",
                "raw": raw_text
            })
        
        # ===============================
        # 3e. Subir imagen a S3
        # ===============================
        imagen_url = None
        s3_key = f"tareas/{usuario_id}/{tarea_id}.jpg"
        
        if S3_BUCKET:
            try:
                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=image_bytes,
                    ContentType='image/jpeg'
                )
                imagen_url = s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={'Bucket': S3_BUCKET, 'Key': s3_key},
                    ExpiresIn=86400  # 24h
                )
                print(f"✅ Imagen subida y URL firmada generada: {imagen_url}")
            except Exception as s3_error:
                print(f"❌ Error al subir a S3 o generar URL firmada: {s3_error}")
        else:
            print("⚠️ S3_BUCKET no configurado, saltando subida de imagen")
        
        # ===============================
        # 3f. Guardar en DynamoDB
        # ===============================
        item = {
            'id': tarea_id,
            'usuarioId': usuario_id,
            'texto': data.get('texto', '')
        }
        
        if imagen_url:
            item['imagenUrl'] = imagen_url
        
        try:
            table_tareas.put_item(Item=item)
            print(f"✅ Tarea guardada en DynamoDB: {tarea_id}")
        except Exception as e:
            return _response(500, {"message": f"Error al guardar en BD: {str(e)}"})
        
        # ===============================
        # 3g. Respuesta Final
        # ===============================
        return _response(200, {
            "message": "Tarea procesada y guardada exitosamente",
            "tarea_id": tarea_id,
            "imagen_url": imagen_url,
            "data": item
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error general: {str(e)}")
        traceback.print_exc()
        return _response(500, {"message": str(e)})

# Wrapper para Serverless
def subirTarea(event, context):
    return lambda_handler(event, context)