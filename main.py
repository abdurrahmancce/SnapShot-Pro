import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# ── Third-party imports ──────────────────────────────────────────────────────
try:
    import pyautogui
except ImportError:
    messagebox.showerror("Missing Library", "pyautogui is not installed.\nRun: pip install pyautogui")
    sys.exit(1)

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFilter
except ImportError:
    messagebox.showerror("Missing Library", "Pillow is not installed.\nRun: pip install pillow")
    sys.exit(1)

# keyboard is optional — graceful fallback if unavailable
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


#  CONSTANTS & THEME DEFINITIONS

APP_TITLE   = "SnapShot Pro"
APP_VERSION = "1.0.0"
SETTINGS_FILE = "settings.json"

# Color palettes for dark and light modes
THEMES = {
    "dark": {
        "bg":           "#0f1117",
        "surface":      "#1a1d27",
        "surface2":     "#22263a",
        "accent":       "#7c6af7",
        "accent2":      "#5eead4",
        "accent_hover": "#9d8fff",
        "text":         "#e8eaf6",
        "text_dim":     "#8b8fa8",
        "border":       "#2d3148",
        "success":      "#4ade80",
        "warning":      "#fbbf24",
        "danger":       "#f87171",
        "btn_fg":       "#ffffff",
        "history_sel":  "#2d3148",
    },
    "light": {
        "bg":           "#f0f2ff",
        "surface":      "#ffffff",
        "surface2":     "#e8eaf6",
        "accent":       "#6050e0",
        "accent2":      "#0d9488",
        "accent_hover": "#4f3fc8",
        "text":         "#1a1d27",
        "text_dim":     "#6b7280",
        "border":       "#d1d5db",
        "success":      "#16a34a",
        "warning":      "#d97706",
        "danger":       "#dc2626",
        "btn_fg":       "#ffffff",
        "history_sel":  "#e0e0f8",
    },
}


#  SETTINGS MANAGER

class SettingsManager:
    """Loads and saves app settings to/from settings.json."""

    DEFAULTS = {
        "theme":              "dark",
        "save_location":      "screenshots",
        "delay":              0,
        "auto_open":          False,
        "sound_enabled":      True,
        "screenshot_count":   0,
        "minimize_on_capture": True,
    }

    def __init__(self, filepath: str = SETTINGS_FILE):
        self.filepath = filepath
        self.data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        """Read settings from disk, falling back to defaults for missing keys."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    saved = json.load(f)
                self.data.update(saved)
            except (json.JSONDecodeError, OSError):
                pass  # corrupt file → use defaults

    def save(self):
        """Persist current settings to disk."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.data, f, indent=4)
        except OSError as e:
            print(f"[Settings] Could not save: {e}")

    def get(self, key, fallback=None):
        return self.data.get(key, fallback)

    def set(self, key, value):
        self.data[key] = value
        self.save()


#  SCREENSHOT ENGINE

