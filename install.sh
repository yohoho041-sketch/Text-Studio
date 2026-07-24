#!/usr/bin/env bash
set -e

INSTALL_BIN_DIR="$HOME/.local/bin"
INSTALL_APP_DIR="$HOME/.local/share/applications"
INSTALL_ICON_DIR="$HOME/.local/share/icons/hicolor/512x512/apps"
INSTALL_LIB_DIR="$HOME/.local/share/text-studio"

echo "🚀 Installing Text Studio on Linux Bluefin..."

mkdir -p "$INSTALL_BIN_DIR"
mkdir -p "$INSTALL_APP_DIR"
mkdir -p "$INSTALL_ICON_DIR"
mkdir -p "$INSTALL_LIB_DIR"

# If executed via curl | bash, create a temporary directory and clone the repo
if [ ! -d "src" ]; then
    TMP_DIR=$(mktemp -d)
    echo "📦 Fetching latest files from GitHub..."
    git clone --depth 1 https://github.com/yohoho041-sketch/Text-Studio.git "$TMP_DIR/Text-Studio"
    cd "$TMP_DIR/Text-Studio"
fi

# Copy source files
cp -r src "$INSTALL_LIB_DIR/"
cp java_studio.py "$INSTALL_LIB_DIR/"

# Copy custom user icon to library folder and system icon path
if [ -f java-studio.png ]; then
    cp java-studio.png "$INSTALL_LIB_DIR/io.github.yohoho041_sketch.TextStudio.png"
    cp java-studio.png "$INSTALL_ICON_DIR/io.github.yohoho041_sketch.TextStudio.png"
fi

# Create binary launcher
cat << EOF > "$INSTALL_BIN_DIR/java-studio"
#!/usr/bin/env bash
PYTHONPATH="$INSTALL_LIB_DIR:\$PYTHONPATH" exec python3 "$INSTALL_LIB_DIR/java_studio.py" "\$@"
EOF
chmod +x "$INSTALL_BIN_DIR/java-studio"

# Create Desktop Launcher Shortcut using absolute path to the icon for instant GNOME reloading
cat << EOF > "$INSTALL_APP_DIR/io.github.yohoho041_sketch.TextStudio.desktop"
[Desktop Entry]
Name=Text Studio
GenericName=Text Editor
Comment=Simple, native GTK4 text editor for Linux Bluefin
Exec=$INSTALL_BIN_DIR/java-studio %F
Icon=$INSTALL_LIB_DIR/io.github.yohoho041_sketch.TextStudio.png
Terminal=false
Type=Application
Categories=Development;TextEditor;Utility;
MimeType=text/plain;text/x-java;
EOF

# Update desktop and icon databases
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$INSTALL_APP_DIR" || true
fi
if command -v gtk4-update-icon-cache &> /dev/null; then
    gtk4-update-icon-cache "$HOME/.local/share/icons/hicolor" || true
elif command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" || true
fi

echo "✅ Text Studio has been installed successfully!"
echo "📍 Launcher binary: $INSTALL_BIN_DIR/java-studio"
echo "🖥️ Desktop shortcut added to App Launcher menu!"
echo "✨ You can launch it by running 'java-studio' or from your application menu."

