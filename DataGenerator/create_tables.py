import json
import os
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Cargar variables de entorno
load_dotenv()

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)

# Mapeo de archivos de esquema a variables de entorno de nombres de tabla
SCHEMA_MAPPING = {
    "recetas.json": os.getenv('TABLE_RECETAS', 'Recetas'),
    "servicios.json": os.getenv('TABLE_SERVICIOS', 'Servicios'),
    "usuarios.json": os.getenv('TABLE_USUARIOS', 'Usuarios'),
    "memoria_contextual.json": os.getenv('TABLE_MEMORIA_CONTEXTUAL', 'MemoriaContextual'),
    "historial_medico.json": os.getenv('TABLE_HISTORIAL_MEDICO', 'HistorialMedico'),
    "usuarios_dependientes.json": os.getenv('TABLE_USUARIOS_DEPENDIENTES', 'UsuariosDependientes'),
    "reglas.json": os.getenv('TABLE_REGLAS', 'TablaReglas')
}

# Definición de tablas sin esquema (creación directa)
TABLES_WITHOUT_SCHEMA = {
    'MemoriaContextual': {
        'partition_key': {'name': 'correo', 'type': 'S'},
        'sort_key': {'name': 'context_id', 'type': 'S'}
    },
    'HistorialMedico': {
        'partition_key': {'name': 'correo', 'type': 'S'},
        'sort_key': {'name': 'fecha', 'type': 'S'}
    }
}

SCHEMAS_DIR = "schemas-validation"

def get_dynamodb_type(json_type):
    if json_type == "string":
        return "S"
    elif json_type == "integer" or json_type == "number":
        return "N"
    elif json_type == "boolean":
        return "BOOL"
    return "S"

def create_table_from_definition(table_name, definition):
    """Crear tabla desde definición directa (sin esquema JSON)"""
    pk = definition['partition_key']
    key_schema = [
        {'AttributeName': pk['name'], 'KeyType': 'HASH'}
    ]
    attribute_definitions = [
        {'AttributeName': pk['name'], 'AttributeType': pk['type']}
    ]

    # Agregar sort key si existe
    if 'sort_key' in definition:
        sk = definition['sort_key']
        key_schema.append({'AttributeName': sk['name'], 'KeyType': 'RANGE'})
        attribute_definitions.append({'AttributeName': sk['name'], 'AttributeType': sk['type']})

    try:
        print(f"📊 Verificando tabla: {table_name}")
        dynamodb.describe_table(TableName=table_name)
        print(f"   ✅ La tabla '{table_name}' ya existe")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"   🔨 Creando tabla '{table_name}'...")
            try:
                dynamodb.create_table(
                    TableName=table_name,
                    KeySchema=key_schema,
                    AttributeDefinitions=attribute_definitions,
                    BillingMode='PAY_PER_REQUEST'
                )
                waiter = dynamodb.get_waiter('table_exists')
                waiter.wait(TableName=table_name)
                print(f"   ✅ Tabla '{table_name}' creada exitosamente")
                return True
            except Exception as create_error:
                print(f"   ❌ Error al crear tabla: {str(create_error)}")
                return False
        else:
            print(f"   ❌ Error al verificar tabla: {str(e)}")
            return False

def verify_table_structure(table_name, expected_key_schema):
    """Verifica si la estructura de la tabla coincide con la esperada"""
    try:
        response = dynamodb.describe_table(TableName=table_name)
        current_key_schema = response['Table']['KeySchema']
        
        # Comparar esquemas de claves
        if len(current_key_schema) != len(expected_key_schema):
            return False
        
        for expected_key in expected_key_schema:
            if expected_key not in current_key_schema:
                return False
        
        return True
    except ClientError:
        return False

