from __future__ import annotations

import json
import re
import socket
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk


ROOT = Path(r"C:\KODA_AI_LAB\04_KODA_Local_AI")
LOG_DIR = ROOT / "logs"

TELEMETRY_FILE = LOG_DIR / "telemetry.jsonl"
SERVICE_LOG = LOG_DIR / "local_ai_service.log"
RELEASE_HISTORY_FILE = ROOT / "data" / "release_history.json"

LOG_FILES = {
    "Local AI Service": SERVICE_LOG,
    "Audit Log": LOG_DIR / "audit_log.jsonl",
    "Blocked Queries": LOG_DIR / "blocked_queries.jsonl",
    "Telemetry Raw": LOG_DIR / "telemetry.jsonl",
}

MAX_TELEMETRY_ROWS = 200
MAX_HTTP_ROWS = 500
MAX_LOG_LINES = 400

HTTP_PATTERN = re.compile(
    r'(?P<ip>(?:\d{1,3}\.){3}\d{1,3})'
    r':(?P<port>\d+)\s+-\s+'
    r'"(?P<method>[A-Z]+)\s+'
    r'(?P<path>\S+)\s+HTTP/[0-9.]+"\s+'
    r'(?P<status>\d{3})'
)


class KODAAIDashboard(tk.Tk):
    def __init__(self):
        super().__init__()

        self._configure_theme()

        self.title("KODAAI Lokal AI  Operasyon Dashboard  v0.2")
        self.geometry("1500x850")
        self.minsize(1150, 650)

        self.status_var = tk.StringVar()
        self.summary_var = tk.StringVar()
        self.routing_leaks_var = tk.StringVar()
        self.updated_var = tk.StringVar()

        self.http_summary_var = tk.StringVar()
        self.http_search_var = tk.StringVar()

        self.log_file_var = tk.StringVar(
            value="Local AI Service"
        )
        self.log_search_var = tk.StringVar()

        self._build_ui()
        self.refresh_all()


    # ---------------------------------------------------------
    # KODAAI BRAND THEME
    # ---------------------------------------------------------

    def _configure_theme(self):
        # KODAAI marka paleti
        bg = "#071525"
        panel = "#0B1E32"
        panel_alt = "#102A44"
        panel_hover = "#163B60"

        text = "#F4F8FF"
        muted = "#A9B9CC"

        cyan = "#20DFFF"
        blue = "#2586FF"
        purple = "#9257FF"
        green = "#2CEFB4"

        border = "#244F76"
        selected = "#174E84"

        self.configure(bg=bg)

        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Ana y?zey
        style.configure(
            ".",
            background=bg,
            foreground=text,
            font=("Segoe UI", 10),
        )

        style.configure(
            "TFrame",
            background=bg,
        )

        style.configure(
            "TLabel",
            background=bg,
            foreground=text,
        )

        style.configure(
            "DashboardTitle.TLabel",
            background=bg,
            foreground="#F4F8FF",
            font=("Segoe UI", 20, "bold"),
        )

        style.configure(
            "DashboardAccent.TLabel",
            background=bg,
            foreground=cyan,
            font=("Segoe UI", 10, "bold"),
        )

        style.configure(
            "DashboardMuted.TLabel",
            background=bg,
            foreground=muted,
            font=("Segoe UI", 9),
        )

        # Butonlar
        style.configure(
            "TButton",
            background="#0C2740",
            foreground=text,
            bordercolor="#23547A",
            lightcolor="#23547A",
            darkcolor="#23547A",
            relief="flat",
            padding=(11, 6),
            font=("Segoe UI", 9, "bold"),
        )

        style.map(
            "TButton",
            background=[
                ("pressed", "#123A5C"),
                ("active", "#103451"),
            ],
            foreground=[
                ("disabled", muted),
                ("active", "#FFFFFF"),
                ("pressed", "#FFFFFF"),
            ],
            bordercolor=[
                ("focus", cyan),
                ("active", "#2D6998"),
            ],
        )

        style.configure(
            "Action.TButton",
            background="#0B2B47",
            foreground=cyan,
            bordercolor="#24638D",
            lightcolor="#24638D",
            darkcolor="#24638D",
            relief="flat",
            padding=(12, 6),
            font=("Segoe UI", 9, "bold"),
        )

        style.map(
            "Action.TButton",
            background=[
                ("pressed", "#123B5D"),
                ("active", "#103652"),
            ],
            foreground=[
                ("active", "#FFFFFF"),
                ("pressed", "#FFFFFF"),
            ],
        )

        # Ana sekmeler - KODAAI navigation
        style.configure(
            "KODAAI.TNotebook",
            background=bg,
            borderwidth=0,
            tabmargins=(0, 8, 0, 0),
        )

        style.layout(
            "KODAAI.TNotebook",
            [
                (
                    "Notebook.client",
                    {
                        "sticky": "nswe",
                    },
                ),
            ],
        )

        style.configure(
            "KODAAI.TNotebook.Tab",
            background="#071525",
            foreground="#91A8BE",
            borderwidth=0,
            relief="flat",
            padding=(22, 10),
            font=("Segoe UI", 10, "bold"),
        )

        style.map(
            "KODAAI.TNotebook.Tab",
            background=[
                ("selected", "#0D2944"),
                ("active", "#0A2036"),
            ],
            foreground=[
                ("selected", "#20DFFF"),
                ("active", "#F4F8FF"),
            ],
        )

        style.layout(
            "KODAAI.TNotebook.Tab",
            [
                (
                    "Notebook.padding",
                    {
                        "sticky": "nswe",
                        "children": [
                            (
                                "Notebook.label",
                                {
                                    "sticky": "nswe",
                                },
                            ),
                        ],
                    },
                ),
            ],
        )

        # Tablolar
        style.configure(
            "Treeview",
            background=panel,
            fieldbackground=panel,
            foreground=text,
            rowheight=31,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            borderwidth=1,
            font=("Segoe UI", 9),
        )

        style.map(
            "Treeview",
            background=[
                ("selected", selected),
            ],
            foreground=[
                ("selected", "#FFFFFF"),
            ],
        )

        style.configure(
            "Treeview.Heading",
            background="#12375A",
            foreground=cyan,
            bordercolor=border,
            lightcolor=border,
            darkcolor=border,
            relief="flat",
            padding=(9, 9),
            font=("Segoe UI", 9, "bold"),
        )

        style.map(
            "Treeview.Heading",
            background=[
                ("active", "#174B77"),
            ],
            foreground=[
                ("active", "#FFFFFF"),
            ],
        )

        # Metin giri?leri
        style.configure(
            "TEntry",
            fieldbackground=panel,
            foreground=text,
            insertcolor=text,
            bordercolor=border,
            padding=7,
        )

        # Combobox
        style.configure(
            "TCombobox",
            fieldbackground=panel,
            background=panel_alt,
            foreground=text,
            arrowcolor=cyan,
            bordercolor=border,
            padding=6,
        )

        style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", panel),
            ],
            foreground=[
                ("readonly", text),
            ],
            selectbackground=[
                ("readonly", selected),
            ],
        )

        # Scrollbar
        style.configure(
            "Vertical.TScrollbar",
            background=panel_alt,
            troughcolor=bg,
            bordercolor=bg,
            arrowcolor=cyan,
        )

        style.configure(
            "Horizontal.TScrollbar",
            background=panel_alt,
            troughcolor=bg,
            bordercolor=bg,
            arrowcolor=cyan,
        )

        # Combobox a??l?r liste
        self.option_add(
            "*TCombobox*Listbox.background",
            panel,
        )

        self.option_add(
            "*TCombobox*Listbox.foreground",
            text,
        )

        self.option_add(
            "*TCombobox*Listbox.selectBackground",
            selected,
        )

        self.option_add(
            "*TCombobox*Listbox.selectForeground",
            "#FFFFFF",
        )


    def _build_ui(self):
        header = ttk.Frame(self, padding=12)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="KODAAI Lokal AI",
            style="DashboardTitle.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Operasyon Dashboard  v0.2",
            style="DashboardAccent.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        ttk.Label(
            header,
            textvariable=self.status_var,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(8, 0))

        ttk.Label(
            header,
            textvariable=self.summary_var,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        ttk.Label(
            header,
            textvariable=self.routing_leaks_var,
            font=("Segoe UI", 9),
            justify="left",
            wraplength=1450,
        ).pack(anchor="w", pady=(4, 0))

        toolbar = ttk.Frame(
            self,
            padding=(12, 0, 12, 10),
        )
        toolbar.pack(fill="x")

        ttk.Button(
            toolbar,
            text="G" + chr(252) + "ncelle",
            command=self.refresh_all,
            style="Action.TButton",
        ).pack(side="left")

        ttk.Label(
            toolbar,
            textvariable=self.updated_var,
        ).pack(side="left", padx=15)

        notebook = ttk.Notebook(self, style="KODAAI.TNotebook")
        notebook.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 12),
        )
        self.telemetry_tab = ttk.Frame(notebook)
        self.logs_tab = ttk.Frame(notebook)
        self.release_tab = ttk.Frame(notebook)

        notebook.add(
            self.telemetry_tab,
            text="  Telemetry",
        )

        notebook.add(
            self.logs_tab,
            text="  Loglar",
        )


        notebook.add(
            self.release_tab,
            text="Sürüm Geçmişi",
        )
        self._build_telemetry_tab()
        self._build_logs_tab()

        self._build_release_tab()
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # RELEASE HISTORY
    # ---------------------------------------------------------

    def _build_release_tab(self):
        header = ttk.Frame(
            self.release_tab,
            padding=12,
        )
        header.pack(fill="x")

        ttk.Label(
            header,
            text="KODAAI Lokal AI  Güncel Sürüm v0.2",
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=(
                "Sürüm geçmişi ve önemli teknik değişiklikler"
            ),
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 8))

        metrics = ttk.Frame(
            self.release_tab,
            padding=(12, 0, 12, 10),
        )
        metrics.pack(fill="x")

        ttk.Label(
            metrics,
            text="Current Version: v0.2",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(0, 25))

        ttk.Label(
            metrics,
            text="Direct Knowledge: 22M+",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(0, 25))

        ttk.Label(
            metrics,
            text="LLM: Gemma 3 4B",
        ).pack(side="left", padx=(0, 25))

        ttk.Label(
            metrics,
            text="Telemetry: Active",
        ).pack(side="left")

        controls = ttk.Frame(
            self.release_tab,
            padding=(12, 0, 12, 8),
        )
        controls.pack(fill="x")

        ttk.Button(
            controls,
            text="YENİLE",
            command=self.refresh_release_history,
        ).pack(side="left")

        frame = ttk.Frame(
            self.release_tab,
            padding=(12, 0, 12, 12),
        )
        frame.pack(
            fill="both",
            expand=True,
        )

        columns = (
            "version",
            "date",
            "area",
            "change",
            "status",
        )

        self.release_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
        )

        headings = {
            "version": "Sürüm",
            "date": "Tarih",
            "area": "Alan",
            "change": "Değişiklik",
            "status": "Durum",
        }

        widths = {
            "version": 90,
            "date": 110,
            "area": 150,
            "change": 850,
            "status": 120,
        }

        for column in columns:
            self.release_tree.heading(
                column,
                text=headings[column],
            )

            self.release_tree.column(
                column,
                width=widths[column],
                anchor="w",
            )

        self.release_tree.column(
            "version",
            anchor="center",
        )

        self.release_tree.column(
            "date",
            anchor="center",
        )

        self.release_tree.column(
            "status",
            anchor="center",
        )

        scroll_y = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.release_tree.yview,
        )

        scroll_x = ttk.Scrollbar(
            frame,
            orient="horizontal",
            command=self.release_tree.xview,
        )

        self.release_tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )

        self.release_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scroll_y.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        scroll_x.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        frame.rowconfigure(
            0,
            weight=1,
        )

        frame.columnconfigure(
            0,
            weight=1,
        )

        self.refresh_release_history()


    def refresh_release_history(self):
        if not hasattr(self, "release_tree"):
            return

        for item in self.release_tree.get_children():
            self.release_tree.delete(item)

        if not RELEASE_HISTORY_FILE.exists():
            self.release_tree.insert(
                "",
                "end",
                values=(
                    "-",
                    "-",
                    "System",
                    "release_history.json bulunamadı.",
                    "ERROR",
                ),
            )
            return

        try:
            with RELEASE_HISTORY_FILE.open(
                "r",
                encoding="utf-8",
            ) as file:
                records = json.load(file)

        except Exception as exc:
            self.release_tree.insert(
                "",
                "end",
                values=(
                    "-",
                    "-",
                    "System",
                    f"Sürüm geçmişi okunamadı: {exc}",
                    "ERROR",
                ),
            )
            return

        for record in records:
            self.release_tree.insert(
                "",
                "end",
                values=(
                    record.get("version", ""),
                    record.get("date", ""),
                    record.get("area", ""),
                    record.get("change", ""),
                    record.get("status", ""),
                ),
            )

    # TELEMETRY
    # ---------------------------------------------------------

    def _build_telemetry_tab(self):
        columns = (
            "timestamp",
            "route",
            "subject",
            "duration",
            "sources",
            "context",
            "accessibility",
            "success",
            "blocked",
        )

        self.tree = ttk.Treeview(
            self.telemetry_tab,
            columns=columns,
            show="headings",
        )

        headings = {
            "timestamp": "Zaman",
            "route": "Route",
            "subject": "Konu",
            "duration": "Sure (ms)",
            "sources": "Kaynak",
            "context": "Context",
            "accessibility": "Accessibility",
            "success": "Basarili",
            "blocked": "Blocked",
        }

        widths = {
            "timestamp": 155,
            "route": 130,
            "subject": 110,
            "duration": 100,
            "sources": 70,
            "context": 75,
            "accessibility": 190,
            "success": 75,
            "blocked": 75,
        }

        for column in columns:
            self.tree.heading(
                column,
                text=headings[column],
            )
            self.tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        self.tree.column(
            "accessibility",
            anchor="w",
        )

        scroll_y = ttk.Scrollbar(
            self.telemetry_tab,
            orient="vertical",
            command=self.tree.yview,
        )

        scroll_x = ttk.Scrollbar(
            self.telemetry_tab,
            orient="horizontal",
            command=self.tree.xview,
        )

        self.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scroll_y.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        scroll_x.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self.telemetry_tab.rowconfigure(
            0,
            weight=1,
        )

        self.telemetry_tab.columnconfigure(
            0,
            weight=1,
        )

    # ---------------------------------------------------------
    # LOGS
    # ---------------------------------------------------------

    def _build_logs_tab(self):
        log_notebook = ttk.Notebook(self.logs_tab)
        log_notebook.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

        self.http_tab = ttk.Frame(log_notebook)
        self.system_log_tab = ttk.Frame(log_notebook)

        log_notebook.add(
            self.http_tab,
            text="HTTP Istekleri",
        )

        log_notebook.add(
            self.system_log_tab,
            text="Sistem Logu",
        )

        self._build_http_tab()
        self._build_system_log_tab()

    def _build_http_tab(self):
        controls = ttk.Frame(
            self.http_tab,
            padding=8,
        )
        controls.pack(fill="x")

        ttk.Label(
            controls,
            textvariable=self.http_summary_var,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        ttk.Label(
            controls,
            text="Filtre:",
        ).pack(
            side="left",
            padx=(30, 5),
        )

        ttk.Entry(
            controls,
            textvariable=self.http_search_var,
            width=30,
        ).pack(side="left")

        ttk.Button(
            controls,
            text="ARA",
            command=self.refresh_http,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Button(
            controls,
            text="TEMIZLE",
            command=self.clear_http_search,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        columns = (
            "ip",
            "port",
            "method",
            "path",
            "status",
        )

        self.http_tree = ttk.Treeview(
            self.http_tab,
            columns=columns,
            show="headings",
        )

        headings = {
            "ip": "IP Adresi",
            "port": "Port",
            "method": "Method",
            "path": "Endpoint",
            "status": "Status",
        }

        widths = {
            "ip": 180,
            "port": 80,
            "method": 100,
            "path": 700,
            "status": 100,
        }

        for column in columns:
            self.http_tree.heading(
                column,
                text=headings[column],
            )

            self.http_tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        self.http_tree.column(
            "path",
            anchor="w",
        )

        frame = ttk.Frame(
            self.http_tab,
            padding=(8, 0, 8, 8),
        )
        frame.pack(
            fill="both",
            expand=True,
        )

        self.http_tree.pack_forget()

        scroll_y = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.http_tree.yview,
        )

        scroll_x = ttk.Scrollbar(
            frame,
            orient="horizontal",
            command=self.http_tree.xview,
        )

        self.http_tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )

        self.http_tree.master = frame

        self.http_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
            in_=frame,
        )

        scroll_y.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        scroll_x.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        frame.rowconfigure(
            0,
            weight=1,
        )

        frame.columnconfigure(
            0,
            weight=1,
        )


    def _build_system_log_tab(self):
        controls = ttk.Frame(
            self.system_log_tab,
            padding=8,
        )
        controls.pack(fill="x")

        ttk.Label(
            controls,
            text="Log:",
        ).pack(side="left")

        combo = ttk.Combobox(
            controls,
            textvariable=self.log_file_var,
            values=list(LOG_FILES.keys()),
            state="readonly",
            width=24,
        )
        combo.pack(
            side="left",
            padx=(6, 15),
        )

        combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.refresh_system_log(),
        )

        ttk.Label(
            controls,
            text="Ara:",
        ).pack(side="left")

        ttk.Entry(
            controls,
            textvariable=self.log_search_var,
            width=30,
        ).pack(
            side="left",
            padx=(6, 8),
        )

        ttk.Button(
            controls,
            text="ARA",
            command=self.refresh_system_log,
        ).pack(side="left")

        ttk.Button(
            controls,
            text="TEMIZLE",
            command=self.clear_log_search,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        frame = ttk.Frame(
            self.system_log_tab,
            padding=(8, 0, 8, 8),
        )
        frame.pack(
            fill="both",
            expand=True,
        )

        columns = (
            "time",
            "level",
            "component",
            "message",
        )

        self.system_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
        )

        headings = {
            "time": "Zaman",
            "level": "Seviye",
            "component": "Bilesen",
            "message": "Olay / Mesaj",
        }

        widths = {
            "time": 150,
            "level": 110,
            "component": 140,
            "message": 900,
        }

        for column in columns:
            self.system_tree.heading(
                column,
                text=headings[column],
            )

            self.system_tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        self.system_tree.column(
            "message",
            anchor="w",
        )

        scroll_y = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.system_tree.yview,
        )

        scroll_x = ttk.Scrollbar(
            frame,
            orient="horizontal",
            command=self.system_tree.xview,
        )

        self.system_tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )

        self.system_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        scroll_y.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        scroll_x.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        frame.rowconfigure(
            0,
            weight=1,
        )

        frame.columnconfigure(
            0,
            weight=1,
        )

    def _port_8080_status(self):
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        sock.settimeout(0.5)

        try:
            return (
                sock.connect_ex(
                    ("127.0.0.1", 8080)
                )
                == 0
            )
        finally:
            sock.close()

    def _load_telemetry(self):
        if not TELEMETRY_FILE.exists():
            return []

        records = []

        with TELEMETRY_FILE.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:

            for line in handle:
                line = line.strip()

                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if (
                    record.get("event_type")
                    == "request_completed"
                ):
                    records.append(record)

        return records[-MAX_TELEMETRY_ROWS:]

    def refresh_telemetry(self):
        records = self._load_telemetry()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for record in reversed(records):
            duration = record.get("duration_ms")

            if isinstance(duration, (int, float)):
                duration = round(duration, 2)

            self.tree.insert(
                "",
                "end",
                values=(
                    record.get("timestamp", ""),
                    record.get("route", ""),
                    record.get("subject", ""),
                    duration if duration is not None else "",
                    record.get("source_count", ""),
                    str(record.get("used_context", "")),
                    record.get("accessibility_layer", ""),
                    str(record.get("success", "")),
                    str(record.get("blocked", "")),
                ),
            )

        route_counts = {}
        route_durations = {}
        durations = []

        for record in records:
            route = record.get(
                "route",
                "UNKNOWN",
            )

            route_counts[route] = (
                route_counts.get(route, 0)
                + 1
            )

            duration = record.get("duration_ms")

            if isinstance(duration, (int, float)):
                durations.append(duration)

                route_durations.setdefault(
                    route,
                    []
                ).append(duration)

        average = (
            sum(durations) / len(durations)
            if durations
            else 0
        )

        def route_average(route_name):
            values = route_durations.get(
                route_name,
                []
            )

            return (
                sum(values) / len(values)
                if values
                else 0
            )

        math_avg = route_average("MATH")
        direct_avg = route_average(
            "DIRECT_KNOWLEDGE"
        )
        rag_avg = route_average("RAG")
        llm_avg = route_average("LLM")

        speed_ratio = (
            llm_avg / direct_avg
            if direct_avg > 0 and llm_avg > 0
            else 0
        )

        llm_records = [
            record
            for record in records
            if record.get("route") == "LLM"
        ]

        llm_none_count = sum(
            1
            for record in llm_records
            if record.get("subject") in (
                None,
                "",
                "None",
            )
        )

        llm_routed_count = (
            len(llm_records)
            - llm_none_count
        )

        routing_leaks = [
            record
            for record in llm_records
            if (
                record.get("subject") in (
                    None,
                    "",
                    "None",
                )
                and record.get("question")
            )
        ]

        self.status_var.set(
            "8080: AKTIF"
            if self._port_8080_status()
            else "8080: KAPALI"
        )

        summary_line_1 = (
            f"Son {len(records)} kayit   |   "
            f"MATH: {route_counts.get('MATH', 0)}   |   "
            f"DIRECT_KNOWLEDGE: "
            f"{route_counts.get('DIRECT_KNOWLEDGE', 0)}   |   "
            f"RAG: {route_counts.get('RAG', 0)}   |   "
            f"LLM: {route_counts.get('LLM', 0)}   |   "
            f"LLM routed: {llm_routed_count}   |   "
            f"LLM subject=None: {llm_none_count}   |   "
            f"RAG_NO_ANSWER: "
            f"{route_counts.get('RAG_NO_ANSWER', 0)}"
        )

        summary_line_2 = (
            f"Genel ort.: {average:.2f} ms   |   "
            f"MATH: {math_avg:.2f} ms   |   "
            f"DIRECT: {direct_avg:.2f} ms   |   "
            f"RAG: {rag_avg:.2f} ms   |   "
            f"LLM: {llm_avg / 1000:.2f} sn"
        )

        if speed_ratio > 0:
            summary_line_2 += (
                f"   |   Direct/LLM hiz farki: "
                f"{speed_ratio:.0f}x"
            )

        self.summary_var.set(
            summary_line_1
            + "\n"
            + summary_line_2
        )

        if routing_leaks:
            leak_lines = [
                "Routing Kacaklari:"
            ]

            for record in routing_leaks[-5:][::-1]:
                timestamp = str(
                    record.get("timestamp", "")
                )

                time_part = (
                    timestamp[11:19]
                    if len(timestamp) >= 19
                    else timestamp
                )

                question = " ".join(
                    str(
                        record.get(
                            "question",
                            ""
                        )
                    ).split()
                )

                if len(question) > 120:
                    question = (
                        question[:117]
                        + "..."
                    )

                leak_lines.append(
                    f"{time_part} | {question}"
                )

            self.routing_leaks_var.set(
                "\n".join(leak_lines)
            )

        else:
            self.routing_leaks_var.set(
                "Routing Kacaklari: "
                "Yeni subject=None + LLM kaydi yok."
            )

    # ---------------------------------------------------------
    # HTTP REQUEST TABLE
    # ---------------------------------------------------------

    def _load_http_requests(self):
        if not SERVICE_LOG.exists():
            return []

        requests = []

        with SERVICE_LOG.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:

            for line in handle:
                match = HTTP_PATTERN.search(line)

                if not match:
                    continue

                requests.append(
                    match.groupdict()
                )

        return requests[-MAX_HTTP_ROWS:]

    def refresh_http(self):
        requests = self._load_http_requests()

        search = (
            self.http_search_var.get()
            .strip()
            .casefold()
        )

        filtered = requests

        if search:
            filtered = [
                item
                for item in requests
                if search
                in " ".join(
                    item.values()
                ).casefold()
            ]

        for item in self.http_tree.get_children():
            self.http_tree.delete(item)

        for item in reversed(filtered):
            self.http_tree.insert(
                "",
                "end",
                values=(
                    item["ip"],
                    item["port"],
                    item["method"],
                    item["path"],
                    item["status"],
                ),
            )

        unique_ips = {
            item["ip"]
            for item in requests
        }

        self.http_summary_var.set(
            f"HTTP: {len(requests)}   |   "
            f"Benzersiz IP: {len(unique_ips)}"
        )

    # ---------------------------------------------------------
    # CLEAN SYSTEM LOG
    # ---------------------------------------------------------

    @staticmethod
    def _clean_log_lines(lines):
        cleaned = []

        skip_patterns = (
            "CategoryInfo",
            "FullyQualifiedErrorId",
            "At C:\\KODA_AI_LAB\\start_local_ai.ps1",
            "+         & $python",
            "+         ~",
        )

        for raw in lines:
            line = raw.rstrip()

            if not line:
                continue

            if any(
                pattern in line
                for pattern in skip_patterns
            ):
                continue

            if "Loading weights:" in line:
                if "100%" in line:
                    cleaned.append(
                        "[MODEL] Weights loaded."
                    )
                continue

            if (
                len(line) > 250
                and "it/s" in line
            ):
                continue

            line = re.sub(
                r"\x1b\[[0-9;]*[A-Za-z]",
                "",
                line,
            )

            cleaned.append(line)

        return cleaned



    def _parse_service_log(self, path):
        rows = []

        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        last_clock = ""

        for raw in lines:
            line = raw.strip()

            if not line:
                continue

            if line.startswith("="):
                continue

            start_match = re.search(
                r"KODAAI LOCAL AI START:\s+"
                r"(\d{4}-\d{2}-\d{2})\s+"
                r"(\d{2}:\d{2}:\d{2})",
                line,
            )

            if start_match:
                last_clock = start_match.group(2)

                rows.append(
                    (
                        last_clock,
                        "START",
                        "SERVICE",
                        "KODAAI Local AI baslatildi",
                    )
                )
                continue

            display_time = (
                last_clock[:5] + ":xx"
                if last_clock
                else ""
            )

            if (
                "unauthenticated requests to the HF Hub"
                in line
            ):
                rows.append(
                    (
                        display_time,
                        "WARNING",
                        "HF HUB",
                        "Authentication token tanimli degil",
                    )
                )
                continue

            if (
                "System.Management.Automation.RemoteException"
                in line
            ):
                continue

            if "Loading weights:" in line:
                if "100%" in line:
                    rows.append(
                        (
                            display_time,
                            "INFO",
                            "MODEL",
                            "Weights loaded",
                        )
                    )
                continue

            http_match = HTTP_PATTERN.search(line)

            if http_match:
                data = http_match.groupdict()

                rows.append(
                    (
                        display_time,
                        "INFO",
                        "HTTP",
                        (
                            f'{data["method"]} '
                            f'{data["path"]} -> '
                            f'{data["status"]}'
                        ),
                    )
                )
                continue

            if "Started server process" in line:
                rows.append(
                    (
                        display_time,
                        "INFO",
                        "SERVICE",
                        line.replace(
                            "INFO:",
                            "",
                        ).strip(),
                    )
                )
                continue

            if "Application startup complete" in line:
                rows.append(
                    (
                        display_time,
                        "INFO",
                        "SERVICE",
                        "Application startup complete",
                    )
                )
                continue

            if "Uvicorn running on" in line:
                rows.append(
                    (
                        display_time,
                        "INFO",
                        "SERVICE",
                        "Uvicorn 127.0.0.1:8080 uzerinde aktif",
                    )
                )
                continue

            if (
                "Waiting for application startup"
                in line
            ):
                continue

            if (
                "Indekslenecek chunk bulunamadi"
                in line
                or "chunk bulunamad" in line.casefold()
            ):
                rows.append(
                    (
                        display_time,
                        "WARNING",
                        "INDEX",
                        "Indekslenecek chunk bulunamadi",
                    )
                )
                continue

            if (
                "ERROR" in line.upper()
                or "EXCEPTION" in line.upper()
            ):
                rows.append(
                    (
                        display_time,
                        "ERROR",
                        "SERVICE",
                        line,
                    )
                )
                continue

        return rows


    def _parse_json_log(
        self,
        path,
        selected,
    ):
        rows = []

        component_map = {
            "Audit Log": "AUDIT",
            "Blocked Queries": "SECURITY",
            "Telemetry Raw": "TELEMETRY",
        }

        component = component_map.get(
            selected,
            "LOG",
        )

        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        for raw in lines:
            raw = raw.strip()

            if not raw:
                continue

            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                continue

            timestamp = str(
                record.get(
                    "timestamp",
                    "",
                )
            )

            time_value = timestamp

            if "T" in timestamp:
                time_value = timestamp.split(
                    "T",
                    1,
                )[1][:8]

            elif " " in timestamp:
                time_value = timestamp.split(
                    " ",
                    1,
                )[1][:8]

            if selected == "Audit Log":
                question = record.get(
                    "question",
                    "",
                )

                response = record.get(
                    "response",
                    "",
                )

                message = (
                    f"Soru: {question} | "
                    f"Cevap: {response}"
                )

                level = "INFO"

            elif selected == "Blocked Queries":
                question = record.get(
                    "question",
                    "",
                )

                reason = record.get(
                    "reason",
                    "",
                )

                message = (
                    f"Sorgu: {question} | "
                    f"Neden: {reason}"
                )

                level = "BLOCKED"

            else:
                route = record.get(
                    "route",
                    record.get(
                        "event_type",
                        "",
                    ),
                )

                duration = record.get(
                    "duration_ms",
                    "",
                )

                message = (
                    f"Route: {route} | "
                    f"Sure: {duration} ms | "
                    f"Context: "
                    f'{record.get("used_context", "")}'
                )

                level = (
                    "ERROR"
                    if record.get("error")
                    else "INFO"
                )

            rows.append(
                (
                    time_value,
                    level,
                    component,
                    message,
                )
            )

        return rows

    def refresh_system_log(self):
        selected = self.log_file_var.get()
        path = LOG_FILES.get(selected)

        for item in self.system_tree.get_children():
            self.system_tree.delete(item)

        if path is None or not path.exists():
            self.system_tree.insert(
                "",
                "end",
                values=(
                    "",
                    "ERROR",
                    "DASHBOARD",
                    "Log dosyasi bulunamadi.",
                ),
            )
            return

        rows = []

        if path == SERVICE_LOG:
            rows = self._parse_service_log(path)

        else:
            rows = self._parse_json_log(
                path,
                selected,
            )

        search = (
            self.log_search_var.get()
            .strip()
            .casefold()
        )

        if search:
            rows = [
                row
                for row in rows
                if search
                in " ".join(
                    str(value)
                    for value in row
                ).casefold()
            ]

        rows = rows[-MAX_LOG_LINES:]

        if not rows:
            self.system_tree.insert(
                "",
                "end",
                values=(
                    "",
                    "INFO",
                    "DASHBOARD",
                    "Eslesen kayit bulunamadi.",
                ),
            )
            return

        for row in reversed(rows):
            self.system_tree.insert(
                "",
                "end",
                values=row,
            )

    def clear_http_search(self):
        self.http_search_var.set("")
        self.refresh_http()

    def clear_log_search(self):
        self.log_search_var.set("")
        self.refresh_system_log()

    def refresh_all(self):
        self.refresh_telemetry()
        self.refresh_http()
        self.refresh_system_log()

        self.updated_var.set(
            "Son g" + chr(252) + "ncelleme: "
            + datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


if __name__ == "__main__":
    app = KODAAIDashboard()
    app.mainloop()