class ScreenshotEngine:
    """
    Handles all screenshot capture logic.
    Keeps UI code completely separate from capture logic.
    """

    def __init__(self, save_dir: str):
        self.save_dir = save_dir
        self._ensure_dir()

    def _ensure_dir(self):
        """Create the screenshots directory if it doesn't exist."""
        Path(self.save_dir).mkdir(parents=True, exist_ok=True)

    def set_save_dir(self, path: str):
        self.save_dir = path
        self._ensure_dir()

    def _generate_filename(self, prefix: str = "screenshot") -> str:
        """Create a unique filename with a timestamp."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.save_dir, f"{prefix}_{ts}.png")

    # ── Capture methods ───────────────────────────────────────────────────────

    def capture_fullscreen(self) -> tuple[Image.Image, str]:
        """Take a full-screen screenshot and save it."""
        img  = pyautogui.screenshot()
        path = self._generate_filename("fullscreen")
        img.save(path)
        return img, path

    def capture_region(self, x: int, y: int, w: int, h: int) -> tuple[Image.Image, str]:
        """Capture a rectangular region of the screen."""
        img  = pyautogui.screenshot(region=(x, y, w, h))
        path = self._generate_filename("region")
        img.save(path)
        return img, path

    def copy_to_clipboard(self, img: Image.Image):
        """
        Copy a PIL Image to the system clipboard.
        Uses a temporary file approach for cross-platform reliability.
        """
        import io
        try:
            # Try using xclip / xsel on Linux
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            proc = subprocess.run(
                ["xclip", "-selection", "clipboard", "-t", "image/png", "-i"],
                input=buf.read(), capture_output=True
            )
            if proc.returncode == 0:
                return True
        except FileNotFoundError:
            pass

        try:
            # Fallback: pyperclip-style via win32clipboard on Windows
            import io, win32clipboard
            buf = io.BytesIO()
            img.convert("RGB").save(buf, "BMP")
            bmp_data = buf.getvalue()[14:]  # strip BMP file header
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data)
            win32clipboard.CloseClipboard()
            return True
        except Exception:
            return False


#  REGION SELECTOR — transparent overlay for drag-selection

class RegionSelector(tk.Toplevel):
    """
    Full-screen transparent overlay that lets the user drag-select a region.
    Returns (x, y, width, height) via the `result` attribute after closing.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None

        # ── Overlay styling ───────────────────────────────────────────────
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.25)
        self.configure(bg="black", cursor="crosshair")
        self.attributes("-topmost", True)

        # ── Canvas covers entire screen ───────────────────────────────────
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.canvas = tk.Canvas(self, width=sw, height=sh,
                                bg="black", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        # Instruction label
        self.canvas.create_text(sw // 2, 40,
                                text="Drag to select a region  •  ESC to cancel",
                                fill="white", font=("Helvetica", 16, "bold"))

        self._start_x = self._start_y = 0
        self._rect_id = None

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",        self._on_drag)
        self.canvas.bind("<ButtonRelease-1>",  self._on_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_press(self, event):
        self._start_x, self._start_y = event.x, event.y
        if self._rect_id:
            self.canvas.delete(self._rect_id)

    def _on_drag(self, event):
        if self._rect_id:
            self.canvas.delete(self._rect_id)
        self._rect_id = self.canvas.create_rectangle(
            self._start_x, self._start_y, event.x, event.y,
            outline="#7c6af7", width=2, fill="#7c6af7", stipple="gray25"
        )

    def _on_release(self, event):
        x1 = min(self._start_x, event.x)
        y1 = min(self._start_y, event.y)
        x2 = max(self._start_x, event.x)
        y2 = max(self._start_y, event.y)
        w  = x2 - x1
        h  = y2 - y1
        if w > 5 and h > 5:           # ignore tiny accidental clicks
            self.result = (x1, y1, w, h)
        self.destroy()


#  STYLED WIDGETS — reusable themed components

class StyledButton(tk.Frame):
    """
    A custom button with rounded-rectangle look, hover effects, and icon support.
    Falls back gracefully when canvas gradients aren't needed.
    """

    def __init__(self, parent, text="", icon="", command=None,
                 style="accent", theme=None, **kwargs):
        super().__init__(parent, bg=theme["bg"] if theme else "#0f1117",
                         **kwargs)
        self.command  = command
        self.theme    = theme or THEMES["dark"]
        self.style    = style
        self._pressed = False

        # Determine base colour based on style
        colour_map = {
            "accent":  self.theme["accent"],
            "success": self.theme["success"],
            "danger":  self.theme["danger"],
            "ghost":   self.theme["surface2"],
        }
        self._base_color  = colour_map.get(style, self.theme["accent"])
        self._hover_color = self.theme["accent_hover"] if style == "accent" else self._base_color

        label_text = f"{icon}  {text}" if icon else text
        self._label = tk.Label(self, text=label_text,
                               bg=self._base_color,
                               fg=self.theme["btn_fg"],
                               font=("Helvetica", 10, "bold"),
                               padx=14, pady=8, cursor="hand2")
        self._label.pack(fill="both", expand=True)

        # Bind hover + click events to both frame and label
        for w in (self, self._label):
            w.bind("<Enter>",          self._on_enter)
            w.bind("<Leave>",          self._on_leave)
            w.bind("<ButtonPress-1>",  self._on_press)
            w.bind("<ButtonRelease-1>",self._on_release)

    def _on_enter(self, _):
        self._label.config(bg=self._hover_color)

    def _on_leave(self, _):
        self._label.config(bg=self._base_color)

    def _on_press(self, _):
        self._pressed = True

    def _on_release(self, _):
        if self._pressed and self.command:
            self.command()
        self._pressed = False

    def update_theme(self, theme: dict):
        self.theme = theme
        colour_map = {
            "accent":  theme["accent"],
            "success": theme["success"],
            "danger":  theme["danger"],
            "ghost":   theme["surface2"],
        }
        self._base_color  = colour_map.get(self.style, theme["accent"])
        self._hover_color = theme["accent_hover"] if self.style == "accent" else self._base_color
        self._label.config(bg=self._base_color, fg=theme["btn_fg"])
        self.config(bg=theme["bg"])


#  MAIN APPLICATION WINDOW

class SnapshotApp(tk.Tk):

    def __init__(self):
        super().__init__()

        # ── App state ─────────────────────────────────────────────────────
        self.settings  = SettingsManager()
        self.engine    = ScreenshotEngine(self.settings.get("save_location", "screenshots"))
        self.theme_name = tk.StringVar(value=self.settings.get("theme", "dark"))
        self.T          = THEMES[self.theme_name.get()]   # active colour palette
        self.counter    = tk.IntVar(value=self.settings.get("screenshot_count", 0))

        self.delay_var    = tk.IntVar(value=self.settings.get("delay", 0))
        self.auto_open    = tk.BooleanVar(value=self.settings.get("auto_open", False))
        self.minimize_var = tk.BooleanVar(value=self.settings.get("minimize_on_capture", True))

        self._history: list[dict] = []   # [{path, thumb, time}, ...]
        self._last_image: Image.Image | None = None
        self._capturing = False

        # ── Window setup ─────────────────────────────────────────────────
        self.title(f"{APP_TITLE}  v{APP_VERSION}")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg=self.T["bg"])

        # Custom title-bar icon (coloured square as placeholder)
        self._set_icon()

        # ── Build UI ─────────────────────────────────────────────────────
        self._build_header()
        self._build_body()
        self._build_statusbar()

        # ── Keyboard shortcut ─────────────────────────────────────────────
        self.bind("<Control-Shift-S>", lambda e: self._capture_fullscreen())
        self.bind("<Control-Shift-R>", lambda e: self._capture_region())
        if KEYBOARD_AVAILABLE:
            keyboard.add_hotkey("ctrl+shift+s", self._hotkey_capture)

        self._set_status("Ready — press Ctrl+Shift+S for quick capture", "dim")

    # ── Icon ──────────────────────────────────────────────────────────────────

    def _set_icon(self):
        """Create a simple camera-lens icon programmatically."""
        try:
            size = 64
            img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([4, 4, size-4, size-4], fill="#7c6af7")
            draw.ellipse([18, 18, size-18, size-18], fill="#0f1117")
            draw.ellipse([24, 24, size-24, size-24], fill="#7c6af7")
            icon = ImageTk.PhotoImage(img)
            self.iconphoto(True, icon)
            self._icon_ref = icon   # prevent GC
        except Exception:
            pass  # skip if ImageDraw is unavailable

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=self.T["surface"], height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        self._header_frame = hdr

        # Logo + title
        tk.Label(hdr, text="📷", font=("Helvetica", 22),
                 bg=self.T["surface"], fg=self.T["accent"]).pack(side="left", padx=(20, 6), pady=10)
        tk.Label(hdr, text=APP_TITLE, font=("Helvetica", 18, "bold"),
                 bg=self.T["surface"], fg=self.T["text"]).pack(side="left", pady=10)

        # Counter badge
        counter_frame = tk.Frame(hdr, bg=self.T["accent"], padx=8, pady=2)
        counter_frame.pack(side="left", padx=20, pady=18)
        tk.Label(counter_frame, text="CAPTURES", font=("Helvetica", 7, "bold"),
                 bg=self.T["accent"], fg="white").pack()
        self._counter_label = tk.Label(counter_frame, textvariable=self.counter,
                                       font=("Helvetica", 13, "bold"),
                                       bg=self.T["accent"], fg="white")
        self._counter_label.pack()

        # Theme toggle (right side)
        self._theme_btn = tk.Label(hdr, text="☀  Light Mode",
                                   font=("Helvetica", 10),
                                   bg=self.T["surface2"], fg=self.T["text"],
                                   padx=12, pady=6, cursor="hand2")
        self._theme_btn.pack(side="right", padx=20, pady=16)
        self._theme_btn.bind("<Button-1>", lambda e: self._toggle_theme())

        self._hdr_sep = tk.Frame(self, bg=self.T["border"], height=1)
        self._hdr_sep.pack(fill="x")

    # ── Three-column body ─────────────────────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True)
        self._body_frame = body

        # Column weights: left=1, center=3, right=2
        body.columnconfigure(0, weight=1, minsize=220)
        body.columnconfigure(1, weight=3)
        body.columnconfigure(2, weight=2, minsize=220)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_center_panel(body)
        self._build_right_panel(body)

    # ── Left panel — capture controls ─────────────────────────────────────────

    def _build_left_panel(self, parent):
        panel = tk.Frame(parent, bg=self.T["surface"], padx=16, pady=16)
        panel.grid(row=0, column=0, sticky="nsew", padx=(12, 4), pady=12)
        self._left_panel = panel

        def section(title):
            tk.Label(panel, text=title, font=("Helvetica", 9, "bold"),
                     bg=self.T["surface"], fg=self.T["text_dim"]).pack(anchor="w", pady=(12, 4))
            tk.Frame(panel, bg=self.T["border"], height=1).pack(fill="x")

        # ── Capture type ──────────────────────────────────────────────────
        section("CAPTURE TYPE")
        btn_data = [
            ("🖥   Full Screen",     self._capture_fullscreen, "accent"),
            ("✂   Select Region",   self._capture_region,     "accent"),
            ("🪟  Active Window",   self._capture_window,     "accent"),
        ]
        self._capture_buttons = []
        for text, cmd, style in btn_data:
            b = StyledButton(panel, text=text, command=cmd,
                             style=style, theme=self.T)
            b.pack(fill="x", pady=3)
            self._capture_buttons.append(b)

        # ── Delay timer ───────────────────────────────────────────────────
        section("DELAY TIMER")
        delay_row = tk.Frame(panel, bg=self.T["surface"])
        delay_row.pack(fill="x", pady=4)
        delays = [("None", 0), ("3 s", 3), ("5 s", 5), ("10 s", 10)]
        self._delay_radios = []
        for label, val in delays:
            rb = tk.Radiobutton(delay_row, text=label, value=val,
                                variable=self.delay_var,
                                bg=self.T["surface"], fg=self.T["text"],
                                selectcolor=self.T["surface2"],
                                activebackground=self.T["surface"],
                                font=("Helvetica", 10),
                                command=lambda v=val: self.settings.set("delay", v))
            rb.pack(side="left", padx=4)
            self._delay_radios.append(rb)

        # ── Options ───────────────────────────────────────────────────────
        section("OPTIONS")
        self._auto_chk = tk.Checkbutton(panel, text="Auto-open after capture",
                                        variable=self.auto_open,
                                        bg=self.T["surface"], fg=self.T["text"],
                                        selectcolor=self.T["surface2"],
                                        activebackground=self.T["surface"],
                                        font=("Helvetica", 10),
                                        command=lambda: self.settings.set("auto_open", self.auto_open.get()))
        self._auto_chk.pack(anchor="w", pady=2)

        self._min_chk = tk.Checkbutton(panel, text="Minimize while capturing",
                                       variable=self.minimize_var,
                                       bg=self.T["surface"], fg=self.T["text"],
                                       selectcolor=self.T["surface2"],
                                       activebackground=self.T["surface"],
                                       font=("Helvetica", 10),
                                       command=lambda: self.settings.set("minimize_on_capture", self.minimize_var.get()))
        self._min_chk.pack(anchor="w", pady=2)

        # ── Save location ─────────────────────────────────────────────────
        section("SAVE LOCATION")
        self._save_loc_var = tk.StringVar(value=self.settings.get("save_location", "screenshots"))
        loc_row = tk.Frame(panel, bg=self.T["surface"])
        loc_row.pack(fill="x", pady=4)
        self._save_entry = tk.Entry(loc_row, textvariable=self._save_loc_var,
                                    bg=self.T["surface2"], fg=self.T["text"],
                                    insertbackground=self.T["text"],
                                    relief="flat", font=("Helvetica", 9))
        self._save_entry.pack(side="left", fill="x", expand=True)
        browse_btn = tk.Label(loc_row, text="📂", font=("Helvetica", 14),
                              bg=self.T["surface"], fg=self.T["accent"],
                              cursor="hand2", padx=4)
        browse_btn.pack(side="right")
        browse_btn.bind("<Button-1>", lambda e: self._browse_save_location())

        # ── Post-capture actions ──────────────────────────────────────────
        section("AFTER CAPTURE")
        self._copy_btn = StyledButton(panel, text="📋  Copy to Clipboard",
                                      command=self._copy_to_clipboard,
                                      style="ghost", theme=self.T)
        self._copy_btn.pack(fill="x", pady=3)

        # Spacer
        tk.Frame(panel, bg=self.T["surface"]).pack(fill="y", expand=True)

        # Keyboard shortcut hint
        tk.Label(panel, text="⌨  Ctrl+Shift+S  Quick Capture",
                 font=("Helvetica", 8), bg=self.T["surface"],
                 fg=self.T["text_dim"]).pack(anchor="w", pady=(8, 0))

    # ── Center panel — preview ─────────────────────────────────────────────

    def _build_center_panel(self, parent):
        panel = tk.Frame(parent, bg=self.T["surface"])
        panel.grid(row=0, column=1, sticky="nsew", padx=4, pady=12)
        self._center_panel = panel

        # Section label
        top_bar = tk.Frame(panel, bg=self.T["surface2"], height=36)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)
        tk.Label(top_bar, text="LIVE PREVIEW", font=("Helvetica", 9, "bold"),
                 bg=self.T["surface2"], fg=self.T["text_dim"],
                 padx=16).pack(side="left", pady=8)
        self._preview_label_info = tk.Label(top_bar, text="",
                                            font=("Helvetica", 9),
                                            bg=self.T["surface2"], fg=self.T["accent"],
                                            padx=16)
        self._preview_label_info.pack(side="right", pady=8)

        # Preview canvas
        self._preview_canvas = tk.Canvas(panel, bg=self.T["bg"],
                                         highlightthickness=0)
        self._preview_canvas.pack(fill="both", expand=True, padx=2, pady=2)
        self._preview_canvas.bind("<Configure>", self._on_preview_resize)

        # Placeholder text
        self._placeholder_id = self._preview_canvas.create_text(
            400, 300, text="📸\n\nCapture a screenshot\nto see a preview here",
            font=("Helvetica", 14), fill=self.T["text_dim"], justify="center"
        )

        # Countdown overlay label
        self._countdown_var = tk.StringVar(value="")
        self._countdown_lbl = tk.Label(panel, textvariable=self._countdown_var,
                                       font=("Helvetica", 72, "bold"),
                                       bg=self.T["bg"], fg=self.T["accent"])

        # Status bar within preview
        self._status_frame = tk.Frame(panel, bg=self.T["surface2"], height=32)
        self._status_frame.pack(fill="x", side="bottom")
        self._status_frame.pack_propagate(False)
        self._status_icon = tk.Label(self._status_frame, text="●",
                                     font=("Helvetica", 8),
                                     bg=self.T["surface2"], fg=self.T["text_dim"])
        self._status_icon.pack(side="left", padx=(12, 4), pady=8)
        self._status_msg = tk.Label(self._status_frame, text="",
                                    font=("Helvetica", 9),
                                    bg=self.T["surface2"], fg=self.T["text"])
        self._status_msg.pack(side="left", pady=8)

    # ── Right panel — history ──────────────────────────────────────────────

    def _build_right_panel(self, parent):
        panel = tk.Frame(parent, bg=self.T["surface"])
        panel.grid(row=0, column=2, sticky="nsew", padx=(4, 12), pady=12)
        self._right_panel = panel

        top = tk.Frame(panel, bg=self.T["surface2"], height=36)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="HISTORY", font=("Helvetica", 9, "bold"),
                 bg=self.T["surface2"], fg=self.T["text_dim"],
                 padx=12).pack(side="left", pady=8)

        clear_btn = tk.Label(top, text="Clear", font=("Helvetica", 9),
                             bg=self.T["surface2"], fg=self.T["danger"],
                             padx=12, cursor="hand2")
        clear_btn.pack(side="right", pady=8)
        clear_btn.bind("<Button-1>", lambda e: self._clear_history())

        # Scrollable history list
        list_frame = tk.Frame(panel, bg=self.T["bg"])
        list_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical",
                                  bg=self.T["surface2"])
        self._history_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                           bg=self.T["bg"], fg=self.T["text"],
                                           selectbackground=self.T["history_sel"],
                                           selectforeground=self.T["accent"],
                                           font=("Courier", 9),
                                           relief="flat", bd=0,
                                           activestyle="none")
        scrollbar.config(command=self._history_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self._history_listbox.pack(side="left", fill="both", expand=True)
        self._history_listbox.bind("<<ListboxSelect>>", self._on_history_select)
        self._history_listbox.bind("<Double-Button-1>",  self._on_history_open)

        # Action buttons below history
        action_frame = tk.Frame(panel, bg=self.T["surface2"], pady=8)
        action_frame.pack(fill="x")
        self._open_btn   = StyledButton(action_frame, text="Open",   style="accent",  theme=self.T, command=self._on_history_open)
        self._del_btn    = StyledButton(action_frame, text="Delete",  style="danger",  theme=self.T, command=self._delete_selected)
        self._open_btn.pack(side="left",  fill="x", expand=True, padx=(8, 4), pady=4)
        self._del_btn.pack( side="right", fill="x", expand=True, padx=(4, 8), pady=4)

    # ── Status bar ─────────────────────────────────────────────────────────

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=self.T["surface"], height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self._bottom_bar = bar

        self._bottom_left = tk.Label(bar, text=f"{APP_TITLE}  v{APP_VERSION}",
                                     font=("Helvetica", 8),
                                     bg=self.T["surface"], fg=self.T["text_dim"])
        self._bottom_left.pack(side="left", padx=12)

        self._bottom_right = tk.Label(bar,
                                      text="Ctrl+Shift+S: Full Screen  •  Ctrl+Shift+R: Region",
                                      font=("Helvetica", 8),
                                      bg=self.T["surface"], fg=self.T["text_dim"])
        self._bottom_right.pack(side="right", padx=12)

    # ── Capture orchestration ──────────────────────────────────────────────

    def _run_capture(self, capture_fn):
        """
        Common wrapper for all capture types:
          1. Optionally minimize
          2. Show countdown
          3. Run capture on a background thread
          4. Restore window + update UI
        """
        if self._capturing:
            return
        self._capturing = True

        delay = self.delay_var.get()

        # Minimize app if requested
        if self.minimize_var.get():
            self.iconify()
        else:
            self.lower()     # push behind other windows

        def _worker():
            # Countdown
            if delay > 0:
                for remaining in range(delay, 0, -1):
                    self.after(0, lambda r=remaining: self._show_countdown(r))
                    time.sleep(1)
                self.after(0, self._hide_countdown)

            time.sleep(0.15)   # tiny pause to let the minimize animation finish

            try:
                img, path = capture_fn()
                self.after(0, lambda: self._on_capture_success(img, path))
            except Exception as exc:
                self.after(0, lambda e=exc: self._on_capture_error(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _capture_fullscreen(self):
        self._run_capture(self.engine.capture_fullscreen)

    def _capture_region(self):
        """Open region selector, then capture the chosen area."""
        # Don't minimize — the selector needs to be on top
        selector = RegionSelector(self)
        self.wait_window(selector)
        region = selector.result
        if not region:
            return  # user cancelled
        self._run_capture(lambda: self.engine.capture_region(*region))

    def _capture_window(self):
        """Capture the topmost window (approximated by region selector guidance)."""
        messagebox.showinfo("Window Capture",
                            "Click OK, then drag a rectangle around the window you want to capture.")
        self._capture_region()

    def _hotkey_capture(self):
        """Called by the global keyboard hook — schedule on main thread."""
        self.after(0, self._capture_fullscreen)

    # ── Post-capture callbacks ─────────────────────────────────────────────

    def _on_capture_success(self, img: Image.Image, path: str):
        """Called on the main thread after a successful capture."""
        self._last_image = img
        self._capturing  = False

        # Increment counter
        count = self.counter.get() + 1
        self.counter.set(count)
        self.settings.set("screenshot_count", count)

        # Update preview
        self._update_preview(img)
        self._preview_label_info.config(text=os.path.basename(path))

        # Add to history
        self._add_to_history(path, img)

        # Status feedback
        self._set_status(f"✓  Saved: {path}", "success")

        # Optional auto-open
        if self.auto_open.get():
            self._open_file(path)

        # Restore window
        self.deiconify()
        self.lift()

    def _on_capture_error(self, exc: Exception):
        self._capturing = False
        self.deiconify()
        self.lift()
        self._set_status(f"✗  Error: {exc}", "danger")
        messagebox.showerror("Capture Error", str(exc))

    # ── Preview ────────────────────────────────────────────────────────────

    def _update_preview(self, img: Image.Image):
        """Fit the screenshot into the preview canvas, preserving aspect ratio."""
        canvas  = self._preview_canvas
        cw = canvas.winfo_width()  or 600
        ch = canvas.winfo_height() or 400

        img_copy = img.copy()
        img_copy.thumbnail((cw - 8, ch - 8), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img_copy)

        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, anchor="center", image=photo)
        canvas._photo_ref = photo   # prevent garbage collection

    def _on_preview_resize(self, event):
        """Re-render preview when the canvas is resized."""
        if self._last_image:
            self._update_preview(self._last_image)

    # ── Countdown ─────────────────────────────────────────────────────────

    def _show_countdown(self, remaining: int):
        self._countdown_var.set(str(remaining))
        self._countdown_lbl.place(relx=0.5, rely=0.5, anchor="center")
        self._countdown_lbl.lift()

    def _hide_countdown(self):
        self._countdown_var.set("")
        self._countdown_lbl.place_forget()

    # ── History management ─────────────────────────────────────────────────

    def _add_to_history(self, path: str, img: Image.Image):
        """Prepend a new entry to the history list."""
        ts    = datetime.now().strftime("%H:%M:%S")
        label = f"  {ts}  {os.path.basename(path)}"
        self._history.insert(0, {"path": path, "img": img, "label": label})
        self._history_listbox.insert(0, label)

    def _on_history_select(self, _event=None):
        """Show the selected history item in the preview."""
        idx = self._history_listbox.curselection()
        if not idx:
            return
        entry = self._history[idx[0]]
        self._update_preview(entry["img"])
        self._preview_label_info.config(text=os.path.basename(entry["path"]))
        self._last_image = entry["img"]

    def _on_history_open(self, _event=None):
        """Open the selected screenshot in the OS default viewer."""
        idx = self._history_listbox.curselection()
        if not idx:
            return
        self._open_file(self._history[idx[0]]["path"])

    def _delete_selected(self):
        """Remove the selected history entry (and optionally the file)."""
        idx = self._history_listbox.curselection()
        if not idx:
            return
        i     = idx[0]
        entry = self._history[i]
        if messagebox.askyesno("Delete Screenshot",
                               f"Delete file?\n{entry['path']}"):
            try:
                os.remove(entry["path"])
            except OSError:
                pass
            self._history.pop(i)
            self._history_listbox.delete(i)
            self._set_status(f"Deleted: {os.path.basename(entry['path'])}", "dim")

    def _clear_history(self):
        """Clear the history list (files remain on disk)."""
        self._history.clear()
        self._history_listbox.delete(0, "end")
        self._set_status("History cleared", "dim")

    # ── Clipboard ─────────────────────────────────────────────────────────

    def _copy_to_clipboard(self):
        if self._last_image is None:
            messagebox.showinfo("No Screenshot", "Capture a screenshot first.")
            return
        success = self.engine.copy_to_clipboard(self._last_image)
        if success:
            self._set_status("✓  Copied to clipboard", "success")
        else:
            self._set_status("⚠  Clipboard copy not supported on this OS", "warning")

    # ── Save location ──────────────────────────────────────────────────────

    def _browse_save_location(self):
        chosen = filedialog.askdirectory(title="Choose Save Location")
        if chosen:
            self._save_loc_var.set(chosen)
            self.engine.set_save_dir(chosen)
            self.settings.set("save_location", chosen)
            self._set_status(f"Save location: {chosen}", "dim")

    # ── File utilities ─────────────────────────────────────────────────────

    @staticmethod
    def _open_file(path: str):
        """Open a file using the OS default application."""
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            print(f"[Open File] {e}")

    # ── Status helpers ─────────────────────────────────────────────────────

    def _set_status(self, message: str, level: str = "dim"):
        colour_map = {
            "dim":     self.T["text_dim"],
            "success": self.T["success"],
            "warning": self.T["warning"],
            "danger":  self.T["danger"],
        }
        icon_map = {
            "dim":     "●",
            "success": "✔",
            "warning": "⚠",
            "danger":  "✖",
        }
        fg = colour_map.get(level, self.T["text_dim"])
        self._status_icon.config(text=icon_map.get(level, "●"), fg=fg)
        self._status_msg.config(text=message, fg=fg)

    # ── Theme toggle ───────────────────────────────────────────────────────

    def _toggle_theme(self):
        new_theme = "light" if self.theme_name.get() == "dark" else "dark"
        self.theme_name.set(new_theme)
        self.T = THEMES[new_theme]
        self.settings.set("theme", new_theme)
        self._apply_theme()

    def _apply_theme(self):
        """Re-colour all widgets when the theme changes."""
        T = self.T
        self.configure(bg=T["bg"])

        # Header
        self._header_frame.configure(bg=T["surface"])
        self._hdr_sep.configure(bg=T["border"])
        icon_lbl = self._theme_btn
        icon_lbl.config(bg=T["surface2"], fg=T["text"],
                        text="🌙  Dark Mode" if self.theme_name.get() == "light" else "☀  Light Mode")

        # Counter badge
        self._counter_label.config(bg=T["accent"])

        # Body panels
        for p in (self._left_panel, self._center_panel, self._right_panel):
            p.configure(bg=T["surface"])

        # Preview canvas
        self._preview_canvas.configure(bg=T["bg"])

        # Left panel internals — easiest to just rebuild, but we do in-place
        for rb in self._delay_radios:
            rb.config(bg=T["surface"], fg=T["text"], selectcolor=T["surface2"],
                      activebackground=T["surface"])
        self._auto_chk.config(bg=T["surface"], fg=T["text"],
                              selectcolor=T["surface2"], activebackground=T["surface"])
        self._min_chk.config(bg=T["surface"], fg=T["text"],
                             selectcolor=T["surface2"], activebackground=T["surface"])
        self._save_entry.config(bg=T["surface2"], fg=T["text"],
                                insertbackground=T["text"])

        for btn in self._capture_buttons:
            btn.update_theme(T)
        self._copy_btn.update_theme(T)
        self._open_btn.update_theme(T)
        self._del_btn.update_theme(T)

        # History listbox
        self._history_listbox.config(bg=T["bg"], fg=T["text"],
                                     selectbackground=T["history_sel"],
                                     selectforeground=T["accent"])

        # Status bar
        self._status_frame.configure(bg=T["surface2"])
        self._status_icon.configure(bg=T["surface2"])
        self._status_msg.configure(bg=T["surface2"])
        self._bottom_bar.configure(bg=T["surface"])
        self._bottom_left.configure(bg=T["surface"], fg=T["text_dim"])
        self._bottom_right.configure(bg=T["surface"], fg=T["text_dim"])

        # Countdown label
        self._countdown_lbl.configure(bg=T["bg"], fg=T["accent"])

        # Body frame
        self._body_frame.configure(bg=T["bg"])

        # Redraw placeholder text colour
        try:
            self._preview_canvas.itemconfig(self._placeholder_id, fill=T["text_dim"])
        except Exception:
            pass


#  ENTRY POINT

def main():
    app = SnapshotApp()
    app.mainloop()


if __name__ == "__main__":
    main()