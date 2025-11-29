#!/usr/bin/env python3
"""
DataPoblator.py

Puebla las tablas DynamoDB usando los archivos JSON generados en ./dynamodb-data.
Adaptado a los esquemas definitivos:

- Usuario.json:     partition_key = id, sort_key = correo           -> usuarios.json
- Tarea.json:       partition_key = usuarioId, sort_key = id      -> tareas.json
- Historial.json:   partition_key = usuarioId, sort_key = id      -> historial.json
- DatosSocioeconomicos.json: partition_key = usuarioId, sort_key = id -> datos_socioeconomicos.json
- DatosEmocionales.json:     partition_key = usuarioId, sort_key = id -> datos_emocionales.json
- DatosAcademicos.json:      partition_key = usuarioId, sort_key = id -> datos_academicos.json

Requisitos:
- AWS credentials configuradas (env o perfil)
- python-dotenv (para cargar .env)
- Boto3 instalado

Uso:
  python DataPoblator.py
"""
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import random as random_module

load_dotenv()

# Configuración AWS
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
dynamodb_client = boto3.client("dynamodb", region_name=AWS_REGION)

# Nombres de tablas (pueden venir desde .env)
TABLE_USUARIOS = os.getenv("TABLE_USUARIOS", "Usuarios")
TABLE_TAREAS = os.getenv("TABLE_TAREAS", "Tareas")
TABLE_HISTORIAL = os.getenv("TABLE_HISTORIAL", "Historial")
TABLE_DATOS_SOCIOECONOMICOS = os.getenv("TABLE_DATOS_SOCIOECONOMICOS", "DatosSocioeconomicos")
TABLE_DATOS_EMOCIONALES = os.getenv("TABLE_DATOS_EMOCIONALES", "DatosEmocionales")
TABLE_DATOS_ACADEMICOS = os.getenv("TABLE_DATOS_ACADEMICOS", "DatosAcademicos")

# Carpeta con los datos JSON generados por generate_data.py
DATA_DIR = Path(__file__).parent / "dynamodb-data"

# Mapeo archivos -> tabla y claves (según esquemas definitivos)
TABLE_MAPPING = {
    "usuarios.json": {
        "table_name": TABLE_USUARIOS,
        "pk": "id",
        "sk": "correo"
    },
    "tareas.json": {
        "table_name": TABLE_TAREAS,
        "pk": "usuarioId",
        "sk": "id"
    },
    "historial.json": {
        "table_name": TABLE_HISTORIAL,
        "pk": "usuarioId",
        "sk": "id"
    },
    "datos_socioeconomicos.json": {
        "table_name": TABLE_DATOS_SOCIOECONOMICOS,
        "pk": "usuarioId",
        "sk": "id"
    },
    "datos_emocionales.json": {
        "table_name": TABLE_DATOS_EMOCIONALES,
        "pk": "usuarioId",
        "sk": "id"
    },
    "datos_academicos.json": {
        "table_name": TABLE_DATOS_ACADEMICOS,
        "pk": "usuarioId",
        "sk": "id"
    }
}

COUNT_LOCK = Lock()


def convert_float_to_decimal(obj: Any) -> Any:
    """Convierte floats a Decimal recursivamente (para DynamoDB)."""
    if isinstance(obj, list):
        return [convert_float_to_decimal(x) for x in obj]
    if isinstance(obj, dict):
        return {k: convert_float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, float):
        return Decimal(str(obj))
    return obj


def table_exists(table_name: str) -> bool:
    """Verifica si la tabla existe en DynamoDB."""
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def load_json_file(filename: str) -> Optional[List[Dict[str, Any]]]:
    """Carga un archivo JSON desde DATA_DIR y convierte floats a Decimal."""
    path = DATA_DIR / filename
    if not path.exists():
        print(f"   ⚠️  Archivo no encontrado: {path}")
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        data = convert_float_to_decimal(data)
        # Normalizar a lista
        if isinstance(data, list):
            return data
        return [data]
    except json.JSONDecodeError as e:
        print(f"   ⚠️  Error decodificando JSON {path}: {e}")
        return None


