import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, Gdk, GtkSource, GLib, Pango

class SimpleJavaEditor(Gtk.Box):
    """Clean Java Text Editor tab view with smart auto-closing braces for Java files."""

    def __init__(self, file_path=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_vexpand(True)
        self.set_hexpand(True)

        self.file_path = file_path
        self.is_dirty = False
        self.on_dirty_changed_cb = None
        self.on_cursor_moved_cb = None

        # GtkSource Buffer & Language
        self.buffer = GtkSource.Buffer()
        self.scheme_mgr = GtkSource.StyleSchemeManager.get_default()
        self._ensure_custom_themes()

        # GtkSource Search Context setup
        self.search_settings = GtkSource.SearchSettings()
        self.search_settings.set_case_sensitive(False)
        self.search_context = GtkSource.SearchContext.new(self.buffer, self.search_settings)
        self.search_context.set_highlight(True)

        self.current_theme = 'adwaita-dark-custom'
        self.set_theme(self.current_theme)

        self.buffer.connect("changed", self._on_buffer_changed)
        self.buffer.connect("notify::cursor-position", self._on_cursor_moved)

        # GtkSource View
        self.view = GtkSource.View.new_with_buffer(self.buffer)
        self.view.set_show_line_numbers(True)
        self.view.set_highlight_current_line(True)
        self.view.set_auto_indent(True)
        self.view.set_tab_width(4)
        self.view.set_insert_spaces_instead_of_tabs(True)
        self.view.set_monospace(True)
        self.view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.view.set_vexpand(True)
        self.view.set_hexpand(True)

        # Keyboard Controller for Java Auto-Closing Braces
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.view.add_controller(key_ctrl)

        # Font provider & Bracket Match CSS styling
        self.font_size = 12
        self.css_provider = Gtk.CssProvider()
        self.view.get_style_context().add_provider(
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.update_font_size(self.font_size)

        # Scrolled Window container
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_child(self.view)
        self.append(scrolled)

        if file_path and os.path.exists(file_path):
            self.open_file(file_path)
        else:
            self.new_file()

    def is_java_file(self):
        """Check if current file is a Java file."""
        if self.file_path:
            return self.file_path.endswith('.java')
        lang = self.buffer.get_language()
        return lang and lang.get_id() == 'java'

    def _is_inside_string(self):
        """Check if cursor is inside a string literal on current line."""
        iter_pos = self.buffer.get_iter_at_offset(self.buffer.get_property("cursor-position"))
        line_start = iter_pos.copy()
        line_start.set_line_offset(0)
        line_text = self.buffer.get_text(line_start, iter_pos, True)

        quotes = 0
        i = 0
        while i < len(line_text):
            if line_text[i] == '"' and (i == 0 or line_text[i-1] != '\\'):
                quotes += 1
            i += 1
        return (quotes % 2) != 0

    def is_programming_file(self):
        """Check if current file is a programming language file."""
        return self.buffer.get_language() is not None

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if self.is_programming_file():
            # Auto-close brackets/parentheses/braces only if outside string literals
            if keyval in (Gdk.KEY_braceleft, Gdk.KEY_parenleft, Gdk.KEY_bracketleft):
                if not self._is_inside_string():
                    pair = ""
                    if keyval == Gdk.KEY_braceleft:
                        pair = "{}"
                    elif keyval == Gdk.KEY_parenleft:
                        pair = "()"
                    elif keyval == Gdk.KEY_bracketleft:
                        pair = "[]"
                    
                    self.buffer.insert_at_cursor(pair)
                    offset = self.buffer.get_property("cursor-position") - 1
                    iter_pos = self.buffer.get_iter_at_offset(offset)
                    self.buffer.place_cursor(iter_pos)
                    return True

            # Skip closing bracket/parenthesis/brace if typed when cursor is right before it
            elif keyval in (Gdk.KEY_braceright, Gdk.KEY_parenright, Gdk.KEY_bracketright):
                expected_char = ""
                if keyval == Gdk.KEY_braceright:
                    expected_char = "}"
                elif keyval == Gdk.KEY_parenright:
                    expected_char = ")"
                elif keyval == Gdk.KEY_bracketright:
                    expected_char = "]"
                
                cursor_offset = self.buffer.get_property("cursor-position")
                iter_pos = self.buffer.get_iter_at_offset(cursor_offset)
                next_iter = iter_pos.copy()
                next_iter.forward_char()
                next_char = self.buffer.get_text(iter_pos, next_iter, True)
                if next_char == expected_char:
                    self.buffer.place_cursor(next_iter)
                    return True

            # Auto-close and skip quotes
            elif keyval in (Gdk.KEY_quotedbl, Gdk.KEY_apostrophe):
                char = '"' if keyval == Gdk.KEY_quotedbl else "'"
                cursor_offset = self.buffer.get_property("cursor-position")
                curr_iter = self.buffer.get_iter_at_offset(cursor_offset)
                
                # Check for typeover: if the next character is the same quote, just step over it
                next_iter = curr_iter.copy()
                next_iter.forward_char()
                next_char = self.buffer.get_text(curr_iter, next_iter, True)
                if next_char == char:
                    self.buffer.place_cursor(next_iter)
                    return True
                
                # Auto-close if character before is not alphanumeric/backslash
                should_autoclose = True
                if cursor_offset > 0:
                    prev_iter = self.buffer.get_iter_at_offset(cursor_offset - 1)
                    prev_char = self.buffer.get_text(prev_iter, curr_iter, True)
                    if prev_char.isalnum() or prev_char in ('_', '\\'):
                        should_autoclose = False
                
                if should_autoclose:
                    self.buffer.insert_at_cursor(char + char)
                    offset = self.buffer.get_property("cursor-position") - 1
                    iter_pos = self.buffer.get_iter_at_offset(offset)
                    self.buffer.place_cursor(iter_pos)
                    return True

            # Split braces and auto-indent when Enter is pressed between { and }
            elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                cursor_offset = self.buffer.get_property("cursor-position")
                if cursor_offset > 0:
                    prev_iter = self.buffer.get_iter_at_offset(cursor_offset - 1)
                    curr_iter = self.buffer.get_iter_at_offset(cursor_offset)
                    next_iter = curr_iter.copy()
                    next_iter.forward_char()
                    
                    prev_char = self.buffer.get_text(prev_iter, curr_iter, True)
                    next_char = self.buffer.get_text(curr_iter, next_iter, True)
                    
                    if prev_char == "{" and next_char == "}":
                        # Get current line indentation
                        line_start = curr_iter.copy()
                        line_start.set_line_offset(0)
                        line_text = self.buffer.get_text(line_start, curr_iter, True)
                        
                        indent = ""
                        for char in line_text:
                            if char in (' ', '\t'):
                                indent += char
                            else:
                                break
                        
                        self.buffer.begin_user_action()
                        self.buffer.insert_at_cursor("\n" + indent + "    \n" + indent)
                        target_offset = cursor_offset + 1 + len(indent) + 4
                        target_iter = self.buffer.get_iter_at_offset(target_offset)
                        self.buffer.place_cursor(target_iter)
                        self.buffer.end_user_action()
                        return True
        return False

    def search_text(self, text):
        self.search_settings.set_search_text(text if text else None)
        if text:
            self.find_next()

    def find_next(self):
        sel = self.buffer.get_selection_bounds()
        if sel:
            search_from = sel[1]
        else:
            search_from = self.buffer.get_iter_at_offset(self.buffer.get_property("cursor-position"))

        res = self.search_context.forward(search_from)
        if not res or not res[0]:
            res = self.search_context.forward(self.buffer.get_start_iter())

        if res and res[0]:
            match_start, match_end = res[1], res[2]
            self.buffer.select_range(match_start, match_end)
            self.view.scroll_to_iter(match_start, 0.1, False, 0.0, 0.5)

    def find_previous(self):
        sel = self.buffer.get_selection_bounds()
        if sel:
            search_from = sel[0]
        else:
            search_from = self.buffer.get_iter_at_offset(self.buffer.get_property("cursor-position"))

        res = self.search_context.backward(search_from)
        if not res or not res[0]:
            res = self.search_context.backward(self.buffer.get_end_iter())

        if res and res[0]:
            match_start, match_end = res[1], res[2]
            self.buffer.select_range(match_start, match_end)
            self.view.scroll_to_iter(match_start, 0.1, False, 0.0, 0.5)

    def set_theme(self, theme_id):
        if theme_id == 'Adwaita-dark':
            theme_id = 'adwaita-dark-custom'
        elif theme_id == 'Adwaita':
            theme_id = 'adwaita-custom'

        self.current_theme = theme_id
        def apply_scheme():
            scheme = self.scheme_mgr.get_scheme(theme_id)
            if not scheme:
                scheme = self.scheme_mgr.get_scheme('adwaita-dark-custom') or self.scheme_mgr.get_scheme('classic')
            if scheme:
                self.buffer.set_style_scheme(scheme)
            self.update_font_size(self.font_size)
            return GLib.SOURCE_REMOVE

        GLib.idle_add(apply_scheme)

    def _ensure_custom_themes(self):
        styles_dir = os.path.expanduser("~/.local/share/gtksourceview-5/styles")
        os.makedirs(styles_dir, exist_ok=True)
        
        dark_custom = os.path.join(styles_dir, "adwaita-dark-custom.xml")
        light_custom = os.path.join(styles_dir, "adwaita-custom.xml")
        
        # Write dark theme
        xml_dark = """<?xml version="1.0" encoding="UTF-8"?>
<style-scheme id="adwaita-dark-custom" name="Adwaita Dark (Custom)" version="1.0" parent-scheme="Adwaita-dark">
  <author>Text Studio</author>
  <description>Adwaita Dark with VS Code style bracket matching</description>
  <style name="bracket-match" background="#3d3d3d"/>
  <style name="bracket-mismatch" background="#7f1d1d" bold="true"/>
</style-scheme>
"""
        try:
            with open(dark_custom, "w", encoding="utf-8") as f:
                f.write(xml_dark)
        except Exception as e:
            print(f"Error writing dark custom scheme: {e}")

        # Write light theme
        xml_light = """<?xml version="1.0" encoding="UTF-8"?>
<style-scheme id="adwaita-custom" name="Adwaita Light (Custom)" version="1.0" parent-scheme="Adwaita">
  <author>Text Studio</author>
  <description>Adwaita Light with VS Code style bracket matching</description>
  <style name="bracket-match" background="#dbdbdb"/>
  <style name="bracket-mismatch" background="#fee2e2" bold="true"/>
</style-scheme>
"""
        try:
            with open(light_custom, "w", encoding="utf-8") as f:
                f.write(xml_light)
        except Exception as e:
            print(f"Error writing light custom scheme: {e}")
        
        self.scheme_mgr.force_rescan()

    def get_available_themes(self):
        return [
            ("adwaita-dark-custom", "Adwaita Dark"),
            ("adwaita-custom", "Adwaita Light")
        ]

    def update_font_size(self, size):
        self.font_size = max(8, min(32, size))

        css = f"""
        textview {{
            font-family: monospace;
            font-size: {self.font_size}pt;
        }}
        """.encode('utf-8')
        self.css_provider.load_from_data(css)

    def goto_line(self, line_num):
        line_num = max(1, line_num) - 1
        iter_pos = self.buffer.get_iter_at_line(line_num)
        self.buffer.place_cursor(iter_pos)
        self.view.scroll_to_iter(iter_pos, 0.1, False, 0.0, 0.5)

    def get_cursor_pos(self):
        iter_pos = self.buffer.get_iter_at_offset(self.buffer.get_property("cursor-position"))
        line = iter_pos.get_line() + 1
        col = iter_pos.get_line_offset() + 1
        return line, col

    def configure_editor_features(self):
        """Configure editor features (line numbers, highlighting, auto-indent) based on file type."""
        is_prog = False
        lang = None

        if self.file_path:
            filename = os.path.basename(self.file_path)
            _, ext = os.path.splitext(filename)
            ext = ext.lower().lstrip('.')

            # Treat common text/documentation/config files as plain text (Notepad-style)
            if ext in ('txt', 'text', 'log', 'md', 'markdown', 'rst', 'csv', 'tsv', ''):
                is_prog = False
            else:
                lang_mgr = GtkSource.LanguageManager.get_default()
                # Guess language based on filename
                lang = lang_mgr.guess_language(filename, None)
                if lang:
                    lang_id = lang.get_id()
                    # Skip common markup/text formats that shouldn't have IDE features
                    if lang_id in ('markdown', 'rst', 'todotxt', 'changelog', 'gdb-log', 'logcat', 'def', 'csv'):
                        is_prog = False
                    else:
                        is_prog = True
                else:
                    is_prog = False
        else:
            is_prog = False

        if is_prog:
            if lang:
                self.buffer.set_language(lang)
            self.buffer.set_highlight_syntax(True)
            self.buffer.set_highlight_matching_brackets(True)
            self.view.set_show_line_numbers(True)
            self.view.set_highlight_current_line(True)
            self.view.set_auto_indent(True)
        else:
            self.buffer.set_language(None)
            self.buffer.set_highlight_syntax(False)
            self.buffer.set_highlight_matching_brackets(False)
            self.view.set_show_line_numbers(False)
            self.view.set_highlight_current_line(False)
            self.view.set_auto_indent(False)

    def new_file(self):
        self.buffer.set_text("")
        self.file_path = None
        self.set_dirty(False)
        self.configure_editor_features()

    def open_file(self, path):
        if not path or not os.path.exists(path):
            return False

        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            self.buffer.set_text(content)
            self.file_path = path
            self.set_dirty(False)
            self.configure_editor_features()
            return True
        except Exception as e:
            print(f"Error opening file {path}: {e}")
            return False

    def save_file(self, path=None):
        target_path = path or self.file_path
        if not target_path:
            return False

        try:
            start_iter = self.buffer.get_start_iter()
            end_iter = self.buffer.get_end_iter()
            text = self.buffer.get_text(start_iter, end_iter, True)

            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(text)

            self.file_path = target_path
            self.set_dirty(False)
            self.configure_editor_features()
            return True
        except Exception as e:
            print(f"Error saving file {target_path}: {e}")
            return False

    def get_text(self):
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()
        return self.buffer.get_text(start_iter, end_iter, True)

    def set_dirty(self, dirty):
        self.is_dirty = dirty
        if self.on_dirty_changed_cb:
            self.on_dirty_changed_cb(self.is_dirty)

    def _on_buffer_changed(self, buffer):
        if not self.is_dirty:
            self.set_dirty(True)

    def _on_cursor_moved(self, buffer, param):
        if self.on_cursor_moved_cb:
            line, col = self.get_cursor_pos()
            self.on_cursor_moved_cb(line, col)
