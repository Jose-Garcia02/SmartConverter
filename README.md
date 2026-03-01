# 🔄 Smart Converter

**Conversor multimedia y documental nativo para Linux/GNOME.**

Smart Converter convierte archivos de audio, video, imagen y documentos desde la terminal, una interfaz gráfica GTK4, o directamente desde el menú de clic derecho de Nautilus (Archivos de GNOME).

---

## ✨ Características

- **Audio:** MP3, WAV, OGG, FLAC, AAC, WMA, M4A, OPUS
- **Video:** MP4, MKV, AVI, WEBM, MOV, FLV, WMV, TS
- **Imágenes:** PNG, JPG, WEBP, GIF, BMP, TIFF, SVG, ICO
- **Documentos:** PDF, DOCX, ODT, XLSX, ODS, PPTX, ODP y más
- **Conversiones multihilo** — procesa múltiples archivos en paralelo
- **Interfaz CLI** con barras de progreso (`tqdm`)
- **Interfaz GUI** nativa GTK4/Adwaita que se integra con GNOME
- **Extensión de Nautilus** — clic derecho → "Convertir con SmartConverter"

## 📋 Requisitos

| Requisito | Versión mínima |
|---|---|
| Linux | Cualquier distro con GNOME (Fedora, Ubuntu, Arch, openSUSE...) |
| Python | >= 3.10 |
| FFmpeg | Cualquiera |
| ImageMagick | >= 7.x recomendado |
| LibreOffice | Cualquiera |
| GTK4 + libadwaita | Incluido en GNOME 42+ |

> El instalador se encarga de instalar las dependencias automáticamente.

---

## 🚀 Instalación

### Método rápido (recomendado)

```bash
git clone https://github.com/josegarcia/SmartConverter.git
cd SmartConverter
chmod +x install.sh
./install.sh
```

El instalador:

1. Detecta tu gestor de paquetes (dnf/apt/pacman/zypper)
2. Instala las dependencias del sistema (ffmpeg, imagemagick, libreoffice, etc.)
3. Crea un entorno virtual aislado con las librerías de Python
4. Registra el comando `smart-converter` en `~/.local/bin/`
5. Crea una entrada `.desktop` para el lanzador de GNOME
6. Configura la extensión de Nautilus para el clic derecho

### Verificar la instalación

```bash
smart-converter --help
```

---

## 🖥️ Uso

### Línea de comandos (CLI)

```bash
# Convertir un video a MP3
smart-converter --input video.mp4 --to mp3

# Convertir varias imágenes a WebP con modo verbose
smart-converter -i foto1.png foto2.jpg foto3.bmp -t webp -v

# Convertir un documento a PDF con 6 hilos
smart-converter --input informe.docx --to pdf --workers 6

# Convertir un PDF a Word
smart-converter --input documento.pdf --to docx
```

#### Opciones CLI

| Opción | Descripción |
|---|---|
| `-i`, `--input` | Archivos de entrada (acepta múltiples) |
| `-t`, `--to` | Formato de salida (ej: `mp3`, `pdf`, `webp`) |
| `-w`, `--workers` | Número de hilos simultáneos (por defecto: 4) |
| `-v`, `--verbose` | Mostrar información detallada |

### Interfaz gráfica (GUI)

```bash
# Abrir la GUI sin archivos (seleccionar desde el diálogo)
smart-converter --gui

# Abrir la GUI con archivos pre-seleccionados
smart-converter --gui --input archivo1.mp4 archivo2.png
```

También puedes abrir Smart Converter desde el **lanzador de aplicaciones de GNOME** buscando "Smart Converter".

### Clic derecho en Nautilus

1. Selecciona uno o más archivos en el gestor de archivos
2. Clic derecho → **"Convertir con SmartConverter"**
3. Elige el formato de salida en la ventana que aparece

> Tras la instalación, reinicia Nautilus con `nautilus -q` para activar la extensión.