def delete_all_items_from_table(table_name: str, pk_name: str, sk_name: Optional[str] = None) -> bool:
    """
    Elimina todos los items de una tabla leyendo con scan y borrándolos en batch.
    Nota: costoso en tablas grandes.
    """
    try:
        table = dynamodb.Table(table_name)
        print(f"   🗑️  Escaneando items en '{table_name}'...")
        scan_kwargs = {}
        items: List[Dict[str, Any]] = []
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            items.extend(resp.get("Items", []))

        if not items:
            print(f"   ℹ️  La tabla '{table_name}' ya está vacía")
            return True

        print(f"   🗑️  Eliminando {len(items)} items de '{table_name}'...")
        batch_size = 25
        for i in range(0, len(items), batch_size):
            chunk = items[i : i + batch_size]
            with table.batch_writer() as writer:
                for it in chunk:
                    if pk_name not in it:
                        print(f"      ⚠️  Item sin PK '{pk_name}', saltando: {it}")
                        continue
                    key = {pk_name: it[pk_name]}
                    if sk_name:
                        if sk_name in it:
                            key[sk_name] = it[sk_name]
                        else:
                            # si no existe la sk en el item, no se puede eliminar por key compuesta: saltamos
                            print(f"      ⚠️  Item sin SK '{sk_name}', saltando: {it}")
                            continue
                    writer.delete_item(Key=key)
        print(f"   ✅ {len(items)} items eliminados de '{table_name}'")
        return True
    except Exception as e:
        print(f"   ❌ Error al limpiar tabla '{table_name}': {e}")
        return False


