import os
import json
import base64
import boto3
import time
import uuid
from io import BytesIO
from botocore.exceptions import ClientError
from decimal import Decimal
import cgi
import re

def convert_decimal(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    if isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    return obj

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
TABLE_TAREAS = os.environ.get('TABLE_TAREAS', 'Tareas')
TABLE_USUARIOS = os.environ.get('TABLE_USUARIOS', 'Usuarios')
S3_BUCKET = os.environ.get('S3_BUCKET_TAREAS')
table_tareas = dynamodb.Table(TABLE_TAREAS)

# ===============================
# Inicializar cliente Gemini
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

def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }

def get_user_id_from_email(correo):
    """Obtiene el ID del usuario desde DynamoDB usando su correo"""
    try:
        table_usuarios = dynamodb.Table(TABLE_USUARIOS)
        
        response = table_usuarios.scan(
            FilterExpression='correo = :correo',
            ExpressionAttributeValues={':correo': correo}
        )
        
        items = response.get('Items', [])
        if items:
            return items[0].get('id')
        return None
    except Exception as e:
        print(f"Error al obtener usuario: {e}")
        return None

def get_email_from_request(fs):
    """Extrae el correo del usuario desde el multipart form"""
    if 'correo' in fs:
        return fs['correo'].value
    return None

def lambda_handler(event, context):
    try:
        # ===============================
        # Parsear multipart/form-data
        # ===============================
        content_type = event.get('headers', {}).get('content-type', '') or \
                       event.get('headers', {}).get('Content-Type', '')
        
        if 'multipart/form-data' not in content_type:
            return _response(400, {"message": "Se requiere multipart/form-data"})
        
        # Decodificar body
        body_encoded = event.get('body', '')
        if event.get('isBase64Encoded', False):
            body_bytes = base64.b64decode(body_encoded)
        else:
            body_bytes = body_encoded.encode('utf-8') if isinstance(body_encoded, str) else body_encoded
        
        # Parsear multipart
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': len(body_bytes)
        }
        
        headers = {
            'content-type': content_type,
            'content-length': str(len(body_bytes))
        }
        
        fs = cgi.FieldStorage(
            fp=BytesIO(body_bytes),
            environ=environ,
            headers=headers,
            keep_blank_values=True
        )
        
        # Extraer correo
        correo = get_email_from_request(fs)
        if not correo:
            return _response(400, {"message": "El campo 'correo' es requerido"})
        
        # Extraer tarea_id del multipart
        if 'id' not in fs:
            return _response(400, {"message": "El campo 'id' es requerido"})
        
        tarea_id = fs['id'].value
        if not tarea_id:
            return _response(400, {"message": "El campo 'id' no puede estar vacío"})
        
        # Extraer imagen
        if 'imagen' not in fs:
            return _response(400, {"message": "El campo 'imagen' es requerido"})
        
        imagen_file = fs['imagen']
        if not imagen_file.file:
            return _response(400, {"message": "No se pudo leer la imagen"})
        
        # Leer bytes de la imagen
        image_bytes = imagen_file.file.read()
        if not image_bytes:
            return _response(400, {"message": "La imagen está vacía"})
        
        # Obtener usuario_id desde DynamoDB
        usuario_id = get_user_id_from_email(correo)
        if not usuario_id:
            return _response(404, {"message": "Usuario no encontrado con ese correo"})
        
        # Verificar que la tarea existe y pertenece al usuario
        try:
            response = table_tareas.get_item(
                Key={
                    'usuarioId': usuario_id,
                    'id': tarea_id
                }
            )
            
            if 'Item' not in response:
                return _response(404, {"message": "Tarea no encontrada"})
            
            current_item = response['Item']
            
            # ===============================
            # Verificar disponibilidad de Gemini
            # ===============================
            if not client:
                return _response(500, {
                    "message": "Gemini no disponible",
                    "error": _INIT_ERROR
                })
            
            # ===============================
            # Análisis con Gemini
            # ===============================
            prompt = """
            Eres un asistente especializado en extraer texto de imágenes de tareas académicas.
            Analiza la imagen proporcionada y extrae TODO el texto visible.
            
            IMPORTANTE: Debes responder ÚNICAMENTE con un objeto JSON válido, sin texto adicional.
            
            Formato de respuesta requerido:
            {
              "texto": "Aquí va todo el texto extraído de la imagen"
            }
            
            Instrucciones:
            - Extrae todo el texto legible en español
            - Preserva saltos de línea importantes usando \\n
            - Mantén el formato y estructura del texto original
            - Si hay listas, tablas o estructuras especiales, intenta mantenerlas
            - Si no hay texto legible, devuelve: {"texto": ""}
            - NO agregues explicaciones, comentarios o texto fuera del JSON
            - NO uses bloques de código markdown (```), solo el JSON puro
            
            Recuerda: SOLO el objeto JSON, nada más.
            """
            
            response_gemini = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt
                ]
            )
            
            # Extracción robusta de JSON
            raw_text = ""
            if hasattr(response_gemini, 'text') and response_gemini.text:
                raw_text = response_gemini.text
            else:
                raw_text = str(response_gemini)
            
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
            # Eliminar imagen antigua de S3 si existe
            # ===============================
            if S3_BUCKET and 'imagenUrl' in current_item and current_item['imagenUrl']:
                try:
                    old_s3_key = f"tareas/{usuario_id}/{tarea_id}.jpg"
                    s3.delete_object(Bucket=S3_BUCKET, Key=old_s3_key)
                    print(f"🗑️ Imagen antigua eliminada: {old_s3_key}")
                except Exception as s3_error:
                    print(f"⚠️ Error al eliminar imagen antigua de S3: {s3_error}")
            
            # ===============================
            # Subir nueva imagen a S3
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
                    print(f"✅ Nueva imagen subida y URL firmada generada: {imagen_url}")
                except Exception as s3_error:
                    print(f"❌ Error al subir a S3 o generar URL firmada: {s3_error}")
            else:
                print("⚠️ S3_BUCKET no configurado, saltando subida de imagen")
            
            # ===============================
            # Actualizar en DynamoDB
            # ===============================
            update_expression = "SET texto = :texto"
            expression_attribute_values = {
                ':texto': data.get('texto', '')
            }
            
            if imagen_url:
                update_expression += ", imagenUrl = :imagenUrl"
                expression_attribute_values[':imagenUrl'] = imagen_url
            
            table_tareas.update_item(
                Key={
                    'usuarioId': usuario_id,
                    'id': tarea_id
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            
            # Obtener item actualizado
            updated_response = table_tareas.get_item(
                Key={
                    'usuarioId': usuario_id,
                    'id': tarea_id
                }
            )
            
            item = convert_decimal(updated_response['Item'])
            return _response(200, {
                "message": "Tarea actualizada exitosamente",
                "data": item
            })
            
        except ClientError as e:
            return _response(500, {"message": f"Error al actualizar tarea: {str(e)}"})
    
    except Exception as e:
        import traceback
        print(f"Error completo: {traceback.format_exc()}")
        return _response(500, {"message": str(e)})