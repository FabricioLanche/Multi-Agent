import os
import json
import boto3
import base64
from botocore.exceptions import ClientError
from decimal import Decimal

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
TABLE_TAREAS = os.environ.get('TABLE_TAREAS', 'Tareas')
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
        
        # Obtener tarea_id de pathParameters o queryStringParameters
        tarea_id = None
        if event.get('pathParameters'):
            tarea_id = event['pathParameters'].get('id')
        elif event.get('queryStringParameters'):
            tarea_id = event['queryStringParameters'].get('tarea_id')
        
        if not tarea_id:
            return _response(400, {"message": "tarea_id es requerido"})
        
        # Obtener la tarea de DynamoDB
        try:
            response = table_tareas.get_item(
                Key={
                    'usuarioId': usuario_id,
                    'id': tarea_id
                }
            )
            
            if 'Item' not in response:
                return _response(404, {"message": "Tarea no encontrada"})
            
            item = convert_decimal(response['Item'])

            return _response(200, {
                "message": "Tarea obtenida exitosamente",
                "data": item
            })
            
        except ClientError as e:
            return _response(500, {"message": f"Error al obtener tarea: {str(e)}"})
    
    except Exception as e:
        return _response(500, {"message": str(e)})

def obtenerTarea(event, context):
    return lambda_handler(event, context)