def recreate_table(table_name, key_schema, attribute_definitions):
    """Elimina y recrea una tabla con la nueva estructura"""
    try:
        print(f"   🗑️  Eliminando tabla existente con estructura incorrecta...")
        dynamodb.delete_table(TableName=table_name)
        waiter = dynamodb.get_waiter('table_not_exists')
        waiter.wait(TableName=table_name)
        print(f"   ✅ Tabla eliminada")
    except Exception as e:
        print(f"   ❌ Error al eliminar tabla: {str(e)}")
        return False
    
    try:
        print(f"   🔨 Recreando tabla con estructura correcta...")
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode='PAY_PER_REQUEST'
        )
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print(f"   ✅ Tabla recreada exitosamente")
        return True
    except Exception as e:
        print(f"   ❌ Error al recrear tabla: {str(e)}")
        return False

def create_table_from_schema(filename, table_name):
    """Crear tabla desde archivo de esquema JSON"""
    filepath = os.path.join(SCHEMAS_DIR, filename)
    if not os.path.exists(filepath):
        print(f"⚠️  Esquema no encontrado: {filepath}, intentando creación directa...")
        # Si no existe el esquema, intentar con definición directa
        if table_name in TABLES_WITHOUT_SCHEMA:
            return create_table_from_definition(table_name, TABLES_WITHOUT_SCHEMA[table_name])
        else:
            print(f"❌ No hay definición alternativa para {table_name}")
            return False

    with open(filepath, 'r') as f:
        schema = json.load(f)

    if "x-dynamodb" not in schema or "partition_key" not in schema["x-dynamodb"]:
        print(f"❌ Definición x-dynamodb faltante en {filename}")
        return False

    x_dynamodb = schema["x-dynamodb"]
    pk_name = x_dynamodb["partition_key"]
    pk_type = "S"
    if "properties" in schema and pk_name in schema["properties"]:
        prop_type = schema["properties"][pk_name].get("type", "string")
        # Manejar tipos que pueden ser arrays (ej: ["string", "null"])
        if isinstance(prop_type, list):
            prop_type = next((t for t in prop_type if t != "null"), "string")
        pk_type = get_dynamodb_type(prop_type)

    key_schema = [
        {'AttributeName': pk_name, 'KeyType': 'HASH'}
    ]
    attribute_definitions = [
        {'AttributeName': pk_name, 'AttributeType': pk_type}
    ]

    # Verificar si existe sort key
    if "sort_key" in x_dynamodb:
        sk_name = x_dynamodb["sort_key"]
        sk_type = "S"
        if "properties" in schema and sk_name in schema["properties"]:
            prop_type = schema["properties"][sk_name].get("type", "string")
            # Manejar tipos que pueden ser arrays (ej: ["string", "null"])
            if isinstance(prop_type, list):
                prop_type = next((t for t in prop_type if t != "null"), "string")
            sk_type = get_dynamodb_type(prop_type)
        
        key_schema.append({'AttributeName': sk_name, 'KeyType': 'RANGE'})
        attribute_definitions.append({'AttributeName': sk_name, 'AttributeType': sk_type})

    try:
        print(f"📊 Verificando tabla: {table_name}")
        table_exists = True
        try:
            dynamodb.describe_table(TableName=table_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                table_exists = False
            else:
                raise
        
        if table_exists:
            # Verificar si la estructura es correcta
            if verify_table_structure(table_name, key_schema):
                print(f"   ✅ La tabla '{table_name}' ya existe con la estructura correcta")
                return True
            else:
                print(f"   ⚠️  La tabla '{table_name}' existe pero con estructura incorrecta")
                return recreate_table(table_name, key_schema, attribute_definitions)
        else:
            print(f"   🔨 Creando tabla '{table_name}'...")
            dynamodb.create_table(
                TableName=table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attribute_definitions,
                BillingMode='PAY_PER_REQUEST'
            )
            waiter = dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=table_name)
            print(f"   ✅ Tabla '{table_name}' creada exitosamente")
            return True
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def main():
    print("🏗️  Creando tablas base desde esquemas...")
    print()
    success = True
    
    for schema_file, table_name in SCHEMA_MAPPING.items():
        if not create_table_from_schema(schema_file, table_name):
            success = False
        print()
    
    if success:
        print("✅ Todas las tablas verificadas/creadas correctamente")
        exit(0)
    else:
        print("⚠️  Algunas tablas no pudieron ser creadas")
        exit(1)

if __name__ == "__main__":
    main()