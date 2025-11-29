"""
=== utils/exceptions.py ===
Excepciones personalizadas
"""
class AgenteBaseError(Exception):
    """Excepción base para errores del agente"""
    pass

class UsuarioNoEncontradoError(AgenteBaseError):
    """Usuario no existe en la base de datos"""
    pass

class ContextoInvalidoError(AgenteBaseError):
    """Contexto solicitado no es válido"""
    pass

class DatosFaltantesError(AgenteBaseError):
    """Faltan datos requeridos en la solicitud"""
    pass

class ConfiguracionInvalidaError(AgenteBaseError):
    """Error en la configuración del servicio"""
    pass
