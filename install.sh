#!/usr/bin/env bash
# ============================================================================
# Smart Converter — Instalador para Linux
# ============================================================================
# Instala la aplicación, dependencias del sistema, extensión de Nautilus,
# comando CLI y acceso directo de escritorio (.desktop).
#
# Uso:
#   chmod +x install.sh
#   ./install.sh
#
# Para desinstalar:
#   ./uninstall.sh
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colores y utilidades
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------------------------------------------------------------------------
# Variables de instalación
# ---------------------------------------------------------------------------
APP_NAME="smart-converter"
APP_DISPLAY_NAME="Smart Converter"
APP_ID="com.smartconverter.app"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/smart-converter"
VENV_DIR="$INSTALL_DIR/.venv"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
ICON_DIR_128="$HOME/.local/share/icons/hicolor/128x128/apps"
ICON_DIR_256="$HOME/.local/share/icons/hicolor/256x256/apps"
ICON_DIR_64="$HOME/.local/share/icons/hicolor/64x64/apps"
ICON_DIR_48="$HOME/.local/share/icons/hicolor/48x48/apps"
NAUTILUS_EXT_DIR="$HOME/.local/share/nautilus-python/extensions"

# ---------------------------------------------------------------------------
# Detección de distro y gestor de paquetes
# ---------------------------------------------------------------------------
detect_package_manager() {
    if command -v dnf &>/dev/null; then
        PKG_MGR="dnf"
        PKG_INSTALL="sudo dnf install -y"
    elif command -v apt &>/dev/null; then
        PKG_MGR="apt"
        PKG_INSTALL="sudo apt install -y"
    elif command -v pacman &>/dev/null; then
        PKG_MGR="pacman"
        PKG_INSTALL="sudo pacman -S --noconfirm"
    elif command -v zypper &>/dev/null; then
        PKG_MGR="zypper"
        PKG_INSTALL="sudo zypper install -y"
    else
        PKG_MGR="unknown"
        PKG_INSTALL=""
    fi
}

# ---------------------------------------------------------------------------
# Mapa de paquetes por distro
# ---------------------------------------------------------------------------
get_system_packages() {
    case "$PKG_MGR" in
        dnf)
            echo "ffmpeg ImageMagick libreoffice nautilus-python python3-gobject gtk4 libadwaita"
            ;;
        apt)
            echo "ffmpeg imagemagick libreoffice nautilus-python python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-venv"
            ;;
        pacman)
            echo "ffmpeg imagemagick libreoffice-fresh python-nautilus python-gobject gtk4 libadwaita"
            ;;
        zypper)
            echo "ffmpeg ImageMagick libreoffice nautilus-python python3-gobject gtk4 libadwaita"
            ;;
        *)
            echo ""
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Cabecera
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        🔄  Smart Converter — Instalador         ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ---------------------------------------------------------------------------
# 1. Verificar Python >= 3.10
# ---------------------------------------------------------------------------
info "Verificando Python..."

if ! command -v python3 &>/dev/null; then
    error "Python 3 no encontrado. Instálalo antes de continuar."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if (( PYTHON_MAJOR < 3 || (PYTHON_MAJOR == 3 && PYTHON_MINOR < 10) )); then
    error "Se requiere Python >= 3.10. Versión actual: $PYTHON_VERSION"
    exit 1
fi
success "Python $PYTHON_VERSION"

# ---------------------------------------------------------------------------
# 2. Dependencias del sistema
# ---------------------------------------------------------------------------
info "Detectando gestor de paquetes..."
detect_package_manager

if [[ "$PKG_MGR" == "unknown" ]]; then
    warn "No se detectó un gestor de paquetes conocido (dnf/apt/pacman/zypper)."
    warn "Asegúrate de tener instalados: ffmpeg, imagemagick, libreoffice,"
    warn "nautilus-python, python3-gobject, gtk4 y libadwaita."
    echo ""
    read -rp "¿Continuar de todas formas? [s/N] " resp
    [[ "$resp" =~ ^[sS]$ ]] || exit 0
else
    success "Gestor de paquetes: $PKG_MGR"
    PACKAGES=$(get_system_packages)
    info "Instalando dependencias del sistema..."
    info "Paquetes: $PACKAGES"
    echo ""
    # shellcheck disable=SC2086
    $PKG_INSTALL $PACKAGES || {
        warn "Algunos paquetes pueden no haberse instalado."
        warn "Verifica manualmente que ffmpeg, imagemagick, libreoffice,"
        warn "nautilus-python, python3-gobject y gtk4 estén disponibles."
    }
    echo ""
fi

# Verificar herramientas clave
MISSING_TOOLS=()
command -v ffmpeg   &>/dev/null || MISSING_TOOLS+=("ffmpeg")
command -v magick   &>/dev/null || command -v convert &>/dev/null || MISSING_TOOLS+=("imagemagick")
command -v soffice  &>/dev/null || MISSING_TOOLS+=("libreoffice")

