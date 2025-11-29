#!/usr/bin/env python3
"""
Generador de datos refactorizado para cumplir con los esquemas definitivos:
Usuario.json, Tarea.json, Historial.json, DatosSocioeconomicos(.json),
DatosEmocionales.json, DatosAcademicos.json

Salida: carpeta dynamodb-data/*.json
"""
import json
import uuid
import random
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configuración
OUTPUT_DIR = Path(__file__).parent / "dynamodb-data"
SCHEMAS_DIR = Path(__file__).parent / "schemas-validation"

USUARIOS_TOTAL = int(os.getenv("USUARIOS_TOTAL", "30"))

CORREOS_DOMINIOS = ["utec.edu.pe", "gmail.com", "outlook.com"]
CARRERAS = ["Ingeniería de Software", "Ingeniería Civil", "Arquitectura", "Administración", "Economía", "Psicología"]
ESTADOS_MATRICULA = ["MATRICULADO", "RETIRADO", "EGRESADO", "SUSPENDIDO", "INACTIVO"]
TIPOS_FINANCIAMIENTO = ["PROPIO", "FAMILIAR", "BECA", "CREDITO", "OTRO"]
SITUACIONES_LABORALES = ["TRABAJA", "NO_TRABAJA", "TRABAJA_Y_ESTUDIA"]
FRECUENCIAS_ACCESO = ["DIARIO", "SEMANAL", "MENSUAL", "RARA_VEZ", "NUNCA"]
USO_SERVICIOS = ["NUNCA", "OCASIONAL", "REGULAR", "FRECUENTE"]

NOMBRES_SIMPLE = [
    "juan.perez", "maria.garcia", "carlos.lopez", "ana.martinez", "luis.rodriguez",
    "carmen.fernandez", "jose.gonzalez", "laura.sanchez", "miguel.torres", "isabel.ramirez",
    "pedro.flores", "sofia.castro", "diego.morales", "valentina.ortiz", "andres.silva",
    "camila.rojas", "magali.flores", "roberto.diaz", "patricia.ruiz", "fernando.vega"
]


def _new_uuid() -> str:
    """Genera UUID v4 como string (36 chars)"""
    return str(uuid.uuid4())


def generar_correo(base: str) -> str:
    dominio = random.choice(CORREOS_DOMINIOS)
    return f"{base}@{dominio}"


def generar_usuarios(cantidad: int = USUARIOS_TOTAL) -> List[Dict[str, Any]]:
    usuarios = []
    usados = set()
    cantidad = max(1, cantidad)
    # Crear usuarios únicos
    while len(usuarios) < cantidad:
        base = random.choice(NOMBRES_SIMPLE)
        correo = generar_correo(base)
        if correo in usados:
            continue
        usuario = {
            "id": _new_uuid(),
            "correo": correo,
            "contrasena": f"hash_{uuid.uuid4().hex[:16]}",
            "autorizacion": random.choice([True, False])
        }
        usuarios.append(usuario)
        usados.add(correo)
    return usuarios


def generar_tareas(usuarios: List[Dict[str, Any]], max_por_usuario: int = 5) -> List[Dict[str, Any]]:
    tareas = []
    posibles_textos = [
        "Entregar práctica 1", "Leer capítulo 3", "Resolver ejercicio adicional",
        "Preparar presentación", "Subir archivo de proyecto"
    ]
    for u in usuarios:
        num = random.randint(0, max_por_usuario)
        for _ in range(num):
            tarea = {
                "id": _new_uuid(),
                "usuarioId": u["id"],
                "imagenUrl": random.choice([None, f"https://cdn.example.com/{uuid.uuid4().hex}.jpg"]),
                "texto": random.choice(posibles_textos)
            }
            # imagenUrl es opcional según el esquema; si None, lo eliminamos para cumplir additionalProperties: false
            if tarea["imagenUrl"] is None:
                tarea.pop("imagenUrl")
            tareas.append(tarea)
    return tareas


