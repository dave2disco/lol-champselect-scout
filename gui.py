import threading
import webbrowser
import tkinter as tk

from core import (
    REGIONS, REGION_NAMES,
    find_league_process, extract_tokens, make_headers,
    get_champ_select_players,
)

# ──────────────────────────────────────────────
#  Design tokens
# ──────────────────────────────────────────────

BG        = "#0a0e1a"
BG2       = "#0f1628"
ACCENT    = "#c89b3c"
ACCENT2   = "#785a28"
ACCENT3   = "#1a1200"
TEXT      = "#f0e6d3"
TEXT_DIM  = "#7a7a8a"
RED       = "#c0392b"
GREEN     = "#2ecc71"
BORDER    = "#1e2d4a"

FONT_TITLE  = ("Georgia", 22, "bold")
FONT_SUB    = ("Georgia", 10, "italic")
FONT_NAME   = ("Consolas", 13, "bold")
FONT_BTN    = ("Georgia", 11, "bold")
FONT_SMALL  = ("Consolas", 9)
FONT_REGION = ("Consolas", 10, "bold")


# ──────────────────────────────────────────────
#  Main window
# ──────────────────────────────────────────────

class ChampSelectApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ChampSelect Scout")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("480x680")
        self._opgg_url   = None
        self._region_var = tk.StringVar(value="EUW")
        self._build_ui()
        self._center_window()

    # ── Layout ──────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg=BG, pady=18)
        header.pack(fill="x", side="top", padx=28)
        tk.Label(header, text="⚔  ChampSelect Scout",
                 font=FONT_TITLE, bg=BG, fg=ACCENT).pack(anchor="w")
        tk.Label(header, text="Reveal player names during champion select",
                 font=FONT_SUB, bg=BG, fg=TEXT_DIM).pack(anchor="w", pady=(2, 0))

        tk.Frame(self, bg=ACCENT2, height=1).pack(fill="x", side="top", padx=28)

        # ── Region selector ──
        region_frame = tk.Frame(self, bg=BG, pady=12)
        region_frame.pack(fill="x", side="top", padx=28)
        tk.Label(region_frame, text="REGION",
                 font=("Consolas", 8, "bold"), bg=BG, fg=ACCENT2).pack(anchor="w")
        grid = tk.Frame(region_frame, bg=BG)
        grid.pack(fill="x", pady=(4, 0))

        self._region_buttons = {}
        for i, name in enumerate(REGION_NAMES):
            btn = tk.Button(
                grid, text=name, font=FONT_REGION,
                bg=ACCENT3, fg=ACCENT2,
                relief="flat", cursor="hand2",
                padx=4, pady=5, width=4,
                command=lambda n=name: self._select_region(n)
            )
            btn.grid(row=0, column=i, padx=2, pady=2, sticky="ew")
            grid.columnconfigure(i, weight=1)
            self._region_buttons[name] = btn
        self._select_region("EUW")

        tk.Frame(self, bg=ACCENT2, height=1).pack(fill="x", side="top", padx=28)

        # ── Footer (packed before middle content so it always stays at the bottom) ──
        footer_frame = tk.Frame(self, bg=BG)
        footer_frame.pack(fill="x", side="bottom")
        tk.Frame(footer_frame, bg=ACCENT2, height=1).pack(fill="x", padx=28)
        tk.Label(footer_frame, text="•  ChampSelect Scout  •",
                 font=("Consolas", 8), bg=BG, fg=ACCENT2).pack(pady=8)

        # ── Bottom action buttons (packed before player panel) ──
        self.copy_btn = tk.Button(
            self, text="COPY LINK",
            font=("Georgia", 9, "bold"), bg=BG, fg=TEXT_DIM,
            relief="flat", cursor="hand2", padx=16, pady=6,
            state="disabled", command=self._copy_link
        )
        self.copy_btn.pack(fill="x", side="bottom", padx=28, pady=(0, 16))

        self.opgg_btn = tk.Button(
            self, text="OPEN ON OP.GG",
            font=FONT_BTN, bg=BG2, fg=TEXT_DIM,
            relief="flat", cursor="hand2", padx=16, pady=10,
            state="disabled", command=self._open_opgg
        )
        self.opgg_btn.pack(fill="x", side="bottom", padx=28, pady=(0, 6))

        # ── Scan button ──
        btn_frame = tk.Frame(self, bg=BG, pady=10)
        btn_frame.pack(fill="x", side="top", padx=28)
        self.scan_btn = tk.Button(
            btn_frame, text="SCAN CHAMP SELECT",
            font=FONT_BTN, bg=ACCENT2, fg=ACCENT,
            relief="flat", cursor="hand2", padx=16, pady=10,
            command=self._on_scan
        )
        self.scan_btn.pack(fill="x")
        self._bind_hover(self.scan_btn, ACCENT, BG, ACCENT2, ACCENT)

        # ── Status label ──
        self.status_var = tk.StringVar(value="Awaiting scan...")
        self.status_lbl = tk.Label(
            self, textvariable=self.status_var,
            font=FONT_SMALL, bg=BG, fg=TEXT_DIM,
            wraplength=420, justify="center", height=2
        )
        self.status_lbl.pack(fill="x", side="top", pady=2)

        # ── Players panel ──
        tk.Label(self, text="DETECTED PLAYERS",
                 font=("Georgia", 9, "bold"), bg=BG, fg=ACCENT2
                 ).pack(anchor="w", side="top", padx=30)

        panel_outer = tk.Frame(self, bg=BORDER, padx=1, pady=1, height=200)
        panel_outer.pack(fill="x", side="top", padx=28, pady=(4, 12))
        panel_outer.pack_propagate(False)

        panel = tk.Frame(panel_outer, bg=BG2)
        panel.pack(fill="both", expand=True)

        self.player_frame = tk.Frame(panel, bg=BG2, pady=8)
        self.player_frame.pack(fill="both", expand=True, padx=10, pady=6)
        self._show_placeholder()

    # ── Region selector ─────────────────────────
    def _select_region(self, name):
        for btn in self._region_buttons.values():
            btn.config(bg=ACCENT3, fg=ACCENT2)
        self._region_buttons[name].config(bg=ACCENT2, fg=ACCENT)
        self._region_var.set(name)

    # ── Helpers ─────────────────────────────────
    def _center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _bind_hover(self, widget, fg_on, bg_on, fg_off, bg_off):
        widget.bind("<Enter>", lambda e: widget.config(bg=bg_on,  fg=fg_on))
        widget.bind("<Leave>", lambda e: widget.config(bg=bg_off, fg=fg_off))

    def _show_placeholder(self):
        for w in self.player_frame.winfo_children():
            w.destroy()
        tk.Label(self.player_frame,
                 text="No data — run a scan",
                 font=FONT_SMALL, bg=BG2, fg=TEXT_DIM).pack(expand=True)

    def _show_players(self, names):
        for w in self.player_frame.winfo_children():
            w.destroy()
        icons = ["①", "②", "③", "④", "⑤"]
        for i, name in enumerate(names[:5]):
            row = tk.Frame(self.player_frame, bg=BG2)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=icons[i] if i < len(icons) else "•",
                     font=("Georgia", 14), bg=BG2, fg=ACCENT,
                     width=3).pack(side="left")
            tk.Label(row, text=name,
                     font=FONT_NAME, bg=BG2, fg=TEXT,
                     anchor="w").pack(side="left", fill="x", expand=True)

    # ── Scan ────────────────────────────────────
    def _on_scan(self):
        self.scan_btn.config(state="disabled", text="Scanning...")
        self.status_var.set("Locating League client...")
        self.status_lbl.config(fg=TEXT_DIM)
        self.opgg_btn.config(state="disabled", bg=BG2, fg=TEXT_DIM)
        self.copy_btn.config(state="disabled")
        self._opgg_url = None
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        cmdline = find_league_process()
        if not cmdline:
            self.after(0, self._update_error,
                       "League client not found.\nOpen the game and retry.")
            return
        tokens = extract_tokens(cmdline)
        if not tokens:
            self.after(0, self._update_error, "Failed to read client tokens.")
            return
        c_port, c_tok, r_port, r_tok = tokens
        region_slug = REGIONS[self._region_var.get()]
        names, opgg, err = get_champ_select_players(
            c_port, make_headers(c_tok),
            r_port, make_headers(r_tok),
            region_slug
        )
        if err:
            self.after(0, self._update_error, err)
        else:
            self.after(0, self._update_success, names, opgg)

    def _update_error(self, msg):
        self._show_placeholder()
        self.status_var.set(msg)
        self.status_lbl.config(fg=RED)
        self.scan_btn.config(state="normal", text="SCAN CHAMP SELECT")

    def _update_success(self, names, opgg):
        self._opgg_url = opgg
        self._show_players(names)
        region = self._region_var.get()
        self.status_var.set(f"✓  {len(names)} players found  •  {region}")
        self.status_lbl.config(fg=GREEN)
        self.scan_btn.config(state="normal", text="SCAN AGAIN")
        self.opgg_btn.config(state="normal", bg=ACCENT2, fg=ACCENT)
        self._bind_hover(self.opgg_btn, BG, ACCENT, ACCENT, BG2)
        self.copy_btn.config(state="normal", fg=TEXT_DIM)

    # ── Actions ─────────────────────────────────
    def _open_opgg(self):
        if self._opgg_url:
            webbrowser.open(self._opgg_url)

    def _copy_link(self):
        if self._opgg_url:
            self.clipboard_clear()
            self.clipboard_append(self._opgg_url)
            self.copy_btn.config(text="Copied!")
            self.after(1800, lambda: self.copy_btn.config(text="COPY LINK"))


# ──────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app = ChampSelectApp()
    app.mainloop()
