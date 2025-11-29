import os
import json
import boto3
import base64
from botocore.exceptions import ClientError
from decimal import Decimal

def convert_decimal(obj):
    if isinstance(obj, Decimal):
        # si es entero devuelve int, si no float
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
TABLE_USUARIOS = os.environ.get('TABLE_USUARIOS', 'Usuarios')
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

def get_user_id(event):
    """Extrae el correo del query string y obtiene el ID del usuario"""
    if event.get('queryStringParameters'):
        correo = event['queryStringParameters'].get('correo')
        if correo:
            return get_user_id_from_email(correo)
    return None

def lambda_handler(event, context):
    try:
        # Obtener correo y validar
        usuario_id = get_user_id(event)
        if not usuario_id:
            return _response(400, {"message": "El parámetro 'correo' es requerido en query string"})
        
        # Listar todas las tareas del usuario
        try:
            response = table_tareas.query(
                KeyConditionExpression='usuarioId = :uid',
                ExpressionAttributeValues={
                    ':uid': usuario_id
                }
            )
            
            tareas = response.get('Items', [])
            tareas = convert_decimal(tareas)

            return _response(200, {
                "message": "Tareas obtenidas exitosamente",
                "count": len(tareas),
                "data": tareas
            })
            
        except ClientError as e:
            return _response(500, {"message": f"Error al listar tareas: {str(e)}"})
    
    except Exception as e:
        return _response(500, {"message": str(e)})

def listarTareas(event, context):
    return lambda_handler(event, context)