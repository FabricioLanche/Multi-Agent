"""
Lambda para listar usuarios
Endpoint: GET /usuarios
Retorna lista básica de usuarios
"""
import json
import os
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

# Configuración DynamoDB
dynamodb = boto3.resource('dynamodb')
table_usuarios = dynamodb.Table(os.getenv('TABLE_USUARIOS', 'Usuario'))


def decimal_to_float(obj):
    """Convierte Decimal a float para JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


def handler(event, context):
    """
    Lista todos los usuarios con información básica
    
    Returns:
        Lista de usuarios con id, correo, autorizacion
    """
    try:
        # Escanear tabla de usuarios
        response = table_usuarios.scan(
            ProjectionExpression='id, correo, autorizacion'
        )
        
        usuarios = response.get('Items', [])
        
        # Manejar paginación si hay muchos resultados
        while 'LastEvaluatedKey' in response:
            response = table_usuarios.scan(
                ProjectionExpression='id, correo, autorizacion',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            usuarios.extend(response.get('Items', []))
        
        # Convertir Decimals a float
        usuarios = decimal_to_float(usuarios)
        
        # Ordenar por correo para consistencia
        usuarios.sort(key=lambda x: x.get('correo', ''))
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps({
                'usuarios': usuarios,
                'total': len(usuarios)
            }, ensure_ascii=False)
        }
    
    except Exception as e:
        print(f"❌ Error listando usuarios: {str(e)}")
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
                'message': 'Error interno al listar usuarios',
                'detalle': str(e)
            }, ensure_ascii=False)
        }
