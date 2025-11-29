#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# =====================================================
#   🚀 TECSUP HCKT – DEPLOY MANAGER (Optimized v2)
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
# VALIDATE ENV
# =====================================================
validate_env() {
    log "Validando variables de entorno..."
    REQUIRED_VARS=("GEMINI_API_KEY" "TABLE_TAREAS" "TABLE_HISTORIAL" "TABLE_USUARIOS")
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
# CONFIGURE AWS ACCOUNT ID
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

    EXPECTED_BUCKET="recetas-medicas-data-${AWS_ACCOUNT_ID}"
    if [ "${S3_BUCKET_RECETAS:-}" != "$EXPECTED_BUCKET" ]; then
        warn "Actualizando S3_BUCKET_RECETAS en .env → $EXPECTED_BUCKET"
        sed -i.bak '/^S3_BUCKET_RECETAS=/d' .env || true
        echo "S3_BUCKET_RECETAS=$EXPECTED_BUCKET" >> .env
        ok "S3_BUCKET_RECETAS actualizado: $EXPECTED_BUCKET"
        # shellcheck disable=SC1090
        source .env
    fi
}

# =====================================================
# INSTALL PYTHON REQUIREMENTS (helper)
# =====================================================
install_python_requirements() {
    local req_dir="$1"   # directory containing requirements.txt
    if [ ! -d "$req_dir" ]; then
        warn "Directorio no existe: $req_dir"
        return 0
    fi

    local req_file="$req_dir/requirements.txt"
    if [ ! -f "$req_file" ]; then
        warn "No existe requirements.txt en $req_dir"
        return 0
    fi

    # Select python executable
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
# SETUP BUCKET S3 (instala requirements primero)
# ===================================================== 
setup_bucket() {
    echo ""
    echo "════════════ SETUP BUCKET S3 ════════════"

    # Asegurarse de instalar requirements del DataGenerator antes de ejecutar el script de bucket
    if [ -d "DataGenerator" ]; then
        install_python_requirements "DataGenerator"
    fi

    # Ejecutar script de creación de bucket (buscar variantes de nombre)
    if [ -f "DataGenerator/create_s3_bucket_for_tareas.py" ]; then
        python3 DataGenerator/create_s3_bucket_for_tareas.py create-bucket || {
            err "Error en creación bucket S3 (create_s3_bucket_for_tareas.py)"
            exit 1
        }
    elif [ -f "DataGenerator/CreateBucket.py" ]; then
        python3 DataGenerator/CreateBucket.py || {
            err "Error en creación bucket S3 (CreateBucket.py)"
            exit 1
        }
    else
        warn "No se encontró script para crear bucket en DataGenerator/ (create_s3_bucket_for_tareas.py o CreateBucket.py)"
    fi

    ok "Intento de creación/configuración de bucket S3 completado"
}

# =====================================================
# CREAR TABLAS + POBLAR
# =====================================================
setup_database() {
    echo ""
    echo "════════════ DATABASE SETUP (DynamoDB) ════════════"

    if [ ! -d "DataGenerator" ]; then
        err "No se encontró carpeta DataGenerator/ (conteniendo scripts Python)"
        exit 1
    fi

    cd DataGenerator || exit 1

    # Instalar dependencias Python (ya instaladas antes por setup_bucket, pero repetimos por seguridad)
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

    ok "Tablas listas"

    log "Verificando existencia de datos en tablas (si existe check_tables.py)..."
    HAS_DATA="NO"
    if [ -f check_tables.py ]; then
        HAS_DATA=$(python3 check_tables.py) || HAS_DATA="NO"
    else
        warn "check_tables.py no encontrado; se preguntará si poblar manualmente"
    fi

    if [ "$HAS_DATA" = "YES" ]; then
        warn "Tablas ya contienen datos."
        read -r -p "¿Limpiar y poblar de nuevo? (s/n): " R
        if [ "$R" = "s" ]; then
            if [ -f populate_tables.py ]; then
                python3 populate_tables.py
            elif [ -f DataPoblator.py ]; then
                python3 DataPoblator.py
            else
                err "No se encontró script de población (populate_tables.py / DataPoblator.py)"
                exit 1
            fi
        fi
    else
        read -r -p "¿Poblar tablas con datos demo? (s/n): " R
        if [ "$R" = "s" ]; then
            if [ -f populate_tables.py ]; then
                python3 populate_tables.py
            elif [ -f DataPoblator.py ]; then
                python3 DataPoblator.py
            else
                err "No se encontró script de población (populate_tables.py / DataPoblator.py)"
                exit 1
            fi
        fi
    fi

    cd "$SCRIPT_DIR" || exit 1
}

# =====================================================
# DEPLOY SERVICES
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
echo "  1) 🏗️  Configurar Base de Datos"
echo "  2) 🚀 Desplegar Servicios"
echo "  3) 🗑️  Eliminar todo"
echo "══════════════════════════════════════"
read -r -p "Seleccione (1-3): " OPT

validate_env
configure_aws_account
setup_bucket

case $OPT in
    1)
        setup_database
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