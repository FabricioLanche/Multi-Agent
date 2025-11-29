"""
DAO para la tabla de Usuarios
"""
from typing import Dict, Optional
from boto3.dynamodb.conditions import Attr
from .base import BaseDAO
from config import Config


class UsuariosDAO(BaseDAO):
    """DAO para la tabla de usuarios"""
    
    def __init__(self):
        super().__init__(Config.TABLE_USUARIOS)
    
    def get_usuario_por_correo(self, correo: str) -> Optional[Dict]:
        """
        Busca usuario por correo electrónico usando scan con filtro
        
        Args:
            correo: Email del usuario
        
        Returns:
            Diccionario con datos del usuario o None
        """
        try:
            response = self.scan_all(
                filter_expression=Attr('correo').eq(correo),
                limit=1
            )
            return response[0] if response else None
        except Exception as e:
            print(f"Error buscando usuario por correo: {str(e)}")
            return None
    
    def existe_usuario(self, correo: str) -> bool:
        """
        Verifica si un usuario existe por correo
        
        Args:
            correo: Email del usuario
        
        Returns:
            True si el usuario existe
        """
        return self.get_usuario_por_correo(correo) is not None
    
    def get_usuario_por_id(self, usuario_id: str, correo: str) -> Optional[Dict]:
        """
        Obtiene usuario por ID y correo (claves completas)
        
        Args:
            usuario_id: ID del usuario (partition key)
            correo: Correo del usuario (sort key)
        
        Returns:
            Diccionario con datos del usuario o None
        """
        return self.get_by_key(usuario_id, correo)
    
    def actualizar_usuario(self, usuario: Dict) -> bool:
        """
        Actualiza un usuario completo
        
        Args:
            usuario: Diccionario con todos los campos del usuario
                     Debe incluir: id, correo, contrasena, autorizacion
        
        Returns:
            True si fue exitoso
        """
        # Validar campos requeridos
        campos_requeridos = ['id', 'correo', 'contrasena', 'autorizacion']
        for campo in campos_requeridos:
            if campo not in usuario:
                print(f"Error: Campo requerido '{campo}' faltante")
                return False
        
        return self.put_item(usuario)
    
    def actualizar_autorizacion(self, correo: str, autorizacion: bool) -> bool:
        """
        Actualiza solo el campo de autorización de un usuario
        
        Args:
            correo: Email del usuario
            autorizacion: Nuevo valor de autorización
        
        Returns:
            True si fue exitoso
        """
        try:
            # Primero obtener el usuario completo
            usuario = self.get_usuario_por_correo(correo)
            
            if not usuario:
                print(f"Usuario con correo {correo} no encontrado")
                return False
            
            # Actualizar campo de autorización
            usuario['autorizacion'] = autorizacion
            
            # Guardar usuario actualizado
            return self.put_item(usuario)
        
        except Exception as e:
            print(f"Error actualizando autorización: {str(e)}")
            return False
    
    def crear_usuario(self, usuario: Dict) -> bool:
        """
        Crea un nuevo usuario
        
        Args:
            usuario: Diccionario con los datos del usuario
                     Debe incluir: id, correo, contrasena, autorizacion
        
        Returns:
            True si fue exitoso
        """
        # Validar campos requeridos
        campos_requeridos = ['id', 'correo', 'contrasena', 'autorizacion']
        for campo in campos_requeridos:
            if campo not in usuario:
                print(f"Error: Campo requerido '{campo}' faltante")
                return False
        
        # Verificar que no exista ya
        if self.existe_usuario(usuario['correo']):
            print(f"Usuario con correo {usuario['correo']} ya existe")
            return False
        
        return self.put_item(usuario)