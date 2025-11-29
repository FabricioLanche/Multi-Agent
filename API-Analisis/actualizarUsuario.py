"""
Lambda para actualizar usuario y datos relacionados
Endpoint: PUT /usuario
Actualiza Usuario + DatosAcademicos + DatosEmocionales + DatosSocioeconomicos
"""
import json
import os
import boto3
import uuid
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

# Configuración DynamoDB
dynamodb = boto3.resource('dynamodb')
table_usuarios = dynamodb.Table(os.getenv('TABLE_USUARIOS', 'Usuario'))
table_academicos = dynamodb.Table(os.getenv('TABLE_DATOS_ACADEMICOS', 'DatosAcademicos'))
table_emocionales = dynamodb.Table(os.getenv('TABLE_DATOS_EMOCIONALES', 'DatosEmocionales'))
table_socioeconomicos = dynamodb.Table(os.getenv('TABLE_DATOS_SOCIOECONOMICOS', 'DatosSocioeconomicos'))


def float_to_decimal(obj):
    """Convierte float a Decimal para DynamoDB"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    return obj


def obtener_usuario_por_correo(correo):
    """Busca usuario por correo"""
    response = table_usuarios.scan(
        FilterExpression=Attr('correo').eq(correo),
        Limit=1
    )
    items = response.get('Items', [])
    return items[0] if items else None


def obtener_o_crear_registro(table, usuario_id, datos_nuevos=None):
    """Obtiene registro existente o crea uno nuevo"""
    try:
        # Buscar registro existente
        response = table.query(
            KeyConditionExpression='usuarioId = :uid',
            ExpressionAttributeValues={':uid': usuario_id},
            Limit=1,
            ScanIndexForward=False
        )
        
        if response.get('Items'):
            # Existe, retornar el existente
            return response['Items'][0]
        else:
            # No existe, crear nuevo con datos provistos
            nuevo_registro = {
                'id': str(uuid.uuid4()),
                'usuarioId': usuario_id
            }
            if datos_nuevos:
                nuevo_registro.update(datos_nuevos)
            return nuevo_registro
    
    except Exception as e:
        print(f"⚠️ Error en obtener_o_crear_registro: {str(e)}")
        # Retornar nuevo registro por defecto
        return {'id': str(uuid.uuid4()), 'usuarioId': usuario_id}


def handler(event, context):
    """
    Actualiza usuario y opcionalmente sus datos relacionados
    
    Body JSON:
    {
        "correo": "required",
        "usuario": { campos de Usuario },
        "datos_academicos": { campos opcionales },
        "datos_emocionales": { campos opcionales },
        "datos_socioeconomicos": { campos opcionales }
    }
    """
    try:
        # Parsear body
        body = json.loads(event.get('body', '{}'))
        correo = body.get('correo')
        
        if not correo:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': True,
                    'message': 'Se requiere el campo "correo"'
                }, ensure_ascii=False)
            }
        
        # 1. Obtener usuario existente
        usuario_existente = obtener_usuario_por_correo(correo)
        
        if not usuario_existente:
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
        
        usuario_id = usuario_existente.get('id')
        actualizaciones = []
        
        # 2. Actualizar Usuario si se provee
        if 'usuario' in body and body['usuario']:
            datos_usuario = body['usuario']
            # Mantener campos clave
            datos_usuario['id'] = usuario_id
            datos_usuario['correo'] = correo
            # Preservar contraseña si no se provee
            if 'contrasena' not in datos_usuario:
                datos_usuario['contrasena'] = usuario_existente.get('contrasena')
            
            # Convertir floats a Decimal
            datos_usuario = float_to_decimal(datos_usuario)
            
            table_usuarios.put_item(Item=datos_usuario)
            actualizaciones.append('usuario')
        
        # 3. Actualizar DatosAcademicos si se provee
        if 'datos_academicos' in body and body['datos_academicos']:
            datos_acad = body['datos_academicos']
            registro_acad = obtener_o_crear_registro(table_academicos, usuario_id, datos_acad)
            
            # Mezclar datos nuevos con existentes
            registro_acad.update(datos_acad)
            registro_acad['usuarioId'] = usuario_id
            
            # Convertir floats a Decimal
            registro_acad = float_to_decimal(registro_acad)
            
            table_academicos.put_item(Item=registro_acad)
            actualizaciones.append('datos_academicos')
        
        # 4. Actualizar DatosEmocionales si se provee
        if 'datos_emocionales' in body and body['datos_emocionales']:
            datos_emo = body['datos_emocionales']
            registro_emo = obtener_o_crear_registro(table_emocionales, usuario_id, datos_emo)
            
            registro_emo.update(datos_emo)
            registro_emo['usuarioId'] = usuario_id
            
            registro_emo = float_to_decimal(registro_emo)
            
            table_emocionales.put_item(Item=registro_emo)
            actualizaciones.append('datos_emocionales')
        
        # 5. Actualizar DatosSocioeconomicos si se provee
        if 'datos_socioeconomicos' in body and body['datos_socioeconomicos']:
            datos_socio = body['datos_socioeconomicos']
            registro_socio = obtener_o_crear_registro(table_socioeconomicos, usuario_id, datos_socio)
            
            registro_socio.update(datos_socio)
            registro_socio['usuarioId'] = usuario_id
            
            registro_socio = float_to_decimal(registro_socio)
            
            table_socioeconomicos.put_item(Item=registro_socio)
            actualizaciones.append('datos_socioeconomicos')
        
        if not actualizaciones:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': True,
                    'message': 'No se proporcionaron datos para actualizar'
                }, ensure_ascii=False)
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps({
                'success': True,
                'message': 'Usuario actualizado exitosamente',
                'correo': correo,
                'usuario_id': usuario_id,
                'tablas_actualizadas': actualizaciones
            }, ensure_ascii=False)
        }
    
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': True,
                'message': 'El body debe ser JSON válido'
            }, ensure_ascii=False)
        }
    
    except Exception as e:
        print(f"❌ Error actualizando usuario: {str(e)}")
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
                'message': 'Error interno al actualizar usuario',
                'detalle': str(e)
            }, ensure_ascii=False)
        }
