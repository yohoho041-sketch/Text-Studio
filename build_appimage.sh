#!/usr/bin/env bash
set -e

APP_NAME="TextStudio"
BUILD_DIR="build/AppDir"

echo "🔨 Building AppImage for Text Studio..."

# Clear previous build
rm -rf build
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/lib/java-studio"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/512x512/apps"

# Copy source code and assets
cp -r src "$BUILD_DIR/usr/lib/java-studio/"
cp java_studio.py "$BUILD_DIR/usr/lib/java-studio/"

if [ -f java-studio.png ]; then
    cp java-studio.png "$BUILD_DIR/usr/share/icons/hicolor/512x512/apps/io.github.bluefin.SimpleJavaEditor.png"
    cp java-studio.png "$BUILD_DIR/io.github.bluefin.SimpleJavaEditor.png"
fi

# Create Desktop Entry inside AppDir matching App ID
cat << 'EOF' > "$BUILD_DIR/io.github.bluefin.SimpleJavaEditor.desktop"
[Desktop Entry]
Name=Text Studio
GenericName=Text Editor
Comment=Simple, native GTK4 text editor for Linux Bluefin
Exec=java-studio %F
Icon=io.github.bluefin.SimpleJavaEditor
Terminal=false
Type=Application
Categories=Development;TextEditor;Utility;
MimeType=text/plain;text/x-java;
EOF

cp "$BUILD_DIR/io.github.bluefin.SimpleJavaEditor.desktop" "$BUILD_DIR/usr/share/applications/"

# Create usr/bin/java-studio wrapper
cat << 'EOF' > "$BUILD_DIR/usr/bin/java-studio"
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
PYTHONPATH="$HERE/../lib/java-studio:$PYTHONPATH" exec python3 "$HERE/../lib/java-studio/java_studio.py" "$@"
EOF
chmod +x "$BUILD_DIR/usr/bin/java-studio"

# Create AppRun entry point script
cat << 'EOF' > "$BUILD_DIR/AppRun"
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:$PATH"
export PYTHONPATH="$HERE/usr/lib/java-studio:$PYTHONPATH"
exec python3 "$HERE/usr/lib/java-studio/java_studio.py" "$@"
EOF
chmod +x "$BUILD_DIR/AppRun"

# Ensure appimagetool is ready
APPIMAGETOOL="/tmp/appimagetool"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "Downloading appimagetool..."
    curl -sL https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -o "$APPIMAGETOOL"
    chmod +x "$APPIMAGETOOL"
fi

# Build AppImage using appimagetool
echo "📦 Packaging AppImage..."
ARCH=x86_64 "$APPIMAGETOOL" --no-appstream "$BUILD_DIR" "${APP_NAME}-x86_64.AppImage"

echo "🎉 AppImage built successfully: $(pwd)/${APP_NAME}-x86_64.AppImage"
chmod +x "${APP_NAME}-x86_64.AppImage"
