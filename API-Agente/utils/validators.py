"""
Validadores de datos para el sistema de agentes académicos
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
    
    # Validar campo correo
    if not body.get('correo'):
        errores.append("El campo 'correo' es requerido")
    elif not validar_email(body['correo']):
        errores.append("El formato del correo es inválido")
    
    # Validar campo contexto
    if not body.get('contexto'):
        errores.append("El campo 'contexto' es requerido")
    elif body['contexto'] not in Config.CONTEXTOS_DISPONIBLES:
        errores.append(
            f"Contexto inválido. Debe ser uno de: {', '.join(Config.CONTEXTOS_DISPONIBLES)}"
        )
    
    # Validar campo mensaje
    if not body.get('mensaje'):
        errores.append("El campo 'mensaje' es requerido")
    elif not isinstance(body['mensaje'], str):
        errores.append("El campo 'mensaje' debe ser un string")
    elif len(body['mensaje']) < 1:
        errores.append("El mensaje no puede estar vacío")
    elif len(body['mensaje']) > 5000:
        errores.append("El mensaje no puede exceder 5000 caracteres")
    
    # Validar historial si existe
    if 'historial' in body:
        if not isinstance(body['historial'], list):
            errores.append("El campo 'historial' debe ser una lista")
        else:
            for idx, msg in enumerate(body['historial']):
                if not isinstance(msg, dict):
                    errores.append(
                        f"El mensaje {idx} del historial debe ser un objeto"
                    )
                elif 'role' not in msg or 'content' not in msg:
                    errores.append(
                        f"El mensaje {idx} debe tener 'role' y 'content'"
                    )
                elif msg['role'] not in ['user', 'assistant', 'system']:
                    errores.append(
                        f"El mensaje {idx} tiene un 'role' inválido. "
                        f"Debe ser 'user', 'assistant' o 'system'"
                    )
    
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
    if not email or not isinstance(email, str):
        return False
    
    # Patrón básico de validación de email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validar_uuid(uuid_string: str) -> bool:
    """
    Valida que un string sea un UUID válido
    
    Args:
        uuid_string: String a validar
    
    Returns:
        True si es un UUID válido
    """
    import re
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    # Patrón UUID v4
    pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'
    return bool(re.match(pattern, uuid_string))


def validar_contexto(contexto: str) -> bool:
    """
    Valida que un contexto sea válido
    
    Args:
        contexto: Nombre del contexto
    
    Returns:
        True si es válido
    """
    return contexto in Config.CONTEXTOS_DISPONIBLES


def validar_longitud_texto(texto: str, min_length: int = 1, max_length: int = 5000) -> bool:
    """
    Valida que un texto esté dentro de un rango de longitud
    
    Args:
        texto: Texto a validar
        min_length: Longitud mínima
        max_length: Longitud máxima
    
    Returns:
        True si está dentro del rango
    """
    if not isinstance(texto, str):
        return False
    
    return min_length <= len(texto) <= max_length


def sanitizar_texto(texto: str, max_length: int = 5000) -> str:
    """
    Limpia y sanitiza texto de entrada
    
    Args:
        texto: Texto a sanitizar
        max_length: Longitud máxima permitida
    
    Returns:
        Texto sanitizado
    """
    if not isinstance(texto, str):
        return ""
    
    # Remover espacios en blanco excesivos
    texto = texto.strip()
    
    # Limitar longitud
    if len(texto) > max_length:
        texto = texto[:max_length]
    
    return texto


def validar_datos_academicos(datos: Dict) -> Optional[List[str]]:
    """
    Valida la estructura de datos académicos
    
    Args:
        datos: Diccionario con datos académicos
    
    Returns:
        Lista de errores o None si es válido
    """
    errores = []
    
    campos_requeridos = ['id', 'usuarioId', 'carrera', 'ciclo_actual']
    for campo in campos_requeridos:
        if campo not in datos:
            errores.append(f"Campo requerido faltante: {campo}")
    
    # Validar tipos específicos
    if 'ciclo_actual' in datos:
        if not isinstance(datos['ciclo_actual'], int) or datos['ciclo_actual'] < 1:
            errores.append("ciclo_actual debe ser un entero positivo")
    
    if 'promedio_ponderado' in datos:
        if not isinstance(datos['promedio_ponderado'], (int, float)):
            errores.append("promedio_ponderado debe ser un número")
        elif not 0 <= datos['promedio_ponderado'] <= 20:
            errores.append("promedio_ponderado debe estar entre 0 y 20")
    
    if 'avance_malla' in datos:
        if not isinstance(datos['avance_malla'], (int, float)):
            errores.append("avance_malla debe ser un número")
        elif not 0 <= datos['avance_malla'] <= 100:
            errores.append("avance_malla debe estar entre 0 y 100")
    
    return errores if errores else None


def validar_tarea(tarea: Dict) -> Optional[List[str]]:
    """
    Valida la estructura de una tarea
    
    Args:
        tarea: Diccionario con datos de la tarea
    
    Returns:
        Lista de errores o None si es válido
    """
    errores = []
    
    campos_requeridos = ['id', 'usuarioId', 'texto']
    for campo in campos_requeridos:
        if campo not in tarea:
            errores.append(f"Campo requerido faltante: {campo}")
    
    # Validar UUIDs
    if 'id' in tarea and not validar_uuid(tarea['id']):
        errores.append("id debe ser un UUID válido")
    
    if 'usuarioId' in tarea and not validar_uuid(tarea['usuarioId']):
        errores.append("usuarioId debe ser un UUID válido")
    
    # Validar texto
    if 'texto' in tarea and not validar_longitud_texto(tarea['texto'], min_length=1):
        errores.append("texto no puede estar vacío")
    
    return errores if errores else None