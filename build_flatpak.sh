#!/usr/bin/env bash
set -e

echo "📦 Building Flatpak package for Linux Bluefin..."

if ! command -v flatpak-builder &> /dev/null; then
    echo "⚠️ flatpak-builder not found. Installing runtime SDK..."
    flatpak install --user -y flathub org.gnome.Platform//46 org.gnome.Sdk//46 || true
fi

echo "🔨 Executing flatpak-builder..."
flatpak-builder --user --install --force-clean build-flatpak io.github.bluefin.SimpleJavaEditor.yml

echo ""
echo "🎉 Flatpak installed successfully on Linux Bluefin!"
echo "✨ BlueJava Studio is now registered in Bazaar / GNOME Software!"
