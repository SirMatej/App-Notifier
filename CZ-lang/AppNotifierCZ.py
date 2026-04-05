import tkinter as tk
import psutil
import pygame

import sys
import os
from pathlib import Path

import pystray
from PIL import Image

import json

NOTIF_W = 320
NOTIF_H = 70
SPEED = 12       # px za frame při slide-in/out
PAUSE = 5000     # ms jak dlouho zůstane notifikace viditelná
GAP = 10         # mezera mezi notifikacemi a od okraje

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

appdata = Path(os.getenv("APPDATA")) / "AppNotifier"
appdata.mkdir(exist_ok=True)

JSON = appdata / "data.json"

class Data:
    def __init__(self):
        pass

    def save(self, data):
        with open(JSON, "w") as f:
            json.dump(data, f)

    def load(self):
        if os.path.exists(JSON):
            with open(JSON, "r") as f:
                return json.load(f)
        return {}

DATA = Data().load()
PICKED_ACCENT = DATA.get("PICKED_ACCENT", "Modrá")
PICKED_BODY = DATA.get("PICKED_BODY", "Modrá") 
PLAY_SOUND = DATA.get("PLAY_SOUND", True)

COLORS_ACCENT = {
    "Modrá": "#89b4fa",
    "Červená": "#f38ba8",
    "Zelená": "#a6e3a1",
    "Fialová": "#cba6f7",
    "Žlutá": "#f9e2af"
}
COLORS_BODY =  {
    "Modrá": "#1e1e2e",
    "Červená": "#2e1e2a",
    "Zelená": "#1e2e23",
    "Fialová": "#271e2e",
    "Žlutá": "#2e2e1e"
}

pygame.mixer.init()

class Notification(tk.Toplevel):
    def __init__(self, parent, app, slot, on_done):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.on_done = on_done
        self.slot = slot  # pořadí notifikace (0 = nejnižší)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.target_x = sw - NOTIF_W - GAP
        self.hidden_x = sw + 10  # mimo obrazovku vpravo
        self.y = sh - NOTIF_H - GAP - slot * (NOTIF_H + GAP)

        self.geometry(f"{NOTIF_W}x{NOTIF_H}+{self.hidden_x}+{self.y}")
        self._build_ui(app)
        self.update_idletasks()
        self._playSound("slideIN.wav")
        self._slide_in(self.hidden_x)

    def _build_ui(self, app):
        self.configure(bg=COLORS_BODY.get(PICKED_BODY, "#1e1e2e"))

        # Levý barevný proužek
        accent = tk.Frame(self, bg=COLORS_ACCENT.get(PICKED_ACCENT, "#89b4fa"), width=4)
        accent.pack(side="left", fill="y")

        body = tk.Frame(self, bg=COLORS_BODY.get(PICKED_BODY, "#1e1e2e"), padx=12, pady=8)
        body.pack(side="left", fill="both", expand=True)

        title = tk.Label(body, text="Nová aplikace spuštěna",
                         bg=COLORS_BODY.get(PICKED_BODY, "#1e1e2e"), fg="#cdd6f4",
                         font=("Segoe UI", 8), anchor="w")
        title.pack(fill="x")

        name = tk.Label(body, text=app,
                        bg=COLORS_BODY.get(PICKED_BODY, "#1e1e2e"), fg=COLORS_ACCENT.get(PICKED_ACCENT, "#89b4fa"),
                        font=("Segoe UI", 11, "bold"), anchor="w")
        name.pack(fill="x")

        # Tlačítko zavřít
        close_btn = tk.Label(self, text="✕", bg=COLORS_BODY.get(PICKED_BODY, "#1e1e2e"), fg="#6c7086",
                             font=("Segoe UI", 9), padx=8, cursor="hand2")
        close_btn.pack(side="right", anchor="n", pady=5)
        close_btn.bind("<Button-1>", lambda e: self._slide_out_activate())

        # Tlačítko ukončení (otevřené aplikace)
        quit_btn = tk.Label(self, text="🚫", bg=COLORS_BODY.get(PICKED_BODY, "#1e1e2e"), fg="#f38ba8", 
                            font=("Segoe UI", 9), padx=8, cursor="hand2")
        quit_btn.pack(side="right", anchor="n", pady=5)
        quit_btn.bind("<Button-1>", lambda e: self._kill_app(app))

        # Tlačítko na vyhledání aplikace online
        search_btn = tk.Label(self, text="🔍", bg=COLORS_BODY.get(PICKED_BODY, "#1e1e2e"), fg="#89b4fa",
                              font=("Segoe UI", 9), padx=8, cursor="hand2")
        search_btn.pack(side="right", anchor="n", pady=5)
        search_btn.bind("<Button-1>", lambda e: self._search_app(app))


    def _slide_in(self, current_x):
        if current_x > self.target_x:
            current_x -= SPEED
            self.geometry(f"+{current_x}+{self.y}")
            self.after(16, self._slide_in, current_x)
        else:
            self.geometry(f"+{self.target_x}+{self.y}")
            self.after(PAUSE, self._slide_out_activate)

    def _slide_out_activate(self):
        self._playSound("slideOUT.wav")
        self._slide_out()

    def _slide_out(self):
        sw = self.winfo_screenwidth()
        current_x = self.winfo_x()
        if current_x < sw:
            current_x += SPEED
            self.geometry(f"+{current_x}+{self.y}")
            self.after(16, self._slide_out)
        else:
            self.destroy()
            self.on_done(self.slot)

    def _kill_app(self, app_name):
        for p in psutil.process_iter(['name']):
            try:
                if p.info.get('name', '').lower() == app_name.lower():
                    p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        self._slide_out_activate()
    
    def _search_app(self, app_name):
        import webbrowser
        query = "what is " + app_name
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        self._slide_out()

    def _playSound(self, sound):
        if not PLAY_SOUND:
            return
        pygame.mixer.music.load(resource_path(sound))
        pygame.mixer.music.play()

