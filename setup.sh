#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# =====================================================
#   🚀 TECSUP HCKT – DEPLOY MANAGER (Bucket robust creation)
# =====================================================

export NODE_OPTIONS="--max-old-space-size=8192"

# Colors...
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
log(){ echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
ok(){ echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"; }
err(){ echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"; }
warn(){ echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"; }
info(){ echo -e "${CYAN}[$(date +'%H:%M:%S')] ℹ️  $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env
if [ ! -f .env ]; then err ".env no encontrado"; exit 1; fi
# shellcheck disable=SC1090
source .env
ok ".env cargado"

# Helper: update or add key in .env
update_env_var() {
    local key="$1"
    local val="$2"
    # If line exists replace, else append
    if grep -q "^${key}=" .env; then
        # create backup and replace
        sed -i.bak "/^${key}=/d" .env || true
    fi
    echo "${key}=${val}" >> .env
    # reload into current shell
    # shellcheck disable=SC1090
    source .env
    ok ".env actualizado: ${key}=${val}"
}

# Helper: short uuid hex (8 chars)
short_uuid() {
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<'PY' 2>/dev/null
import uuid,sys
print(uuid.uuid4().hex[:8])
PY
    elif command -v uuidgen >/dev/null 2>&1; then
        uuidgen | tr -d '-' | cut -c1-8
    else
        # fallback timestamp-random
        date +%s%N | sha1sum | cut -c1-8
    fi
}

# Install requirements helper (kept as in previous)
install_python_requirements() {
    local req_dir="$1"
    if [ ! -d "$req_dir" ]; then warn "Dir no existe: $req_dir"; return 0; fi
    local req_file="$req_dir/requirements.txt"
    if [ ! -f "$req_file" ]; then warn "No requirements.txt en $req_dir"; return 0; fi
    local PY=python3
    if ! command -v "$PY" >/dev/null 2>&1; then PY=python; fi
    log "Instalando dependencias en $req_dir..."
    "$PY" -m pip install --upgrade pip setuptools wheel --quiet
    "$PY" -m pip install -r "$req_file" --quiet
    ok "Dependencies instaladas para $req_dir"
}

# =====================================================
# Robust setup_bucket: try create, if name taken generate suffix and retry,
# on success update .env automatically and call Python configurator
# =====================================================
setup_bucket() {
    echo ""
    echo "════════════ SETUP BUCKET S3 (robusto) ════════════"

    # Ensure requirements (so Python script has dotenv/boto3)
    if [ -d "DataGenerator" ]; then
        install_python_requirements "DataGenerator"
    fi

    # Determine desired bucket name
    if [ -n "${S3_BUCKET_TAREAS:-}" ]; then
        desired_bucket="$S3_BUCKET_TAREAS"
    else
        # Determine AWS_ACCOUNT_ID if not present
        if [ -z "${AWS_ACCOUNT_ID:-}" ]; then
            if ! command -v aws >/dev/null 2>&1; then
                err "AWS_ACCOUNT_ID indefinido y aws cli no disponible"
                exit 1
            fi
            AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
            update_env_var "AWS_ACCOUNT_ID" "$AWS_ACCOUNT_ID"
        fi
        desired_bucket="tareas-imagenes-${AWS_ACCOUNT_ID}"
    fi

    # Try create using aws cli if available (preferred)
    created_bucket=""
    if command -v aws >/dev/null 2>&1; then
        attempt_bucket="$desired_bucket"
        max_attempts=3
        attempt=1
        while [ $attempt -le $max_attempts ]; do
            log "Intentando crear bucket: ${attempt_bucket} (intento ${attempt}/${max_attempts})"
            # create depending on region
            if [ "${AWS_REGION:-us-east-1}" = "us-east-1" ]; then
                set +e
                out=$(aws s3api create-bucket --bucket "${attempt_bucket}" 2>&1)
                rc=$?
                set -e
            else
                set +e
                out=$(aws s3api create-bucket --bucket "${attempt_bucket}" --create-bucket-configuration LocationConstraint="${AWS_REGION}" 2>&1)
                rc=$?
                set -e
            fi

            if [ $rc -eq 0 ]; then
                ok "Bucket creado: ${attempt_bucket}"
                created_bucket="${attempt_bucket}"
                break
            else
                # inspect error
                if echo "$out" | grep -qi "BucketAlreadyOwnedByYou"; then
                    warn "Bucket ${attempt_bucket} ya existe y es tuyo → se usará"
                    created_bucket="${attempt_bucket}"
                    break
                elif echo "$out" | grep -qi "BucketAlreadyExists"; then
                    warn "Bucket ${attempt_bucket} ya existe (otra cuenta). Intentando sufijo..."
                    suffix=$(short_uuid)
                    attempt_bucket="${desired_bucket}-${suffix}"
                    attempt=$((attempt+1))
                    continue
                else
                    err "Error creando bucket '${attempt_bucket}': ${out}"
                    # No retry for unexpected errors
                    break
                fi
            fi
        done
    else
        warn "aws cli no disponible: intentar crear bucket usando script Python"
    fi

    # If we didn't create a bucket via aws cli, try via Python configurator (it will attempt to create as well)
    if [ -z "$created_bucket" ]; then
        # Export S3_BUCKET_TAREAS to desired_bucket before calling python script
        export S3_BUCKET_TAREAS="$desired_bucket"
        log "Llamando a script Python para crear/configurar bucket: S3_BUCKET_TAREAS=${S3_BUCKET_TAREAS}"
        if [ -f "DataGenerator/create_s3_bucket_for_tareas.py" ]; then
            python3 DataGenerator/create_s3_bucket_for_tareas.py create-bucket || {
                warn "Python script create_s3_bucket_for_tareas.py no pudo crear el bucket '${desired_bucket}'"
                # try with suffix
                suffix=$(short_uuid)
                alt_bucket="${desired_bucket}-${suffix}"
                export S3_BUCKET_TAREAS="$alt_bucket"
                log "Reintentando con bucket alternativo: ${alt_bucket}"
                python3 DataGenerator/create_s3_bucket_for_tareas.py create-bucket || {
                    err "Falló creación del bucket alternativo (${alt_bucket}) con Python"
                    return 1
                }
                created_bucket="${alt_bucket}"
            }
            # If python script succeeded, S3_BUCKET_TAREAS env is already set; use it
            if [ -z "${created_bucket}" ]; then
                created_bucket="${S3_BUCKET_TAREAS:-$desired_bucket}"
            fi
        elif [ -f "DataGenerator/CreateBucket.py" ]; then
            python3 DataGenerator/CreateBucket.py create-bucket || {
                warn "Python script CreateBucket.py no pudo crear el bucket '${desired_bucket}'"
                suffix=$(short_uuid)
                alt_bucket="${desired_bucket}-${suffix}"
                export S3_BUCKET_TAREAS="$alt_bucket"
                log "Reintentando con bucket alternativo: ${alt_bucket}"
                python3 DataGenerator/CreateBucket.py create-bucket || {
                    err "Falló creación del bucket alternativo (${alt_bucket}) con Python"
                    return 1
                }
                created_bucket="${alt_bucket}"
            }
            if [ -z "${created_bucket}" ]; then
                created_bucket="${S3_BUCKET_TAREAS:-$desired_bucket}"
            fi
        else
            err "No se encontró ningún script Python para configuración de bucket en DataGenerator/"
            return 1
        fi
    fi

    # If we have a created_bucket, persist to .env (overwrite existing S3_BUCKET_TAREAS)
    if [ -n "${created_bucket}" ]; then
        update_env_var "S3_BUCKET_TAREAS" "${created_bucket}"
        export S3_BUCKET_TAREAS="${created_bucket}"
        ok "Bucket final a usar: ${created_bucket}"
        # Run configurator python script to ensure policies/CORS/etc are set (idempotent)
        if [ -f "DataGenerator/create_s3_bucket_for_tareas.py" ]; then
            python3 DataGenerator/create_s3_bucket_for_tareas.py create-bucket || warn "Advertencia: Python configurador falló (pero bucket creado)"
        elif [ -f "DataGenerator/CreateBucket.py" ]; then
            python3 DataGenerator/CreateBucket.py create-bucket || warn "Advertencia: Python configurador falló (pero bucket creado)"
        fi
        return 0
    else
        err "No se pudo crear ni determinar un bucket S3 válido"
        return 1
    fi
}

# =====================================================
# INSTALL PYTHON REQUIREMENTS (helper)
# =====================================================
install_python_requirements() {
    local req_dir="$1"
    if [ ! -d "$req_dir" ]; then
        warn "Directorio no existe: $req_dir"
        return 0
    fi

    local req_file="$req_dir/requirements.txt"
    if [ ! -f "$req_file" ]; then
        warn "No existe requirements.txt en $req_dir"
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        PY=python3
    elif command -v python >/dev/null 2>&1; then
        PY=python
    else
        err "Python no encontrado. Instala Python antes de continuar."
        exit 1
    fi

    log "Instalando dependencias Python en $req_dir usando $PY -m pip ..."
    "$PY" -m pip install --upgrade pip setuptools wheel --quiet
    "$PY" -m pip install -r "$req_file" --quiet
    ok "Dependencies instaladas para $req_dir"
}

# =====================================================
# SETUP BUCKET S3 (instala requirements primero) - pasa subcomando create-bucket si es necesario
# =====================================================
setup_bucket() {
    echo ""
    echo "════════════ SETUP BUCKET S3 ════════════"

    # Instalar dependencies de DataGenerator (contiene CreateBucket/DataPoblator)
    if [ -d "DataGenerator" ]; then
        install_python_requirements "DataGenerator"
    fi

    # Ejecutar script de creación de bucket (buscar variantes)
    if [ -f "DataGenerator/create_s3_bucket_for_tareas.py" ]; then
        python3 DataGenerator/create_s3_bucket_for_tareas.py create-bucket || {
            err "Error en creación bucket S3 (create_s3_bucket_for_tareas.py)"
            exit 1
        }
    elif [ -f "DataGenerator/CreateBucket.py" ]; then
        # CreateBucket.py requiere un subcomando posicional
        python3 DataGenerator/CreateBucket.py create-bucket || {
            err "Error en creación bucket S3 (CreateBucket.py create-bucket)"
            exit 1
        }
    else
        warn "No se encontró script para crear bucket en DataGenerator/ (create_s3_bucket_for_tareas.py o CreateBucket.py)"
    fi

    ok "Intento de creación/configuración de bucket S3 completado"
}

# =====================================================
# CREATE TABLES + POPULATE (incluye ejecución de DataPoblator.py para poblar tablas y S3)
# =====================================================
setup_database_and_populate() {
    echo ""
    echo "════════════ DATABASE SETUP (DynamoDB) + POPULATE ════════════"

    if [ ! -d "DataGenerator" ]; then
        err "No se encontró carpeta DataGenerator/ (contiene scripts Python)"
        exit 1
    fi

    cd DataGenerator || exit 1

    # Ensure requirements are installed (idempotent)
    install_python_requirements "DataGenerator"

    log "Creando tablas DynamoDB..."
    if [ -f create_tables.py ]; then
        python3 create_tables.py || { err "Error creando tablas"; exit 1; }
    elif [ -f CreateTables.py ]; then
        python3 CreateTables.py || { err "Error creando tablas"; exit 1; }
    else
        err "No se encontró create_tables.py o CreateTables.py en DataGenerator/"
        exit 1
    fi
    ok "Tablas creadas/verificadas"

    # Ejecutar el script de poblado (DataPoblator.py preferido)
    # Si se exporta AUTO_CONFIRM=true se intentará ejecución no interactiva (responder 's' a prompts).
    POPULATOR_RUN=false
    if [ -f DataPoblator.py ]; then
        POPULATOR_SCRIPT="DataPoblator.py"
        POPULATOR_RUN=true
    elif [ -f populate_tables.py ]; then
        POPULATOR_SCRIPT="populate_tables.py"
        POPULATOR_RUN=true
    elif [ -f DataPoblator.py ]; then
        POPULATOR_SCRIPT="DataPoblator.py"
        POPULATOR_RUN=true
    fi

    if [ "$POPULATOR_RUN" = true ]; then
        log "Ejecutando script de poblado: $POPULATOR_SCRIPT"
        # Si el usuario exportó AUTO_CONFIRM=true, ejecutamos no interactivo (yes 's')
        if [ "${AUTO_CONFIRM:-false}" = "true" ]; then
            log "AUTO_CONFIRM=true → ejecución no interactiva (respondiendo 's' a prompts)"
            yes s | python3 "$POPULATOR_SCRIPT" || {
                err "Error ejecutando $POPULATOR_SCRIPT (non-interactive)"
                exit 1
            }
        else
            # Intentamos ejecutar interactivamente; si falla por prompts o errores, se mostrará al usuario.
            python3 "$POPULATOR_SCRIPT" || {
                err "Error ejecutando $POPULATOR_SCRIPT"
                exit 1
            }
        fi
        ok "Población de tablas/S3 completada (script: $POPULATOR_SCRIPT)"
    else
        warn "No se encontró script de poblado (DataPoblator.py / populate_tables.py) en DataGenerator/"
    fi

    cd "$SCRIPT_DIR" || exit 1
}

# =====================================================
# DEPLOY SERVICES (sin cambios funcionales importantes)
# =====================================================
deploy_services() {
    echo ""
    echo "════════════ DEPLOY SERVERLESS COMPOSE ════════════"

    ok "Entorno Node listo"

    if ! command -v serverless >/dev/null 2>&1; then
        err "Serverless CLI no encontrado. Instala 'serverless' antes de continuar."
        exit 1
    fi

    STG="${STAGE:-dev}"
    log "Ejecutando serverless deploy --stage ${STG} ..."
    serverless deploy --stage "${STG}" || {
        err "Falló el deploy"
        exit 1
    }

    ok "Servicios desplegados exitosamente 🚀"
}

# =====================================================
# MENU
# =====================================================
echo ""
echo "══════════════════════════════════════"
echo "  📋 OPCIONES"
echo "══════════════════════════════════════"
echo "  1) 🏗️  Crear bucket, tablas y poblar"
echo "  2) 🚀 Desplegar Servicios"
echo "  3) 🗑️  Eliminar todo"
echo "══════════════════════════════════════"
read -r -p "Seleccione (1-3): " OPT

validate_env
configure_aws_account

case $OPT in
    1)
        setup_bucket
        setup_database_and_populate
        ;;
    2)
        deploy_services
        ;;
    3)
        warn "Esta acción borrará los recursos..."
        read -r -p "¿Continuar? (s/n): " C
        if [ "$C" = "s" ]; then
            serverless compose remove || { err "Error eliminando recursos"; exit 1; }
        fi
        ;;
    *)
        err "Opción inválida"
        exit 1
        ;;
esac

ok "✨ Operación completada"