import os
import sys
import json
import subprocess
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, Adw, Gdk, Gio, GLib, GtkSource, Pango

from .editor import SimpleJavaEditor
from .sidebar import FolderSidebar

CONFIG_DIR = os.path.expanduser("~/.config/text-studio")
SESSION_FILE = os.path.join(CONFIG_DIR, "session.json")

class CustomOpenDialog(Gtk.Window):
    """Custom File/Folder picker dialog that allows selecting EITHER files or folders."""

    def __init__(self, parent, callback):
        super().__init__(title="Open File or Folder", transient_for=parent, modal=True)
        self.set_default_size(500, 520)
        self.callback = callback
        self.current_dir = os.path.abspath(os.path.expanduser("~"))
        self.selected_path = None

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_start(18)
        main_box.set_margin_end(18)
        main_box.set_margin_top(18)
        main_box.set_margin_bottom(18)
        self.set_child(main_box)

        # Path bar and Go Up button
        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.btn_up = Gtk.Button(icon_name="go-up-symbolic")
        self.btn_up.connect("clicked", self._on_go_up)
        path_box.append(self.btn_up)

        self.lbl_path = Gtk.Label(label=self.current_dir)
        self.lbl_path.set_hexpand(True)
        self.lbl_path.set_xalign(0.0)
        self.lbl_path.set_ellipsize(Pango.EllipsizeMode.MIDDLE if 'Pango' in globals() else 0)
        self.lbl_path.add_css_class("caption")
        path_box.append(self.lbl_path)
        
        main_box.append(path_box)

        # Scrolled List Box of items
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-activated", self._on_row_activated)
        self.list_box.connect("row-selected", self._on_row_selected)
        self.list_box.add_css_class("boxed-list")

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.list_box)
        main_box.append(scrolled)

        # Bottom Actions
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda b: self.destroy())
        btn_box.append(btn_cancel)

        self.btn_open = Gtk.Button(label="Open Selected")
        self.btn_open.add_css_class("suggested-action")
        self.btn_open.set_hexpand(True)
        self.btn_open.set_sensitive(False)
        self.btn_open.connect("clicked", self._on_open_clicked)
        btn_box.append(self.btn_open)

        main_box.append(btn_box)

        self._refresh_list()

    def _refresh_list(self):
        # Clear rows
        while True:
            child = self.list_box.get_first_child()
            if not child:
                break
            self.list_box.remove(child)

        self.lbl_path.set_text(self.current_dir)
        self.selected_path = None
        self.btn_open.set_sensitive(False)

        # 1. Add current directory selector row
        current_name = os.path.basename(self.current_dir) or self.current_dir
        self._add_row(f'Open Current Folder: "{current_name}"', is_dir=True, is_current_dir_selector=True)

        try:
            entries = sorted(os.listdir(self.current_dir))
            # Put directories first, files second
            dirs = []
            files = []
            for e in entries:
                if e.startswith('.'):
                    continue
                path = os.path.join(self.current_dir, e)
                if os.path.isdir(path):
                    dirs.append(e)
                else:
                    files.append(e)

            for d in dirs:
                self._add_row(d, is_dir=True)
            for f in files:
                self._add_row(f, is_dir=False)
        except Exception as e:
            print(f"Error loading dir: {e}")

    def _add_row(self, name, is_dir=False, is_current_dir_selector=False):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        if is_current_dir_selector:
            icon_name = "emblem-documents-symbolic"
        else:
            icon_name = "folder-symbolic" if is_dir else "text-x-generic-symbolic"
            
        icon = Gtk.Image.new_from_icon_name(icon_name)
        box.append(icon)

        lbl = Gtk.Label(label=name)
        lbl.set_xalign(0.0)
        
        if is_current_dir_selector:
            lbl.add_css_class("title-4")
            
        box.append(lbl)

        row.set_child(box)
        row.path = self.current_dir if is_current_dir_selector else os.path.join(self.current_dir, name)
        row.is_dir = is_dir
        row.is_current_dir_selector = is_current_dir_selector
        self.list_box.append(row)

    def _on_go_up(self, btn):
        parent = os.path.dirname(self.current_dir)
        if parent and parent != self.current_dir:
            self.current_dir = parent
            self._refresh_list()

    def _on_row_selected(self, listbox, row):
        if row and hasattr(row, 'path'):
            self.selected_path = row.path
            self.btn_open.set_sensitive(True)
        else:
            self.selected_path = None
            self.btn_open.set_sensitive(False)

    def _on_row_activated(self, listbox, row):
        if row and hasattr(row, 'path'):
            if row.is_current_dir_selector:
                self.selected_path = row.path
                self._on_open_clicked(None)
            elif row.is_dir:
                self.current_dir = row.path
                self._refresh_list()
            else:
                self.selected_path = row.path
                self._on_open_clicked(None)

    def _on_open_clicked(self, btn):
        if self.selected_path:
            self.callback(self.selected_path)
            self.destroy()


