#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# =====================================================
#   🚀 TECSUP HCKT – DEPLOY MANAGER (Complete, robust)
#   - Valida .env
#   - Crea/configura bucket S3 (con sufijo si nombre tomado)
#   - Crea/verifica tablas DynamoDB
#   - Poblado de tablas y subida a S3 (DataPoblator / populate_tables)
#   - Deploy services (serverless)
# =====================================================

export NODE_OPTIONS="--max-old-space-size=8192"

# ===== COLORS =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
ok()   { echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"; }
err()  { echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"; }
info() { echo -e "${CYAN}[$(date +'%H:%M:%S')] ℹ️  $1${NC}"; }

# Resolve script directory (so relative paths work)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# =====================================================
# CHECK .env and load it
# =====================================================
if [ ! -f .env ]; then
    err ".env no encontrado. Copia .env.example → .env y configúralo"
    exit 1
fi
# shellcheck disable=SC1090
source .env
ok ".env cargado correctamente"

# Ensure AWS_REGION variable exists (default to us-east-1)
AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_REGION

# =====================================================
# Helpers
# =====================================================

# Update or add a variable in .env and reload it into current shell
update_env_var() {
    local key="$1"
    local val="$2"
    # remove existing line if present (create backup)
    if grep -q "^${key}=" .env 2>/dev/null; then
        sed -i.bak "/^${key}=/d" .env || true
    fi
    echo "${key}=${val}" >> .env
    # reload
    # shellcheck disable=SC1090
    source .env
    ok ".env actualizado: ${key}=${val}"
}

# Short uuid hex (8 chars)
short_uuid() {
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<'PY' 2>/dev/null
import uuid
print(uuid.uuid4().hex[:8])
PY
    elif command -v uuidgen >/dev/null 2>&1; then
        uuidgen | tr -d '-' | cut -c1-8
    else
        date +%s%N | sha1sum | cut -c1-8
    fi
}

# Install pip requirements for a directory if requirements.txt exists
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

    local PY="python3"
    if ! command -v "$PY" >/dev/null 2>&1; then
        PY="python"
    fi
    log "Instalando dependencias Python en $req_dir usando $PY -m pip ..."
    "$PY" -m pip install --upgrade pip setuptools wheel --quiet
    "$PY" -m pip install -r "$req_file" --quiet
    ok "Dependencies instaladas para $req_dir"
}

# =====================================================
# ENV validation (adjusted to your .env format)
# =====================================================
validate_env() {
    log "Validando variables de entorno..."
    REQUIRED_VARS=(
        "GEMINI_API_KEY"
        "TABLE_USUARIOS"
        "TABLE_TAREAS"
        "TABLE_HISTORIAL"
        "TABLE_DATOS_SOCIOECONOMICOS"
        "TABLE_DATOS_EMOCIONALES"
        "TABLE_DATOS_ACADEMICOS"
    )
    MISSING=()
    for v in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!v:-}" ]; then
            MISSING+=("$v")
        fi
    done
    if [ ${#MISSING[@]} -gt 0 ]; then
        err "Faltan variables de entorno requeridas:"
        for m in "${MISSING[@]}"; do echo " - $m"; done
        exit 1
    fi
    ok "Variables obligatorias encontradas"
}

# =====================================================
# Configure AWS Account ID and S3 bucket default
# - Does NOT overwrite S3_BUCKET_TAREAS if already defined.
# - If S3_BUCKET_TAREAS not defined, sets default using AWS_ACCOUNT_ID.
# =====================================================
configure_aws_account() {
    if [ -z "${AWS_ACCOUNT_ID:-}" ]; then
        warn "AWS_ACCOUNT_ID no configurado → obteniendo con aws cli…"
        if ! command -v aws >/dev/null 2>&1; then
            err "aws cli no instalado o no en PATH"
            exit 1
        fi
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text || true)
        if [ -z "$AWS_ACCOUNT_ID" ]; then
            err "No se pudo obtener AWS_ACCOUNT_ID. Verifica credenciales/configuración de AWS CLI"
            exit 1
        fi
        update_env_var "AWS_ACCOUNT_ID" "$AWS_ACCOUNT_ID"
    else
        ok "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
    fi

    if [ -z "${S3_BUCKET_TAREAS:-}" ]; then
        DEFAULT_BUCKET="tareas-imagenes-${AWS_ACCOUNT_ID}"
        warn "S3_BUCKET_TAREAS no definido → estableciendo por defecto: $DEFAULT_BUCKET"
        update_env_var "S3_BUCKET_TAREAS" "$DEFAULT_BUCKET"
    else
        ok "S3_BUCKET_TAREAS: $S3_BUCKET_TAREAS"
    fi
}

# =====================================================
# Robust S3 bucket creation:
# - Prefer aws cli; if name taken by other account, append short uuid and retry
# - If aws cli unavailable, fallback to Python scripts in DataGenerator
# - Persist final bucket name to .env (S3_BUCKET_TAREAS)
# =====================================================
setup_bucket() {
    echo ""
    echo "════════════ SETUP BUCKET S3 (robusto) ════════════"

    # Ensure DataGenerator dependencies so Python scripts can run
    if [ -d "DataGenerator" ]; then
        install_python_requirements "DataGenerator"
    fi

    local desired_bucket="${S3_BUCKET_TAREAS:-}"
    if [ -z "$desired_bucket" ]; then
        err "S3_BUCKET_TAREAS no definido y no se pudo calcular. Ejecuta configure_aws_account primero."
        return 1
    fi

    local created_bucket=""
    # Try aws cli approach
    if command -v aws >/dev/null 2>&1; then
        local attempt_bucket="$desired_bucket"
        local max_attempts=3
        local attempt=1
        while [ $attempt -le $max_attempts ]; do
            log "Intentando crear bucket: ${attempt_bucket} (intento ${attempt}/${max_attempts})"
            if [ "$AWS_REGION" = "us-east-1" ]; then
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
                if echo "$out" | grep -qi "BucketAlreadyOwnedByYou"; then
                    warn "Bucket ${attempt_bucket} ya existe y es tuyo → se usará"
                    created_bucket="${attempt_bucket}"
                    break
                elif echo "$out" | grep -qi "BucketAlreadyExists"; then
                    warn "Bucket ${attempt_bucket} ya existe (otra cuenta). Generando sufijo y reintentando..."
                    suffix=$(short_uuid)
                    attempt_bucket="${desired_bucket}-${suffix}"
                    attempt=$((attempt+1))
                    continue
                else
                    err "Error creando bucket '${attempt_bucket}': ${out}"
                    break
                fi
            fi
        done
    else
        warn "aws cli no disponible: fallando al método aws; se intentará crear con script Python"
    fi

    # If aws cli did not produce a created_bucket, try Python configurator scripts
    if [ -z "$created_bucket" ]; then
        export S3_BUCKET_TAREAS="$desired_bucket"
        log "Usando scripts Python para crear/configurar bucket: S3_BUCKET_TAREAS=${S3_BUCKET_TAREAS}"
        if [ -f "DataGenerator/create_s3_bucket_for_tareas.py" ]; then
            if python3 DataGenerator/create_s3_bucket_for_tareas.py create-bucket; then
                created_bucket="${S3_BUCKET_TAREAS:-$desired_bucket}"
            else
                warn "create_s3_bucket_for_tareas.py falló, reintentando con sufijo"
                suffix=$(short_uuid)
                alt_bucket="${desired_bucket}-${suffix}"
                export S3_BUCKET_TAREAS="$alt_bucket"
                if python3 DataGenerator/create_s3_bucket_for_tareas.py create-bucket; then
                    created_bucket="$alt_bucket"
                else
                    err "No se pudo crear bucket con create_s3_bucket_for_tareas.py (incluyendo alternativo)"
                    return 1
                fi
            fi
        elif [ -f "DataGenerator/CreateBucket.py" ]; then
            if python3 DataGenerator/CreateBucket.py create-bucket; then
                created_bucket="${S3_BUCKET_TAREAS:-$desired_bucket}"
            else
                warn "CreateBucket.py falló, reintentando con sufijo"
                suffix=$(short_uuid)
                alt_bucket="${desired_bucket}-${suffix}"
                export S3_BUCKET_TAREAS="$alt_bucket"
                if python3 DataGenerator/CreateBucket.py create-bucket; then
                    created_bucket="$alt_bucket"
                else
                    err "No se pudo crear bucket con CreateBucket.py (incluyendo alternativo)"
                    return 1
                fi
            fi
        else
            err "No se encontró script Python para creación/configuración de bucket en DataGenerator/"
            return 1
        fi
    fi

    # Persist chosen bucket in .env and export for this session
    if [ -n "$created_bucket" ]; then
        update_env_var "S3_BUCKET_TAREAS" "$created_bucket"
        export S3_BUCKET_TAREAS="$created_bucket"
        ok "Bucket final a usar: $created_bucket"
        # Run configurator again (idempotent) to ensure policies/CORS set
        if [ -f "DataGenerator/create_s3_bucket_for_tareas.py" ]; then
            python3 DataGenerator/create_s3_bucket_for_tareas.py create-bucket || warn "Advertencia: Python configurador falló (pero bucket creado)"
        elif [ -f "DataGenerator/CreateBucket.py" ]; then
            python3 DataGenerator/CreateBucket.py create-bucket || warn "Advertencia: Python configurador falló (pero bucket creado)"
        fi
        return 0
    else
        err "No se pudo determinar bucket S3 válido"
        return 1
    fi
}

# =====================================================
# CREATE TABLES + POPULATE (runs DataPoblator or populate_tables)
# =====================================================
setup_database_and_populate() {
    echo ""
    echo "════════════ DATABASE SETUP (DynamoDB) + POPULATE ════════════"

    if [ ! -d "DataGenerator" ]; then
        err "No se encontró carpeta DataGenerator/ (contiene scripts Python)"
        exit 1
    fi
    cd DataGenerator || exit 1

    install_python_requirements "DataGenerator"

    log "Creando/verificando tablas DynamoDB..."
    if [ -f create_tables.py ]; then
        python3 create_tables.py || { err "Error creando tablas"; exit 1; }
    elif [ -f CreateTables.py ]; then
        python3 CreateTables.py || { err "Error creando tablas"; exit 1; }
    else
        err "No se encontró create_tables.py o CreateTables.py en DataGenerator/"
        exit 1
    fi
    ok "Tablas creadas/verificadas"

    # Decide which populador exists
    POPULATOR_SCRIPT=""
    if [ -f DataPoblator.py ]; then
        POPULATOR_SCRIPT="DataPoblator.py"
    elif [ -f populate_tables.py ]; then
        POPULATOR_SCRIPT="populate_tables.py"
    elif [ -f DataPoblator.py ]; then
        POPULATOR_SCRIPT="DataPoblator.py"
    fi

    if [ -n "$POPULATOR_SCRIPT" ]; then
        log "Ejecutando script de poblado: $POPULATOR_SCRIPT"
        if [ "${AUTO_CONFIRM:-false}" = "true" ]; then
            log "AUTO_CONFIRM=true → ejecución no interactiva (respondiendo 's' a prompts)"
            yes s | python3 "$POPULATOR_SCRIPT" || { err "Error ejecutando $POPULATOR_SCRIPT (non-interactive)"; exit 1; }
        else
            python3 "$POPULATOR_SCRIPT" || { err "Error ejecutando $POPULATOR_SCRIPT"; exit 1; }
        fi
        ok "Población de tablas/S3 completada (script: $POPULATOR_SCRIPT)"
    else
        warn "No se encontró script de poblado (DataPoblator.py / populate_tables.py) en DataGenerator/"
    fi

    cd "$SCRIPT_DIR" || exit 1
}

# =====================================================
# Deploy services
# =====================================================
deploy_services() {
    echo ""
    echo "════════════ DEPLOY SERVERLESS COMPOSE ════════════"
    log "Limpieza suave (solo __pycache__)..."
    find API-*/ -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    if [ ! -d node_modules ]; then
        warn "Instalando dependencias Node (serverless/plugins)..."
        if [ -f package-lock.json ]; then
            npm ci
        else
            npm install
        fi
    fi

    ok "Entorno Node listo"

    if ! command -v serverless >/dev/null 2>&1; then
        err "Serverless CLI no encontrado. Instala 'serverless' antes de continuar."
        exit 1
    fi

    STG="${STAGE:-dev}"
    log "Ejecutando serverless deploy --stage ${STG} ..."
    serverless deploy --stage "${STG}" || { err "Falló el deploy"; exit 1; }
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

# Validate env and aws/account before executing options
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