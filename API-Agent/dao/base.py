"""
Clase base para todos los DAOs con operaciones comunes de DynamoDB
"""
import boto3
from typing import Dict, List, Optional, Any
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
import json

class BaseDAO:
    """Clase base para acceso a datos en DynamoDB"""
    
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name
    
    def get_by_key(self, partition_key: str, sort_key: Optional[str] = None) -> Optional[Dict]:
        """
        Obtiene un registro por clave primaria
        
        Args:
            partition_key: Valor de la partition key
            sort_key: Valor de la sort key (opcional)
        
        Returns:
            Diccionario con el registro o None si no existe
        """
        try:
            key = {'correo': partition_key} if 'correo' in self._get_key_schema() else {self._get_partition_key_name(): partition_key}
            
            if sort_key and self._has_sort_key():
                key[self._get_sort_key_name()] = sort_key
            
            response = self.table.get_item(Key=key)
            return self._decimal_to_float(response.get('Item'))
        except Exception as e:
            print(f"Error en get_by_key: {str(e)}")
            return None
    
    def query_by_partition(
        self, 
        partition_value: str, 
        limit: Optional[int] = None,
        sort_key_condition: Optional[Any] = None,
        scan_index_forward: bool = False
    ) -> List[Dict]:
        """
        Query por partition key con opciones adicionales
        
        Args:
            partition_value: Valor de la partition key
            limit: Límite de registros a retornar
            sort_key_condition: Condición adicional para sort key
            scan_index_forward: True para orden ascendente, False para descendente
        
        Returns:
            Lista de registros
        """
        try:
            key_name = self._get_partition_key_name()
            key_condition = Key(key_name).eq(partition_value)
            
            if sort_key_condition:
                key_condition = key_condition & sort_key_condition
            
            query_params = {
                'KeyConditionExpression': key_condition,
                'ScanIndexForward': scan_index_forward
            }
            
            if limit:
                query_params['Limit'] = limit
            
            response = self.table.query(**query_params)
            return [self._decimal_to_float(item) for item in response.get('Items', [])]
        except Exception as e:
            print(f"Error en query_by_partition: {str(e)}")
            return []
    
    def scan_all(self, limit: Optional[int] = None, filter_expression: Optional[Any] = None) -> List[Dict]:
        """
        Escanea toda la tabla (usar con cuidado)
        
        Args:
            limit: Límite de registros
            filter_expression: Expresión de filtro
        
        Returns:
            Lista de registros
        """
        try:
            scan_params = {}
            
            if limit:
                scan_params['Limit'] = limit
            
            if filter_expression:
                scan_params['FilterExpression'] = filter_expression
            
            response = self.table.scan(**scan_params)
            return [self._decimal_to_float(item) for item in response.get('Items', [])]
        except Exception as e:
            print(f"Error en scan_all: {str(e)}")
            return []
    
    def put_item(self, item: Dict) -> bool:
        """
        Inserta o actualiza un registro
        
        Args:
            item: Diccionario con el registro
        
        Returns:
            True si fue exitoso, False en caso contrario
        """
        try:
            self.table.put_item(Item=self._float_to_decimal(item))
            return True
        except Exception as e:
            print(f"Error en put_item: {str(e)}")
            return False
    
    def delete_item(self, partition_key: str, sort_key: Optional[str] = None) -> bool:
        """
        Elimina un registro
        
        Args:
            partition_key: Valor de la partition key
            sort_key: Valor de la sort key (opcional)
        
        Returns:
            True si fue exitoso, False en caso contrario
        """
        try:
            key = {self._get_partition_key_name(): partition_key}
            
            if sort_key and self._has_sort_key():
                key[self._get_sort_key_name()] = sort_key
            
            self.table.delete_item(Key=key)
            return True
        except Exception as e:
            print(f"Error en delete_item: {str(e)}")
            return False
    
    # Métodos auxiliares
    def _get_partition_key_name(self) -> str:
        """Obtiene el nombre de la partition key desde el esquema de la tabla"""
        key_schema = self.table.key_schema
        for key in key_schema:
            if key['KeyType'] == 'HASH':
                return key['AttributeName']
        return 'correo'  # Default
    
    def _get_sort_key_name(self) -> Optional[str]:
        """Obtiene el nombre de la sort key si existe"""
        key_schema = self.table.key_schema
        for key in key_schema:
            if key['KeyType'] == 'RANGE':
                return key['AttributeName']
        return None
    
    def _has_sort_key(self) -> bool:
        """Verifica si la tabla tiene sort key"""
        return self._get_sort_key_name() is not None
    
    def _get_key_schema(self) -> List[str]:
        """Retorna lista de nombres de atributos clave"""
        return [key['AttributeName'] for key in self.table.key_schema]
    
    @staticmethod
    def _decimal_to_float(obj):
        """Convierte Decimal a float para serialización JSON"""
        if isinstance(obj, list):
            return [BaseDAO._decimal_to_float(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: BaseDAO._decimal_to_float(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj
    
    @staticmethod
    def _float_to_decimal(obj):
        """Convierte float a Decimal para DynamoDB"""
        if isinstance(obj, list):
            return [BaseDAO._float_to_decimal(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: BaseDAO._float_to_decimal(value) for key, value in obj.items()}
        elif isinstance(obj, float):
            return Decimal(str(obj))
        return obj


# ===== FACTORY PARA DAOS =====
class DAOFactory:
    """Factory para crear y cachear instancias de DAOs"""
    
    _instances = {}
    
    @classmethod
    def get_dao(cls, dao_type: str):
        """
        Obtiene una instancia singleton de un DAO
        
        Args:
            dao_type: Tipo de DAO ('usuarios', 'recetas', 'servicios', 'historial', 'memoria')
        
        Returns:
            Instancia del DAO solicitado
        """
        if dao_type not in cls._instances:
            # Lazy import para evitar circular dependencies
            dao_map = cls._get_dao_map()
            
            if dao_type not in dao_map:
                raise ValueError(f"DAO tipo '{dao_type}' no existe")
            
            cls._instances[dao_type] = dao_map[dao_type]()
        
        return cls._instances[dao_type]
    
    @classmethod
    def _get_dao_map(cls):
        """
        Lazy loading de los DAOs para evitar circular imports
        """
        # Import here to avoid circular dependency
        from dao.usuarios_dao import UsuariosDAO
        from dao.recetas_dao import RecetasDAO
        from dao.servicios_dao import ServiciosDAO
        from dao.historial_dao import HistorialDAO
        from dao.memoria_dao import MemoriaDAO
        
        return {
            'usuarios': UsuariosDAO,
            'recetas': RecetasDAO,
            'servicios': ServiciosDAO,
            'historial': HistorialDAO,
            'memoria': MemoriaDAO
        }