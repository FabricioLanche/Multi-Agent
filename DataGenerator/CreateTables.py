#!/usr/bin/env python3
"""
Crear/verificar tablas DynamoDB a partir de esquemas JSON (x-dynamodb).
- Lee archivos JSON en ./schemas-validation
- Utiliza x-dynamodb.partition_key y opcional x-dynamodb.sort_key
- Crea o recrea tablas según sea necesario
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
dynamodb = boto3.client("dynamodb", region_name=AWS_REGION)

SCHEMAS_DIR = Path(__file__).parent / "schemas-validation"

# Mapeo esquema -> nombre de tabla (se pueden sobreescribir con variables de entorno)
SCHEMA_MAPPING = {
    "Usuario.json": os.getenv("TABLE_USUARIOS", "Usuarios"),
    "Tarea.json": os.getenv("TABLE_TAREAS", "Tareas"),
    "Historial.json": os.getenv("TABLE_HISTORIAL", "Historial"),
    "DatosSocioeconomicos.json": os.getenv("TABLE_DATOS_SOCIOECONOMICOS", "DatosSocioeconomicos"),
    "DatosEmocionales.json": os.getenv("TABLE_DATOS_EMOCIONALES", "DatosEmocionales"),
    "DatosAcademicos.json": os.getenv("TABLE_DATOS_ACADEMICOS", "DatosAcademicos")
}

# Tablas definidas manualmente si no hay esquema (opcional)
TABLES_WITHOUT_SCHEMA = {
    # ejemplo de cómo añadir definiciones directas si hiciera falta
    # "SomeTable": {"partition_key": {"name": "pk", "type": "S"}, "sort_key": {"name": "sk", "type": "S"}}
}


def json_type_to_dynamodb_attr_type(json_type: str) -> str:
    """
    Mapea tipos JSON Schema a AttributeType válidos para AttributeDefinitions
    (S, N, B). Si se recibe boolean u otro, se mapea a S (y se advierte).
    """
    t = (json_type or "").lower()
    if t in ("string", "str"):
        return "S"
    if t in ("integer", "int", "number", "float", "double"):
        return "N"
    if t in ("binary", "bytes"):
        return "B"
    if t == "boolean":
        # DynamoDB no permite BOOL como AttributeDefinition para keys, mapear a S
        print("⚠️  'boolean' como tipo de clave no es soportado por AttributeDefinitions; usando 'S' (string).")
        return "S"
    # fallback
    return "S"


def find_schema_file(filename: str) -> Path:
    """
    Buscar archivo de esquema en SCHEMAS_DIR. Devuelve Path o lanza FileNotFoundError.
    """
    p = SCHEMAS_DIR / filename
    if p.exists():
        return p
    # Probar versiones en minúsculas / capitalizadas
    alternatives = [
        filename,
        filename.capitalize(),
        filename.lower(),
        filename.title()
    ]
    for alt in alternatives:
        p2 = SCHEMAS_DIR / alt
        if p2.exists():
            return p2
    raise FileNotFoundError(f"Esquema no encontrado: {filename} en {SCHEMAS_DIR}")


def verify_table_structure(table_name: str, expected_key_schema: list) -> bool:
    """
    Compara la KeySchema actual de una tabla con la esperada.
    expected_key_schema: [{'AttributeName': 'id','KeyType':'HASH'}, ...]
    """
    try:
        resp = dynamodb.describe_table(TableName=table_name)
        current = resp["Table"]["KeySchema"]
        # Convertir a set de tuplas (AttributeName, KeyType) para comparar
        curr_set = {(k["AttributeName"], k["KeyType"]) for k in current}
        expected_set = {(k["AttributeName"], k["KeyType"]) for k in expected_key_schema}
        return curr_set == expected_set
    except ClientError as e:
        # Si no existe o error: devolver False
        return False


def recreate_table(table_name: str, key_schema: list, attribute_definitions: list) -> bool:
    """
    Elimina (si existe) y crea la tabla con la definición dada.
    """
    try:
        print(f"   🗑️  Eliminando tabla (si existe) {table_name}...")
        try:
            dynamodb.delete_table(TableName=table_name)
            waiter = dynamodb.get_waiter("table_not_exists")
            waiter.wait(TableName=table_name)
            print("   ✅ Eliminada")
        except ClientError as e:
            # Si no existe, seguir adelante
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                print(f"   ⚠️  Error al eliminar (continuando): {e}")
        # Crear
        print(f"   🔨 Creando tabla {table_name}...")
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode="PAY_PER_REQUEST"
        )
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
        print(f"   ✅ Tabla '{table_name}' recreada correctamente")
        return True
    except Exception as e:
        print(f"   ❌ Error al recrear tabla {table_name}: {e}")
        return False


def create_table_from_schema(schema_filename: str, table_name: str) -> bool:
    """
    Lee el esquema JSON y crea/verifica la tabla DynamoDB basada en x-dynamodb.
    """
    try:
        schema_path = find_schema_file(schema_filename)
    except FileNotFoundError:
        print(f"⚠️  Esquema {schema_filename} no encontrado en {SCHEMAS_DIR}.")
        # Intentar definición alternativa
        if table_name in TABLES_WITHOUT_SCHEMA:
            print(f"   🔨 Intentando crear tabla con definición manual para {table_name}")
            return create_table_from_definition(table_name, TABLES_WITHOUT_SCHEMA[table_name])
        else:
            print(f"   ❌ No hay definición alternativa para {table_name}. Saltando.")
            return False

    # Cargar esquema
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except Exception as e:
        print(f"   ❌ Error al leer esquema {schema_path}: {e}")
        return False

    if "x-dynamodb" not in schema or "partition_key" not in schema["x-dynamodb"]:
        print(f"   ❌ El esquema {schema_path.name} no contiene 'x-dynamodb.partition_key'")
        return False

    xdyn = schema["x-dynamodb"]
    pk_name = xdyn["partition_key"]
    pk_type = "S"
    # Determinar tipo desde propiedades si es posible
    if "properties" in schema and pk_name in schema["properties"]:
        prop = schema["properties"][pk_name].get("type", "string")
        if isinstance(prop, list):
            # eliminar "null" si aparece
            prop = next((p for p in prop if p != "null"), prop[0])
        pk_type = json_type_to_dynamodb_attr_type(prop)

    key_schema = [{"AttributeName": pk_name, "KeyType": "HASH"}]
    attribute_definitions = [{"AttributeName": pk_name, "AttributeType": pk_type}]

    # sort_key opcional
    if "sort_key" in xdyn:
        sk_name = xdyn["sort_key"]
        sk_type = "S"
        if "properties" in schema and sk_name in schema["properties"]:
            prop = schema["properties"][sk_name].get("type", "string")
            if isinstance(prop, list):
                prop = next((p for p in prop if p != "null"), prop[0])
            sk_type = json_type_to_dynamodb_attr_type(prop)
        key_schema.append({"AttributeName": sk_name, "KeyType": "RANGE"})
        attribute_definitions.append({"AttributeName": sk_name, "AttributeType": sk_type})

    # Verificar existencia y estructura
    try:
        print(f"📊 Verificando tabla: {table_name} (esquema: {schema_path.name})")
        try:
            dynamodb.describe_table(TableName=table_name)
            exists = True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                exists = False
            else:
                raise

        if exists:
            if verify_table_structure(table_name, key_schema):
                print(f"   ✅ La tabla '{table_name}' ya existe con la estructura esperada.")
                return True
            else:
                print(f"   ⚠️  La tabla '{table_name}' existe pero su estructura difiere. Se recreará.")
                return recreate_table(table_name, key_schema, attribute_definitions)
        else:
            print(f"   🔨 Creando tabla '{table_name}'...")
            dynamodb.create_table(
                TableName=table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attribute_definitions,
                BillingMode="PAY_PER_REQUEST"
            )
            waiter = dynamodb.get_waiter("table_exists")
            waiter.wait(TableName=table_name)
            print(f"   ✅ Tabla '{table_name}' creada exitosamente")
            return True
    except Exception as e:
        print(f"   ❌ Error al procesar tabla '{table_name}': {e}")
        return False


def create_table_from_definition(table_name: str, definition: dict) -> bool:
    """
    Crear tabla a partir de una definición manual (TABLES_WITHOUT_SCHEMA).
    definition = { 'partition_key': {'name':'correo','type':'S'}, 'sort_key': {...} }
    """
    pk = definition["partition_key"]
    key_schema = [{"AttributeName": pk["name"], "KeyType": "HASH"}]
    attr_defs = [{"AttributeName": pk["name"], "AttributeType": pk["type"]}]
    if "sort_key" in definition:
        sk = definition["sort_key"]
        key_schema.append({"AttributeName": sk["name"], "KeyType": "RANGE"})
        attr_defs.append({"AttributeName": sk["name"], "AttributeType": sk["type"]})

    try:
        print(f"📊 Verificando tabla manual: {table_name}")
        try:
            dynamodb.describe_table(TableName=table_name)
            exists = True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                exists = False
            else:
                raise

        if exists:
            if verify_table_structure(table_name, key_schema):
                print(f"   ✅ La tabla '{table_name}' ya existe con la estructura esperada.")
                return True
            else:
                print(f"   ⚠️  La tabla '{table_name}' existe pero su estructura difiere. Se recreará.")
                return recreate_table(table_name, key_schema, attr_defs)
        else:
            print(f"   🔨 Creando tabla '{table_name}' (definición manual)...")
            dynamodb.create_table(
                TableName=table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attr_defs,
                BillingMode="PAY_PER_REQUEST"
            )
            waiter = dynamodb.get_waiter("table_exists")
            waiter.wait(TableName=table_name)
            print(f"   ✅ Tabla '{table_name}' creada exitosamente")
            return True
    except Exception as e:
        print(f"   ❌ Error creando tabla manual {table_name}: {e}")
        return False


def main():
    print("🏗️  Creando/verificando tablas desde esquemas (x-dynamodb)...")
    print(f"🔎 Buscando esquemas en: {SCHEMAS_DIR}")
    success = True
    for schema_file, table_name in SCHEMA_MAPPING.items():
        ok = create_table_from_schema(schema_file, table_name)
        if not ok:
            success = False
        print()
    if success:
        print("✅ Todas las tablas verificadas/creadas correctamente")
        exit(0)
    else:
        print("⚠️  Hubo errores creando/verificando algunas tablas")
        exit(1)


if __name__ == "__main__":
    main()