---

## 📁 Estructura del proyecto

```
SmartConverter/
├── smart_converter/
│   ├── __init__.py
│   ├── main.py                    # Punto de entrada (CLI o GUI)
│   ├── core/
│   │   ├── media_engine.py        # FFmpeg + ImageMagick
│   │   ├── doc_engine.py          # LibreOffice + pdf2docx
│   │   └── orchestrator.py        # ThreadPool multihilo
│   ├── interfaces/
│   │   ├── cli.py                 # argparse + tqdm
│   │   └── gui_gtk.py             # GTK4/Adwaita
│   └── nautilus_ext/
│       └── SmartConverterExt.py   # Extensión de Nautilus
├── install.sh                     # Instalador automático
├── uninstall.sh                   # Desinstalador
├── pyproject.toml                 # Metadatos del paquete
├── requirements.txt               # Dependencias de Python
├── pyrightconfig.json             # Configuración del type checker
└── README.md
```

---

## 🔄 Formatos soportados

### Audio

| Entrada | Salidas posibles |
|---|---|
| MP3, WAV, OGG, FLAC, AAC, WMA, M4A, OPUS | Cualquiera de los otros formatos de audio |

### Video

| Entrada | Salidas posibles |
|---|---|
| MP4, MKV, AVI, WEBM, MOV, FLV, WMV, TS | Cualquiera de los otros formatos de video |

### Imágenes

| Entrada | Salidas posibles |
|---|---|
| PNG, JPG, JPEG, WEBP, GIF, BMP, TIFF, SVG, ICO | Cualquiera de los otros formatos de imagen |

### Documentos

| Entrada | Salidas posibles |
|---|---|
| DOC, DOCX, ODT | PDF, y otros formatos ofimáticos |
| XLS, XLSX, ODS | PDF, y otros formatos ofimáticos |
| PPT, PPTX, ODP | PDF, y otros formatos ofimáticos |
| PDF | DOCX |

---

## 🗑️ Desinstalación

```bash
cd SmartConverter
./uninstall.sh
```

Elimina la aplicación, el comando CLI, el acceso directo y la extensión de Nautilus. **No** desinstala las dependencias del sistema (ffmpeg, libreoffice, etc.) ya que podrían ser usadas por otros programas.

---

## 🛠️ Desarrollo

### Configurar entorno de desarrollo

```bash
git clone https://github.com/josegarcia/SmartConverter.git
cd SmartConverter
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
pip install PyGObject-stubs    # Stubs de tipo para GTK
```

### Ejecutar en modo desarrollo

```bash
# CLI
python -m smart_converter.main --input archivo.mp4 --to mp3

# GUI
python -m smart_converter.main --gui
```

### Type checking

El proyecto usa Pyright/Pylance en modo **strict**:

```bash
pip install pyright
pyright smart_converter/
```

---

## 🤝 Contribuir

1. Haz fork del repositorio
2. Crea una rama para tu feature: `git checkout -b mi-feature`
3. Haz commit de tus cambios: `git commit -m 'Añadir nueva feature'`
4. Push a la rama: `git push origin mi-feature`
5. Abre un Pull Request

---

## 📄 Licencia

Este proyecto está bajo la licencia [GPL-3.0](LICENSE).

---

## 🙏 Agradecimientos

Smart Converter se apoya en las siguientes herramientas de código abierto:

- [FFmpeg](https://ffmpeg.org/) — Conversión de audio y video
- [ImageMagick](https://imagemagick.org/) — Conversión de imágenes
- [LibreOffice](https://www.libreoffice.org/) — Conversión de documentos
- [pdf2docx](https://github.com/ArtifexSoftware/pdf2docx) — PDF a Word
- [GTK4](https://gtk.org/) / [libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) — Interfaz gráfica
- [tqdm](https://github.com/tqdm/tqdm) — Barras de progreso en terminal