class CheckMgr(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.prev = self.get_running_apps()
        self.active_slots = set()  # obsazené sloty
        self.after(1000, self.check)

    def _next_slot(self):
        slot = 0
        while slot in self.active_slots:
            slot += 1
        return slot

    def _on_done(self, slot):
        self.active_slots.discard(slot)

    def check(self):
        aktu = self.get_running_apps()
        nove = aktu - self.prev
        for exe in nove:
            slot = self._next_slot()
            self.active_slots.add(slot)
            Notification(self, exe, slot, self._on_done)
        self.prev = aktu
        self.after(1000, self.check)

    @staticmethod
    def get_running_apps():
        proc_names = set()
        for p in psutil.process_iter(['name']):
            try:
                name = p.info.get('name')
                if name:
                    proc_names.add(name.lower())
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return proc_names

class systemTrayIcon:
    def __init__(self):
        global PLAY_SOUND
        self.menu = pystray.Menu(
            pystray.MenuItem("Zvuk", self.toggle_sound, checked=lambda item: PLAY_SOUND),
            pystray.MenuItem("Nastavit barvu", pystray.Menu(
                pystray.MenuItem("Červená", self.change_theme("Červená")),
                pystray.MenuItem("Žlutá", self.change_theme("Žlutá")),
                pystray.MenuItem("Zelená", self.change_theme("Zelená")),
                pystray.MenuItem("Modrá", self.change_theme("Modrá")),
                pystray.MenuItem("Fialová", self.change_theme("Fialová"))
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Ukončit", self.quit)
        )
        self.icon = pystray.Icon(
            "AppNotifier",
            icon=Image.open(resource_path("icon.ico")),  # načti jako PIL Image
            title="App Notifier",
            menu=self.menu
        )
    
    def quit(self): #ukončit celou aplikaci
        Data().save({
            "PICKED_ACCENT": PICKED_ACCENT,
            "PICKED_BODY": PICKED_BODY,
            "PLAY_SOUND": PLAY_SOUND
        })

        self.icon.stop()
        root.destroy()
    
    def toggle_sound(self):
        global PLAY_SOUND
        PLAY_SOUND = not PLAY_SOUND
        Data().save({  # Přidejte toto pro okamžité uložení
            "PICKED_ACCENT": PICKED_ACCENT,
            "PICKED_BODY": PICKED_BODY,
            "PLAY_SOUND": PLAY_SOUND
        })
        self.icon.update_menu()
    
    def change_theme(self, color):
        def inner():
            global PICKED_ACCENT, PICKED_BODY
            PICKED_ACCENT = color
            PICKED_BODY = color
            Data().save({  # Přidejte toto pro okamžité uložení
                "PICKED_ACCENT": PICKED_ACCENT,
                "PICKED_BODY": PICKED_BODY,
                "PLAY_SOUND": PLAY_SOUND
            })
            self.icon.update_menu()
        return inner

import threading

if __name__ == '__main__':
    trayicon = systemTrayIcon()

    # Pystray ve vedlejším vlákně
    t = threading.Thread(target=trayicon.icon.run, daemon=True)
    t.start()

    # Tkinter v hlavním vlákně
    root = CheckMgr()
    root.mainloop()