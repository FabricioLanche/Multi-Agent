"""
Servicio de autenticación y validación de tokens
"""
import base64
import json
import os
import boto3
from typing import Optional, Dict

# Inicializar clientes
cognito = boto3.client('cognito-idp', region_name=os.getenv('AWS_REGION', 'us-east-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))

# Configuración de Cognito
USER_POOL_ID = os.getenv('USER_POOL_ID', 'us-east-1_CbDyhAcqE')
CLIENT_ID = os.getenv('CLIENT_ID', '3srpb1h5s3o6d2a5qu4bvoomq9')


class AuthService:
    """Servicio para autenticación y validación"""
    
    @staticmethod
    def get_user_from_token(event: Dict) -> Optional[Dict]:
        """
        Obtiene la información completa del usuario desde Cognito usando el token
        Similar a como lo hace API-REGISTRO/handler.py
        
        Args:
            event: Evento Lambda de API Gateway
        
        Returns:
            Diccionario con datos del usuario o None si falla
        """
        try:
            # 1. Extraer token del header
            headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
            auth_header = headers.get('authorization')
            
            if not auth_header or not auth_header.startswith("Bearer "):
                print("❌ No se encontró token de autorización")
                return None
                
            token = auth_header.split(" ")[1]
            
            # 2. Decodificar JWT para obtener email
            payload = AuthService.decode_jwt_payload(token)
            if not payload:
                print("❌ No se pudo decodificar el token")
                return None
            
            # Extraer email y limpiar espacios/caracteres extra
            email = (payload.get('email') or payload.get('cognito:username') or '').strip()
            if not email:
                print("❌ No se encontró email en el token")
                return None
            
            print(f"✅ Email extraído del token: {email}")
            
            # 3. Buscar usuario en DynamoDB (igual que API-REGISTRO)
            table_usuarios = dynamodb.Table(os.getenv('TABLE_USUARIOS', 'Usuarios'))
            
            response = table_usuarios.get_item(Key={'correo': email})
            user_data = response.get('Item')
            
            if user_data:
                print(f"✅ Usuario encontrado en DynamoDB: {email}")
                return {
                    'correo': user_data.get('correo'),
                    'nombre': user_data.get('nombre', 'Usuario'),
                    'sexo': user_data.get('sexo', ''),
                    'role': user_data.get('role', 'USER')
                }
            else:
                print(f"⚠️  Usuario no encontrado en DynamoDB, extrayendo del ID Token")
                # Si no está en DynamoDB, usar datos del token
                return {
                    'correo': email,
                    'nombre': payload.get('name', 'Usuario'),
                    'sexo': payload.get('gender', ''),
                    'role': payload.get('custom:role', 'USER')
                }
        
        except Exception as e:
            print(f"❌ Error obteniendo usuario: {str(e)}")
            return None
    
    @staticmethod
    def decode_jwt_payload(token: str) -> Optional[Dict]:
        """
        Decodifica el payload de un JWT sin verificar firma
        (Se asume que API Gateway ya validó el token)
        
        Args:
            token: Token JWT
        
        Returns:
            Diccionario con el payload o None si falla
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            payload = parts[1]
            # Ajustar padding base64
            padding = '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload + padding).decode('utf-8')
            return json.loads(decoded)
        except Exception as e:
            print(f"Error decodificando JWT: {str(e)}")
            return None
    
    @staticmethod
    def validate_email(email: str) -> bool:
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
