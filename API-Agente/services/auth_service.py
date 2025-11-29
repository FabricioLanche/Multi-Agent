"""
Servicios principales del sistema de agentes académicos
"""
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from dao.base import DAOFactory
from contextos.base_contexto import ContextoFactory
from services.gemini_service import GeminiService
from config import Config


# ===== EXCEPCIONES PERSONALIZADAS =====
class UsuarioNoEncontradoError(Exception):
    """Usuario no existe en la base de datos"""
    pass


class ContextoInvalidoError(Exception):
    """Contexto solicitado no es válido"""
    pass

# ===== SERVICIO DE AUTENTICACIÓN (SIMPLIFICADO) =====
class AuthService:
    """Servicio simplificado de autenticación (sin tokens)"""
    
    @staticmethod
    def validar_usuario_existe(correo: str) -> bool:
        """
        Valida que un usuario exista en la base de datos
        
        Args:
            correo: Email del usuario
        
        Returns:
            True si el usuario existe
        """
        try:
            usuarios_dao = DAOFactory.get_dao('usuarios')
            return usuarios_dao.existe_usuario(correo)
        except Exception as e:
            print(f"Error validando usuario: {str(e)}")
            return False
    
    @staticmethod
    def validar_email(email: str) -> bool:
        """
        Valida formato básico de email
        
        Args:
            email: String con el email
        
        Returns:
            True si es válido
        """
        import re
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))