# Text Studio

**Text Studio** is a clean, ultra-fast GTK 4 and Libadwaita text editor specially created for Java coding on Linux Bluefin, Fedora, and all modern Linux distributions.

![Text Studio](assets/text-studio.svg)

---

## Features

- **Multi-Tab Editing**: Open and edit multiple Java files simultaneously with clean GTK 4 tab management.
- **Distraction-Free Mode**: Fullscreen mode (F11) for deep coding focus.
- **Java Syntax & Bracket Highlighting**: Vibrant bracket matching and syntax support designed specifically for Java files.
- **Native Adwaita Dark / Light Themes**: Automatically respects your system appearance preference.
- **Folder Navigation Sidebar**: Single-click file navigation for your Java project folders.
- **Fast Search & Line Navigation**: Quick text search (Ctrl+F) and line jumper (Ctrl+L).

---

## Quick 1-Command Installation

You can install **Text Studio** on any Linux distribution (Bluefin, Fedora, Ubuntu, Arch, etc.) by running this single command in your terminal:

```bash
curl -sSL https://raw.githubusercontent.com/yohoho041-sketch/Text-Studio/main/install.sh | bash
```

---

## Alternative Installation Methods

### Method 1: Git Clone & Install

```bash
git clone https://github.com/yohoho041-sketch/Text-Studio.git
cd Text-Studio
./install.sh
```

### Method 2: Local Flatpak Build

```bash
git clone https://github.com/yohoho041-sketch/Text-Studio.git
cd Text-Studio
flatpak-builder --user --install --force-clean build-dir io.github.yohoho041_sketch.TextStudio.yml
```

---

## How to Uninstall

To cleanly remove **Text Studio** from your system:

```bash
rm -rf ~/.local/share/text-studio
rm -f ~/.local/bin/text-studio
rm -f ~/.local/share/applications/io.github.yohoho041_sketch.TextStudio.desktop
rm -f ~/.local/share/icons/hicolor/512x512/apps/io.github.yohoho041_sketch.TextStudio.png
```

---

## License

This project is licensed under the [MIT License](LICENSE).