if (( ${#MISSING_TOOLS[@]} > 0 )); then
    warn "Herramientas no encontradas: ${MISSING_TOOLS[*]}"
    warn "Algunas conversiones no funcionarán hasta instalarlas."
else
    success "FFmpeg, ImageMagick y LibreOffice verificados"
fi

# ---------------------------------------------------------------------------
# 3. Copiar archivos de la aplicación
# ---------------------------------------------------------------------------
info "Instalando Smart Converter en $INSTALL_DIR..."

mkdir -p "$INSTALL_DIR"

# Copiar el paquete Python y archivos de proyecto
rsync -a --delete \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='Hoja_de_ruta.md' \
    "$SCRIPT_DIR/smart_converter" \
    "$SCRIPT_DIR/assets" \
    "$SCRIPT_DIR/pyproject.toml" \
    "$SCRIPT_DIR/requirements.txt" \
    "$INSTALL_DIR/"

success "Archivos copiados"

# ---------------------------------------------------------------------------
# 4. Crear entorno virtual e instalar dependencias de Python
# ---------------------------------------------------------------------------
info "Configurando entorno virtual..."

python3 -m venv "$VENV_DIR" --system-site-packages

info "Instalando dependencias de Python..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip setuptools wheel 2>/dev/null || true
"$VENV_DIR/bin/pip" install --quiet pdf2docx tqdm

# Instalar el propio paquete smart_converter en el venv (silencioso)
# Si falla (ej: Python 3.14 + setuptools incompatible), el launcher
# usa PYTHONPATH como alternativa — la app funciona igualmente.
if "$VENV_DIR/bin/pip" install --quiet "$INSTALL_DIR" 2>/dev/null; then
    success "Paquete smart_converter instalado en el venv"
else
    info "Usando PYTHONPATH como mecanismo de carga (compatible con Python 3.14+)"
fi

# Verificar imports
"$VENV_DIR/bin/python" -c "from smart_converter.core import MediaEngine, DocEngine, Orchestrator; from tqdm import tqdm" 2>/dev/null \
    && success "Todas las dependencias verificadas" \
    || warn "Algunas dependencias no se instalaron correctamente"

# ---------------------------------------------------------------------------
# 5. Crear lanzador CLI (~/.local/bin/smart-converter)
# ---------------------------------------------------------------------------
info "Creando comando CLI..."

mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/$APP_NAME" << 'LAUNCHER_EOF'
#!/usr/bin/env bash
# Smart Converter — Lanzador CLI/GUI
INSTALL_DIR="$HOME/.local/share/smart-converter"
export PYTHONPATH="$INSTALL_DIR${PYTHONPATH:+:$PYTHONPATH}"
exec "$INSTALL_DIR/.venv/bin/python" -m smart_converter.main "$@"
LAUNCHER_EOF

chmod +x "$BIN_DIR/$APP_NAME"
success "Comando 'smart-converter' disponible en $BIN_DIR"

# Verificar que ~/.local/bin esté en PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "$BIN_DIR no está en tu PATH."
    warn "Añade esto a tu ~/.bashrc o ~/.zshrc:"
    echo -e "  ${BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
fi

# ---------------------------------------------------------------------------
# 6. Instalar iconos
# ---------------------------------------------------------------------------
info "Instalando iconos..."

# Instalar iconos PNG del proyecto en el tema de iconos del sistema
_icon_installed=0

if [[ -f "$SCRIPT_DIR/assets/icon-256.png" ]]; then
    mkdir -p "$ICON_DIR_256"
    cp "$SCRIPT_DIR/assets/icon-256.png" "$ICON_DIR_256/$APP_ID.png"
    _icon_installed=1
fi
if [[ -f "$SCRIPT_DIR/assets/icon-128.png" ]]; then
    mkdir -p "$ICON_DIR_128"
    cp "$SCRIPT_DIR/assets/icon-128.png" "$ICON_DIR_128/$APP_ID.png"
    _icon_installed=1
fi
if [[ -f "$SCRIPT_DIR/assets/icon-64.png" ]]; then
    mkdir -p "$ICON_DIR_64"
    cp "$SCRIPT_DIR/assets/icon-64.png" "$ICON_DIR_64/$APP_ID.png"
    _icon_installed=1
fi
if [[ -f "$SCRIPT_DIR/assets/icon-48.png" ]]; then
    mkdir -p "$ICON_DIR_48"
    cp "$SCRIPT_DIR/assets/icon-48.png" "$ICON_DIR_48/$APP_ID.png"
    _icon_installed=1
fi

# Fallback: generar un SVG si no hay PNGs disponibles
if (( _icon_installed == 0 )); then
    mkdir -p "$ICON_DIR"
    cat > "$ICON_DIR/$APP_ID.svg" << 'SVG_EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#3584e4"/>
      <stop offset="100%" style="stop-color:#1c71d8"/>
    </linearGradient>
  </defs>
  <rect width="128" height="128" rx="16" fill="url(#bg)"/>
  <g fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
    <rect x="20" y="30" width="36" height="46" rx="4" fill="#fff" fill-opacity="0.2"/>
    <line x1="28" y1="42" x2="48" y2="42"/>
    <line x1="28" y1="50" x2="48" y2="50"/>
    <line x1="28" y1="58" x2="40" y2="58"/>
    <line x1="62" y1="53" x2="78" y2="53"/>
    <polyline points="72,47 78,53 72,59"/>
    <rect x="84" y="30" width="36" height="46" rx="4" fill="#fff" fill-opacity="0.2"/>
    <line x1="92" y1="42" x2="112" y2="42"/>
    <line x1="92" y1="50" x2="112" y2="50"/>
    <line x1="92" y1="58" x2="104" y2="58"/>
  </g>
  <text x="64" y="100" text-anchor="middle" font-family="sans-serif" font-size="12" font-weight="bold" fill="#fff">CONVERTER</text>
</svg>
SVG_EOF
fi

# Actualizar caché de iconos
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

success "Iconos instalados"

# ---------------------------------------------------------------------------
# 7. Crear entrada de escritorio (.desktop)
# ---------------------------------------------------------------------------
info "Creando acceso directo de escritorio..."

mkdir -p "$DESKTOP_DIR"

# Determinar ruta absoluta del icono para el .desktop
# (Usar ruta absoluta es más compatible con tiling WMs como niri)
_DESKTOP_ICON="$APP_ID"
for _sz in 256 128 64 48; do
    _icon_path="$HOME/.local/share/icons/hicolor/${_sz}x${_sz}/apps/$APP_ID.png"
    if [[ -f "$_icon_path" ]]; then
        _DESKTOP_ICON="$_icon_path"
        break
    fi
done

cat > "$DESKTOP_DIR/$APP_ID.desktop" << EOF
[Desktop Entry]
Type=Application
Name=$APP_DISPLAY_NAME
Comment=Convierte archivos multimedia y documentos fácilmente
Exec=$BIN_DIR/$APP_NAME --gui %F
Icon=$_DESKTOP_ICON
Terminal=false
Categories=Utility;GTK;
Keywords=converter;ffmpeg;imagemagick;pdf;video;audio;image;
MimeType=audio/mpeg;audio/ogg;audio/flac;audio/wav;video/mp4;video/x-matroska;video/webm;video/avi;image/png;image/jpeg;image/webp;image/gif;application/pdf;application/vnd.openxmlformats-officedocument.wordprocessingml.document;application/vnd.oasis.opendocument.text;
StartupNotify=true
EOF

# Validar el archivo .desktop si desktop-file-validate está disponible
if command -v desktop-file-validate &>/dev/null; then
    desktop-file-validate "$DESKTOP_DIR/$APP_ID.desktop" 2>/dev/null \
        && success "Archivo .desktop válido" \
        || warn "El archivo .desktop tiene advertencias menores (no afecta funcionamiento)"
else
    success "Archivo .desktop creado"
fi

# Actualizar base de datos de escritorio
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# ---------------------------------------------------------------------------
# 8. Instalar extensión de Nautilus
# ---------------------------------------------------------------------------
info "Configurando extensión de Nautilus..."

mkdir -p "$NAUTILUS_EXT_DIR"

# Copiar directamente la extensión (no usar wrapper importlib — causa problemas
# con el contexto de gi.repository en nautilus-python)
cp "$INSTALL_DIR/smart_converter/nautilus_ext/SmartConverterExt.py" \
    "$NAUTILUS_EXT_DIR/SmartConverterExt.py"

success "Extensión de Nautilus configurada"
info "Reinicia Nautilus para activarla: ${BOLD}nautilus -q${NC}"

# ---------------------------------------------------------------------------
# 9. Resumen final
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       ✅  Instalación completada con éxito       ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Directorio:${NC}     $INSTALL_DIR"
echo -e "  ${BOLD}Comando CLI:${NC}    smart-converter --input archivo.mp4 --to mp3"
echo -e "  ${BOLD}Modo GUI:${NC}       smart-converter --gui"
echo -e "  ${BOLD}Escritorio:${NC}     Buscar '${APP_DISPLAY_NAME}' en el lanzador"
echo -e "  ${BOLD}Clic derecho:${NC}   Reiniciar Nautilus → clic derecho sobre archivos"
echo ""
echo -e "  Para desinstalar: ${BOLD}./uninstall.sh${NC}"
echo ""
