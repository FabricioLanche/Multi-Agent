#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# =====================================================
#   🚀 TECSUP HCKT – DEPLOY MANAGER (Optimized v3)
#   - Crea bucket S3 para tareas
#   - Crea tablas DynamoDB
#   - Pobla tablas (DataPoblator.py / populate_tables.py)
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

# =====================================================
# BANNER
# =====================================================
echo ""
echo "═══════════════════════════════════════════════"
echo "         🏥 TECSUP HCKT – DEPLOY MANAGER        "
echo "═══════════════════════════════════════════════"
echo ""

# Resolve script directory (so relative paths work)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# =====================================================
# CHECK .env
# =====================================================
if [ ! -f .env ]; then
    err "No existe .env"
    info "Copia .env.example → .env y configúralo"
    exit 1
fi
# shellcheck disable=SC1090
source .env
ok ".env cargado correctamente"

# =====================================================
# VALIDATE ENV (ajustado a tu .env)
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
# CONFIGURE AWS ACCOUNT ID (no sobrescribe S3_BUCKET_TAREAS si ya existe)
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

        if ! grep -q '^AWS_ACCOUNT_ID=' .env; then
            echo "AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID" >> .env
        fi
        ok "AWS_ACCOUNT_ID configurado: $AWS_ACCOUNT_ID"
    else
        ok "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
    fi

    # Si S3_BUCKET_TAREAS NO está definido, creamos uno por defecto con account id
    if [ -z "${S3_BUCKET_TAREAS:-}" ]; then
        DEFAULT_BUCKET="tareas-imagenes-${AWS_ACCOUNT_ID}"
        warn "S3_BUCKET_TAREAS no definido → estableciendo por defecto: $DEFAULT_BUCKET"
        sed -i.bak '/^S3_BUCKET_TAREAS=/d' .env || true
        echo "S3_BUCKET_TAREAS=$DEFAULT_BUCKET" >> .env
        # shellcheck disable=SC1090
        source .env
        ok "S3_BUCKET_TAREAS añadido a .env: $DEFAULT_BUCKET"
    else
        ok "S3_BUCKET_TAREAS: $S3_BUCKET_TAREAS"
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