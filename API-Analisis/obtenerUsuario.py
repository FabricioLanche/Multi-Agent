"""
Lambda para obtener usuario completo
Endpoint: GET /usuario?correo={email}
Retorna datos consolidados de 4 tablas
"""
import json
import os
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

# Configuración DynamoDB
dynamodb = boto3.resource('dynamodb')
table_usuarios = dynamodb.Table(os.getenv('TABLE_USUARIOS', 'Usuario'))
table_academicos = dynamodb.Table(os.getenv('TABLE_DATOS_ACADEMICOS', 'DatosAcademicos'))
table_emocionales = dynamodb.Table(os.getenv('TABLE_DATOS_EMOCIONALES', 'DatosEmocionales'))
table_socioeconomicos = dynamodb.Table(os.getenv('TABLE_DATOS_SOCIOECONOMICOS', 'DatosSocioeconomicos'))


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
    """Busca usuario por correo usando scan con paginación"""
    try:
        # Primer scan
        response = table_usuarios.scan(
            FilterExpression=Attr('correo').eq(correo)
        )
        
        # Revisar items del primer scan
        items = response.get('Items', [])
        if items:
            return items[0]
        
        # Si no se encontró, continuar con paginación
        while 'LastEvaluatedKey' in response:
            response = table_usuarios.scan(
                FilterExpression=Attr('correo').eq(correo),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items = response.get('Items', [])
            if items:
                return items[0]
        
        return None
    except Exception as e:
        print(f"❌ Error buscando usuario por correo '{correo}': {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def obtener_datos_por_usuario_id(table, usuario_id):
    """Obtiene datos de una tabla por usuarioId"""
    try:
        response = table.query(
            KeyConditionExpression='usuarioId = :uid',
            ExpressionAttributeValues={':uid': usuario_id},
            Limit=1,
            ScanIndexForward=False  # Más reciente primero
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        print(f"⚠️ Error obteniendo datos de {table.name}: {str(e)}")
        return None


def handler(event, context):
    """
    Obtiene datos completos de un usuario
    
    Query params:
        correo: Email del usuario
    
    Returns:
        Objeto con datos de Usuario + DatosAcademicos + DatosEmocionales + DatosSocioeconomicos
    """
    try:
        # Obtener correo del query string
        correo = event.get('queryStringParameters', {}).get('correo')
        
        if not correo:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': True,
                    'message': 'Se requiere el parámetro "correo" en query string'
                }, ensure_ascii=False)
            }
        
        # 1. Obtener usuario
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
        
        # 2. Obtener datos académicos
        datos_academicos = obtener_datos_por_usuario_id(table_academicos, usuario_id)
        
        # 3. Obtener datos emocionales
        datos_emocionales = obtener_datos_por_usuario_id(table_emocionales, usuario_id)
        
        # 4. Obtener datos socioeconómicos
        datos_socioeconomicos = obtener_datos_por_usuario_id(table_socioeconomicos, usuario_id)
        
        # Consolidar respuesta
        usuario_completo = {
            'usuario': usuario,
            'datos_academicos': datos_academicos,
            'datos_emocionales': datos_emocionales,
            'datos_socioeconomicos': datos_socioeconomicos
        }
        
        # Convertir Decimals a float
        usuario_completo = decimal_to_float(usuario_completo)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps(usuario_completo, ensure_ascii=False)
        }
    
    except Exception as e:
        print(f"❌ Error obteniendo usuario: {str(e)}")
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
                'message': 'Error interno al obtener usuario',
                'detalle': str(e)
            }, ensure_ascii=False)
        }
