#!/usr/bin/env bash
# ============================================================================
# Smart Converter — Desinstalador
# ============================================================================
# Elimina todos los archivos instalados por install.sh.
# NO desinstala las dependencias del sistema (ffmpeg, libreoffice, etc.)
# ya que podrían ser usadas por otros programas.
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }

APP_NAME="smart-converter"
APP_ID="com.smartconverter.app"

INSTALL_DIR="$HOME/.local/share/smart-converter"
BIN_LINK="$HOME/.local/bin/$APP_NAME"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_ID.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/scalable/apps/$APP_ID.svg"
ICON_DIRS=(
    "$HOME/.local/share/icons/hicolor/256x256/apps"
    "$HOME/.local/share/icons/hicolor/128x128/apps"
    "$HOME/.local/share/icons/hicolor/64x64/apps"
    "$HOME/.local/share/icons/hicolor/48x48/apps"
    "$HOME/.local/share/icons/hicolor/scalable/apps"
)
NAUTILUS_EXT="$HOME/.local/share/nautilus-python/extensions/SmartConverterExt.py"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║      🗑️  Smart Converter — Desinstalador         ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "Se eliminarán los siguientes elementos:"
echo ""
[[ -d "$INSTALL_DIR" ]]  && echo "  📁 $INSTALL_DIR"
[[ -f "$BIN_LINK" ]]     && echo "  🔗 $BIN_LINK"
[[ -f "$DESKTOP_FILE" ]] && echo "  🖥️  $DESKTOP_FILE"
echo -n ""; for _d in "${ICON_DIRS[@]}"; do [[ -f "$_d/$APP_ID.png" || -f "$_d/$APP_ID.svg" ]] && echo "  🎨 Iconos en ~/.local/share/icons/" && break; done
[[ -f "$NAUTILUS_EXT" ]] && echo "  🐚 $NAUTILUS_EXT"
echo ""

read -rp "¿Confirmar desinstalación? [s/N] " resp
if [[ ! "$resp" =~ ^[sS]$ ]]; then
    info "Desinstalación cancelada."
    exit 0
fi

echo ""

# Eliminar archivos
if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    success "Directorio de instalación eliminado"
fi

if [[ -f "$BIN_LINK" ]]; then
    rm -f "$BIN_LINK"
    success "Comando CLI eliminado"
fi

if [[ -f "$DESKTOP_FILE" ]]; then
    rm -f "$DESKTOP_FILE"
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    success "Acceso directo de escritorio eliminado"
fi

if [[ -f "$ICON_FILE" ]]; then
    rm -f "$ICON_FILE"
fi
for _d in "${ICON_DIRS[@]}"; do
    rm -f "$_d/$APP_ID.png" "$_d/$APP_ID.svg" 2>/dev/null
done
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
success "Iconos eliminados"

if [[ -f "$NAUTILUS_EXT" ]]; then
    rm -f "$NAUTILUS_EXT"
    success "Extensión de Nautilus eliminada"
fi

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║    ✅  Smart Converter desinstalado por completo  ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${YELLOW}Nota:${NC} Las dependencias del sistema (ffmpeg, libreoffice, etc.)"
echo -e "  no se eliminaron porque podrían ser usadas por otros programas."
echo ""
