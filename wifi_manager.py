"""
WiFi Manager Pro — Python 3.x | Windows  v2.0
Функции: сканирование сетей, мониторинг сигнала, управление подключением,
         просмотр сохранённых профилей, получение паролей, статистика,
         поиск по сетям, ping, трассировка, экспорт лога, горячие клавиши,
         копирование данных, быстрые действия через контекстное меню.
Зависимости: только стандартная библиотека + tkinter (встроен в Python).
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import subprocess
import threading
import time
import re
import os
import sys
import json
import csv
from datetime import datetime


# ──────────────────────────── ЦВЕТА И СТИЛИ ────────────────────────────

BG        = "#0d1117"
PANEL     = "#161b22"
BORDER    = "#30363d"
ACCENT    = "#58a6ff"
ACCENT2   = "#3fb950"
WARN      = "#f0883e"
DANGER    = "#f85149"
TEXT      = "#e6edf3"
SUBTEXT   = "#8b949e"
HOVER     = "#1f2937"
PURPLE    = "#bc8cff"

FONT_HEAD = ("Consolas", 18, "bold")
FONT_SUB  = ("Consolas", 10)
FONT_BODY = ("Consolas", 10)
FONT_MONO = ("Courier New", 9)


# ──────────────────────────── УТИЛИТЫ ────────────────────────────

def run_cmd(cmd: str, timeout: int = 15) -> str:
    """Выполнить команду и вернуть stdout (или сообщение об ошибке)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, encoding="cp866", errors="replace",
            timeout=timeout
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "[Ошибка]: Превышено время ожидания команды"
    except Exception as e:
        return f"[Ошибка]: {e}"


def signal_bars(rssi: int) -> str:
    """Конвертировать RSSI (%) в символьные полосы."""
    if rssi >= 80:   return "████  Отличный"
    if rssi >= 60:   return "███░  Хороший"
    if rssi >= 40:   return "██░░  Средний"
    if rssi >= 20:   return "█░░░  Слабый"
    return               "░░░░  Нет сигнала"


def signal_color(rssi: int) -> str:
    if rssi >= 60: return ACCENT2
    if rssi >= 30: return WARN
    return DANGER


def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ──────────────────────────── ПАРСЕРЫ ────────────────────────────

def parse_networks(raw: str) -> list[dict]:
    """Разобрать вывод `netsh wlan show networks mode=bssid`."""
    networks = []
    current: dict | None = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("SSID") and "BSSID" not in line:
            if current:
                networks.append(current)
            ssid = line.split(":", 1)[-1].strip()
            current = {"ssid": ssid or "<Скрытая>", "bssid": "—",
                       "signal": 0, "auth": "—", "cipher": "—",
                       "band": "—", "channel": "—"}
        elif current:
            if "BSSID" in line:
                current["bssid"] = line.split(":", 1)[-1].strip()
            elif re.search(r"Сигнал|Signal", line):
                m = re.search(r"(\d+)%", line)
                current["signal"] = int(m.group(1)) if m else 0
            elif re.search(r"Тип проверки подлинности|Authentication", line):
                current["auth"] = line.split(":", 1)[-1].strip()
            elif re.search(r"Тип шифрования|Cipher", line):
                current["cipher"] = line.split(":", 1)[-1].strip()
            elif re.search(r"Радиотип|Radio type", line):
                current["band"] = line.split(":", 1)[-1].strip()
            elif re.search(r"Канал|Channel", line):
                current["channel"] = line.split(":", 1)[-1].strip()
    if current:
        networks.append(current)
    return networks


def parse_profiles(raw: str) -> list[str]:
    """Имена сохранённых профилей."""
    profiles = []
    for line in raw.splitlines():
        m = re.search(r"Профиль всех пользователей\s*:\s*(.+)|All User Profile\s*:\s*(.+)", line)
        if m:
            profiles.append((m.group(1) or m.group(2)).strip())
    return profiles


def parse_profile_password(raw: str) -> str:
    """Извлечь пароль из вывода профиля."""
    for line in raw.splitlines():
        m = re.search(r"Содержимое ключа\s*:\s*(.+)|Key Content\s*:\s*(.+)", line)
        if m:
            return (m.group(1) or m.group(2)).strip()
    return "—"


def parse_connection_info(raw: str) -> dict:
    """Текущее подключение."""
    info = {}
    for line in raw.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            info[key.strip()] = val.strip()
    return info


def parse_ip_info(raw: str) -> dict:
    """Разобрать вывод ipconfig для текущего Wi-Fi адаптера."""
    info = {}
    in_wifi = False
    for line in raw.splitlines():
        if re.search(r"Wi-Fi|Беспроводная|Wireless", line, re.IGNORECASE):
            in_wifi = True
        if in_wifi:
            if re.search(r"IPv4|IPv4-адрес", line):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m: info["IPv4"] = m.group(1)
            elif re.search(r"Маска|Subnet", line):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m: info["Маска"] = m.group(1)
            elif re.search(r"Шлюз|Gateway", line):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m: info["Шлюз"] = m.group(1)
            elif re.search(r"DNS", line):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m and "DNS" not in info: info["DNS"] = m.group(1)
            elif line.strip() == "" and in_wifi and info:
                break  # конец секции
    return info


# ══════════════════════════════════════════════════════════════════
#  ГЛАВНОЕ ОКНО
# ══════════════════════════════════════════════════════════════════

class WiFiManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WiFi Manager Pro  v2.0")
        self.geometry("1060x720")
        self.minsize(860, 580)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._monitor_running = False
        self._monitor_thread: threading.Thread | None = None
        self._networks: list[dict] = []
        self._profiles: list[str] = []
        self._ping_running = False
        self._notebook: ttk.Notebook | None = None

        self._build_ui()
        self._bind_hotkeys()
        self._refresh_networks()
        self._refresh_profiles()
        self._refresh_status()

    # ─────────── ГОРЯЧИЕ КЛАВИШИ ───────────

    def _bind_hotkeys(self):
        self.bind("<F5>",          lambda e: self._refresh_networks())
        self.bind("<Control-q>",   lambda e: self.destroy())
        self.bind("<Control-s>",   lambda e: self._refresh_status())
        self.bind("<F1>",          lambda e: self._show_about_popup())

    # ─────────── UI BUILDER ───────────

    def _build_ui(self):
        # ── Заголовок ──
        header = tk.Frame(self, bg=PANEL, height=56)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(header, text="📡  WiFi Manager Pro",
                 font=FONT_HEAD, bg=PANEL, fg=ACCENT).pack(side="left", padx=20, pady=10)

        # Кнопка быстрого обновления в хедере
        self._btn(header, "🔄 F5", self._refresh_networks, ACCENT).pack(side="left", padx=4, pady=12)

        self._status_dot = tk.Label(header, text="●", font=("Consolas", 14),
                                    bg=PANEL, fg=SUBTEXT)
        self._status_dot.pack(side="right", padx=6)
        self._status_lbl = tk.Label(header, text="Статус: —",
                                    font=FONT_SUB, bg=PANEL, fg=SUBTEXT)
        self._status_lbl.pack(side="right", padx=(0, 4))

        # Время последнего обновления
        self._last_scan_lbl = tk.Label(header, text="", font=FONT_MONO, bg=PANEL, fg=SUBTEXT)
        self._last_scan_lbl.pack(side="right", padx=16)

        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x")

        # ── Вкладки ──
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",        background=BG,    borderwidth=0)
        style.configure("TNotebook.Tab",    background=PANEL, foreground=SUBTEXT,
                        padding=[14, 6],    font=FONT_SUB,    borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", ACCENT)])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self._notebook = nb

        self._tab_scan      = self._make_frame(nb)
        self._tab_profiles  = self._make_frame(nb)
        self._tab_monitor   = self._make_frame(nb)
        self._tab_connect   = self._make_frame(nb)
        self._tab_tools     = self._make_frame(nb)
        self._tab_info      = self._make_frame(nb)

        nb.add(self._tab_scan,     text="  🔍 Сканирование  ")
        nb.add(self._tab_profiles, text="  💾 Профили  ")
        nb.add(self._tab_monitor,  text="  📊 Мониторинг  ")
        nb.add(self._tab_connect,  text="  🔗 Подключение  ")
        nb.add(self._tab_tools,    text="  🛠 Диагностика  ")
        nb.add(self._tab_info,     text="  ℹ️ О программе  ")

        self._build_scan_tab()
        self._build_profiles_tab()
        self._build_monitor_tab()
        self._build_connect_tab()
        self._build_tools_tab()
        self._build_info_tab()

    def _make_frame(self, parent) -> tk.Frame:
        return tk.Frame(parent, bg=BG)

    # ─────────── ВКЛАДКА 1: СКАНИРОВАНИЕ ───────────

    def _build_scan_tab(self):
        tab = self._tab_scan

        toolbar = tk.Frame(tab, bg=BG)
        toolbar.pack(fill="x", padx=16, pady=(14, 0))

        self._btn_scan = self._btn(toolbar, "🔄  Обновить (F5)", self._refresh_networks)
        self._btn_scan.pack(side="left")

        self._sort_var = tk.StringVar(value="Сигнал ↓")
        tk.Label(toolbar, text="Сортировка:", bg=BG, fg=SUBTEXT, font=FONT_SUB).pack(side="left", padx=(16, 4))
        sort_cb = ttk.Combobox(toolbar, textvariable=self._sort_var,
                               values=["Сигнал ↓", "Сигнал ↑", "Имя A→Z", "Канал"],
                               width=12, state="readonly", font=FONT_SUB)
        sort_cb.pack(side="left")
        sort_cb.bind("<<ComboboxSelected>>", lambda e: self._render_networks())

        # Поиск
        tk.Label(toolbar, text="Поиск:", bg=BG, fg=SUBTEXT, font=FONT_SUB).pack(side="left", padx=(16, 4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._render_networks())
        search_entry = self._entry(toolbar, width=18)
        search_entry.config(textvariable=self._search_var)
        search_entry.pack(side="left")

        # Фильтр безопасности
        tk.Label(toolbar, text="Безопасность:", bg=BG, fg=SUBTEXT, font=FONT_SUB).pack(side="left", padx=(10, 4))
        self._filter_auth = tk.StringVar(value="Все")
        filter_cb = ttk.Combobox(toolbar, textvariable=self._filter_auth,
                                 values=["Все", "WPA2", "WPA3", "Open"],
                                 width=8, state="readonly", font=FONT_SUB)
        filter_cb.pack(side="left")
        filter_cb.bind("<<ComboboxSelected>>", lambda e: self._render_networks())

        self._scan_count = tk.Label(toolbar, text="", bg=BG, fg=SUBTEXT, font=FONT_SUB)
        self._scan_count.pack(side="right")

        # Таблица
        cols = ("SSID", "Сигнал", "Безопасность", "Шифр", "Канал", "Диапазон", "BSSID")
        frame = tk.Frame(tab, bg=BG)
        frame.pack(fill="both", expand=True, padx=16, pady=10)

        style = ttk.Style()
        style.configure("Scan.Treeview",
                        background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, borderwidth=0,
                        rowheight=26, font=FONT_BODY)
        style.configure("Scan.Treeview.Heading",
                        background=BORDER, foreground=SUBTEXT,
                        borderwidth=0, font=FONT_SUB)
        style.map("Scan.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])

        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                  style="Scan.Treeview")
        widths = [200, 130, 110, 80, 60, 100, 150]
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col,
                               command=lambda c=col: self._sort_by_column(c))
            self._tree.column(col, width=w, minwidth=50)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._tree.bind("<Double-1>", self._on_network_dblclick)
        self._tree.bind("<Button-3>", self._on_network_rightclick)

        # Строка подсказки + кнопки
        bottom = tk.Frame(tab, bg=BG)
        bottom.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(bottom, text="ДвКлик — подключиться  •  ПКМ — контекстное меню  •  F5 — обновить",
                 bg=BG, fg=SUBTEXT, font=FONT_MONO).pack(side="left")
        self._btn(bottom, "📋 Экспорт в CSV", self._export_networks_csv, ACCENT2).pack(side="right")

        # Контекстное меню
        self._ctx_menu = tk.Menu(self, tearoff=0, bg=PANEL, fg=TEXT,
                                 activebackground=ACCENT, activeforeground=BG,
                                 font=FONT_SUB, bd=0)
        self._ctx_menu.add_command(label="🔗  Подключиться",      command=self._ctx_connect)
        self._ctx_menu.add_command(label="📶  Пинг шлюза",        command=self._ctx_ping_gateway)
        self._ctx_menu.add_command(label="📋  Копировать SSID",   command=self._ctx_copy_ssid)
        self._ctx_menu.add_command(label="📋  Копировать BSSID",  command=self._ctx_copy_bssid)

    def _sort_by_column(self, col: str):
        """Сортировка по клику на заголовок столбца."""
        col_map = {
            "SSID": "ssid", "Сигнал": "signal",
            "Безопасность": "auth", "Канал": "channel",
            "Диапазон": "band", "BSSID": "bssid", "Шифр": "cipher"
        }
        key = col_map.get(col, "ssid")
        reverse = self._sort_var.get().endswith("↓")
        self._networks.sort(key=lambda n: n.get(key, ""), reverse=not reverse)
        self._render_networks()

    def _render_networks(self):
        sort = self._sort_var.get()
        search = self._search_var.get().lower()
        auth_filter = self._filter_auth.get()

        nets = list(self._networks)

        # Фильтры
        if search:
            nets = [n for n in nets if search in n["ssid"].lower() or search in n["bssid"].lower()]
        if auth_filter != "Все":
            nets = [n for n in nets if auth_filter.upper() in n["auth"].upper()]

        # Сортировка
        if sort == "Сигнал ↓":   nets.sort(key=lambda n: n["signal"], reverse=True)
        elif sort == "Сигнал ↑": nets.sort(key=lambda n: n["signal"])
        elif sort == "Имя A→Z":  nets.sort(key=lambda n: n["ssid"].lower())
        elif sort == "Канал":    nets.sort(key=lambda n: n.get("channel", "0"))

        for row in self._tree.get_children():
            self._tree.delete(row)

        for n in nets:
            sig_txt = f"{n['signal']}%  {signal_bars(n['signal'])}"
            tag = "good" if n["signal"] >= 60 else ("warn" if n["signal"] >= 30 else "bad")
            self._tree.insert("", "end", values=(
                n["ssid"], sig_txt, n["auth"], n.get("cipher", "—"),
                n.get("channel", "—"), n.get("band", "—"), n["bssid"]
            ), tags=(tag,))

        self._tree.tag_configure("good", foreground=ACCENT2)
        self._tree.tag_configure("warn", foreground=WARN)
        self._tree.tag_configure("bad",  foreground=DANGER)
        self._scan_count.config(text=f"Найдено: {len(nets)} / {len(self._networks)}")

    def _refresh_networks(self):
        self._btn_scan.config(state="disabled", text="⏳  Сканирование...")
        self._scan_count.config(text="Сканирование…")

        def task():
            raw = run_cmd("netsh wlan show networks mode=bssid")
            self._networks = parse_networks(raw)
            ts = datetime.now().strftime("%H:%M:%S")
            self.after(0, lambda: (
                self._render_networks(),
                self._btn_scan.config(state="normal", text="🔄  Обновить (F5)"),
                self._last_scan_lbl.config(text=f"Обновлено: {ts}")
            ))
        threading.Thread(target=task, daemon=True).start()

    def _on_network_dblclick(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        ssid = self._tree.item(sel[0])["values"][0]
        auth = self._tree.item(sel[0])["values"][2]
        self._open_connect_dialog(ssid, str(auth))

    def _on_network_rightclick(self, event):
        row = self._tree.identify_row(event.y)
        if row:
            self._tree.selection_set(row)
            self._ctx_menu.post(event.x_root, event.y_root)

    def _ctx_connect(self):
        sel = self._tree.selection()
        if sel:
            ssid = self._tree.item(sel[0])["values"][0]
            auth = self._tree.item(sel[0])["values"][2]
            self._open_connect_dialog(ssid, str(auth))

    def _ctx_ping_gateway(self):
        """Перейти на вкладку Диагностика и пингануть шлюз."""
        if self._notebook:
            self._notebook.select(4)

    def _ctx_copy_ssid(self):
        sel = self._tree.selection()
        if sel:
            ssid = str(self._tree.item(sel[0])["values"][0])
            self.clipboard_clear()
            self.clipboard_append(ssid)

    def _ctx_copy_bssid(self):
        sel = self._tree.selection()
        if sel:
            bssid = str(self._tree.item(sel[0])["values"][6])
            self.clipboard_clear()
            self.clipboard_append(bssid)

    def _export_networks_csv(self):
        if not self._networks:
            messagebox.showinfo("Экспорт", "Нет данных для экспорта. Выполните сканирование.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")],
            initialfile=f"wifi_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["ssid","bssid","signal","auth","cipher","band","channel"])
                writer.writeheader()
                writer.writerows(self._networks)
            messagebox.showinfo("Экспорт", f"Сохранено: {path}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # ─────────── ВКЛАДКА 2: ПРОФИЛИ ───────────

    def _build_profiles_tab(self):
        tab = self._tab_profiles

        toolbar = tk.Frame(tab, bg=BG)
        toolbar.pack(fill="x", padx=16, pady=(14, 0))
        self._btn_prof   = self._btn(toolbar, "🔄  Обновить", self._refresh_profiles)
        self._btn_prof.pack(side="left")
        self._btn_pass   = self._btn(toolbar, "🔑  Показать пароль", self._show_password, WARN)
        self._btn_pass.pack(side="left", padx=8)
        self._btn_copy_pass = self._btn(toolbar, "📋 Копировать пароль", self._copy_password, PURPLE)
        self._btn_copy_pass.pack(side="left")
        self._btn_del    = self._btn(toolbar, "🗑  Удалить профиль", self._delete_profile, DANGER)
        self._btn_del.pack(side="left", padx=8)
        self._btn_export = self._btn(toolbar, "💾  Экспорт всех", self._export_profiles, ACCENT2)
        self._btn_export.pack(side="left")
        self._btn_connect_profile = self._btn(toolbar, "🔗  Подключиться", self._connect_to_profile, ACCENT)
        self._btn_connect_profile.pack(side="left", padx=8)

        self._prof_count_lbl = tk.Label(toolbar, text="", bg=BG, fg=SUBTEXT, font=FONT_SUB)
        self._prof_count_lbl.pack(side="right")

        frame = tk.Frame(tab, bg=BG)
        frame.pack(fill="both", expand=True, padx=16, pady=10)

        self._prof_list = tk.Listbox(frame, bg=PANEL, fg=TEXT, selectbackground=ACCENT,
                                     selectforeground=BG, font=FONT_BODY, borderwidth=0,
                                     highlightthickness=0, activestyle="none")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._prof_list.yview)
        self._prof_list.configure(yscrollcommand=vsb.set)
        self._prof_list.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._prof_detail = scrolledtext.ScrolledText(
            tab, height=7, bg=PANEL, fg=ACCENT2, font=FONT_MONO,
            borderwidth=0, state="disabled"
        )
        self._prof_detail.pack(fill="x", padx=16, pady=(0, 10))

        self._prof_list.bind("<<ListboxSelect>>", self._on_profile_select)
        self._prof_list.bind("<Double-1>", lambda e: self._connect_to_profile())

    def _refresh_profiles(self):
        raw = run_cmd("netsh wlan show profiles")
        self._profiles = parse_profiles(raw)
        self._prof_list.delete(0, "end")
        for p in self._profiles:
            self._prof_list.insert("end", f"  📶  {p}")
        self._prof_count_lbl.config(text=f"Профилей: {len(self._profiles)}")

    def _on_profile_select(self, event):
        sel = self._prof_list.curselection()
        if not sel:
            return
        name = self._profiles[sel[0]]
        raw = run_cmd(f'netsh wlan show profile name="{name}"')
        self._show_prof_detail(raw)

    def _show_prof_detail(self, text: str):
        self._prof_detail.config(state="normal")
        self._prof_detail.delete("1.0", "end")
        self._prof_detail.insert("end", text)
        self._prof_detail.config(state="disabled")

    def _show_password(self):
        sel = self._prof_list.curselection()
        if not sel:
            messagebox.showinfo("WiFi Manager", "Выберите профиль в списке.")
            return
        name = self._profiles[sel[0]]
        raw = run_cmd(f'netsh wlan show profile name="{name}" key=clear')
        pwd = parse_profile_password(raw)
        messagebox.showinfo(f"Пароль: {name}", f"🔑  Пароль: {pwd}")

    def _copy_password(self):
        """Скопировать пароль выбранного профиля в буфер обмена."""
        sel = self._prof_list.curselection()
        if not sel:
            messagebox.showinfo("WiFi Manager", "Выберите профиль в списке.")
            return
        name = self._profiles[sel[0]]
        raw = run_cmd(f'netsh wlan show profile name="{name}" key=clear')
        pwd = parse_profile_password(raw)
        if pwd == "—":
            messagebox.showinfo("Пароль", "Пароль не найден или профиль открытый.")
            return
        self.clipboard_clear()
        self.clipboard_append(pwd)
        messagebox.showinfo("Скопировано", f"Пароль для «{name}» скопирован в буфер.")

    def _connect_to_profile(self):
        """Подключиться к выбранному профилю напрямую."""
        sel = self._prof_list.curselection()
        if not sel:
            messagebox.showinfo("WiFi Manager", "Выберите профиль в списке.")
            return
        name = self._profiles[sel[0]]
        out = run_cmd(f'netsh wlan connect name="{name}"')
        color = ACCENT2 if "успешно" in out.lower() or "success" in out.lower() else WARN
        messagebox.showinfo("Подключение", out.strip() or f"Подключение к «{name}»...")
        self.after(1500, self._refresh_status)

    def _delete_profile(self):
        sel = self._prof_list.curselection()
        if not sel:
            messagebox.showinfo("WiFi Manager", "Выберите профиль в списке.")
            return
        name = self._profiles[sel[0]]
        if not messagebox.askyesno("Удалить профиль",
                                   f"Удалить профиль «{name}»?\nСеть будет забыта."):
            return
        out = run_cmd(f'netsh wlan delete profile name="{name}"')
        messagebox.showinfo("Результат", out.strip() or "Удалено.")
        self._refresh_profiles()

    def _export_profiles(self):
        folder = os.path.expanduser("~\\Desktop\\WiFi_Profiles")
        os.makedirs(folder, exist_ok=True)
        out = run_cmd(f'netsh wlan export profile folder="{folder}" key=clear')
        messagebox.showinfo("Экспорт", f"Профили сохранены в:\n{folder}\n\n{out[:300]}")

    # ─────────── ВКЛАДКА 3: МОНИТОРИНГ ───────────

    def _build_monitor_tab(self):
        tab = self._tab_monitor

        toolbar = tk.Frame(tab, bg=BG)
        toolbar.pack(fill="x", padx=16, pady=(14, 6))

        self._btn_mon_start = self._btn(toolbar, "▶  Запустить мониторинг",
                                        self._toggle_monitor)
        self._btn_mon_start.pack(side="left")

        tk.Label(toolbar, text="Интервал (сек):", bg=BG, fg=SUBTEXT, font=FONT_SUB).pack(side="left", padx=(16, 4))
        self._interval_var = tk.IntVar(value=3)
        sp = ttk.Spinbox(toolbar, from_=1, to=60, textvariable=self._interval_var,
                         width=5, font=FONT_SUB)
        sp.pack(side="left")

        self._btn_mon_clear = self._btn(toolbar, "🗑  Очистить", self._clear_monitor, DANGER)
        self._btn_mon_clear.pack(side="left", padx=8)

        self._btn_mon_export = self._btn(toolbar, "💾  Сохранить лог", self._export_monitor_log, ACCENT2)
        self._btn_mon_export.pack(side="left")

        self._mon_stats_lbl = tk.Label(toolbar, text="", bg=BG, fg=SUBTEXT, font=FONT_SUB)
        self._mon_stats_lbl.pack(side="right")

        # Canvas для графика сигнала
        self._canvas = tk.Canvas(tab, bg=PANEL, height=140, highlightthickness=0)
        self._canvas.pack(fill="x", padx=16, pady=(0, 8))
        self._signal_history: list[int] = []
        self._signal_timestamps: list[str] = []
        self._canvas.bind("<Configure>", lambda e: self._draw_signal_graph())

        self._mon_log = scrolledtext.ScrolledText(
            tab, bg=PANEL, fg=ACCENT2, font=FONT_MONO,
            borderwidth=0, state="disabled"
        )
        self._mon_log.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    def _toggle_monitor(self):
        if self._monitor_running:
            self._monitor_running = False
            self._btn_mon_start.config(text="▶  Запустить мониторинг", bg=ACCENT)
        else:
            self._monitor_running = True
            self._btn_mon_start.config(text="⏹  Остановить", bg=DANGER)
            self._signal_history.clear()
            self._signal_timestamps.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()

    def _monitor_loop(self):
        while self._monitor_running:
            raw = run_cmd("netsh wlan show interfaces")
            info = parse_connection_info(raw)
            sig_str = ""
            for k, v in info.items():
                if re.search(r"Сигнал|Signal", k):
                    sig_str = v
                    break
            sig  = int(re.search(r"\d+", sig_str).group()) if re.search(r"\d+", sig_str) else 0
            ts   = datetime.now().strftime("%H:%M:%S")
            ssid = info.get("SSID", info.get("Имя", "—"))
            line = f"[{ts}]  SSID: {ssid:<22}  Сигнал: {sig:3}%  {signal_bars(sig)}\n"
            self.after(0, lambda l=line, s=sig, t=ts: self._mon_append(l, s, t))
            time.sleep(self._interval_var.get())

    def _mon_append(self, line: str, sig: int, ts: str):
        self._mon_log.config(state="normal")
        self._mon_log.insert("end", line)
        self._mon_log.see("end")
        self._mon_log.config(state="disabled")

        self._signal_history.append(sig)
        self._signal_timestamps.append(ts)
        if len(self._signal_history) > 60:
            self._signal_history.pop(0)
            self._signal_timestamps.pop(0)
        self._draw_signal_graph()

        # Статистика
        if self._signal_history:
            avg = sum(self._signal_history) / len(self._signal_history)
            mn  = min(self._signal_history)
            mx  = max(self._signal_history)
            self._mon_stats_lbl.config(
                text=f"Avg: {avg:.0f}%  Min: {mn}%  Max: {mx}%",
                fg=signal_color(int(avg))
            )

    def _draw_signal_graph(self):
        c = self._canvas
        c.delete("all")
        w = c.winfo_width() or 900
        h = 140
        pad = 8

        c.create_rectangle(0, 0, w, h, fill=PANEL, outline="")

        for pct in (25, 50, 75, 100):
            y = h - pad - (h - 2*pad) * pct // 100
            c.create_line(pad, y, w - pad, y, fill=BORDER, dash=(4, 4))
            c.create_text(pad + 2, y, text=f"{pct}%", anchor="w",
                          fill=SUBTEXT, font=FONT_MONO)

        hist = self._signal_history
        if len(hist) < 2:
            return

        xs = [pad + 32 + (w - pad - 32) * i // (len(hist) - 1) for i in range(len(hist))]
        ys = [h - pad - (h - 2*pad) * v // 100 for v in hist]

        pts_area = [pad + 32, h - pad] + [x for p in zip(xs, ys) for x in p] + [xs[-1], h - pad]
        c.create_polygon(pts_area, fill="#1f3b5c", outline="")

        pts_line = [x for p in zip(xs, ys) for x in p]
        c.create_line(pts_line, fill=ACCENT, width=2, smooth=True)

        c.create_oval(xs[-1]-4, ys[-1]-4, xs[-1]+4, ys[-1]+4, fill=ACCENT, outline=BG, width=2)
        c.create_text(xs[-1]+6, ys[-1], text=f"{hist[-1]}%", anchor="w",
                      fill=ACCENT, font=FONT_MONO)

    def _clear_monitor(self):
        self._mon_log.config(state="normal")
        self._mon_log.delete("1.0", "end")
        self._mon_log.config(state="disabled")
        self._signal_history.clear()
        self._signal_timestamps.clear()
        self._mon_stats_lbl.config(text="")
        self._draw_signal_graph()

    def _export_monitor_log(self):
        """Сохранить лог мониторинга в текстовый файл."""
        content = self._mon_log.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Экспорт", "Лог пустой. Запустите мониторинг.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
            initialfile=f"wifi_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"WiFi Monitor Log — {get_timestamp()}\n")
                f.write("=" * 60 + "\n")
                f.write(content)
            messagebox.showinfo("Сохранено", f"Лог сохранён:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # ─────────── ВКЛАДКА 4: ПОДКЛЮЧЕНИЕ ───────────

    def _build_connect_tab(self):
        tab = self._tab_connect

        inner = tk.Frame(tab, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(inner, text="Подключиться к Wi-Fi", font=("Consolas", 14, "bold"),
                 bg=BG, fg=ACCENT).grid(row=0, column=0, columnspan=2, pady=(0, 20))

        labels = ["SSID (Имя сети):", "Пароль:", "Тип безопасности:"]
        for i, lbl in enumerate(labels):
            tk.Label(inner, text=lbl, bg=BG, fg=SUBTEXT, font=FONT_SUB, anchor="w"
                     ).grid(row=i+1, column=0, sticky="w", padx=(0, 12), pady=6)

        self._conn_ssid = self._entry(inner)
        self._conn_ssid.grid(row=1, column=1, pady=6, ipady=4)

        # Поле пароля с кнопкой показать/скрыть
        pass_frame = tk.Frame(inner, bg=BG)
        pass_frame.grid(row=2, column=1, pady=6)
        self._conn_pass = self._entry(pass_frame, show="●")
        self._conn_pass.pack(side="left")
        self._show_pass_var = tk.BooleanVar(value=False)
        tk.Checkbutton(pass_frame, text="👁", variable=self._show_pass_var,
                       command=self._toggle_pass_visibility,
                       bg=BG, fg=SUBTEXT, activebackground=BG,
                       selectcolor=BG, font=FONT_SUB).pack(side="left", padx=4)

        self._conn_auth = ttk.Combobox(inner, values=["WPA2PSK", "WPA3SAE", "open"],
                                       width=28, state="readonly", font=FONT_SUB)
        self._conn_auth.set("WPA2PSK")
        self._conn_auth.grid(row=3, column=1, pady=6)

        self._btn(inner, "🔗  Подключиться", self._do_connect
                  ).grid(row=4, column=0, columnspan=2, pady=(20, 8))
        self._btn(inner, "⚡  Отключиться от текущей сети", self._do_disconnect, WARN
                  ).grid(row=5, column=0, columnspan=2, pady=4)
        self._btn(inner, "🔄  Перезапустить Wi-Fi адаптер", self._restart_adapter, DANGER
                  ).grid(row=6, column=0, columnspan=2, pady=4)
        self._btn(inner, "📋  Скопировать текущий IP", self._copy_current_ip, ACCENT2
                  ).grid(row=7, column=0, columnspan=2, pady=4)

        self._conn_result = tk.Label(inner, text="", bg=BG, fg=ACCENT2,
                                     font=FONT_SUB, wraplength=380)
        self._conn_result.grid(row=8, column=0, columnspan=2, pady=(12, 0))

    def _toggle_pass_visibility(self):
        show = "" if self._show_pass_var.get() else "●"
        self._conn_pass.config(show=show)

    def _open_connect_dialog(self, ssid: str, auth: str):
        self._conn_ssid.delete(0, "end")
        self._conn_ssid.insert(0, ssid)
        auth_val = "WPA2PSK" if "WPA2" in auth else ("open" if "Open" in auth else "WPA2PSK")
        self._conn_auth.set(auth_val)
        if self._notebook:
            self._notebook.select(3)

    def _do_connect(self):
        ssid = self._conn_ssid.get().strip()
        pwd  = self._conn_pass.get().strip()
        auth = self._conn_auth.get()

        if not ssid:
            self._conn_result.config(text="⚠ Введите SSID!", fg=WARN)
            return

        if auth == "open":
            key_xml  = ""
            auth_xml = "<authentication>open</authentication><encryption>none</encryption>"
        else:
            key_xml  = f"<keyMaterial>{pwd}</keyMaterial>"
            auth_xml = (f"<authentication>{auth}</authentication>"
                        f"<encryption>AES</encryption>")

        xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{ssid}</name>
  <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>auto</connectionMode>
  <MSM><security>
    <authEncryption>{auth_xml}</authEncryption>
    {"<sharedKey><keyType>passPhrase</keyType><protected>false</protected>" + key_xml + "</sharedKey>" if pwd else ""}
  </security></MSM>
</WLANProfile>"""

        tmp = os.path.join(os.environ.get("TEMP", "."), "_wm_profile.xml")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(xml)

        def task():
            add = run_cmd(f'netsh wlan add profile filename="{tmp}"')
            con = run_cmd(f'netsh wlan connect name="{ssid}"')
            try: os.remove(tmp)
            except: pass
            msg   = (con + add).strip()
            color = ACCENT2 if "успешно" in msg.lower() or "success" in msg.lower() else WARN
            self.after(0, lambda: self._conn_result.config(text=f"✔ {msg[:200]}", fg=color))
            self.after(1500, self._refresh_status)

        self._conn_result.config(text="⏳ Подключение…", fg=SUBTEXT)
        threading.Thread(target=task, daemon=True).start()

    def _do_disconnect(self):
        out = run_cmd("netsh wlan disconnect")
        self._conn_result.config(text=out.strip()[:200], fg=WARN)
        self.after(1000, self._refresh_status)

    def _restart_adapter(self):
        if not messagebox.askyesno("Перезапуск адаптера",
                                   "Перезапустить Wi-Fi адаптер?\n(Нужны права администратора)"):
            return
        def task():
            out1 = run_cmd('netsh interface set interface "Wi-Fi" disabled')
            time.sleep(1.5)
            out2 = run_cmd('netsh interface set interface "Wi-Fi" enabled')
            msg  = (out1 + out2).strip() or "Адаптер перезапущен."
            self.after(0, lambda: self._conn_result.config(text=msg[:200], fg=ACCENT2))
            self.after(2000, self._refresh_status)
        self._conn_result.config(text="⏳ Перезапуск адаптера…", fg=SUBTEXT)
        threading.Thread(target=task, daemon=True).start()

    def _copy_current_ip(self):
        """Скопировать текущий IP-адрес Wi-Fi в буфер обмена."""
        raw  = run_cmd("ipconfig")
        info = parse_ip_info(raw)
        ip   = info.get("IPv4", "")
        if ip:
            self.clipboard_clear()
            self.clipboard_append(ip)
            self._conn_result.config(text=f"✔ IP скопирован: {ip}", fg=ACCENT2)
        else:
            self._conn_result.config(text="IP не найден (нет подключения?)", fg=WARN)

    # ─────────── ВКЛАДКА 5: ДИАГНОСТИКА ───────────

    def _build_tools_tab(self):
        tab = self._tab_tools

        # ── Левая панель: IP-инфо ──
        left = tk.Frame(tab, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(16, 8), pady=14)

        tk.Label(left, text="🌐  Сетевая информация", font=("Consolas", 11, "bold"),
                 bg=BG, fg=ACCENT).pack(anchor="w")

        self._ip_info_box = scrolledtext.ScrolledText(
            left, height=10, bg=PANEL, fg=ACCENT2, font=FONT_MONO,
            borderwidth=0, state="disabled"
        )
        self._ip_info_box.pack(fill="both", expand=True, pady=(8, 0))

        self._btn(left, "🔄  Обновить IP-инфо", self._refresh_ip_info).pack(pady=6)

        # Прочие утилиты
        tk.Label(left, text="⚙️  Быстрые действия", font=("Consolas", 11, "bold"),
                 bg=BG, fg=ACCENT).pack(anchor="w", pady=(10, 4))

        quick_frame = tk.Frame(left, bg=BG)
        quick_frame.pack(fill="x")
        self._btn(quick_frame, "🔄  Сбросить TCP/IP",  self._reset_tcpip, WARN).pack(side="left", padx=(0, 6))
        self._btn(quick_frame, "🔄  Обновить DHCP",    self._renew_dhcp,  ACCENT2).pack(side="left", padx=(0, 6))
        self._btn(quick_frame, "🗑  Очистить DNS-кэш", self._flush_dns,   ACCENT).pack(side="left")

        # ── Правая панель: Ping / Tracert ──
        right = tk.Frame(tab, bg=BG)
        right.pack(side="right", fill="both", expand=True, padx=(8, 16), pady=14)

        tk.Label(right, text="📶  Ping / Трассировка", font=("Consolas", 11, "bold"),
                 bg=BG, fg=ACCENT).pack(anchor="w")

        ping_row = tk.Frame(right, bg=BG)
        ping_row.pack(fill="x", pady=(8, 0))
        tk.Label(ping_row, text="Хост:", bg=BG, fg=SUBTEXT, font=FONT_SUB).pack(side="left")
        self._ping_host = self._entry(ping_row, width=22)
        self._ping_host.insert(0, "8.8.8.8")
        self._ping_host.pack(side="left", padx=6)

        self._btn_ping  = self._btn(ping_row, "📶 Ping",    self._do_ping,    ACCENT)
        self._btn_ping.pack(side="left", padx=(0, 4))
        self._btn_trace = self._btn(ping_row, "🗺 Tracert", self._do_tracert, PURPLE)
        self._btn_trace.pack(side="left")
        self._btn_stop_ping = self._btn(ping_row, "⏹ Стоп", self._stop_ping, DANGER)
        self._btn_stop_ping.pack(side="left", padx=4)

        self._ping_log = scrolledtext.ScrolledText(
            right, bg=PANEL, fg=ACCENT2, font=FONT_MONO,
            borderwidth=0, state="disabled"
        )
        self._ping_log.pack(fill="both", expand=True, pady=(8, 0))
        self._btn(right, "🗑  Очистить", self._clear_ping_log, DANGER).pack(pady=4)

        # Запустить IP-инфо сразу
        self.after(500, self._refresh_ip_info)

    def _refresh_ip_info(self):
        def task():
            raw_iface = run_cmd("netsh wlan show interfaces")
            raw_ip    = run_cmd("ipconfig")
            info_w    = parse_connection_info(raw_iface)
            info_ip   = parse_ip_info(raw_ip)

            ssid = info_w.get("SSID", info_w.get("Имя", "—"))
            bssid = info_w.get("BSSID", "—")
            sig_str = next((v for k, v in info_w.items() if re.search(r"Сигнал|Signal", k)), "—")
            radio   = next((v for k, v in info_w.items() if re.search(r"Тип радио|Radio type", k)), "—")

            lines = [
                f"{'SSID':<18}: {ssid}",
                f"{'BSSID':<18}: {bssid}",
                f"{'Сигнал':<18}: {sig_str}",
                f"{'Радио':<18}: {radio}",
                "─" * 38,
                f"{'IPv4':<18}: {info_ip.get('IPv4', '—')}",
                f"{'Маска':<18}: {info_ip.get('Маска', '—')}",
                f"{'Шлюз':<18}: {info_ip.get('Шлюз', '—')}",
                f"{'DNS':<18}: {info_ip.get('DNS', '—')}",
                "─" * 38,
                f"Обновлено: {datetime.now().strftime('%H:%M:%S')}",
            ]
            text = "\n".join(lines)
            self.after(0, lambda: self._set_text(self._ip_info_box, text))
        threading.Thread(target=task, daemon=True).start()

    def _do_ping(self):
        host = self._ping_host.get().strip() or "8.8.8.8"
        self._ping_running = True
        self._append_ping_log(f"\n─── Ping {host} ───\n")
        def task():
            out = run_cmd(f"ping -n 4 {host}", timeout=20)
            if self._ping_running:
                self.after(0, lambda: self._append_ping_log(out + "\n"))
            self._ping_running = False
        threading.Thread(target=task, daemon=True).start()

    def _do_tracert(self):
        host = self._ping_host.get().strip() or "8.8.8.8"
        self._ping_running = True
        self._append_ping_log(f"\n─── Tracert {host} ───\n")
        def task():
            out = run_cmd(f"tracert -d -h 20 {host}", timeout=60)
            if self._ping_running:
                self.after(0, lambda: self._append_ping_log(out + "\n"))
            self._ping_running = False
        threading.Thread(target=task, daemon=True).start()

    def _stop_ping(self):
        self._ping_running = False
        self._append_ping_log("[Остановлено]\n")

    def _append_ping_log(self, text: str):
        self._ping_log.config(state="normal")
        self._ping_log.insert("end", text)
        self._ping_log.see("end")
        self._ping_log.config(state="disabled")

    def _clear_ping_log(self):
        self._ping_log.config(state="normal")
        self._ping_log.delete("1.0", "end")
        self._ping_log.config(state="disabled")

    def _reset_tcpip(self):
        if not messagebox.askyesno("Сброс TCP/IP",
                                   "Сбросить стек TCP/IP?\nПотребуется перезагрузка."):
            return
        out = run_cmd("netsh int ip reset")
        messagebox.showinfo("TCP/IP Reset", out[:500] or "Выполнено. Перезагрузите ПК.")

    def _renew_dhcp(self):
        def task():
            out = run_cmd("ipconfig /release & ipconfig /renew", timeout=30)
            self.after(0, lambda: messagebox.showinfo("DHCP обновлён", out[:500] or "Готово."))
            self.after(500, self._refresh_ip_info)
        threading.Thread(target=task, daemon=True).start()

    def _flush_dns(self):
        out = run_cmd("ipconfig /flushdns")
        messagebox.showinfo("DNS кэш", out.strip() or "Кэш DNS очищен.")

    # ─────────── ВКЛАДКА 6: О ПРОГРАММЕ ───────────

    def _build_info_tab(self):
        tab = self._tab_info
        inner = tk.Frame(tab, bg=BG)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        lines = [
            ("📡  WiFi Manager Pro", ("Consolas", 22, "bold"), ACCENT),
            ("Версия 2.0  •  Python 3.x  •  Windows", FONT_SUB, SUBTEXT),
            ("", FONT_SUB, BG),
            ("Возможности:", ("Consolas", 11, "bold"), TEXT),
            ("  🔍  Сканирование Wi-Fi сетей с поиском и фильтрацией", FONT_SUB, TEXT),
            ("  📊  Мониторинг сигнала с графиком и статистикой (avg/min/max)", FONT_SUB, TEXT),
            ("  💾  Просмотр, подключение, удаление профилей", FONT_SUB, TEXT),
            ("  🔑  Показ и копирование сохранённых паролей", FONT_SUB, TEXT),
            ("  🔗  Подключение (WPA2, WPA3, Open) + показ/скрытие пароля", FONT_SUB, TEXT),
            ("  📋  Копирование SSID / BSSID / IP через ПКМ и кнопки", FONT_SUB, TEXT),
            ("  🌐  IP-инфо: адрес, маска, шлюз, DNS", FONT_SUB, TEXT),
            ("  📶  Ping и трассировка до любого хоста", FONT_SUB, TEXT),
            ("  🔄  Сброс TCP/IP, обновление DHCP, очистка DNS", FONT_SUB, TEXT),
            ("  💾  Экспорт сетей в CSV, лога мониторинга в TXT", FONT_SUB, TEXT),
            ("  ⚡  Отключение и перезапуск Wi-Fi адаптера", FONT_SUB, TEXT),
            ("", FONT_SUB, BG),
            ("Горячие клавиши:", ("Consolas", 11, "bold"), TEXT),
            ("  F5 — обновить сканирование   Ctrl+Q — выход   F1 — о программе", FONT_MONO, SUBTEXT),
            ("", FONT_SUB, BG),
            ("Зависимости: только стандартная библиотека Python", FONT_MONO, SUBTEXT),
            ("Использует: netsh wlan, ipconfig, ping, tracert (встроены в Windows)", FONT_MONO, SUBTEXT),
        ]

        for text, font, color in lines:
            tk.Label(inner, text=text, font=font, bg=BG, fg=color,
                     anchor="w").pack(anchor="w", pady=1)

    def _show_about_popup(self):
        messagebox.showinfo("О программе",
                            "WiFi Manager Pro v2.0\n"
                            "Python 3.x | Windows\n\n"
                            "F5 — обновить\n"
                            "Ctrl+Q — выход\n"
                            "F1 — это окно")

    # ─────────── СТАТУС СТРОКА ───────────

    def _refresh_status(self):
        def task():
            raw  = run_cmd("netsh wlan show interfaces")
            info = parse_connection_info(raw)
            ssid = info.get("SSID", info.get("Имя", ""))
            sig_str = next((v for k, v in info.items() if re.search(r"Сигнал|Signal", k)), "")

            if ssid:
                sig   = int(re.search(r"\d+", sig_str).group()) if re.search(r"\d+", sig_str) else 0
                msg   = f"Подключено: {ssid}  ({sig}%)"
                color = signal_color(sig)
                dot   = ACCENT2
            else:
                msg   = "Не подключено"
                color = SUBTEXT
                dot   = DANGER

            self.after(0, lambda: (
                self._status_lbl.config(text=msg, fg=color),
                self._status_dot.config(fg=dot)
            ))

        threading.Thread(target=task, daemon=True).start()
        self.after(10_000, self._refresh_status)

    # ─────────── ВСПОМОГАТЕЛЬНЫЕ ───────────

    def _set_text(self, widget: scrolledtext.ScrolledText, text: str):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.config(state="disabled")

    def _btn(self, parent, text: str, cmd=None, color=ACCENT) -> tk.Button:
        b = tk.Button(
            parent, text=text, command=cmd,
            bg=color, fg=BG, activebackground=TEXT, activeforeground=BG,
            font=FONT_SUB, relief="flat", cursor="hand2",
            padx=12, pady=5
        )
        b.bind("<Enter>", lambda e: b.config(bg=TEXT))
        b.bind("<Leave>", lambda e: b.config(bg=color))
        return b

    def _entry(self, parent, show="", width=30) -> tk.Entry:
        e = tk.Entry(parent, bg=PANEL, fg=TEXT, insertbackground=ACCENT,
                     font=FONT_BODY, relief="flat", width=width,
                     highlightthickness=1, highlightcolor=ACCENT,
                     highlightbackground=BORDER, show=show)
        return e


# ══════════════════════════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if sys.platform != "win32":
        print("Эта программа работает только на Windows.")
        sys.exit(1)

    app = WiFiManager()
    app.mainloop()