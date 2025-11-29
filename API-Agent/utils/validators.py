"""
=== utils/validators.py ===
Validadores de datos
"""
from typing import Dict, List, Optional
from config import Config

def validar_request_agente(body: Dict) -> Optional[List[str]]:
    """
    Valida el body de la request para el agente
    
    Args:
        body: Diccionario con los datos de la request
    
    Returns:
        Lista de errores o None si es válido
    """
    errores = []
    
    # Validar campos requeridos
    if not body.get('correo'):
        errores.append("El campo 'correo' es requerido")
    elif not validar_email(body['correo']):
        errores.append("El formato del correo es inválido")
    
    if not body.get('contexto'):
        errores.append("El campo 'contexto' es requerido")
    elif body['contexto'] not in Config.CONTEXTOS_DISPONIBLES:
        errores.append(
            f"Contexto inválido. Debe ser uno de: {Config.CONTEXTOS_DISPONIBLES}"
        )
    
    if not body.get('mensaje'):
        errores.append("El campo 'mensaje' es requerido")
    elif len(body['mensaje']) > 2000:
        errores.append("El mensaje no puede exceder 2000 caracteres")
    
    # Validar historial si existe
    if 'historial' in body:
        if not isinstance(body['historial'], list):
            errores.append("El campo 'historial' debe ser una lista")
        else:
            for idx, msg in enumerate(body['historial']):
                if not isinstance(msg, dict):
                    errores.append(f"Mensaje {idx} del historial debe ser un objeto")
                elif 'role' not in msg or 'content' not in msg:
                    errores.append(f"Mensaje {idx} debe tener 'role' y 'content'")
    
    return errores if errores else None


def validar_email(email: str) -> bool:
    """
    Valida formato básico de email
    
    Args:
        email: String con el email
    
    Returns:
        True si es válido
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validar_fecha_iso(fecha: str) -> bool:
    """
    Valida que una fecha esté en formato ISO 8601
    
    Args:
        fecha: String con la fecha
    
    Returns:
        True si es válido
    """
    from datetime import datetime
    try:
        datetime.fromisoformat(fecha.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False
