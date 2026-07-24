import os
import re
import csv
import queue
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import qrcode
from PIL import Image, ImageTk

# ==========================================
# DESIGN THEME & COLOR CONSTANTS (Catppuccin-inspired)
# ==========================================
BG_DARK = "#0f0f17"       # App background
BG_PANEL = "#161622"      # Left sidebar background
BG_CARD = "#1f1f2e"       # Main area content cards
BG_INPUT = "#2b2b3d"      # Entry/Text widgets background
FG_TEXT = "#e2e8f0"       # High contrast text
FG_MUTED = "#94a3b8"      # Low contrast text
ACCENT_BLUE = "#3b82f6"   # Primary action color
ACCENT_HOVER = "#60a5fa"  # Primary action hover
ACCENT_GREEN = "#10b981"  # Success color / generation start
ACCENT_RED = "#f43f5e"    # Error/danger color
ACCENT_PURPLE = "#8b5cf6" # Secondary actions

class QRGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("muhp - Premium QR Code Studio")
        self.geometry("980x680")
        self.configure(bg=BG_DARK)
        self.minsize(920, 620)
        
        # Icon / Window properties
        self.setup_styles()
        
        # State Variables
        self.fg_color = "#000000"
        self.bg_color = "#ffffff"
        self.current_qr_image = None
        self.qr_photo = None
        
        # Bulk generation states
        self.imported_data = []  # List of rows for bulk generation
        self.csv_headers = []
        self.selected_file_path = ""
        self.queue = queue.Queue()
        self.bulk_running = False
        
        # UI components setup
        self.create_widgets()
        
        # Apply default color palette
        self.apply_palette("Classic Light")
        
        # Setup polling for thread queue
        self.check_queue()

    def setup_styles(self):
        """Set up global ttk styles for widgets that require it."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # TCombobox custom styling
        style.configure("TCombobox", 
                        fieldbackground=BG_INPUT, 
                        background=BG_INPUT, 
                        foreground=FG_TEXT, 
                        bordercolor=BG_INPUT, 
                        arrowcolor=FG_TEXT,
                        padding=5)
        style.map("TCombobox", 
                  fieldbackground=[("readonly", BG_INPUT)],
                  foreground=[("readonly", FG_TEXT)])
        
        # Configure the dropdown list colors globally via OptionDB
        self.option_add('*TCombobox*Listbox.background', BG_INPUT)
        self.option_add('*TCombobox*Listbox.foreground', FG_TEXT)
        self.option_add('*TCombobox*Listbox.selectBackground', ACCENT_BLUE)
        self.option_add('*TCombobox*Listbox.selectForeground', BG_DARK)
        self.option_add('*TCombobox*Listbox.font', ("Segoe UI", 9))
        
        # TProgressbar styling
        style.configure("Horizontal.TProgressbar",
                        background=ACCENT_BLUE,
                        troughcolor=BG_INPUT,
                        bordercolor=BG_INPUT,
                        lightcolor=ACCENT_BLUE,
                        darkcolor=ACCENT_BLUE)

    def create_widgets(self):
        """Create and layout all Tkinter widgets."""
        # --- Root grid config ---
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main Area
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # SIDEBAR PANEL (Left, Settings)
        # ==========================================
        sidebar = tk.Frame(self, bg=BG_PANEL, width=280, padx=15, pady=15)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        
        # Sidebar Logo Header
        logo_frame = tk.Frame(sidebar, bg=BG_PANEL)
        logo_frame.pack(fill="x", pady=(0, 20))
        logo_lbl = tk.Label(logo_frame, text="❖ muhp Studio", bg=BG_PANEL, fg=ACCENT_BLUE, 
                            font=("Segoe UI Semibold", 16, "bold"))
        logo_lbl.pack(anchor="w")
        sub_lbl = tk.Label(logo_frame, text="Professional Generator", bg=BG_PANEL, fg=FG_MUTED, 
                           font=("Segoe UI", 8))
        sub_lbl.pack(anchor="w", padx=2)
        
        # Separator line
        self.create_sep(sidebar, BG_INPUT).pack(fill="x", pady=(0, 15))

        # Config Header
        cfg_title = tk.Label(sidebar, text="QR CODE STYLING", bg=BG_PANEL, fg=FG_TEXT,
                             font=("Segoe UI", 10, "bold"))
        cfg_title.pack(anchor="w", pady=(0, 10))

        # --- Error Correction Level ---
        lbl_err = tk.Label(sidebar, text="Error Correction Level", bg=BG_PANEL, fg=FG_MUTED, font=("Segoe UI", 9))
        lbl_err.pack(anchor="w", pady=(5, 2))
        self.var_err = tk.StringVar(value="Medium (15%)")
        cb_err = ttk.Combobox(sidebar, textvariable=self.var_err, state="readonly", 
                              values=["Low (7%)", "Medium (15%)", "Quartile (25%)", "High (30%)"])
        cb_err.pack(fill="x", pady=(0, 10))

        # --- Box Size ---
        lbl_box = tk.Label(sidebar, text="Box Size (pixels per block)", bg=BG_PANEL, fg=FG_MUTED, font=("Segoe UI", 9))
        lbl_box.pack(anchor="w", pady=(5, 0))
        self.var_box_size = tk.IntVar(value=10)
        slider_box = tk.Scale(sidebar, from_=5, to=30, orient="horizontal", variable=self.var_box_size,
                              bg=BG_PANEL, fg=FG_TEXT, activebackground=ACCENT_BLUE, highlightthickness=0,
                              troughcolor=BG_INPUT, bd=0, font=("Segoe UI", 8))
        slider_box.pack(fill="x", pady=(0, 10))

        # --- Border Size ---
        lbl_border = tk.Label(sidebar, text="Border Size (blocks)", bg=BG_PANEL, fg=FG_MUTED, font=("Segoe UI", 9))
        lbl_border.pack(anchor="w", pady=(5, 0))
        self.var_border_size = tk.IntVar(value=4)
        slider_border = tk.Scale(sidebar, from_=0, to=10, orient="horizontal", variable=self.var_border_size,
                                 bg=BG_PANEL, fg=FG_TEXT, activebackground=ACCENT_BLUE, highlightthickness=0,
                                 troughcolor=BG_INPUT, bd=0, font=("Segoe UI", 8))
        slider_border.pack(fill="x", pady=(0, 15))
        
        self.create_sep(sidebar, BG_INPUT).pack(fill="x", pady=(0, 15))

        # --- Color Themes & Custom Colors ---
        lbl_colors = tk.Label(sidebar, text="COLOR PROFILE", bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 10, "bold"))
        lbl_colors.pack(anchor="w", pady=(0, 10))
        
        # Color Palettes
        lbl_pal = tk.Label(sidebar, text="Presets Palette", bg=BG_PANEL, fg=FG_MUTED, font=("Segoe UI", 9))
        lbl_pal.pack(anchor="w", pady=(5, 2))
        self.var_palette = tk.StringVar(value="Classic Light")
        cb_pal = ttk.Combobox(sidebar, textvariable=self.var_palette, state="readonly",
                              values=["Classic Light", "Classic Dark", "Neon Indigo", "Cyberpunk", "Forest", "Sunset"])
        cb_pal.pack(fill="x", pady=(0, 12))
        cb_pal.bind("<<ComboboxSelected>>", lambda e: self.apply_palette(self.var_palette.get()))

        # Custom Foreground Color
        fg_frame = tk.Frame(sidebar, bg=BG_PANEL)
        fg_frame.pack(fill="x", pady=4)
        self.fg_preview = tk.Canvas(fg_frame, width=20, height=20, bg="#000000", highlightthickness=1, highlightbackground=BG_INPUT)
        self.fg_preview.pack(side="left")
        self.fg_preview.bind("<Button-1>", lambda e: self.pick_color("fg"))
        
        btn_fg = self.create_hover_button(fg_frame, "Foreground Color", lambda: self.pick_color("fg"),
                                           BG_INPUT, FG_TEXT, BG_CARD, font=("Segoe UI", 9), anchor="w")
        btn_fg.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Custom Background Color
        bg_frame = tk.Frame(sidebar, bg=BG_PANEL)
        bg_frame.pack(fill="x", pady=4)
        self.bg_preview = tk.Canvas(bg_frame, width=20, height=20, bg="#ffffff", highlightthickness=1, highlightbackground=BG_INPUT)
        self.bg_preview.pack(side="left")
        self.bg_preview.bind("<Button-1>", lambda e: self.pick_color("bg"))
        
        btn_bg = self.create_hover_button(bg_frame, "Background Color", lambda: self.pick_color("bg"),
                                           BG_INPUT, FG_TEXT, BG_CARD, font=("Segoe UI", 9), anchor="w")
        btn_bg.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Footer branding
        footer = tk.Label(sidebar, text="Built with Python & Tkinter", bg=BG_PANEL, fg=FG_MUTED, font=("Segoe UI Italic", 8))
        footer.pack(side="bottom", fill="x", pady=10)

        # ==========================================
        # MAIN CONTENT AREA (Right, Tabs)
        # ==========================================
        self.main_area = tk.Frame(self, bg=BG_DARK, padx=20, pady=15)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(1, weight=1) # The Tab Frames

        # --- Tab Header Navigation ---
        tab_header = tk.Frame(self.main_area, bg=BG_DARK)
        tab_header.grid(row=0, column=0, sticky="ew", pady=(0, 15))

        self.btn_tab_single = tk.Button(
            tab_header, text="Single QR Code", font=("Segoe UI Semibold", 11, "bold"),
            bg=BG_CARD, fg=FG_TEXT, activebackground=BG_CARD, activeforeground=FG_TEXT,
            bd=0, relief="flat", padx=20, pady=10, cursor="hand2",
            command=self.show_single_tab
        )
        self.btn_tab_single.pack(side="left", padx=(0, 4))

        self.btn_tab_bulk = tk.Button(
            tab_header, text="Bulk Generator", font=("Segoe UI Semibold", 11, "bold"),
            bg=BG_DARK, fg=FG_MUTED, activebackground=BG_DARK, activeforeground=FG_TEXT,
            bd=0, relief="flat", padx=20, pady=10, cursor="hand2",
            command=self.show_bulk_tab
        )
        self.btn_tab_bulk.pack(side="left")

        # Underline indicator
        self.tab_indicator = tk.Frame(self.main_area, bg=ACCENT_BLUE, height=3)
        self.tab_indicator.grid(row=0, column=0, sticky="sw", pady=(32, 12)) # Placed manually

        # ==========================================
        # TAB 1: SINGLE QR CODE FRAME
        # ==========================================
        self.frame_single = tk.Frame(self.main_area, bg=BG_DARK)
        self.frame_single.grid_columnconfigure(0, weight=1) # Input card
        self.frame_single.grid_columnconfigure(1, weight=1) # Preview card
        self.frame_single.grid_rowconfigure(0, weight=1)

        # --- Left Side: Input Card ---
        card_input = tk.Frame(self.frame_single, bg=BG_CARD, padx=20, pady=20, bd=0)
        card_input.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        card_input.grid_columnconfigure(0, weight=1)
        card_input.grid_rowconfigure(1, weight=1)

        lbl_input = tk.Label(card_input, text="Enter URL or Text to Encode:", bg=BG_CARD, fg=FG_TEXT,
                             font=("Segoe UI Semibold", 11))
        lbl_input.pack(anchor="w", pady=(0, 10))

        # Text input wrapper
        text_wrapper = tk.Frame(card_input, bg=BG_INPUT, bd=1)
        text_wrapper.pack(fill="both", expand=True, pady=(0, 15))
        self.txt_single_input = tk.Text(text_wrapper, bg=BG_INPUT, fg=FG_TEXT, insertbackground=FG_TEXT,
                                        relief="flat", font=("Segoe UI", 10), wrap="word", undo=True)
        self.txt_single_input.pack(fill="both", expand=True, padx=8, pady=8)
        self.txt_single_input.insert("1.0", "https://github.com")

        # Action Buttons for Single QR
        single_btn_frame = tk.Frame(card_input, bg=BG_CARD)
        single_btn_frame.pack(fill="x")
        
        self.btn_generate_single = self.create_hover_button(
            single_btn_frame, "Generate QR Code", self.generate_single_qr,
            ACCENT_BLUE, BG_DARK, ACCENT_HOVER, font=("Segoe UI", 10, "bold")
        )
        self.btn_generate_single.pack(fill="x", side="left", expand=True, padx=(0, 5))

        # --- Right Side: Preview Card ---
        card_preview = tk.Frame(self.frame_single, bg=BG_CARD, padx=20, pady=20)
        card_preview.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        card_preview.grid_columnconfigure(0, weight=1)
        card_preview.grid_rowconfigure(1, weight=1)

        lbl_preview = tk.Label(card_preview, text="Live Preview", bg=BG_CARD, fg=FG_TEXT,
                               font=("Segoe UI Semibold", 11))
        lbl_preview.pack(anchor="w", pady=(0, 10))

        # Frame for Preview Image (keeps aspect ratio)
        self.preview_container = tk.Frame(card_preview, bg=BG_INPUT, bd=1)
        self.preview_container.pack(fill="both", expand=True, pady=(0, 15))
        
        self.preview_label = tk.Label(self.preview_container, text="Generate code to view preview",
                                      bg=BG_INPUT, fg=FG_MUTED, font=("Segoe UI Italic", 10))
        self.preview_label.pack(fill="both", expand=True, padx=20, pady=20)

        # Export Button
        self.btn_save_single = self.create_hover_button(
            card_preview, "Export QR Image", self.save_single_qr,
            ACCENT_PURPLE, FG_TEXT, "#7c3aed", font=("Segoe UI", 10, "bold")
        )
        self.btn_save_single.pack(fill="x")
        self.btn_save_single.config(state="disabled", bg=BG_INPUT, fg=FG_MUTED)

        # ==========================================
        # TAB 2: BULK QR CODE FRAME
        # ==========================================
        self.frame_bulk = tk.Frame(self.main_area, bg=BG_DARK)
        self.frame_bulk.grid_columnconfigure(0, weight=1)
        self.frame_bulk.grid_rowconfigure(0, weight=1)

        card_bulk = tk.Frame(self.frame_bulk, bg=BG_CARD, padx=20, pady=20)
        card_bulk.grid(row=0, column=0, sticky="nsew")
        card_bulk.grid_columnconfigure(0, weight=1) # Left options
        card_bulk.grid_columnconfigure(1, weight=1) # Right logs/details
        card_bulk.grid_rowconfigure(0, weight=1)

        # --- Bulk Left Side: Configuration ---
        left_bulk_pane = tk.Frame(card_bulk, bg=BG_CARD)
        left_bulk_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        # Source Selection (Manual vs File)
        lbl_source = tk.Label(left_bulk_pane, text="Input Source", bg=BG_CARD, fg=FG_TEXT, font=("Segoe UI Semibold", 10))
        lbl_source.pack(anchor="w", pady=(0, 5))
        
        source_frame = tk.Frame(left_bulk_pane, bg=BG_CARD)
        source_frame.pack(fill="x", pady=(0, 10))
        
        self.var_source_type = tk.StringVar(value="manual")
        
        self.rb_manual = tk.Radiobutton(source_frame, text="Manual List", variable=self.var_source_type, value="manual",
                                        bg=BG_CARD, fg=FG_TEXT, activebackground=BG_CARD, activeforeground=FG_TEXT,
                                        selectcolor=BG_DARK, font=("Segoe UI", 9), command=self.toggle_source_view)
        self.rb_manual.pack(side="left", padx=(0, 15))
        
        self.rb_file = tk.Radiobutton(source_frame, text="Import File (TXT/CSV)", variable=self.var_source_type, value="file",
                                      bg=BG_CARD, fg=FG_TEXT, activebackground=BG_CARD, activeforeground=FG_TEXT,
                                      selectcolor=BG_DARK, font=("Segoe UI", 9), command=self.toggle_source_view)
        self.rb_file.pack(side="left")

        # Container for changing sub-frames
        self.bulk_source_container = tk.Frame(left_bulk_pane, bg=BG_CARD)
        self.bulk_source_container.pack(fill="both", expand=True, pady=(0, 10))

        # Frame A: Manual Entry Frame
        self.frame_bulk_manual = tk.Frame(self.bulk_source_container, bg=BG_CARD)
        lbl_m_desc = tk.Label(self.frame_bulk_manual, text="Enter items (one per line):", bg=BG_CARD, fg=FG_MUTED, font=("Segoe UI", 9))
        lbl_m_desc.pack(anchor="w", pady=(0, 3))
        
        txt_m_wrapper = tk.Frame(self.frame_bulk_manual, bg=BG_INPUT, bd=1)
        txt_m_wrapper.pack(fill="both", expand=True)
        self.txt_bulk_manual = tk.Text(txt_m_wrapper, bg=BG_INPUT, fg=FG_TEXT, insertbackground=FG_TEXT,
                                       relief="flat", font=("Segoe UI", 9), wrap="word", height=6)
        self.txt_bulk_manual.pack(fill="both", expand=True, padx=5, pady=5)
        self.txt_bulk_manual.insert("1.0", "Item 1\nItem 2\nItem 3")

        # Frame B: File Import Frame
        self.frame_bulk_file = tk.Frame(self.bulk_source_container, bg=BG_CARD)
        
        btn_import = self.create_hover_button(self.frame_bulk_file, "Select TXT or CSV File", self.import_bulk_file,
                                               BG_INPUT, FG_TEXT, BG_DARK, font=("Segoe UI", 9, "bold"))
        btn_import.pack(anchor="w", fill="x", pady=(0, 5))
        
        self.lbl_file_status = tk.Label(self.frame_bulk_file, text="No file selected", bg=BG_CARD, fg=FG_MUTED,
                                        font=("Segoe UI Italic", 9), anchor="w")
        self.lbl_file_status.pack(fill="x", pady=(0, 8))
        
        # CSV options (shown only if loaded file is CSV)
        self.frame_csv_options = tk.Frame(self.frame_bulk_file, bg=BG_CARD)
        
        lbl_col = tk.Label(self.frame_csv_options, text="Data Column to Encode:", bg=BG_CARD, fg=FG_MUTED, font=("Segoe UI", 9))
        lbl_col.pack(anchor="w", pady=(2, 1))
        self.var_csv_col = tk.StringVar()
        self.cb_csv_col = ttk.Combobox(self.frame_csv_options, textvariable=self.var_csv_col, state="readonly")
        self.cb_csv_col.pack(fill="x", pady=(0, 8))

        lbl_name_col = tk.Label(self.frame_csv_options, text="Filename Column (Optional):", bg=BG_CARD, fg=FG_MUTED, font=("Segoe UI", 9))
        lbl_name_col.pack(anchor="w", pady=(2, 1))
        self.var_csv_name_col = tk.StringVar()
        self.cb_csv_name_col = ttk.Combobox(self.frame_csv_options, textvariable=self.var_csv_name_col, state="readonly")
        self.cb_csv_name_col.pack(fill="x", pady=(0, 8))

        # Show manual frame by default
        self.frame_bulk_manual.pack(fill="both", expand=True)

        # Naming & Save details in Sidebar/bottom options
        lbl_naming = tk.Label(left_bulk_pane, text="QR Code Naming Scheme", bg=BG_CARD, fg=FG_TEXT, font=("Segoe UI Semibold", 10))
        lbl_naming.pack(anchor="w", pady=(5, 5))
        
        self.var_naming_scheme = tk.StringVar(value="Content")
        cb_naming = ttk.Combobox(left_bulk_pane, textvariable=self.var_naming_scheme, state="readonly",
                                 values=["Content (Sanitized)", "Sequential numbers", "Prefix + Sequential"])
        cb_naming.pack(fill="x", pady=(0, 5))
        cb_naming.bind("<<ComboboxSelected>>", lambda e: self.toggle_prefix_field())
        
        # Optional Prefix frame
        self.frame_prefix = tk.Frame(left_bulk_pane, bg=BG_CARD)
        lbl_prefix = tk.Label(self.frame_prefix, text="Prefix:", bg=BG_CARD, fg=FG_MUTED, font=("Segoe UI", 9))
        lbl_prefix.pack(side="left", padx=(0, 5))
        self.ent_prefix = tk.Entry(self.frame_prefix, bg=BG_INPUT, fg=FG_TEXT, insertbackground=FG_TEXT,
                                   relief="flat", font=("Segoe UI", 9), bd=3)
        self.ent_prefix.pack(side="left", fill="x", expand=True)
        self.ent_prefix.insert(0, "qr_")
        
        # Destination Folder Selector
        lbl_dest = tk.Label(left_bulk_pane, text="Output Directory", bg=BG_CARD, fg=FG_TEXT, font=("Segoe UI Semibold", 10))
        lbl_dest.pack(anchor="w", pady=(10, 5))
        
        dest_frame = tk.Frame(left_bulk_pane, bg=BG_CARD)
        dest_frame.pack(fill="x")
        
        btn_dest = self.create_hover_button(dest_frame, "Browse...", self.browse_output_dir,
                                            BG_INPUT, FG_TEXT, BG_DARK, font=("Segoe UI", 9, "bold"))
        btn_dest.pack(side="left")
        
        self.selected_output_dir = ""
        self.lbl_dest_path = tk.Label(dest_frame, text="No folder selected", bg=BG_CARD, fg=FG_MUTED,
                                      font=("Segoe UI Italic", 9), anchor="w")
        self.lbl_dest_path.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # --- Bulk Right Side: Progress & Logs ---
        right_bulk_pane = tk.Frame(card_bulk, bg=BG_CARD)
        right_bulk_pane.grid(row=0, column=1, sticky="nsew", padx=(15, 0))
        right_bulk_pane.grid_columnconfigure(0, weight=1)
        right_bulk_pane.grid_rowconfigure(1, weight=1)

        lbl_logs = tk.Label(right_bulk_pane, text="Execution Logs", bg=BG_CARD, fg=FG_TEXT, font=("Segoe UI Semibold", 10))
        lbl_logs.pack(anchor="w", pady=(0, 8))

        # Terminal-style console box
        log_wrapper = tk.Frame(right_bulk_pane, bg=BG_DARK, bd=1)
        log_wrapper.pack(fill="both", expand=True, pady=(0, 10))
        
        self.txt_logs = tk.Text(log_wrapper, bg=BG_DARK, fg=ACCENT_GREEN, insertbackground=ACCENT_GREEN,
                                relief="flat", font=("Consolas", 9), wrap="word", state="disabled")
        self.txt_logs.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Progress Bar and Count indicator
        self.progress_frame = tk.Frame(right_bulk_pane, bg=BG_CARD)
        self.progress_frame.pack(fill="x", pady=(5, 10))
        
        self.lbl_progress_status = tk.Label(self.progress_frame, text="Ready", bg=BG_CARD, fg=FG_TEXT, font=("Segoe UI Semibold", 9))
        self.lbl_progress_status.pack(anchor="w", pady=(0, 4))
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, style="Horizontal.TProgressbar", orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x")

        # Start Bulk Button
        self.btn_start_bulk = self.create_hover_button(
            right_bulk_pane, "Generate Bulk QRs", self.start_bulk_generation,
            ACCENT_GREEN, BG_DARK, "#059669", font=("Segoe UI", 10, "bold")
        )
        self.btn_start_bulk.pack(fill="x", pady=(5, 0))

        # Default display setup
        self.show_single_tab()

    # ==========================================
    # HELPER COMPONENT CREATION
    # ==========================================
    def create_sep(self, parent, color):
        """Creates a thin styling separator."""
        return tk.Frame(parent, bg=color, height=1)

    def create_hover_button(self, parent, text, command, bg_color, fg_color, hover_bg, font, **kwargs):
        """Create buttons with mouse hover events."""
        # Clean margin properties since Tkinter button doesn't take marginRight, etc.
        pack_args = {}
        for margin in ['marginRight', 'marginLeft', 'marginTop', 'marginBottom']:
            if margin in kwargs:
                kwargs.pop(margin)
                
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg=fg_color,
            activebackground=hover_bg,
            activeforeground=fg_color,
            font=font,
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            **kwargs
        )
        def on_enter(e):
            if btn['state'] != "disabled":
                btn.config(bg=hover_bg)
        def on_leave(e):
            if btn['state'] != "disabled":
                btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def pick_color(self, target):
        """Open system color chooser dialog and update local color properties."""
        initial = self.fg_color if target == "fg" else self.bg_color
        color = colorchooser.askcolor(title=f"Choose {'Foreground' if target == 'fg' else 'Background'} Color", color=initial)
        if color[1]:
            # Set to custom palette value
            self.var_palette.set("Custom")
            if target == "fg":
                self.fg_color = color[1]
                self.fg_preview.config(bg=color[1])
            else:
                self.bg_color = color[1]
                self.bg_preview.config(bg=color[1])
            self.log_to_console(f"Custom color chosen: {target} = {color[1]}")

    def apply_palette(self, name):
        """Apply predefined high-contrast color combinations."""
        palettes = {
            "Classic Light": ("#000000", "#ffffff"),
            "Classic Dark": ("#ffffff", "#121212"),
            "Neon Indigo": ("#818cf8", "#0f172a"),
            "Cyberpunk": ("#f43f5e", "#0f172a"),
            "Forest": ("#065f46", "#f0fdf4"),
            "Sunset": ("#ea580c", "#fef2e9")
        }
        if name in palettes:
            fg, bg = palettes[name]
            self.fg_color = fg
            self.bg_color = bg
            self.fg_preview.config(bg=fg)
            self.bg_preview.config(bg=bg)
            self.log_to_console(f"Applied color palette: {name} (FG: {fg}, BG: {bg})")

    # ==========================================
    # NAVIGATION ACTIONS (Tabbing)
    # ==========================================
    def show_single_tab(self):
        """Navigates main panel to single generator."""
        self.frame_bulk.grid_remove()
        self.frame_single.grid(row=1, column=0, sticky="nsew")
        
        # Tabs button highlight
        self.btn_tab_single.config(bg=BG_CARD, fg=FG_TEXT)
        self.btn_tab_bulk.config(bg=BG_DARK, fg=FG_MUTED)
        
        # Position indicator bar
        self.tab_indicator.place(x=self.btn_tab_single.winfo_x(), y=42, width=self.btn_tab_single.winfo_width())

    def show_bulk_tab(self):
        """Navigates main panel to bulk generator."""
        self.frame_single.grid_remove()
        self.frame_bulk.grid(row=1, column=0, sticky="nsew")
        
        # Tabs button highlight
        self.btn_tab_single.config(bg=BG_DARK, fg=FG_MUTED)
        self.btn_tab_bulk.config(bg=BG_CARD, fg=FG_TEXT)
        
        # Position indicator bar
        self.tab_indicator.place(x=self.btn_tab_bulk.winfo_x(), y=42, width=self.btn_tab_bulk.winfo_width())

    def toggle_source_view(self):
        """Toggle between Manual entries panel and File importing panel in Bulk tab."""
        val = self.var_source_type.get()
        if val == "manual":
            self.frame_bulk_file.pack_forget()
            self.frame_bulk_manual.pack(fill="both", expand=True)
        else:
            self.frame_bulk_manual.pack_forget()
            self.frame_bulk_file.pack(fill="both", expand=True)

    def toggle_prefix_field(self):
        """Enable or disable prefix field based on the naming scheme selection."""
        val = self.var_naming_scheme.get()
        if "Prefix" in val:
            self.frame_prefix.pack(fill="x", pady=(2, 5))
        else:
            self.frame_prefix.pack_forget()

    # ==========================================
    # SINGLE QR GENERATION LOGIC
    # ==========================================
    def get_qr_settings(self):
        """Parses inputs from style sidebar settings."""
        # Map error correction levels
        err_map = {
            "Low (7%)": qrcode.constants.ERROR_CORRECT_L,
            "Medium (15%)": qrcode.constants.ERROR_CORRECT_M,
            "Quartile (25%)": qrcode.constants.ERROR_CORRECT_Q,
            "High (30%)": qrcode.constants.ERROR_CORRECT_H,
        }
        error_level = err_map.get(self.var_err.get(), qrcode.constants.ERROR_CORRECT_M)
        box_size = self.var_box_size.get()
        border = self.var_border_size.get()
        return error_level, box_size, border

    def generate_single_qr(self):
        """Generates single QR code, sets preview label image, and enables export."""
        content = self.txt_single_input.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("Empty Content", "Please enter some URL or text content to generate.")
            return

        error_level, box_size, border = self.get_qr_settings()

        try:
            # Generate QR Matrix
            qr = qrcode.QRCode(
                version=None,  # Auto size adjustment
                error_correction=error_level,
                box_size=box_size,
                border=border
            )
            qr.add_data(content)
            qr.make(fit=True)

            # Draw PIL Image
            self.current_qr_image = qr.make_image(fill_color=self.fg_color, back_color=self.bg_color)
            
            # Display inside canvas container
            self.update_preview_display(self.current_qr_image)
            
            # Enable Export
            self.btn_save_single.config(state="normal", bg=ACCENT_PURPLE, fg=FG_TEXT)
            self.log_to_console("Single QR generated successfully.")

        except Exception as e:
            messagebox.showerror("Generation Error", f"Failed to generate QR Code:\n{str(e)}")

    def update_preview_display(self, pil_image):
        """Resizes the PIL image dynamically to fit the current Preview Frame size."""
        self.preview_container.update()
        frame_width = self.preview_container.winfo_width()
        frame_height = self.preview_container.winfo_height()
        
        # Calculate fit size with some padding (20px each side)
        fit_size = min(frame_width - 40, frame_height - 40, 320)
        if fit_size < 50:
            fit_size = 250 # Fallback
            
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.ANTIALIAS

        img_resized = pil_image.resize((fit_size, fit_size), resample_filter)
        self.qr_photo = ImageTk.PhotoImage(img_resized)
        
        # Configure preview widget
        self.preview_label.config(image=self.qr_photo, text="")

    def save_single_qr(self):
        """Open system filedialog to save the generated Single QR code."""
        if not self.current_qr_image:
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Save QR Code",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                self.current_qr_image.save(file_path)
                messagebox.showinfo("Saved Successfully", f"QR Code exported to:\n{file_path}")
                self.log_to_console(f"Exported single QR code: {file_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save the image:\n{str(e)}")

    # ==========================================
    # BULK QR GENERATION LOGIC (Threaded & Asynchronous)
    # ==========================================
    def import_bulk_file(self):
        """Imports CSV or TXT lists and populates configuration options."""
        file_path = filedialog.askopenfilename(
            title="Import QR Data Source",
            filetypes=[("Text/CSV Data Files", "*.txt;*.csv"), ("CSV Files", "*.csv"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        self.selected_file_path = file_path
        file_name = os.path.basename(file_path)
        self.lbl_file_status.config(text=f"Loaded: {file_name}", fg=ACCENT_BLUE)
        self.imported_data = []
        self.csv_headers = []
        
        try:
            if file_path.lower().endswith('.csv'):
                with open(file_path, newline='', encoding='utf-8') as f:
                    # Detect delimiter
                    sample = f.read(2048)
                    f.seek(0)
                    dialect = csv.Sniffer().sniff(sample) if ',' in sample or ';' in sample or '\t' in sample else 'excel'
                    
                    reader = csv.reader(f, dialect)
                    rows = list(reader)
                    if rows:
                        self.imported_data = rows
                        
                        # Populate CSV Column Selection boxes
                        headers = [f"Col {i+1}: {val[:15]}" for i, val in enumerate(rows[0])]
                        self.csv_headers = headers
                        
                        # Populate columns selector
                        self.cb_csv_col.config(values=headers)
                        self.cb_csv_col.current(0)
                        
                        # Populate naming columns
                        name_options = ["None (Use Naming Scheme)"] + headers
                        self.cb_csv_name_col.config(values=name_options)
                        self.cb_csv_name_col.current(0)
                        
                        self.frame_csv_options.pack(fill="x", pady=(5, 0))
                        self.log_to_console(f"Imported CSV file: {file_name} with {len(rows)} rows.")
            else:
                # Text file parse
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                    self.imported_data = [[line] for line in lines] # 1 column format
                    self.frame_csv_options.pack_forget()
                    self.log_to_console(f"Imported Text file: {file_name} with {len(lines)} lines.")
                    
        except Exception as e:
            self.lbl_file_status.config(text="Failed to load file", fg=ACCENT_RED)
            messagebox.showerror("File Load Error", f"Could not read the data file:\n{str(e)}")

    def browse_output_dir(self):
        """Open folder dialog to set save destination path."""
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.selected_output_dir = folder
            # Truncate displays for aesthetics
            display_folder = folder if len(folder) < 30 else "..." + folder[-27:]
            self.lbl_dest_path.config(text=display_folder, fg=ACCENT_BLUE)
            self.log_to_console(f"Destination folder set: {folder}")

    def log_to_console(self, text):
        """Prints lines of logs to the right terminal panel."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.config(state="normal")
        self.txt_logs.insert("end", f"[{timestamp}] {text}\n")
        self.txt_logs.see("end")
        self.txt_logs.config(state="disabled")

    def start_bulk_generation(self):
        """Pre-validates and initiates worker thread for bulk tasks."""
        if self.bulk_running:
            return

        # 1. Output directory check
        output_dir = self.selected_output_dir
        if not output_dir or not os.path.isdir(output_dir):
            messagebox.showwarning("Destination Folder Required", "Please choose a valid destination folder for export files.")
            return

        # 2. Extract Data Items to encode
        items_to_process = []  # List of tuples: (content, filename_or_none)
        
        source = self.var_source_type.get()
        if source == "manual":
            # Extract from manual box
            text_lines = self.txt_bulk_manual.get("1.0", "end-1c").split('\n')
            for line in text_lines:
                val = line.strip()
                if val:
                    items_to_process.append((val, None))
        else:
            # Extract from loaded file structure
            if not self.imported_data:
                messagebox.showwarning("Data File Empty", "No records found in the imported file.")
                return
            
            is_csv = self.selected_file_path.lower().endswith('.csv')
            if is_csv:
                # Column check
                data_col_idx = self.cb_csv_col.current()
                name_col_idx = self.cb_csv_name_col.current() - 1 # -1 is the "None" offset
                
                # Check for headers - ask if first row is headers if column indices look like strings
                skip_header = messagebox.askyesno("CSV Header Check", "Does the first row of your CSV contain column headers/labels?")
                start_row = 1 if skip_header else 0
                
                for row in self.imported_data[start_row:]:
                    if not row or data_col_idx >= len(row):
                        continue
                    content = row[data_col_idx].strip()
                    if not content:
                        continue
                    
                    filename_val = None
                    if name_col_idx >= 0 and name_col_idx < len(row):
                        filename_val = row[name_col_idx].strip()
                        
                    items_to_process.append((content, filename_val))
            else:
                # Flat text files
                for row in self.imported_data:
                    if row and row[0].strip():
                        items_to_process.append((row[0].strip(), None))

        if not items_to_process:
            messagebox.showwarning("No Items Found", "Could not extract any content items to encode.")
            return

        # Disable Controls
        self.set_bulk_controls_state("disabled")
        self.bulk_running = True
        self.progress_bar.config(value=0, maximum=len(items_to_process))
        self.lbl_progress_status.config(text=f"Initializing generation (0 / {len(items_to_process)})...")
        
        # Start Worker Thread
        error_level, box_size, border = self.get_qr_settings()
        naming_scheme = self.var_naming_scheme.get()
        prefix = self.ent_prefix.get() if "Prefix" in naming_scheme else ""
        
        args = (items_to_process, output_dir, naming_scheme, prefix, error_level, box_size, border)
        
        self.worker_thread = threading.Thread(target=self.bulk_generation_worker, args=args, daemon=True)
        self.worker_thread.start()

    def set_bulk_controls_state(self, state):
        """Toggles lock state on panels during threaded processing."""
        self.btn_start_bulk.config(state=state, bg=BG_INPUT if state == "disabled" else ACCENT_GREEN)
        self.rb_manual.config(state=state)
        self.rb_file.config(state=state)
        self.txt_bulk_manual.config(state=state)
        self.ent_prefix.config(state=state)

    def bulk_generation_worker(self, items, out_dir, naming_scheme, prefix, err_lvl, size, border):
        """Worker thread executing QR creation loop and dumping status inside Queue."""
        total = len(items)
        success_count = 0
        
        self.queue.put(('log', f"Starting generation of {total} QR Codes..."))
        
        for idx, (content, custom_filename) in enumerate(items):
            try:
                # 1. Create QR
                qr = qrcode.QRCode(
                    version=None,
                    error_correction=err_lvl,
                    box_size=size,
                    border=border
                )
                qr.add_data(content)
                qr.make(fit=True)
                img = qr.make_image(fill_color=self.fg_color, back_color=self.bg_color)
                
                # 2. File Naming logic
                fname = ""
                if custom_filename:
                    # Naming column provided from CSV
                    fname = self.sanitize_filename(custom_filename)
                elif "Content" in naming_scheme:
                    # Sanitize content
                    fname = self.sanitize_filename(content)
                elif "Prefix" in naming_scheme:
                    fname = f"{prefix}{idx+1:04d}"
                else: # Sequential numbers
                    fname = f"qr_{idx+1:04d}"
                
                # Append extension and solve duplicates
                full_path = os.path.join(out_dir, f"{fname}.png")
                counter = 1
                while os.path.exists(full_path):
                    full_path = os.path.join(out_dir, f"{fname}_{counter}.png")
                    counter += 1
                
                # 3. Save
                img.save(full_path)
                success_count += 1
                
                # Update statuses
                self.queue.put(('progress', idx + 1, total))
                self.queue.put(('log', f"Success [{idx+1}/{total}]: Saved '{os.path.basename(full_path)}'"))
                
            except Exception as e:
                self.queue.put(('log', f"Error [{idx+1}/{total}]: Content '{content[:20]}...' failed - {str(e)}"))
                
        self.queue.put(('done', success_count))

    def sanitize_filename(self, content, max_len=25):
        """Strip unsafe OS filename characters and return clean string."""
        clean = re.sub(r'[\\/*?:"<>|]', "", content)
        clean = re.sub(r'\s+', "_", clean).strip("_")
        if not clean:
            clean = "qr_code"
        return clean[:max_len]

    def check_queue(self):
        """Periodically polls worker thread queue for GUI status updates (runs in main Tk loop)."""
        try:
            while True:
                msg = self.queue.get_nowait()
                msg_type = msg[0]
                
                if msg_type == 'log':
                    self.log_to_console(msg[1])
                elif msg_type == 'progress':
                    curr, total = msg[1], msg[2]
                    self.progress_bar.config(value=curr)
                    self.lbl_progress_status.config(text=f"Generating ({curr} / {total})...")
                elif msg_type == 'done':
                    cnt = msg[1]
                    self.log_to_console(f"--- Bulk Generation Finished! Successfully created {cnt} codes. ---")
                    self.lbl_progress_status.config(text=f"Completed! {cnt} QR codes exported.")
                    messagebox.showinfo("Bulk Done", f"Successfully generated {cnt} QR Code images inside the destination folder.")
                    self.bulk_running = False
                    self.set_bulk_controls_state("normal")
                elif msg_type == 'error':
                    self.log_to_console(f"CRITICAL ERROR: {msg[1]}")
                    messagebox.showerror("Worker Failure", f"Bulk processing failed:\n{msg[1]}")
                    self.bulk_running = False
                    self.set_bulk_controls_state("normal")
                    
                self.queue.task_done()
        except queue.Empty:
            pass
        
        # Schedule next check
        self.after(100, self.check_queue)


if __name__ == "__main__":
    app = QRGeneratorApp()
    app.mainloop()
