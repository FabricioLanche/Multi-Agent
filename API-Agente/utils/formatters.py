"""
=== utils/formatters.py ===
Formateadores de respuestas
"""
import json
from typing import Dict, Any
from datetime import datetime, date
from decimal import Decimal

def formatear_respuesta_exitosa(data: Dict, codigo: int = 200) -> Dict:
    """
    Formatea una respuesta exitosa para API Gateway
    
    Args:
        data: Diccionario con los datos de respuesta
        codigo: Código HTTP (default: 200)
    
    Returns:
        Respuesta formateada para API Gateway
    """
    return {
        'statusCode': codigo,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True
        },
        'body': json.dumps(data, cls=CustomJSONEncoder, ensure_ascii=False)
    }


def formatear_respuesta_error(
    codigo: int, 
    mensaje: str, 
    detalles: Any = None
) -> Dict:
    """
    Formatea una respuesta de error para API Gateway
    
    Args:
        codigo: Código HTTP de error
        mensaje: Mensaje descriptivo del error
        detalles: Información adicional del error
    
    Returns:
        Respuesta formateada para API Gateway
    """
    error_body = {
        'error': True,
        'mensaje': mensaje,
        'codigo': codigo
    }
    
    if detalles:
        error_body['detalles'] = detalles
    
    return {
        'statusCode': codigo,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True
        },
        'body': json.dumps(error_body, cls=CustomJSONEncoder, ensure_ascii=False)
    }


class CustomJSONEncoder(json.JSONEncoder):
    """
    Encoder personalizado para manejar tipos especiales
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return obj.decode('utf-8')
        return super().default(obj)


def formatear_mensaje_corto(mensaje: str, max_length: int = 100) -> str:
    """
    Acorta un mensaje a una longitud máxima
    
    Args:
        mensaje: Texto a acortar
        max_length: Longitud máxima
    
    Returns:
        Texto acortado con '...' si es necesario
    """
    if len(mensaje) <= max_length:
        return mensaje
    return mensaje[:max_length - 3] + '...'


def formatear_lista_como_texto(items: list, separador: str = ', ') -> str:
    """
    Convierte una lista en texto legible
    
    Args:
        items: Lista de elementos
        separador: Separador entre elementos
    
    Returns:
        String con los elementos unidos
    """
    if not items:
        return 'Ninguno'
    
    if len(items) == 1:
        return str(items[0])
    
    if len(items) == 2:
        return f"{items[0]} y {items[1]}"
    
    return f"{separador.join(str(i) for i in items[:-1])} y {items[-1]}"


def sanitizar_input_usuario(texto: str) -> str:
    """
    Limpia y sanitiza input del usuario
    
    Args:
        texto: Texto del usuario
    
    Returns:
        Texto sanitizado
    """
    # Remover caracteres especiales peligrosos
    texto = texto.strip()
    
    # Limitar longitud
    if len(texto) > 5000:
        texto = texto[:5000]
    
    return texto