class SimpleJavaWindow(Adw.ApplicationWindow):
    """Multi-tab Minimalist Text Editor with Session Persistence and Fullscreen Focus Mode."""

    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("Text Studio")
        self.set_default_size(1050, 720)

        self.initializing = True
        self.is_fullscreen = False
        self.current_theme_id = 'adwaita-dark-custom'
        self.current_font_size = 12
        self.autosave_enabled = False
        self.autosave_timeout_id = None
        self._save_session_timeout_id = None
        self.force_close = False

        # Apply Global CSS to remove black line between HeaderBar and TabBar
        self._setup_global_css()

        # Main vertical box layout container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        # Header Bar Setup packaged inside a Slide Down Revealer
        self.header_bar = Adw.HeaderBar()
        self.header_bar.set_show_title(False)
        self.header_bar.set_margin_bottom(-1)
        self.header_revealer = Gtk.Revealer()
        self.header_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.header_revealer.set_transition_duration(250)
        self.header_revealer.set_child(self.header_bar)
        self.header_revealer.set_reveal_child(True)
        self.header_revealer.set_margin_bottom(-1)
        # Default Windowed Mode: Pack header bar normally at the top of main_box
        self.main_box.append(self.header_revealer)

        # Overlay container for the rest of the application
        self.overlay = Gtk.Overlay()
        self.overlay.set_vexpand(True)
        self.overlay.set_hexpand(True)
        self.main_box.append(self.overlay)

        # Main content layout (underneath the overlay)
        self.main_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_layout.set_vexpand(True)
        self.main_layout.set_hexpand(True)
        self.overlay.set_child(self.main_layout)

        # 1. Left Controls: Sidebar Toggle, New Tab, Open, Save, Run Code Button
        self.btn_sidebar = Gtk.ToggleButton(icon_name="sidebar-show-symbolic")
        self.btn_sidebar.add_css_class("flat")
        self.btn_sidebar.set_active(False)
        self.btn_sidebar.set_tooltip_text("Toggle Folder Sidebar (Ctrl+B)")
        self.btn_sidebar.connect("toggled", lambda b: (self.sidebar.set_visible(b.get_active()), self._save_session()))
        self.header_bar.pack_start(self.btn_sidebar)

        # Open Button
        btn_open = Gtk.Button()
        box_open_label = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box_open_label.append(Gtk.Image.new_from_icon_name("document-open-symbolic"))
        box_open_label.append(Gtk.Label(label="Open"))
        btn_open.set_child(box_open_label)
        btn_open.set_tooltip_text("Open File or Folder (Ctrl+O)")
        btn_open.connect("clicked", lambda b: self.open_custom_picker())
        self.header_bar.pack_start(btn_open)

        # Save Button
        btn_save = Gtk.Button()
        box_save_label = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box_save_label.append(Gtk.Image.new_from_icon_name("document-save-symbolic"))
        box_save_label.append(Gtk.Label(label="Save"))
        btn_save.set_child(box_save_label)
        btn_save.set_tooltip_text("Save Active File (Ctrl+S)")
        btn_save.connect("clicked", lambda b: self.save_current_file())
        self.header_bar.pack_start(btn_save)

        # Run Button (suggested-action, visible for .java files)
        self.btn_run = Gtk.Button()
        self.btn_run.add_css_class("suggested-action")
        box_run_label = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box_run_label.append(Gtk.Image.new_from_icon_name("media-playback-start-symbolic"))
        box_run_label.append(Gtk.Label(label="Run"))
        self.btn_run.set_child(box_run_label)
        self.btn_run.set_tooltip_text("Run Java Program (Ctrl+R)")
        self.btn_run.connect("clicked", lambda b: self.run_active_file())
        self.btn_run.set_visible(False)
        self.header_bar.pack_start(self.btn_run)

        # Right Controls: Find, Fullscreen, and settings menu (flat style)
        btn_find = Gtk.Button(icon_name="edit-find-symbolic")
        btn_find.add_css_class("flat")
        btn_find.set_tooltip_text("Find Text (Ctrl+F)")
        btn_find.connect("clicked", lambda b: self.toggle_search_bar())
        self.header_bar.pack_end(btn_find)

        self.btn_fullscreen = Gtk.Button(icon_name="view-fullscreen-symbolic")
        self.btn_fullscreen.add_css_class("flat")
        self.btn_fullscreen.set_tooltip_text("Full Screen Mode (F11)")
        self.btn_fullscreen.connect("clicked", lambda b: self.toggle_fullscreen_mode())
        self.header_bar.pack_end(self.btn_fullscreen)

        # 2. Right Controls: Settings & Features Menu (Popover)
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_button.add_css_class("flat")
        menu_button.set_tooltip_text("Menu & Preferences")

        self.popover = Gtk.Popover()
        self.popover.set_autohide(True)

        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        popover_box.set_margin_start(8)
        popover_box.set_margin_end(8)
        popover_box.set_margin_top(8)
        popover_box.set_margin_bottom(8)
        popover_box.set_size_request(280, -1)

        list_box = Gtk.ListBox()
        list_box.add_css_class("boxed-list")
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        popover_box.append(list_box)

        # 1. Go to Line Row
        row_goto = Adw.ActionRow()
        row_goto.set_title("Go to Line...")
        row_goto.set_subtitle("Ctrl+L")
        row_goto.set_icon_name("go-jump-symbolic")
        row_goto.set_activatable(True)
        row_goto.connect("activated", lambda r: (self.popover.popdown(), self._show_goto_line_dialog()))
        list_box.append(row_goto)

        # 2. Auto-Save Row
        row_autosave = Adw.ActionRow()
        row_autosave.set_title("Auto-Save")
        row_autosave.set_subtitle("Automatically save changes")
        row_autosave.set_icon_name("document-save-symbolic")
        
        self.switch_autosave = Gtk.Switch()
        self.switch_autosave.set_valign(Gtk.Align.CENTER)
        self.switch_autosave.connect("state-set", self._on_autosave_toggled)
        row_autosave.add_suffix(self.switch_autosave)
        list_box.append(row_autosave)

        # 3. Theme Row
        is_dark = "dark" in self.current_theme_id.lower()
        sm = Adw.StyleManager.get_default()
        sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK if is_dark else Adw.ColorScheme.FORCE_LIGHT)

        self.row_theme = Adw.ActionRow()
        self.row_theme.set_title("Dark Mode")
        self.row_theme.set_subtitle("Use dark theme")
        self.row_theme.set_icon_name("weather-clear-night-symbolic" if is_dark else "weather-clear-symbolic")

        self.switch_theme = Gtk.Switch()
        self.switch_theme.set_valign(Gtk.Align.CENTER)
        self.switch_theme.set_active(is_dark)
        self.switch_theme.connect("state-set", self._on_theme_toggled)
        self.row_theme.add_suffix(self.switch_theme)
        list_box.append(self.row_theme)

        # 4. Font Size Row
        row_font = Adw.ActionRow()
        row_font.set_title("Font Size")
        row_font.set_icon_name("preferences-desktop-font-symbolic")
        
        font_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        font_box.set_valign(Gtk.Align.CENTER)
        
        btn_font_dec = Gtk.Button(icon_name="zoom-out-symbolic")
        btn_font_dec.add_css_class("flat")
        btn_font_dec.connect("clicked", lambda b: self._change_font_size(self.current_font_size - 1))
        font_box.append(btn_font_dec)

        self.lbl_font_size = Gtk.Label(label=str(self.current_font_size))
        self.lbl_font_size.add_css_class("caption")
        font_box.append(self.lbl_font_size)

        btn_font_inc = Gtk.Button(icon_name="zoom-in-symbolic")
        btn_font_inc.add_css_class("flat")
        btn_font_inc.connect("clicked", lambda b: self._change_font_size(self.current_font_size + 1))
        font_box.append(btn_font_inc)
        
        row_font.add_suffix(font_box)
        list_box.append(row_font)

        # 5. Save As Row
        row_save_as = Adw.ActionRow()
        row_save_as.set_title("Save As...")
        row_save_as.set_icon_name("document-save-as-symbolic")
        row_save_as.set_activatable(True)
        row_save_as.connect("activated", lambda r: (self.popover.popdown(), self.save_file_as_dialog()))
        list_box.append(row_save_as)

        self.popover.set_child(popover_box)
        menu_button.set_popover(self.popover)
        self.header_bar.pack_end(menu_button)

        # Inline Minimalist Search Bar (Ctrl+F) with Next / Prev buttons
        self.search_bar = Gtk.SearchBar()
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search in code (Ctrl+F)...")
        self.search_entry.set_width_chars(30)
        self.search_entry.connect("search-changed", self._on_search_text_changed)
        self.search_entry.connect("activate", lambda e: self._find_next_match())
        search_box.append(self.search_entry)

        btn_prev = Gtk.Button(icon_name="go-up-symbolic")
        btn_prev.set_tooltip_text("Previous Match (Shift+Enter)")
        btn_prev.connect("clicked", lambda b: self._find_prev_match())
        search_box.append(btn_prev)

        btn_next = Gtk.Button(icon_name="go-down-symbolic")
        btn_next.set_tooltip_text("Next Match (Enter)")
        btn_next.connect("clicked", lambda b: self._find_next_match())
        search_box.append(btn_next)

        self.search_bar.set_child(search_box)
        self.main_layout.append(self.search_bar)
        self.connect("notify::focus-widget", self._on_focus_widget_changed)
        self.search_bar.connect("notify::search-mode-enabled", self._on_search_mode_changed)

        # 3. Main Paned (Sidebar | Multi-Tab Editor Area)
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_paned.set_position(260)
        self.main_paned.set_vexpand(True)
        self.main_paned.set_hexpand(True)
        self.main_layout.append(self.main_paned)

        # Sidebar Component (HIDDEN BY DEFAULT!)
        self.sidebar = FolderSidebar(
            on_file_selected_cb=self._on_sidebar_file_selected,
            on_open_folder_request_cb=self.open_custom_picker,
            on_file_renamed_cb=self._on_sidebar_file_renamed
        )
        self.sidebar.set_size_request(240, -1)
        self.sidebar.set_visible(False)
        self.main_paned.set_start_child(self.sidebar)
        self.main_paned.set_shrink_start_child(False)

        # Multi-Tab Component (Adw.TabBar + Adw.TabView)
        self.tab_view = Adw.TabView()
        self.tab_view.set_vexpand(True)
        self.tab_view.set_hexpand(True)

        self.tab_bar = Adw.TabBar()
        self.tab_bar.set_view(self.tab_view)
        self.tab_bar.set_autohide(False)

        # End action button inside TabBar to support visually opening a new tab in Full Screen Mode
        btn_tabbar_new = Gtk.Button(icon_name="tab-new-symbolic")
        btn_tabbar_new.set_tooltip_text("New File (Ctrl+N)")
        btn_tabbar_new.connect("clicked", lambda b: self.new_tab())
        self.tab_bar.set_end_action_widget(btn_tabbar_new)

        editor_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        editor_container.set_vexpand(True)
        editor_container.set_hexpand(True)
        editor_container.append(self.tab_bar)
        editor_container.append(self.tab_view)
        self.main_paned.set_end_child(editor_container)

        # Tab Signals
        self.tab_view.connect("notify::selected-page", self._on_tab_selected_changed)
        self.tab_view.connect("page-attached", lambda tv, page, pos: (page.set_close_button_tooltip("Close Tab (Ctrl+W)"), self._save_session()))
        self.tab_view.connect("page-detached", lambda tv, page, pos: self._save_session())

        # Minimalist Status Bar with Cursor Line & Column Counter
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.set_margin_start(8)
        status_box.set_margin_end(8)
        status_box.set_margin_bottom(4)

        self.status_bar = Gtk.Label(label=" Ready")
        self.status_bar.set_xalign(0.0)
        self.status_bar.set_hexpand(True)
        status_box.append(self.status_bar)

        self.cursor_label = Gtk.Label(label="Ln 1, Col 1")
        self.cursor_label.set_xalign(1.0)
        status_box.append(self.cursor_label)

        self.main_layout.append(status_box)

        # Setup Drag and Drop File Opening
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect("drop", self._on_file_dropped)
        self.add_controller(drop_target)

        # Event Controller Motion (Only added when in Fullscreen to save power!)
        self.motion_ctrl = Gtk.EventControllerMotion.new()
        self.motion_ctrl.connect("motion", self._on_window_motion)

        # Shortcuts
        controller = Gtk.EventControllerKey.new()
        controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(controller)

        self.initializing = False

        # Load session state or create initial tab
        self._load_session()

        # Connect close request to save session immediately & cleanup timeouts
        self.connect("close-request", self._on_close_request)

    def _on_close_request(self, win):
        if self.force_close:
            if self._save_session_timeout_id:
                GLib.source_remove(self._save_session_timeout_id)
                self._save_session_timeout_id = None
            if self.autosave_timeout_id:
                GLib.source_remove(self.autosave_timeout_id)
                self.autosave_timeout_id = None
            self._do_save_session()
            return False

        # Gather unsaved (dirty) tabs
        n_pages = self.tab_view.get_n_pages()
        dirty_editors = []
        for i in range(n_pages):
            page = self.tab_view.get_nth_page(i)
            editor = page.get_child()
            if editor.is_dirty:
                dirty_editors.append((page, editor))

        if not dirty_editors:
            self.force_close = True
            return self._on_close_request(win)

        self._show_unsaved_changes_dialog(dirty_editors)
        return True # Block close request until user answers dialog

    def _show_unsaved_changes_dialog(self, dirty_editors):
        dialog = Adw.AlertDialog.new(
            "Save Changes?",
            "You have unsaved changes in your files. Do you want to save them before closing?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("discard", "Close without Saving")
        dialog.add_response("save", "Save")
        
        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        def on_response(dlg, response_id):
            if response_id == "discard":
                self.force_close = True
                self.close()
            elif response_id == "save":
                self._save_all_and_close(dirty_editors)

        dialog.connect("response", on_response)
        dialog.present(self)

    def _save_all_and_close(self, dirty_editors):
        if not dirty_editors:
            self.force_close = True
            self.close()
            return

        page, editor = dirty_editors[0]
        if editor.file_path:
            if editor.save_file():
                page.set_title(os.path.basename(editor.file_path))
                self._save_all_and_close(dirty_editors[1:])
            else:
                self.status_bar.set_text(" Saving failed. Close aborted.")
        else:
            self.tab_view.set_selected_page(page)
            self._save_untitled_and_continue(page, editor, dirty_editors[1:])

    def _save_untitled_and_continue(self, page, editor, remaining_dirty):
        try:
            dialog = Gtk.FileDialog.new()
            dialog.set_title("Save File As")
            dialog.set_initial_name("Untitled.txt")

            def on_finish(dlg, result):
                try:
                    gfile = dlg.save_finish(result)
                    if gfile:
                        file_path = gfile.get_path()
                        if file_path:
                            if editor.save_file(file_path):
                                page.set_title(os.path.basename(file_path))
                                self._update_title()
                                if self.sidebar.current_folder:
                                    self.sidebar.refresh()
                                self._save_session()
                                self._update_run_button_visibility()
                                self._save_all_and_close(remaining_dirty)
                                return
                except Exception as e:
                    print("Save file cancelled or error:", e)
                self.status_bar.set_text(" Close cancelled.")

            dialog.save(self, None, on_finish)
        except Exception as e:
            print("Gtk.FileDialog save error:", e)
            self.status_bar.set_text(" Close cancelled due to save error.")

    def _setup_global_css(self):
        css_provider = Gtk.CssProvider()
        css_data = """
        headerbar, .titlebar, tabbar, .tab-bar, .tab-box, tab, revealer, overlay {
            border: 0px solid transparent !important;
            border-bottom: 0px solid transparent !important;
            border-top: 0px solid transparent !important;
            box-shadow: none !important;
            background-image: none !important;
            outline: none !important;
        }
        """.encode('utf-8')
        css_provider.load_from_data(css_data)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    def _update_run_button_visibility(self):
        editor = self.get_active_editor()
        if editor and editor.file_path and editor.file_path.endswith(".java"):
            self.btn_run.set_visible(True)
        else:
            self.btn_run.set_visible(False)

    def _on_window_motion(self, controller, x, y):
        if not self.is_fullscreen:
            return

        # Auto-hide / Auto-show header bar based on cursor hover y coordinates
        if y <= 12:
            self.header_revealer.set_reveal_child(True)
        elif y > 70:
            if self.header_revealer.get_reveal_child():
                self.header_revealer.set_reveal_child(False)

    def _on_autosave_toggled(self, switch, state):
        self.autosave_enabled = state
        self._save_session()
        self.status_bar.set_text(f" Auto-Save turned {'ON' if state else 'OFF'}")
        return False

    def _save_session(self):
        if self.initializing:
            return

        # Debounce session saving to avoid frequent disk I/O and conserve power
        if self._save_session_timeout_id:
            GLib.source_remove(self._save_session_timeout_id)
            
        self._save_session_timeout_id = GLib.timeout_add(4000, self._do_save_session)

    def _do_save_session(self):
        self._save_session_timeout_id = None
        os.makedirs(CONFIG_DIR, exist_ok=True)

        opened_files = []
        n_pages = self.tab_view.get_n_pages()
        for i in range(n_pages):
            page = self.tab_view.get_nth_page(i)
            editor = page.get_child()
            if editor.file_path and os.path.exists(editor.file_path):
                opened_files.append(editor.file_path)

        active_editor = self.get_active_editor()
        active_file = active_editor.file_path if (active_editor and active_editor.file_path) else None

        data = {
            "last_folder": self.sidebar.current_folder,
            "opened_files": opened_files,
            "active_file": active_file,
            "theme": self.current_theme_id,
            "font_size": self.current_font_size,
            "sidebar_visible": self.sidebar.get_visible(),
            "autosave_enabled": self.autosave_enabled
        }

        try:
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving session: {e}")
        return GLib.SOURCE_REMOVE

    def _load_session(self):
        session_loaded = False
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.current_theme_id = data.get("theme", "adwaita-dark-custom")
                if self.current_theme_id == "Adwaita-dark":
                    self.current_theme_id = "adwaita-dark-custom"
                elif self.current_theme_id == "Adwaita":
                    self.current_theme_id = "adwaita-custom"
                self.current_font_size = data.get("font_size", 12)
                
                # Update Font Size label
                if hasattr(self, 'lbl_font_size'):
                    self.lbl_font_size.set_text(str(self.current_font_size))

                # Update theme switch state and window color scheme
                is_dark = "dark" in self.current_theme_id.lower()
                self.switch_theme.set_active(is_dark)
                self.row_theme.set_icon_name("weather-clear-night-symbolic" if is_dark else "weather-clear-symbolic")
                sm = Adw.StyleManager.get_default()
                sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK if is_dark else Adw.ColorScheme.FORCE_LIGHT)
                self.autosave_enabled = data.get("autosave_enabled", False)
                self.switch_autosave.set_active(self.autosave_enabled)

                # Restore Folder
                last_folder = data.get("last_folder")
                if last_folder and os.path.isdir(last_folder):
                    self.sidebar.load_folder(last_folder)

                # Restore Sidebar visibility state
                sidebar_visible = data.get("sidebar_visible", False)
                self.sidebar.set_visible(sidebar_visible)
                self.btn_sidebar.set_active(sidebar_visible)

                # Restore Opened Files
                opened_files = data.get("opened_files", [])
                active_file = data.get("active_file")

                for path in opened_files:
                    if os.path.exists(path):
                        self.new_tab(file_path=path)
                        session_loaded = True

                # Select active tab
                if active_file:
                    n_pages = self.tab_view.get_n_pages()
                    for i in range(n_pages):
                        page = self.tab_view.get_nth_page(i)
                        editor = page.get_child()
                        if editor.file_path == active_file:
                            self.tab_view.set_selected_page(page)
                            break

            except Exception as e:
                print(f"Error loading session: {e}")

        if not session_loaded or self.tab_view.get_n_pages() == 0:
            self.new_tab()
        self._update_run_button_visibility()

    def toggle_search_bar(self):
        is_mode = self.search_bar.get_search_mode()
        self.search_bar.set_search_mode(not is_mode)
        if not is_mode:
            self.search_entry.grab_focus()
        else:
            editor = self.get_active_editor()
            if editor:
                editor.search_text(None)

    def _on_search_text_changed(self, entry):
        query = entry.get_text()
        editor = self.get_active_editor()
        if editor:
            editor.search_text(query)

    def _find_next_match(self):
        editor = self.get_active_editor()
        if editor:
            editor.find_next()

    def _find_prev_match(self):
        editor = self.get_active_editor()
        if editor:
            editor.find_previous()

    def toggle_fullscreen_mode(self):
        if not self.is_fullscreen:
            self.fullscreen()
            self.is_fullscreen = True
            
            # Update fullscreen button icon & tooltip
            self.btn_fullscreen.set_icon_name("view-restore-symbolic")
            self.btn_fullscreen.set_tooltip_text("Exit Full Screen (F11)")
            
            # Full Screen Mode: Move header bar to overlay layer so it floats over editor
            self.header_revealer.unparent()
            self.overlay.add_overlay(self.header_revealer)
            self.header_revealer.set_valign(Gtk.Align.START)
            self.header_revealer.set_halign(Gtk.Align.FILL)
            
            self.header_revealer.set_reveal_child(False)
            self.status_bar.set_visible(False)
            self.cursor_label.set_visible(False)
            self.tab_bar.set_visible(True)
            self.sidebar.set_visible(self.btn_sidebar.get_active())

            # Enable motion tracking for header bar auto-hide
            self.add_controller(self.motion_ctrl)
        else:
            self.unfullscreen()
            self.is_fullscreen = False

            # Disable motion tracking when not in fullscreen to save power
            self.remove_controller(self.motion_ctrl)
            
            # Update fullscreen button icon & tooltip
            self.btn_fullscreen.set_icon_name("view-fullscreen-symbolic")
            self.btn_fullscreen.set_tooltip_text("Full Screen Mode (F11)")
            
            # Windowed Mode: Return header bar to main vertical box so it is stacked normally with 0px gap
            self.header_revealer.unparent()
            self.main_box.prepend(self.header_revealer)
            
            self.header_revealer.set_reveal_child(True)
            self.sidebar.set_visible(self.btn_sidebar.get_active())
            self.status_bar.set_visible(True)
            self.cursor_label.set_visible(True)
            self.tab_bar.set_visible(True)

    def get_active_editor(self):
        page = self.tab_view.get_selected_page()
        if page:
            return page.get_child()
        return None

    def new_tab(self, file_path=None, title="Untitled"):
        editor = SimpleJavaEditor(file_path=file_path)
        editor.set_theme(self.current_theme_id)
        editor.update_font_size(self.current_font_size)

        page = self.tab_view.append(editor)

        if file_path:
            title = os.path.basename(file_path)

        page.set_title(title)
        self.tab_view.set_selected_page(page)

        # Track dirty state and cursor position per tab
        editor.on_dirty_changed_cb = lambda dirty: self._on_tab_dirty_changed(editor, page, title, dirty)
        editor.on_cursor_moved_cb = lambda line, col: self.cursor_label.set_text(f"Ln {line}, Col {col}")

        self._save_session()
        self._update_run_button_visibility()
        return editor

    def _on_sidebar_file_selected(self, file_path):
        self._open_file_internal(file_path, update_sidebar_folder=False)

    def open_file(self, file_path):
        self._open_file_internal(file_path, update_sidebar_folder=True)

    def _open_file_internal(self, file_path, update_sidebar_folder=True):
        if not file_path or not os.path.exists(file_path):
            return

        file_path = os.path.abspath(file_path)

        if os.path.isdir(file_path):
            self.open_folder(file_path)
            return

        # If a file was selected: load parent folder but do NOT open/show the sidebar!
        if update_sidebar_folder:
            parent_dir = os.path.dirname(file_path)
            if parent_dir and os.path.isdir(parent_dir):
                self.sidebar.load_folder(parent_dir)
                self.sidebar.set_visible(False)
                self.btn_sidebar.set_active(False)

        # 2. Check if already open in a tab
        n_pages = self.tab_view.get_n_pages()
        for i in range(n_pages):
            page = self.tab_view.get_nth_page(i)
            editor = page.get_child()
            if editor.file_path and os.path.abspath(editor.file_path) == file_path:
                self.tab_view.set_selected_page(page)
                self._update_run_button_visibility()
                return

        # 3. Auto-close pristine "Untitled" tab if it is the ONLY tab open!
        if n_pages == 1:
            only_page = self.tab_view.get_nth_page(0)
            only_editor = only_page.get_child()
            if not only_editor.file_path and not only_editor.is_dirty and only_editor.get_text().strip() == "":
                self.new_tab(file_path=file_path)
                self.tab_view.close_page(only_page)
                self.status_bar.set_text(f" Opened {os.path.basename(file_path)}")
                self._update_title()
                self._save_session()
                self._update_run_button_visibility()
                return

        # 4. Open in new tab
        self.new_tab(file_path=file_path)
        self.status_bar.set_text(f" Opened {os.path.basename(file_path)}")
        self._save_session()
        self._update_run_button_visibility()

    def open_multiple_files(self, paths):
        for path in paths:
            if path:
                self.open_file(path)

    def _on_sidebar_file_renamed(self, old_path, new_path):
        """Called when a file is renamed inside the sidebar folder tree."""
        n_pages = self.tab_view.get_n_pages()
        for i in range(n_pages):
            page = self.tab_view.get_nth_page(i)
            editor = page.get_child()
            if editor.file_path and os.path.abspath(editor.file_path) == os.path.abspath(old_path):
                editor.file_path = new_path
                dirty_mark = " *" if editor.is_dirty else ""
                page.set_title(f"{os.path.basename(new_path)}{dirty_mark}")
                self._update_title()
                self._save_session()
                self._update_run_button_visibility()
                break

    def rename_active_file(self):
        """Show rename dialog for the active tab's file."""
        editor = self.get_active_editor()
        if not editor or not editor.file_path:
            self.status_bar.set_text(" No saved file to rename")
            return

        old_path = os.path.abspath(editor.file_path)
        old_name = os.path.basename(old_path)

        dialog = Gtk.Window()
        dialog.set_title("Rename File")
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        dialog.set_default_size(360, 160)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)

        lbl = Gtk.Label(label=f"New Name for {old_name}:")
        lbl.set_xalign(0.0)
        box.append(lbl)

        entry = Gtk.Entry()
        entry.set_text(old_name)
        box.append(entry)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda b: dialog.destroy())
        btn_box.append(btn_cancel)

        btn_rename = Gtk.Button(label="Rename")
        btn_rename.add_css_class("suggested-action")
        btn_rename.set_hexpand(True)

        def on_rename(b):
            new_name = entry.get_text().strip()
            if new_name and new_name != old_name:
                parent_dir = os.path.dirname(old_path)
                new_path = os.path.join(parent_dir, new_name)
                try:
                    # Update active editor path & Tab title
                    os.rename(old_path, new_path)
                    editor.file_path = new_path
                    page = self.tab_view.get_selected_page()
                    dirty_mark = " *" if editor.is_dirty else ""
                    page.set_title(f"{new_name}{dirty_mark}")
                    
                    self.status_bar.set_text(f" Renamed to {new_name}")
                    self._update_title()
                    
                    # Refresh sidebar if active
                    if self.sidebar.current_folder:
                        self.sidebar.refresh()
                        
                    self._save_session()
                    self._update_run_button_visibility()
                except Exception as e:
                    print(f"Error renaming active file: {e}")
            dialog.destroy()

        btn_rename.connect("clicked", on_rename)
        entry.connect("activate", on_rename)

        btn_box.append(btn_rename)
        box.append(btn_box)

        dialog.set_child(box)
        dialog.present()

    def _on_tab_dirty_changed(self, editor, page, title, dirty):
        dirty_mark = " *" if dirty else ""
        page.set_title(f"{title}{dirty_mark}")
        self._update_title()
        self._update_run_button_visibility()

        # Handle Debounced Auto-Save
        if dirty and self.autosave_enabled and editor.file_path:
            if self.autosave_timeout_id:
                GLib.source_remove(self.autosave_timeout_id)
            self.autosave_timeout_id = GLib.timeout_add(1000, self._trigger_auto_save, editor, page)

    def _trigger_auto_save(self, editor, page):
        self.autosave_timeout_id = None
        if editor.file_path and editor.is_dirty:
            if editor.save_file():
                page.set_title(os.path.basename(editor.file_path))
                self.status_bar.set_text(f" Auto-saved {os.path.basename(editor.file_path)}")
                self._update_title()
                self._save_session()
        return GLib.SOURCE_REMOVE

    def _on_tab_selected_changed(self, tab_view, param):
        self._update_title()
        editor = self.get_active_editor()
        if editor:
            line, col = editor.get_cursor_pos()
            self.cursor_label.set_text(f"Ln {line}, Col {col}")
        self._save_session()
        self._update_run_button_visibility()

    def _update_title(self):
        editor = self.get_active_editor()
        if editor and editor.file_path:
            filename = os.path.basename(editor.file_path)
            dirty_mark = " *" if editor.is_dirty else ""
            self.set_title(f"{filename}{dirty_mark} - Text Studio")
        else:
            self.set_title("Text Studio")

    def _on_theme_toggled(self, switch, state):
        theme_id = 'adwaita-dark-custom' if state else 'adwaita-custom'
        theme_name = 'Adwaita Dark' if state else 'Adwaita Light'
        self.current_theme_id = theme_id
        
        # Synchronize window color scheme
        sm = Adw.StyleManager.get_default()
        sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK if state else Adw.ColorScheme.FORCE_LIGHT)

        # Update icon dynamically
        if state:
            self.row_theme.set_icon_name("weather-clear-night-symbolic")
        else:
            self.row_theme.set_icon_name("weather-clear-symbolic")

        # Apply theme to ALL open tabs
        n_pages = self.tab_view.get_n_pages()
        for i in range(n_pages):
            page = self.tab_view.get_nth_page(i)
            editor = page.get_child()
            editor.set_theme(theme_id)

        self.status_bar.set_text(f" Theme changed to {theme_name}")
        self._save_session()
        return False

    def _on_focus_widget_changed(self, window, spec):
        focused = self.get_focus()
        if not focused:
            return
            
        if self.search_bar.get_search_mode():
            widget = focused
            in_search_bar = False
            while widget:
                if widget == self.search_bar:
                    in_search_bar = True
                    break
                widget = widget.get_parent()
                
            if not in_search_bar:
                self.search_bar.set_search_mode(False)

    def _on_search_mode_changed(self, search_bar, spec):
        if not search_bar.get_search_mode():
            self.search_entry.set_text("")

    def _change_font_size(self, size):
        self.current_font_size = max(8, min(32, size))
        if hasattr(self, 'lbl_font_size'):
            self.lbl_font_size.set_text(str(self.current_font_size))

        # Apply font size to ALL open tabs
        n_pages = self.tab_view.get_n_pages()
        for i in range(n_pages):
            page = self.tab_view.get_nth_page(i)
            editor = page.get_child()
            editor.update_font_size(self.current_font_size)

        self._save_session()

    def open_folder(self, folder_path):
        folder_path = os.path.abspath(os.path.expanduser(folder_path))
        if os.path.isdir(folder_path):
            if self.sidebar.load_folder(folder_path):
                self.status_bar.set_text(f" Opened folder: {folder_path}")
                # Automatically open/show the sidebar when a folder is opened!
                self.sidebar.set_visible(True)
                self.btn_sidebar.set_active(True)
                self._save_session()
                return True
        return False

    def open_custom_picker(self):
        """Open custom dialog that lets user pick EITHER files or folders."""
        dialog = CustomOpenDialog(self, self.open_file)
        dialog.present()

    def run_active_file(self):
        """Executes the active document in a Ptyxis terminal session."""
        editor = self.get_active_editor()
        if not editor or not editor.file_path or not editor.file_path.endswith(".java"):
            self.status_bar.set_text(" No active Java file to run")
            return

        file_path = os.path.abspath(editor.file_path)
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        class_name = base_name[:-5]

        # Clean command format
        cmd = f"javac {base_name} && java {class_name}; echo ''; read -p 'Press Enter to close...' -r"

        try:
            subprocess.Popen(["ptyxis", f"--working-directory={dir_name}", "--", "sh", "-c", cmd])
            self.status_bar.set_text(f" Executing {base_name} inside Terminal...")
        except Exception as e:
            print(f"Error launching terminal: {e}")
            self.status_bar.set_text(" Error launching terminal")

    def save_current_file(self):
        editor = self.get_active_editor()
        if not editor:
            return

        if not editor.file_path:
            self.save_file_as_dialog()
        else:
            if editor.save_file():
                page = self.tab_view.get_selected_page()
                page.set_title(os.path.basename(editor.file_path))
                self.status_bar.set_text(f" Saved {os.path.basename(editor.file_path)}")
                self._update_title()
                self._save_session()
                self._update_run_button_visibility()

    def save_file_as_dialog(self):
        editor = self.get_active_editor()
        if not editor:
            return

        try:
            dialog = Gtk.FileDialog.new()
            dialog.set_title("Save File As")
            dialog.set_initial_name(os.path.basename(editor.file_path) if editor.file_path else "Untitled.txt")

            def on_finish(dlg, result):
                try:
                    gfile = dlg.save_finish(result)
                    if gfile:
                        file_path = gfile.get_path()
                        if file_path:
                            if editor.save_file(file_path):
                                page = self.tab_view.get_selected_page()
                                page.set_title(os.path.basename(file_path))
                                self.status_bar.set_text(f" Saved {file_path}")
                                self._update_title()
                                if self.sidebar.current_folder:
                                    self.sidebar.refresh()
                                self._save_session()
                                self._update_run_button_visibility()
                except Exception as e:
                    print("Save file cancelled or error:", e)

            dialog.save(self, None, on_finish)
        except Exception as e:
            print("Gtk.FileDialog save error:", e)

    def close_current_tab(self):
        page = self.tab_view.get_selected_page()
        if page:
            self.tab_view.close_page(page)
            self._save_session()
            self._update_run_button_visibility()

    def _show_goto_line_dialog(self):
        editor = self.get_active_editor()
        if not editor:
            return

        dialog = Gtk.Window()
        dialog.set_title("Go to Line")
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        dialog.set_default_size(300, 140)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)

        lbl = Gtk.Label(label="Line number:")
        lbl.set_xalign(0.0)
        box.append(lbl)

        entry = Gtk.Entry()
        entry.set_text("1")
        box.append(entry)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda b: dialog.destroy())
        btn_box.append(btn_cancel)

        btn_go = Gtk.Button(label="Go")
        btn_go.add_css_class("suggested-action")
        btn_go.set_hexpand(True)

        def on_go(b):
            try:
                num = int(entry.get_text().strip())
                editor.goto_line(num)
            except ValueError:
                pass
            dialog.destroy()

        btn_go.connect("clicked", on_go)
        entry.connect("activate", on_go)
        btn_box.append(btn_go)
        box.append(btn_box)

        dialog.set_child(box)
        dialog.present()

    def _on_file_dropped(self, target, value, x, y):
        if isinstance(value, Gio.File):
            path = value.get_path()
            if path:
                if os.path.isdir(path):
                    self.open_folder(path)
                else:
                    self.open_file(path)
                return True
        return False

    def _on_key_pressed(self, controller, keyval, keycode, state):
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        if keyval == Gdk.KEY_F11:
            self.toggle_fullscreen_mode()
            return True
        elif keyval == Gdk.KEY_Escape:
            if self.is_fullscreen:
                self.toggle_fullscreen_mode()
                return True
            elif self.search_bar.get_search_mode():
                self.toggle_search_bar()
                return True
        elif keyval == Gdk.KEY_F2:
            self.rename_active_file()
            return True
        elif ctrl:
            if keyval == Gdk.KEY_n:
                self.new_tab()
                return True
            elif keyval == Gdk.KEY_w:
                self.close_current_tab()
                return True
            elif keyval == Gdk.KEY_o:
                self.open_custom_picker()
                return True
            elif keyval == Gdk.KEY_s:
                self.save_current_file()
                return True
            elif keyval == Gdk.KEY_r:
                if self.btn_run.get_visible():
                    self.run_active_file()
                return True
            elif keyval == Gdk.KEY_f:
                self.toggle_search_bar()
                return True
            elif keyval == Gdk.KEY_l:
                self._show_goto_line_dialog()
                return True
            elif keyval == Gdk.KEY_b:
                self.btn_sidebar.set_active(not self.btn_sidebar.get_active())
                return True
            elif keyval in (Gdk.KEY_equal, Gdk.KEY_plus, Gdk.KEY_KP_Add):
                self._change_font_size(self.current_font_size + 1)
                return True
            elif keyval in (Gdk.KEY_minus, Gdk.KEY_underscore, Gdk.KEY_KP_Subtract):
                self._change_font_size(self.current_font_size - 1)
                return True
        return False


class SimpleJavaApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.bluefin.SimpleJavaEditor",
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = SimpleJavaWindow(self)
        win.present()

    def do_open(self, files, n_files, hint):
        win = self.props.active_window
        if not win:
            win = SimpleJavaWindow(self)

        paths = [f.get_path() for f in files if f.get_path()]
        if paths:
            win.open_multiple_files(paths)

        win.present()
