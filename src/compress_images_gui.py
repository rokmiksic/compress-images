#!/usr/bin/env python3
"""GTK4 front end for compress-images."""

import json
import os
import threading
from tempfile import TemporaryDirectory
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

from compress_images_core import (
    compress_batch,
    create_zip_archive,
    extract_zip_safely,
    format_bytes,
    gather_images,
    is_zip_path,
    parse_size_mb,
)

SETTINGS_PATH = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "compress-images" / "settings.json"
DEFAULT_SETTINGS = {"language": "English", "unit": "MB", "format": "JPG", "recursive": True, "limit": "1"}


def load_settings():
    try:
        values = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return {**DEFAULT_SETTINGS, **values}
    except (OSError, ValueError, TypeError):
        return DEFAULT_SETTINGS.copy()


def save_settings(values):
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = SETTINGS_PATH.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(values, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary_path.replace(SETTINGS_PATH)
    except OSError:
        pass


def next_available_path(path: Path) -> Path:
    """Avoid overwriting an existing ZIP or archive output directory."""
    if not path.exists():
        return path
    for counter in range(2, 10000):
        candidate = path.with_name(f"{path.name}_{counter}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find a free output name for '{path.name}'.")


TEXT = {
    "English": {
        "title": "Compress Images", "choose_folder": "Choose folder", "choose_files": "Choose images or ZIP",
        "subtitle": "Fast, safe batch image conversion",
        "nothing": "No source selected", "limit": "Maximum size per image", "format": "Output format", "unit": "Unit",
        "recursive": "Include subfolders", "start": "Start compression", "help": "Original files are never changed.",
        "ready": "Ready", "select": "Choose a folder or one or more images first.", "done": "Done",
        "found": "Found", "converted": "converted", "failed": "failed", "saved": "Saved",
        "error": "Error", "folder": "Folder", "files": "images", "original": "Original", "no_images": "No supported images found.",
    },
    "Slovenian": {
        "title": "Stiskanje slik", "choose_folder": "Izberi mapo", "choose_files": "Izberi slike ali ZIP",
        "subtitle": "Hitro in varno paketno pretvarjanje slik",
        "nothing": "Vir ni izbran", "limit": "Največja velikost posamezne slike", "format": "Izhodni format", "unit": "Enota",
        "recursive": "Vključi podmape", "start": "Začni stiskanje", "help": "Originalne datoteke ostanejo nedotaknjene.",
        "ready": "Pripravljeno", "select": "Najprej izberi mapo ali eno oziroma več slik.", "done": "Končano",
        "found": "Najdenih", "converted": "pretvorjenih", "failed": "napak", "saved": "Prihranek",
        "error": "Napaka", "folder": "Mapa", "files": "slik", "original": "Original", "no_images": "Ni najdenih podprtih slik.",
    },
    "German": {
        "title": "Bilder komprimieren", "choose_folder": "Ordner wählen", "choose_files": "Bilder oder ZIP wählen",
        "subtitle": "Schnelle und sichere Stapelkonvertierung von Bildern",
        "nothing": "Keine Quelle ausgewählt", "limit": "Maximale Größe pro Bild", "format": "Ausgabeformat", "unit": "Einheit",
        "recursive": "Unterordner einbeziehen", "start": "Komprimierung starten", "help": "Originaldateien werden nie verändert.",
        "ready": "Bereit", "select": "Bitte zuerst einen Ordner oder Bilder auswählen.", "done": "Fertig",
        "found": "Gefunden", "converted": "konvertiert", "failed": "Fehler", "saved": "Gespart",
        "error": "Fehler", "folder": "Ordner", "files": "Bilder", "original": "Original", "no_images": "Keine unterstützten Bilder gefunden.",
    },
    "Croatian": {
        "title": "Komprimiranje slika", "choose_folder": "Odaberi mapu", "choose_files": "Odaberi slike ili ZIP",
        "subtitle": "Brza i sigurna grupna pretvorba slika",
        "nothing": "Izvor nije odabran", "limit": "Najveća veličina pojedine slike", "format": "Izlazni format", "unit": "Jedinica",
        "recursive": "Uključi podmape", "start": "Pokreni komprimiranje", "help": "Izvorne datoteke se ne mijenjaju.",
        "ready": "Spremno", "select": "Najprije odaberite mapu ili slike.", "done": "Gotovo",
        "found": "Pronađeno", "converted": "pretvoreno", "failed": "neuspješno", "saved": "Ušteđeno",
        "error": "Greška", "folder": "Mapa", "files": "slika", "original": "Izvorno", "no_images": "Nisu pronađene podržane slike.",
    },
    "Serbian": {
        "title": "Kompresija slika", "choose_folder": "Izaberi fasciklu", "choose_files": "Izaberi slike ili ZIP",
        "subtitle": "Brza i sigurna grupna konverzija slika",
        "nothing": "Izvor nije izabran", "limit": "Najveća veličina slike", "format": "Izlazni format", "unit": "Jedinica",
        "recursive": "Uključi podfascikle", "start": "Pokreni kompresiju", "help": "Originalne datoteke ostaju nepromenjene.",
        "ready": "Spremno", "select": "Prvo izaberi fasciklu ili slike.", "done": "Završeno",
        "found": "Pronađeno", "converted": "konvertovano", "failed": "neuspešno", "saved": "Ušteđeno",
        "error": "Greška", "folder": "Fascikla", "files": "slika", "original": "Original", "no_images": "Nisu pronađene podržane slike.",
    },
    "French": {
        "title": "Compresser les images", "choose_folder": "Choisir un dossier", "choose_files": "Choisir des images ou ZIP",
        "subtitle": "Conversion d'images rapide et sûre par lots",
        "nothing": "Aucune source sélectionnée", "limit": "Taille maximale par image", "format": "Format de sortie", "unit": "Unité",
        "recursive": "Inclure les sous-dossiers", "start": "Lancer la compression", "help": "Les originaux ne sont jamais modifiés.",
        "ready": "Prêt", "select": "Choisissez d'abord un dossier ou des images.", "done": "Terminé",
        "found": "Trouvées", "converted": "converties", "failed": "échecs", "saved": "Économisé",
        "error": "Erreur", "folder": "Dossier", "files": "images", "original": "Original", "no_images": "Aucune image prise en charge trouvée.",
    },
}


class App(Gtk.Application):
    def __init__(self):
        # Allow a fresh process to load the latest preferences on every launch.
        super().__init__(application_id="com.github.compress-images", flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.source_paths: list[Path] = []
        self.folder_mode = False
        self.labels = {}
        self.ui_text = TEXT["English"]
        self.settings = load_settings()

    def do_activate(self):
        # Reload preferences when Plasma activates an already-running application instance.
        self.settings = load_settings()
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_default_size(760, 620)
        self.window.set_title("Compress Images")
        self.window.connect("close-request", self.on_close)
        css = Gtk.CssProvider()
        css.load_from_data(b".hero { padding: 22px; border-radius: 16px; background: alpha(@accent_bg_color, 0.12); } .section { padding: 18px; border-radius: 12px; background: alpha(@window_fg_color, 0.04); } .mono { font-family: monospace; }")
        Gtk.StyleContext.add_provider_for_display(self.window.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.build_ui()
        self.window.present()

    def t(self, key):
        return TEXT[self.language_dropdown.get_selected_item().get_string()][key]

    def build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(28); outer.set_margin_bottom(28); outer.set_margin_start(32); outer.set_margin_end(32)
        header = Gtk.Box(spacing=12); header.add_css_class("hero")
        self.title_label = Gtk.Label(label="Compress Images"); self.title_label.add_css_class("title-1"); self.title_label.set_hexpand(True); self.title_label.set_xalign(0)
        self.language_dropdown = Gtk.DropDown.new_from_strings(list(TEXT))
        self.language_dropdown.set_selected(max(0, list(TEXT).index(self.settings["language"]) if self.settings["language"] in TEXT else 0)); self.language_dropdown.connect("notify::selected-item", self.refresh_text)
        header.append(self.title_label); header.append(self.language_dropdown); outer.append(header)
        self.subtitle_label = Gtk.Label(label="Fast, safe batch image conversion"); self.subtitle_label.set_xalign(0); self.subtitle_label.add_css_class("dim-label"); outer.append(self.subtitle_label)

        source_box = Gtk.Box(spacing=10); source_box.set_margin_top(22); source_box.add_css_class("section")
        self.folder_button = Gtk.Button(label="Choose folder"); self.folder_button.connect("clicked", self.choose_folder)
        self.files_button = Gtk.Button(label="Choose images"); self.files_button.connect("clicked", self.choose_files)
        source_box.append(self.folder_button); source_box.append(self.files_button); outer.append(source_box)
        self.source_label = Gtk.Label(label="No source selected"); self.source_label.set_xalign(0); self.source_label.add_css_class("dim-label"); outer.append(self.source_label)

        grid = Gtk.Grid(column_spacing=18, row_spacing=14); grid.set_margin_top(18); grid.set_margin_bottom(16); grid.add_css_class("section")
        self.limit_label = Gtk.Label(label="Maximum size per image (MB)"); self.limit_label.set_xalign(0)
        self.limit_entry = Gtk.Entry(); self.limit_entry.set_text(str(self.settings.get("limit", "1"))); self.limit_entry.set_width_chars(8); self.limit_entry.connect("changed", self.persist_settings)
        self.unit_dropdown = Gtk.DropDown.new_from_strings(["MB", "KB"])
        self.unit_dropdown.set_selected(1 if self.settings.get("unit") == "KB" else 0); self.unit_dropdown.connect("notify::selected-item", self.persist_settings)
        self.format_label = Gtk.Label(label="Output format"); self.format_label.set_xalign(0)
        self.format_dropdown = Gtk.DropDown.new_from_strings(["JPG", "WEBP", "AVIF", "PNG"])
        self.format_dropdown.set_selected(["JPG", "WEBP", "AVIF", "PNG"].index(self.settings.get("format", "JPG")) if self.settings.get("format", "JPG") in ["JPG", "WEBP", "AVIF", "PNG"] else 0); self.format_dropdown.connect("notify::selected-item", self.persist_settings)
        self.recursive_switch = Gtk.Switch(); self.recursive_switch.set_active(bool(self.settings.get("recursive", True))); self.recursive_switch.connect("notify::active", self.persist_settings)
        self.recursive_label = Gtk.Label(label="Include subfolders"); self.recursive_label.set_xalign(0)
        self.unit_label = Gtk.Label(label="Unit"); self.unit_label.set_xalign(0)
        grid.attach(self.limit_label, 0, 0, 1, 1); grid.attach(self.limit_entry, 1, 0, 1, 1); grid.attach(self.unit_dropdown, 2, 0, 1, 1)
        grid.attach(self.format_label, 0, 1, 1, 1); grid.attach(self.format_dropdown, 1, 1, 1, 1)
        grid.attach(self.recursive_label, 0, 2, 1, 1); grid.attach(self.recursive_switch, 1, 2, 1, 1); outer.append(grid)

        self.start_button = Gtk.Button(label="Start compression"); self.start_button.add_css_class("suggested-action"); self.start_button.connect("clicked", self.start); outer.append(self.start_button)
        self.status = Gtk.Label(label="Ready"); self.status.set_xalign(0); self.status.set_wrap(True); self.status.set_margin_top(22); outer.append(self.status)
        self.help_label = Gtk.Label(label="Original files are never changed."); self.help_label.set_xalign(0); self.help_label.add_css_class("dim-label"); self.help_label.set_margin_top(10); outer.append(self.help_label)
        self.window.set_child(outer)
        # Apply the saved language immediately; otherwise the widgets remain in English until a manual change.
        self.refresh_text()

    def refresh_text(self, *_):
        self.ui_text = TEXT[self.language_dropdown.get_selected_item().get_string()]
        self.title_label.set_label(self.t("title")); self.subtitle_label.set_label(self.t("subtitle"))
        self.folder_button.set_label(self.t("choose_folder")); self.files_button.set_label(self.t("choose_files"))
        self.limit_label.set_label(self.t("limit")); self.unit_label.set_label(self.t("unit")); self.format_label.set_label(self.t("format")); self.recursive_label.set_label(self.t("recursive"))
        self.start_button.set_label(self.t("start")); self.help_label.set_label(self.t("help"))
        if not self.source_paths: self.source_label.set_label(self.t("nothing"))
        self.persist_settings()

    def persist_settings(self, *_):
        if not hasattr(self, "language_dropdown"):
            return
        save_settings({
            "language": self.language_dropdown.get_selected_item().get_string(),
            "unit": self.unit_dropdown.get_selected_item().get_string(),
            "format": self.format_dropdown.get_selected_item().get_string(),
            "recursive": self.recursive_switch.get_active(),
            "limit": self.limit_entry.get_text(),
        })

    def on_close(self, *_):
        self.persist_settings()
        return False

    def choose_folder(self, *_):
        dialog = Gtk.FileDialog(title=self.t("choose_folder"))
        dialog.select_folder(self.window, None, self.folder_selected)

    def folder_selected(self, dialog, result):
        try: selected = dialog.select_folder_finish(result)
        except GLib.Error: return
        self.source_paths = [Path(selected.get_path())]; self.folder_mode = True
        self.source_label.set_label(f"{self.t('folder')}: {self.source_paths[0]}")

    def choose_files(self, *_):
        dialog = Gtk.FileDialog(title=self.t("choose_files"))
        dialog.open_multiple(self.window, None, self.files_selected)

    def files_selected(self, dialog, result):
        try: selected = dialog.open_multiple_finish(result)
        except GLib.Error: return
        self.source_paths = [Path(selected.get_item(i).get_path()) for i in range(selected.get_n_items())]
        self.folder_mode = False; self.source_label.set_label(f"{len(self.source_paths)} {self.t('files')}")

    def start(self, *_):
        if not self.source_paths: self.status.set_label(self.t("select")); return
        try: amount = parse_size_mb(self.limit_entry.get_text())
        except ValueError as exc: self.status.set_label(f"{self.t('error')}: {exc}"); return
        recursive = self.recursive_switch.get_active()
        fmt = self.format_dropdown.get_selected_item().get_string().lower()
        unit = self.unit_dropdown.get_selected_item().get_string()
        max_bytes = int(amount * (1024 if unit == "KB" else 1024 * 1024))
        self.start_button.set_sensitive(False); self.status.set_label(self.t("ready") + "...")
        threading.Thread(target=self.process, args=(max_bytes, recursive, fmt), daemon=True).start()

    def process(self, max_bytes, recursive_setting, fmt):
        tx = self.ui_text
        if self.folder_mode:
            root = self.source_paths[0]; images = gather_images(root, recursive_setting); output_root = root / "compressed"; recursive = recursive_setting
        else:
            # Files selected explicitly in the chooser may have no extension.
            # Let the conversion engine validate their actual image contents.
            zip_sources = [p for p in self.source_paths if is_zip_path(p) and p.is_file()]
            images = [p for p in self.source_paths if not is_zip_path(p) and p.is_file()]
            root = Path(os.path.commonpath([str(p.parent) for p in self.source_paths])) if self.source_paths else Path.cwd()
            output_root = root / "compressed"; recursive = True
        if not self.folder_mode and not images and not zip_sources:
            GLib.idle_add(self.finish, self.t("no_images"))
            return
        converted = failed = 0; original = compressed = 0; lines = []

        def report(result, display_root=None):
            index, source, destination, size, error = result
            display_name = source.name
            if display_root is not None:
                display_name = str(source.relative_to(display_root))
            if error is not None:
                line = f"[{index}] {display_name} -> {tx['error']}: {error}"
            else:
                line = f"[{index}] {display_name} -> {destination.name} | {format_bytes(source.stat().st_size)} -> {format_bytes(size)}"
            lines.append(line)
            GLib.idle_add(self.status.set_label, line)

        def collect(results):
            nonlocal converted, failed, original, compressed
            for _, source, _, size, error in results:
                original += source.stat().st_size
                if error is not None:
                    failed += 1
                else:
                    converted += 1; compressed += size

        if images:
            lines.append(f"{tx['found']} {len(images)}")
            collect(compress_batch(images, root, output_root, recursive, max_bytes, fmt, report))

        for archive in ([] if self.folder_mode else zip_sources):
            try:
                with TemporaryDirectory(prefix="compress-images-zip-") as temporary:
                    extracted_root = Path(temporary) / "input"
                    extract_zip_safely(archive, extracted_root)
                    archive_images = gather_images(extracted_root, True)
                    lines.append(f"{archive.name}: {tx['found']} {len(archive_images)}")
                    if not archive_images:
                        continue
                    archive_output = next_available_path(output_root / archive.stem)
                    archive_results = compress_batch(
                        archive_images,
                        extracted_root,
                        archive_output,
                        True,
                        max_bytes,
                        fmt,
                        lambda result: report(result, extracted_root),
                    )
                    collect(archive_results)
                    if any(error is None for _, _, _, _, error in archive_results):
                        archive_zip = next_available_path(output_root / f"{archive.stem}-compressed.zip")
                        create_zip_archive(archive_output, archive_zip)
                        lines.append(f"{archive.name} -> {archive_zip.name}")
            except Exception as exc:
                failed += 1
                lines.append(f"{archive.name} -> {tx['error']}: {exc}")

        summary = "\n".join(lines[-min(len(lines), 8):] + [f"\n{tx['done']}: {converted} {tx['converted']}, {failed} {tx['failed']}", f"{tx['original']}: {format_bytes(original)} | {tx['saved']}: {format_bytes(original - compressed)}"])
        GLib.idle_add(self.finish, summary)

    def finish(self, summary):
        self.status.set_label(summary); self.start_button.set_sensitive(True); return False


if __name__ == "__main__":
    raise SystemExit(App().run([]))