def batch_write_items(table, items: List[Dict[str, Any]]) -> Tuple[int, int, List[Dict[str, Any]]]:
    """
    Inserta items en la tabla usando batch_writer con reintentos por batch.
    Retorna: (success_count, error_count, error_details)
    """
    total = len(items)
    if total == 0:
        return 0, 0, []
    batch_size = 25
    batches = [items[i : i + batch_size] for i in range(0, total, batch_size)]

    success_count = 0
    error_count = 0
    error_details: List[Dict[str, Any]] = []

    def process_batch(batch: List[Dict[str, Any]]) -> Tuple[int, int, List[Dict[str, Any]]]:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                local_success = 0
                local_errors = 0
                local_details: List[Dict[str, Any]] = []
                with table.batch_writer() as writer:
                    for it in batch:
                        try:
                            writer.put_item(Item=it)
                            local_success += 1
                        except Exception as e:
                            local_errors += 1
                            local_details.append({"item": str(it)[:200], "error": str(e)})
                return local_success, local_errors, local_details
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code == "ProvisionedThroughputExceededException":
                    wait = (2 ** attempt) + random_module.uniform(0, 1)
                    time.sleep(wait)
                    continue
                else:
                    return 0, len(batch), [{"batch_error": str(e)}]
            except Exception as e:
                # retry on generic exceptions as well a few times
                wait = (2 ** attempt) + random_module.uniform(0, 1)
                time.sleep(wait)
                continue
        # after retries
        return 0, len(batch), [{"batch_error": "max_retries_exceeded"}]

    # Ejecutar en paralelo algunos batches para acelerar
    max_workers = min(8, max(1, len(batches)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_batch = {executor.submit(process_batch, b): b for b in batches}
        for future in as_completed(future_to_batch):
            try:
                s, e, details = future.result()
                with COUNT_LOCK:
                    success_count += s
                    error_count += e
                    error_details.extend(details)
                    processed = success_count + error_count
                    pct = (processed / total) * 100
                    print(f"      📊 Progreso: {processed}/{total} ({pct:.1f}%)")
            except Exception as exc:
                with COUNT_LOCK:
                    error_count += len(future_to_batch[future])
                    error_details.append({"batch_exception": str(exc)})

    return success_count, error_count, error_details


def populate_table(filename: str, config: Dict[str, Any]) -> bool:
    """Puebla una tabla a partir de un archivo JSON y la configuración de claves."""
    table_name = config["table_name"]
    pk = config["pk"]
    sk = config.get("sk")

    print(f"\n📤 Poblando tabla: {table_name}")
    print(f"   Archivo: {filename}")

    if not table_exists(table_name):
        print(f"   ❌ La tabla '{table_name}' no existe. Crea las tablas primero.")
        return False

    # Limpiar tabla
    print("   🗑️  Limpiando la tabla antes de insertar...")
    if not delete_all_items_from_table(table_name, pk, sk):
        print("   ❌ Error limpiando la tabla. Abortando inserción.")
        return False

    # Cargar items
    items = load_json_file(filename)
    if items is None:
        print("   ❌ No se pudo cargar el archivo de datos.")
        return False

    if len(items) == 0:
        print("   ℹ️  No hay items para insertar.")
        return True

    # Validar que los items contengan la PK (y SK si aplica)
    missing_pk = [i for i in items if pk not in i]
    if missing_pk:
        print(f"   ❌ {len(missing_pk)} items no tienen la clave primaria '{pk}'. Ejemplo: {list(missing_pk[0].keys())}")
        return False
    if sk:
        missing_sk = [i for i in items if sk not in i]
        if missing_sk:
            print(f"   ⚠️  {len(missing_sk)} items no tienen la clave de ordenamiento '{sk}'. Estos items serán insertados si la tabla no requiere SK ")
            # Nota: si la tabla realmente necesita SK, DynamoDB exigirá la clave; aquí solo advertimos.

    # Preparar items (ya convertidos floats->Decimal)
    # Asegurarse de eliminar campos con value = None (DynamoDB no acepta atributos con valor None)
    def clean_item(it: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = {}
        for k, v in it.items():
            if v is None:
                continue
            # DynamoDB Document model accepts Decimal, lists, dicts, str, bool, None (None is removed)
            cleaned[k] = v
        return cleaned

    cleaned_items = [clean_item(it) for it in items]

    # Insertar
    table = dynamodb.Table(table_name)
    print(f"   📝 Insertando {len(cleaned_items)} items en '{table_name}' ...")
    success_count, error_count, error_details = batch_write_items(table, cleaned_items)

    print(f"   ✅ Insertados: {success_count}")
    if error_count > 0:
        print(f"   ⚠️  Errores: {error_count}")
        if error_details:
            print("   Detalles (primeros 5):")
            for d in error_details[:5]:
                print(f"      - {d}")
    return error_count == 0


def verify_credentials() -> bool:
    """Verifica que existan credenciales AWS disponibles."""
    try:
        session = boto3.Session()
        creds = session.get_credentials()
        if creds is None:
            print("❌ No se encontraron credenciales de AWS. Configura AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY")
            return False
        print("✅ Credenciales AWS encontradas")
        print(f"   Región: {AWS_REGION}")
        return True
    except Exception as e:
        print(f"❌ Error verificando credenciales: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("🚀 POBLADOR DE TABLAS (adaptado a esquemas definitivos)")
    print("=" * 60)

    if not verify_credentials():
        return

    if not DATA_DIR.exists():
        print(f"❌ Directorio de datos no encontrado: {DATA_DIR}")
        return

    results: Dict[str, bool] = {}
    for filename, cfg in TABLE_MAPPING.items():
        # Saltar archivos que no existan en la carpeta de datos
        full_path = DATA_DIR / filename
        if not full_path.exists():
            print(f"\n⚠️  Archivo faltante: {full_path} -> saltando")
            results[filename] = False
            continue

        ok = populate_table(filename, cfg)
        results[filename] = ok
        # pequeña pausa entre tablas
        time.sleep(0.4)

    # Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE POBLACIÓN")
    print("=" * 60)
    success = sum(1 for v in results.values() if v)
    failed = len(results) - success
    print(f"\n✅ Tablas pobladas correctamente: {success}")
    if failed:
        print(f"❌ Tablas con errores o faltantes: {failed}")
        for fn, ok in results.items():
            if not ok:
                print(f"   - {fn} -> {TABLE_MAPPING.get(fn, {}).get('table_name')}")
    print("\n🎉 Proceso completado")
    print("=" * 60)


if __name__ == "__main__":
    main()