def generar_historial(usuarios: List[Dict[str, Any]], max_por_usuario: int = 4) -> List[Dict[str, Any]]:
    historiales = []
    ejemplos = [
        "Asistió a asesoría", "Registró baja temporal", "Solicitó revisión de nota",
        "Se inscribió en curso electivo", "Reportó problema de matrícula"
    ]
    for u in usuarios:
        num = random.randint(0, max_por_usuario)
        for _ in range(num):
            h = {
                "id": _new_uuid(),
                "usuarioId": u["id"],
                "texto": random.choice(ejemplos)
            }
            historiales.append(h)
    return historiales


def generar_datos_socioeconomicos(usuarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Genera exactamente un registro socioeconómico por usuario (uno a uno).
    Todos los registros incluyen los campos requeridos por el esquema.
    """
    datos = []
    for u in usuarios:
        ingreso = round(random.uniform(0, 5000), 2)
        d = {
            "id": _new_uuid(),
            "usuarioId": u["id"],
            "tipo_financiamiento": random.choice(TIPOS_FINANCIAMIENTO),
            "situacion_laboral": random.choice(SITUACIONES_LABORALES),
            "ingreso_estimado": ingreso,
            "dependencia_economica": random.choice([True, False])
        }
        datos.append(d)
    return datos


def generar_datos_emocionales(usuarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Genera exactamente un registro emocional por usuario (uno a uno).
    Incluye los campos requeridos; otros campos también se generan.
    """
    datos = []
    for u in usuarios:
        d = {
            "id": _new_uuid(),
            "usuarioId": u["id"],
            "frecuencia_acceso_plataforma": random.choice(FRECUENCIAS_ACCESO),
            "horas_estudio_estimadas": round(random.uniform(0, 40), 1),
            "uso_servicios_tutoria": random.choice(USO_SERVICIOS),
            "uso_servicios_psicologia": random.choice(USO_SERVICIOS),
            "actividades_extracurriculares": random.choice([True, False])
        }
        datos.append(d)
    return datos


def generar_datos_academicos(usuarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Genera exactamente un registro académico por usuario (uno a uno).
    Asegura presencia de campos requeridos: id, usuarioId, carrera, ciclo_actual.
    """
    datos = []
    for u in usuarios:
        promedio = round(random.uniform(10.0, 20.0), 2)
        creditos_aprobados = random.randint(0, 240)
        creditos_desaprobados = random.randint(0, 30)
        historial_retirados = []
        if random.random() < 0.2:
            num_retiros = random.randint(1, 3)
            for _ in range(num_retiros):
                curso = f"CUR{random.randint(100,499)}"
                periodo = f"{random.randint(2015,2025)}-{random.choice(['I','II'])}"
                historial_retirados.append({"curso": curso, "periodo": periodo})
        cursos_reprobados = []
        if random.random() < 0.25:
            cursos_reprobados = [f"CUR{random.randint(100,499)}" for _ in range(random.randint(1, 4))]
        d = {
            "id": _new_uuid(),
            "usuarioId": u["id"],
            "carrera": random.choice(CARRERAS),
            "ciclo_actual": random.randint(1, 12),
            "estado_matricula": random.choice(ESTADOS_MATRICULA),
            "creditos_aprobados": creditos_aprobados,
            "creditos_desaprobados": creditos_desaprobados,
            "promedio_ponderado": promedio,
            "historial_retirados": historial_retirados,
            "avance_malla": round(random.uniform(0, 100), 2),
            "cursos_reprobados": cursos_reprobados,
            "asistencia_promedio": round(random.uniform(50, 100), 2)
        }
        datos.append(d)
    return datos


def find_schema_file(nombre_esquema: str) -> Optional[Path]:
    """
    Intenta localizar un archivo de esquema JSON en SCHEMAS_DIR probando variantes.
    Devuelve la Path si existe, o None si no lo encuentra.
    """
    candidates = []
    base = nombre_esquema
    # Variantes comunes
    candidates.append(f"{base}.json")
    candidates.append(f"{base.capitalize()}.json")
    candidates.append(f"{base.title()}.json")
    candidates.append(f"{base.lower()}.json")
    # Algunas conversiones específicas
    candidates.append("Usuario.json")
    candidates.append("Tarea.json")
    candidates.append("Historial.json")
    candidates.append("DatosSocioeconomicos.json")
    candidates.append("DatosSocieconomicos.json")  # cubrir la posible variación que enviaste
    candidates.append("DatosEmocionales.json")
    candidates.append("DatosAcademicos.json")

    for c in candidates:
        p = SCHEMAS_DIR / c
        if p.exists():
            return p
    return None


def validar_con_esquema(datos: List[Dict[str, Any]], nombre_esquema: str) -> bool:
    """
    Validación básica: verifica que cada objeto tenga las propiedades 'required'
    definidas en el esquema json (no hace validación completa JSON Schema).
    """
    schema_file = find_schema_file(nombre_esquema)
    if schema_file is None:
        print(f"⚠️  No se encontró esquema para '{nombre_esquema}' en {SCHEMAS_DIR}. Se omite validación estricta.")
        return True

    try:
        with open(schema_file, "r", encoding="utf-8") as f:
            esquema = json.load(f)
    except Exception as e:
        print(f"❌ Error al leer esquema {schema_file}: {e}")
        return False

    required = esquema.get("required", [])
    ok = True
    # datos puede ser una lista de objetos; si es un dict único, lo convertimos a lista
    items = datos if isinstance(datos, list) else [datos]
    for idx, item in enumerate(items):
        for campo in required:
            if campo not in item:
                print(f"⚠️  Falta campo requerido '{campo}' en {nombre_esquema} (registro índice {idx}) -> id: {item.get('id')}")
                ok = False
    if ok:
        print(f"✅ Datos de {nombre_esquema} cumplen los campos requeridos ({len(items)} registros).")
    else:
        print(f"❌ {nombre_esquema} NO pasó la validación básica (faltan campos requeridos).")
    return ok


def guardar_json(datos: Any, nombre_archivo: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    ruta = OUTPUT_DIR / nombre_archivo
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    count = len(datos) if isinstance(datos, list) else 1
    print(f"📝 Generado: {ruta} ({count} registros)")


def main() -> None:
    print("=" * 60)
    print("🚀 GENERADOR DE DATOS - AJUSTADO A ESQUEMAS DEFINITIVOS")
    print("=" * 60)
    print()

    # Usuarios
    print("📊 Generando usuarios...")
    usuarios = generar_usuarios()
    validar_con_esquema(usuarios, "Usuario")
    guardar_json(usuarios, "usuarios.json")
    print()

    # Tareas
    print("📊 Generando tareas...")
    tareas = generar_tareas(usuarios)
    validar_con_esquema(tareas, "Tarea")
    guardar_json(tareas, "tareas.json")
    print()

    # Historial
    print("📊 Generando historial...")
    historial = generar_historial(usuarios)
    validar_con_esquema(historial, "Historial")
    guardar_json(historial, "historial.json")
    print()

    # Datos socioeconómicos
    print("📊 Generando datos socioeconómicos...")
    socio = generar_datos_socioeconomicos(usuarios)
    validar_con_esquema(socio, "DatosSocioeconomicos")
    guardar_json(socio, "datos_socioeconomicos.json")
    print()

    # Datos emocionales
    print("📊 Generando datos emocionales...")
    emoc = generar_datos_emocionales(usuarios)
    validar_con_esquema(emoc, "DatosEmocionales")
    guardar_json(emoc, "datos_emocionales.json")
    print()

    # Datos académicos
    print("📊 Generando datos académicos...")
    ac = generar_datos_academicos(usuarios)
    validar_con_esquema(ac, "DatosAcademicos")
    guardar_json(ac, "datos_academicos.json")
    print()

    print("=" * 60)
    print("✨ Generación completada")
    print(f"📂 Archivos guardados en: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()