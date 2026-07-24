import os
import shutil
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GLib, Pango

class FolderSidebar(Gtk.Box):
    """Clean minimalist sidebar for managing files in an opened directory."""

    def __init__(self, on_file_selected_cb, on_open_folder_request_cb, on_file_renamed_cb=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_margin_start(4)
        self.set_margin_end(4)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        self.on_file_selected = on_file_selected_cb
        self.on_open_folder_request = on_open_folder_request_cb
        self.on_file_renamed = on_file_renamed_cb
        self.current_folder = None
        self.active_file_path = None

        # Clean Sidebar Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header.set_margin_bottom(4)

        self.lbl_folder_title = Gtk.Label(label="Files")
        self.lbl_folder_title.set_hexpand(True)
        self.lbl_folder_title.set_xalign(0.0)
        self.lbl_folder_title.add_css_class("title-4")
        self.lbl_folder_title.set_ellipsize(Pango.EllipsizeMode.END)
        header.append(self.lbl_folder_title)

        # Action Buttons: New File, Rename, Delete, Refresh
        btn_new_file = Gtk.Button(icon_name="document-new-symbolic")
        btn_new_file.add_css_class("flat")
        btn_new_file.set_tooltip_text("Create New File in Folder")
        btn_new_file.connect("clicked", lambda b: self._show_create_file_dialog())
        header.append(btn_new_file)

        self.btn_rename = Gtk.Button(icon_name="document-properties-symbolic")
        self.btn_rename.add_css_class("flat")
        self.btn_rename.set_tooltip_text("Rename Selected File")
        self.btn_rename.set_sensitive(False)
        self.btn_rename.connect("clicked", lambda b: self._show_rename_dialog())
        header.append(self.btn_rename)

        self.btn_delete = Gtk.Button(icon_name="user-trash-symbolic")
        self.btn_delete.add_css_class("flat")
        self.btn_delete.set_tooltip_text("Delete Selected File")
        self.btn_delete.set_sensitive(False)
        self.btn_delete.connect("clicked", lambda b: self._delete_selected_file())
        header.append(self.btn_delete)

        btn_refresh = Gtk.Button(icon_name="view-refresh-symbolic")
        btn_refresh.add_css_class("flat")
        btn_refresh.set_tooltip_text("Refresh Directory")
        btn_refresh.connect("clicked", lambda b: self.refresh())
        header.append(btn_refresh)

        self.append(header)

        # File List Box with Single Click Activation (Native Navigation Sidebar)
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(True)
        self.list_box.connect("row-activated", self._on_row_activated)
        self.list_box.add_css_class("navigation-sidebar")

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.list_box)
        self.append(scrolled)

    def load_folder(self, folder_path):
        if not folder_path or not os.path.isdir(folder_path):
            return False

        self.current_folder = os.path.abspath(folder_path)
        folder_name = os.path.basename(self.current_folder) or self.current_folder
        self.lbl_folder_title.set_text(folder_name)
        self.lbl_folder_title.set_tooltip_text(self.current_folder)
        self.refresh()
        return True

    def refresh(self):
        # Clear existing rows
        while True:
            child = self.list_box.get_first_child()
            if not child:
                break
            self.list_box.remove(child)

        self.active_file_path = None
        self.btn_rename.set_sensitive(False)
        self.btn_delete.set_sensitive(False)

        if not self.current_folder or not os.path.exists(self.current_folder):
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label="No Folder Opened\nClick Open Folder")
            lbl.set_margin_top(20)
            lbl.set_margin_bottom(20)
            lbl.set_justify(Gtk.Justification.CENTER)
            lbl.add_css_class("dim-label")
            row.set_child(lbl)
            self.list_box.append(row)
            return

        try:
            entries = sorted(os.listdir(self.current_folder))
            visible_entries = [e for e in entries if not e.startswith('.') or e.endswith('.java')]

            dirs = [e for e in visible_entries if os.path.isdir(os.path.join(self.current_folder, e))]
            files = [e for e in visible_entries if os.path.isfile(os.path.join(self.current_folder, e))]

            # 1. Add Parent Directory row if not at root
            parent_dir = os.path.dirname(self.current_folder)
            if parent_dir and parent_dir != self.current_folder:
                row_up = self._create_row(".. (Parent Folder)", is_dir=True, is_parent=True, full_path=parent_dir)
                self.list_box.append(row_up)

            # 2. Add Subdirectories
            for d in dirs:
                full = os.path.join(self.current_folder, d)
                row = self._create_row(d, is_dir=True, full_path=full)
                self.list_box.append(row)

            # 3. Add Files
            for f in files:
                full = os.path.join(self.current_folder, f)
                row = self._create_row(f, is_dir=False, full_path=full)
                self.list_box.append(row)

        except Exception as e:
            print(f"Error listing folder contents: {e}")

    def _create_row(self, name, is_dir=False, is_parent=False, full_path=None):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        if is_parent:
            icon_name = "go-up-symbolic"
        elif is_dir:
            icon_name = "folder-symbolic"
        elif name.endswith('.java'):
            icon_name = "text-x-script-symbolic"
        else:
            icon_name = "text-x-generic-symbolic"

        icon = Gtk.Image.new_from_icon_name(icon_name)
        box.append(icon)

        lbl = Gtk.Label(label=name)
        lbl.set_xalign(0.0)
        lbl.set_hexpand(True)
        lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        lbl.set_tooltip_text(name)

        if name.endswith('.java'):
            lbl.add_css_class("accent")

        box.append(lbl)
        row.set_child(box)

        row.full_path = full_path
        row.is_dir = is_dir
        row.is_parent = is_parent

        return row

    def _on_row_activated(self, listbox, row):
        if not hasattr(row, 'full_path') or not row.full_path:
            return

        if row.is_dir:
            self.active_file_path = None
            self.btn_rename.set_sensitive(False)
            self.btn_delete.set_sensitive(False)
            self.load_folder(row.full_path)
        else:
            self.active_file_path = row.full_path
            self.btn_rename.set_sensitive(True)
            self.btn_delete.set_sensitive(True)
            self.on_file_selected(row.full_path)

    def _show_create_file_dialog(self):
        if not self.current_folder:
            self.on_open_folder_request()
            return

        dialog = Gtk.Window()
        dialog.set_title("Create New File")
        
        parent_win = self.get_root()
        if isinstance(parent_win, Gtk.Window):
            dialog.set_transient_for(parent_win)
            
        dialog.set_modal(True)
        dialog.set_default_size(360, 160)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)

        lbl = Gtk.Label(label="File Name (e.g. Main.java):")
        lbl.set_xalign(0.0)
        box.append(lbl)

        entry = Gtk.Entry()
        entry.set_text("Main.java")
        box.append(entry)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda b: dialog.destroy())
        btn_box.append(btn_cancel)

        btn_create = Gtk.Button(label="Create File")
        btn_create.add_css_class("suggested-action")
        btn_create.set_hexpand(True)

        def on_create(b):
            filename = entry.get_text().strip()
            if filename:
                full_path = os.path.join(self.current_folder, filename)
                if not os.path.exists(full_path):
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write("")
                self.refresh()
                self.on_file_selected(full_path)
            dialog.destroy()

        btn_create.connect("clicked", on_create)
        entry.connect("activate", on_create)

        btn_box.append(btn_create)
        box.append(btn_box)

        dialog.set_child(box)
        dialog.present()

    def _show_rename_dialog(self):
        if not self.active_file_path or not os.path.exists(self.active_file_path):
            return

        old_path = self.active_file_path
        old_name = os.path.basename(old_path)

        dialog = Gtk.Window()
        dialog.set_title("Rename File")
        
        parent_win = self.get_root()
        if isinstance(parent_win, Gtk.Window):
            dialog.set_transient_for(parent_win)
            
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
                    os.rename(old_path, new_path)
                    self.active_file_path = new_path
                    self.refresh()
                    if self.on_file_renamed:
                        self.on_file_renamed(old_path, new_path)
                except Exception as e:
                    print(f"Error renaming: {e}")
            dialog.destroy()

        btn_rename.connect("clicked", on_rename)
        entry.connect("activate", on_rename)

        btn_box.append(btn_rename)
        box.append(btn_box)

        dialog.set_child(box)
        dialog.present()

    def _delete_selected_file(self):
        if not self.active_file_path or not os.path.exists(self.active_file_path):
            return

        filename = os.path.basename(self.active_file_path)

        dialog = Gtk.Window()
        dialog.set_title("Confirm Delete")
        
        parent_win = self.get_root()
        if isinstance(parent_win, Gtk.Window):
            dialog.set_transient_for(parent_win)
            
        dialog.set_modal(True)
        dialog.set_default_size(360, 150)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)

        lbl = Gtk.Label(label=f"Are you sure you want to delete '{filename}'?")
        lbl.set_xalign(0.0)
        box.append(lbl)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda b: dialog.destroy())
        btn_box.append(btn_cancel)

        btn_delete = Gtk.Button(label="Delete")
        btn_delete.add_css_class("destructive-action")
        btn_delete.set_hexpand(True)

        def on_delete(b):
            try:
                if os.path.isdir(self.active_file_path):
                    shutil.rmtree(self.active_file_path)
                else:
                    os.remove(self.active_file_path)
                self.active_file_path = None
                self.btn_rename.set_sensitive(False)
                self.btn_delete.set_sensitive(False)
                self.refresh()
            except Exception as e:
                print(f"Error deleting file: {e}")
            dialog.destroy()

        btn_delete.connect("clicked", on_delete)
        btn_box.append(btn_delete)
        box.append(btn_box)

        dialog.set_child(box)

        # Set Cancel button as the default focus element
        btn_cancel.grab_focus()

        dialog.present()
