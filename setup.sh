#!/bin/bash

# =====================================================
#   🚀 RIMAC HCKT – DEPLOY MANAGER (Optimized v2)
# =====================================================

export NODE_OPTIONS="--max-old-space-size=8192"

# ===== COLORS =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
ok() { echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"; }
err() { echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"; }
info() { echo -e "${CYAN}[$(date +'%H:%M:%S')] ℹ️  $1${NC}"; }

# =====================================================
#   BANNER
# =====================================================
echo ""
echo "═══════════════════════════════════════════════"
echo "         🏥 RIMAC HCKT – DEPLOY MANAGER        "
echo "═══════════════════════════════════════════════"
echo ""

# =====================================================
#   CHECK .env
# =====================================================
if [ ! -f .env ]; then
    err "No existe .env"
    info "Copia .env.example → .env"
    exit 1
fi
source .env
ok ".env cargado correctamente"

# =====================================================
#   VALIDAR VARIABLES DE ENTORNO
# =====================================================
validate_env() {
    log "Validando variables de entorno..."

    REQUIRED_VARS=("GEMINI_API_KEY" "TABLE_RECETAS" "TABLE_SERVICIOS" "TABLE_USUARIOS")
    MISSING=()

    for v in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!v}" ]; then
            MISSING+=("$v")
        fi
    done

    if [ ${#MISSING[@]} -gt 0 ]; then
        err "Faltan variables:"
        for m in "${MISSING[@]}"; do echo " - $m"; done
        exit 1
    fi

    ok "Variables validadas"
}

# =====================================================
#   CONFIGURAR AWS ACCOUNT ID
# =====================================================
configure_aws_account() {
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        warn "AWS_ACCOUNT_ID no configurado → obteniendo…"
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

        if [ -z "$AWS_ACCOUNT_ID" ]; then
            err "No se pudo obtener AWS_ACCOUNT_ID"
            exit 1
        fi

        echo "AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID" >> .env
        ok "AWS_ACCOUNT_ID configurado: $AWS_ACCOUNT_ID"
    else
        ok "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
    fi

    EXPECTED_BUCKET="recetas-medicas-data-${AWS_ACCOUNT_ID}"
    if [ "$S3_BUCKET_RECETAS" != "$EXPECTED_BUCKET" ]; then
        warn "Actualizando S3_BUCKET_RECETAS…"
        sed -i.bak '/^S3_BUCKET_RECETAS=/d' .env
        echo "S3_BUCKET_RECETAS=$EXPECTED_BUCKET" >> .env
        ok "S3_BUCKET_RECETAS actualizado: $EXPECTED_BUCKET"
    fi
}

# =====================================================
#   CREAR TABLAS + POBLAR
# =====================================================
setup_database() {
    echo ""
    echo "════════════ DATABASE SETUP (DynamoDB) ════════════"

    cd DataGenerator || exit 1

    pip install -r requirements.txt --quiet

    log "Creando tablas..."
    python3 create_tables.py || {
        err "Error creando tablas"
        exit 1
    }

    ok "Tablas listas"

    log "Revisando si existen datos en las tablas..."
    HAS_DATA=$(python3 check_tables.py)

    if [ "$HAS_DATA" = "YES" ]; then
        warn "Tablas tienen datos."
        read -p "¿Limpiar y poblar de nuevo? (s/n): " R
        [ "$R" = "s" ] && python3 DataPoblator.py
    else
        read -p "¿Poblar tablas con datos demo? (s/n): " R
        [ "$R" = "s" ] && python3 DataPoblator.py
    fi

    cd ..
}

# =====================================================
#   CONFIGURAR S3
# =====================================================
setup_s3() {
    echo ""
    echo "════════════ S3 SETUP ════════════"
    python3 DataGenerator/setup_s3.py || {
        err "Error en configuración S3"
        exit 1
    }
    ok "S3 configurado"
}

# =====================================================
#   DEPLOY SERVICIOS (OPTIMIZADO)
# =====================================================
deploy_services() {
    echo ""
    echo "════════════ DEPLOY SERVERLESS COMPOSE ════════════"

    # 🔹 No limpiar .serverless (evita recompilar Docker)
    log "Limpieza suave (solo pycache)..."
    find API-*/ -name "__pycache__" -exec rm -rf {} + 2>/dev/null

    # 🔹 Instalar dependencias solo si falta node_modules
    if [ ! -d node_modules ]; then
        warn "Instalando dependencias Serverless..."
        npm install --save-dev serverless-python-requirements
    fi

    ok "Entorno Node listo"

    # 🔹 Deploy Real Compose (rápido)
    serverless deploy --stage "${stage:-dev}" || {
        err "Falló el deploy"
        exit 1
    }

    ok "Servicios desplegados exitosamente 🚀"
}

# =====================================================
#   MENÚ
# =====================================================
echo ""
echo "══════════════════════════════════════"
echo "  📋 OPCIONES"
echo "══════════════════════════════════════"
echo "  1) 🏗️  Configurar Base de Datos"
echo "  2) 🚀 Desplegar Servicios"
echo "  3) 🗑️  Eliminar todo"
echo "══════════════════════════════════════"
read -p "Seleccione (1-3): " OPT

validate_env
configure_aws_account
setup_s3

case $OPT in
    1)
        setup_database
        ;;
    2)
        deploy_services
        ;;
    3)
        warn "Esta acción borrará los recursos..."
        read -p "¿Continuar? (s/n): " C
        [ "$C" = "s" ] && serverless compose remove
        ;;
    *)
        err "Opción inválida"
        exit 1
        ;;
esac

ok "✨ Operación completada"
