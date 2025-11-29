import os
import json
import boto3
import base64
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
TABLE_RECETAS = os.environ.get('TABLE_RECETAS', 'Recetas')
S3_BUCKET = os.environ.get('S3_BUCKET_RECETAS')
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
        
        # Obtener receta_id de pathParameters
        receta_id = None
        if event.get('pathParameters'):
            receta_id = event['pathParameters'].get('id')
        
        if not receta_id:
            return _response(400, {"message": "receta_id es requerido"})
        
        # Eliminar de DynamoDB
        try:
            # Primero obtener la receta para saber si tiene imagen en S3
            response = table_recetas.get_item(
                Key={
                    'correo': user_email,
                    'receta_id': receta_id
                }
            )
            
            if 'Item' not in response:
                return _response(404, {"message": "Receta no encontrada"})
            
            item = response['Item']
            
            # Eliminar imagen de S3 si existe
            if S3_BUCKET and 'url_receta' in item and item['url_receta']:
                try:
                    # Extraer key del S3 desde la URL
                    s3_key = f"recetas/{user_email}/{receta_id}.jpg"
                    s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
                except Exception as s3_error:
                    print(f"Error al eliminar imagen de S3: {s3_error}")
            
            # Eliminar de DynamoDB
            table_recetas.delete_item(
                Key={
                    'correo': user_email,
                    'receta_id': receta_id
                }
            )
            
            return _response(200, {
                "message": "Receta eliminada exitosamente",
                "receta_id": receta_id
            })
            
        except ClientError as e:
            return _response(500, {"message": f"Error al eliminar receta: {str(e)}"})
    
    except Exception as e:
        return _response(500, {"message": str(e)})

def eliminarReceta(event, context):
    return lambda_handler(event, context)
