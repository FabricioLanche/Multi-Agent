import os
import json
import boto3
import base64
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
TABLE_TAREAS = os.environ.get('TABLE_TAREAS', 'Tareas')
S3_BUCKET = os.environ.get('S3_BUCKET_TAREAS')
table_tareas = dynamodb.Table(TABLE_TAREAS)

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

def get_user_id(event):
    """Extrae el ID del usuario desde el token"""
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    auth_header = headers.get('authorization')
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_jwt_payload(token)
        if payload:
            return payload.get('sub') or payload.get('id') or payload.get('user_id')
    return None

def lambda_handler(event, context):
    try:
        # Autenticación
        usuario_id = get_user_id(event)
        if not usuario_id:
            return _response(401, {"message": "No autorizado. Token faltante o inválido."})
        
        # Obtener tarea_id de pathParameters
        tarea_id = None
        if event.get('pathParameters'):
            tarea_id = event['pathParameters'].get('id')
        
        if not tarea_id:
            return _response(400, {"message": "tarea_id es requerido"})
        
        # Eliminar de DynamoDB
        try:
            # Primero obtener la tarea para saber si tiene imagen en S3
            response = table_tareas.get_item(
                Key={
                    'usuarioId': usuario_id,
                    'id': tarea_id
                }
            )
            
            if 'Item' not in response:
                return _response(404, {"message": "Tarea no encontrada"})
            
            item = response['Item']
            
            # Eliminar imagen de S3 si existe
            if S3_BUCKET and 'imagenUrl' in item and item['imagenUrl']:
                try:
                    # Extraer key del S3 desde la URL
                    s3_key = f"tareas/{usuario_id}/{tarea_id}.jpg"
                    s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
                except Exception as s3_error:
                    print(f"Error al eliminar imagen de S3: {s3_error}")
            
            # Eliminar de DynamoDB
            table_tareas.delete_item(
                Key={
                    'usuarioId': usuario_id,
                    'id': tarea_id
                }
            )
            
            return _response(200, {
                "message": "Tarea eliminada exitosamente",
                "tarea_id": tarea_id
            })
            
        except ClientError as e:
            return _response(500, {"message": f"Error al eliminar tarea: {str(e)}"})
    
    except Exception as e:
        return _response(500, {"message": str(e)})

def eliminarTarea(event, context):
    return lambda_handler(event, context)