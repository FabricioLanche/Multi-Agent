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
TABLE_RECETAS = os.environ.get('TABLE_RECETAS', 'Recetas')
table_recetas = dynamodb.Table(TABLE_RECETAS)

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

def get_user_email(event):
    """Extrae el email del usuario desde el token"""
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    auth_header = headers.get('authorization')
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_jwt_payload(token)
        if payload:
            return payload.get('email') or payload.get('username')
    return None

def lambda_handler(event, context):
    try:
        # Autenticación
        user_email = get_user_email(event)
        if not user_email:
            return _response(401, {"message": "No autorizado. Token faltante o inválido."})
        
        # Listar todas las recetas del usuario
        try:
            response = table_recetas.query(
                KeyConditionExpression='correo = :email',
                ExpressionAttributeValues={
                    ':email': user_email
                }
            )
            
            recetas = response.get('Items', [])
            recetas = convert_decimal(recetas)

            return _response(200, {
                "message": "Recetas obtenidas exitosamente",
                "count": len(recetas),
                "data": recetas
            })
            
        except ClientError as e:
            return _response(500, {"message": f"Error al listar recetas: {str(e)}"})
    
    except Exception as e:
        return _response(500, {"message": str(e)})

def listarRecetas(event, context):
    return lambda_handler(event, context)
