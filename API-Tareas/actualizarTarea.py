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
    """Extrae el correo del body y obtiene el ID del usuario"""
    try:
        body = json.loads(event.get('body', '{}'))
        correo = body.get('correo')
        if correo:
            return get_user_id_from_email(correo)
    except:
        pass
    return None

def lambda_handler(event, context):
    try:
        # Parsear body
        try:
            body = json.loads(event.get('body', '{}'))
        except:
            return _response(400, {"message": "Body JSON inválido"})
        
        # Validar correo
        correo = body.get('correo')
        if not correo:
            return _response(400, {"message": "El campo 'correo' es requerido"})
        
        # Obtener usuario_id desde DynamoDB
        usuario_id = get_user_id_from_email(correo)
        if not usuario_id:
            return _response(404, {"message": "Usuario no encontrado con ese correo"})
        # Obtener tarea_id de pathParameters
        tarea_id = None
        if event.get('pathParameters'):
            tarea_id = event['pathParameters'].get('id')
        
        if not tarea_id:
            return _response(400, {"message": "tarea_id es requerido"})
        
        # Verificar que la tarea existe
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
            
            # Preparar atributos a actualizar
            update_expression = []
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            # Campos permitidos para actualizar
            allowed_fields = ['texto', 'imagenUrl']
            
            for field in allowed_fields:
                if field in body:
                    update_expression.append(f"#{field} = :{field}")
                    expression_attribute_names[f"#{field}"] = field
                    expression_attribute_values[f":{field}"] = body[field]
            
            if not update_expression:
                return _response(400, {"message": "No hay campos para actualizar"})
            
            # Actualizar en DynamoDB
            table_tareas.update_item(
                Key={
                    'usuarioId': usuario_id,
                    'id': tarea_id
                },
                UpdateExpression="SET " + ", ".join(update_expression),
                ExpressionAttributeNames=expression_attribute_names,
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
        return _response(500, {"message": str(e)})

def actualizarTarea(event, context):
    return lambda_handler(event, context)