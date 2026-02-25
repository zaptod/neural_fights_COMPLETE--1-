# main.py  —  Neural Fights Launcher
# AppState replaces controller.lista_armas / lista_personagens / recarregar_dados()
import tkinter as tk
from tkinter import messagebox
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.app_state import AppState
import os as _os
import sys as _sys

def _setup_worldmap_hook():
    """
    PATCH 5 — WorldMap reactive subscription.
    Fires on every characters_changed / gods_changed event instead of only at import time.
    Replaces the _init_worldmap_hook() call in database.py.
    """
    def _worldmap_sync(data=None):
        try:
            base = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
            wm_path = _os.path.join(base, "world_map_module", "world_map")
            if wm_path not in _sys.path:
                _sys.path.insert(0, wm_path)
            from map_god_registry import WorldStateSync
            sync = WorldStateSync(_os.path.join(base, "world_map_module", "data"))
            for p in AppState.get().characters:
                if p.god_id:
                    sync.on_character_update(p.nome, p.god_id)
            sync.reload()
        except Exception:
            pass  # WorldMap module absent — silent skip

    state = AppState.get()
    state.subscribe("characters_changed", _worldmap_sync)
    state.subscribe("gods_changed",       _worldmap_sync)

_setup_worldmap_hook()

# --- IMPORTING SCREENS (VIEWS) ---
from ui.view_armas import TelaArmas
from ui.view_chars import TelaPersonagens
from ui.view_luta import TelaLuta
from ui.view_sons import TelaSons

COR_FUNDO = "#2C3E50"
COR_TEXTO = "#ECF0F1"


class SistemaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Neural Fights - Launcher & Gerenciador")
        self.geometry("1050x780")
        self.minsize(820, 600)          # prevents buttons from going off-screen
        self.resizable(True, True)
        self.configure(bg=COR_FUNDO)

        # ── Single source of truth ────────────────────────────────────────────
        self._state = AppState.get()

        # ── Backward-compat properties (views still use controller.lista_*) ──
        # These are live properties that always reflect the current AppState.
        # No more stale copies.

        container = tk.Frame(self, bg=COR_FUNDO)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (MenuPrincipal, TelaArmas, TelaPersonagens, TelaLuta, TelaInteracoes, TelaSons):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MenuPrincipal")
        self.tournament_window = None

    # ── Properties that mirror AppState (backward compat for old views) ───────

    @property
    def lista_armas(self):
        return self._state.weapons

    @lista_armas.setter
    def lista_armas(self, value):
        self._state.set_weapons(value)

    @property
    def lista_personagens(self):
        return self._state.characters

    @lista_personagens.setter
    def lista_personagens(self, value):
        self._state.set_characters(value)

    # ── Legacy method kept — but now it's nearly free (no disk I/O) ──────────
    def recarregar_dados(self):
        """
        Kept for backward compatibility.
        AppState is already the live store; this is now a no-op
        unless you explicitly need a full reload from disk.
        """
        pass  # AppState was already loaded at startup and is kept in sync

    def forcar_reload_disco(self):
        """Force a full re-read from disk (use only if external process wrote files)."""
        self._state.reload_all()

    def show_frame(self, page_name):
        """Navigate to a screen. No disk I/O — AppState is always current."""
        frame = self.frames[page_name]
        frame.tkraise()
        if hasattr(frame, "atualizar_dados"):
            frame.atualizar_dados()


class MenuPrincipal(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.configure(bg=COR_FUNDO)

        tk.Label(self, text="NEURAL FIGHTS", font=("Impact", 40),
                 bg=COR_FUNDO, fg="#E74C3C").pack(pady=(60, 10))
        tk.Label(self, text="Sistema de Gerenciamento e Simulação", font=("Helvetica", 14),
                 bg=COR_FUNDO, fg="#BDC3C7").pack(pady=(0, 50))

        btn_style = {
            "font": ("Helvetica", 14, "bold"),
            "width": 30, "pady": 10,
            "bg": "#34495E", "fg": "white",
            "activebackground": "#2980B9",
            "activeforeground": "white",
            "relief": "flat",
        }

        tk.Button(self, text="⚔️  FORJAR ARMAS",
                  command=lambda: controller.show_frame("TelaArmas"), **btn_style).pack(pady=10)
        tk.Button(self, text="👤  CRIAR PERSONAGENS",
                  command=lambda: controller.show_frame("TelaPersonagens"), **btn_style).pack(pady=10)
        tk.Button(self, text="🎮  SIMULAÇÃO (LUTA)",
                  command=lambda: controller.show_frame("TelaLuta"), **btn_style).pack(pady=10)
        tk.Button(self, text="🏆  MODO TORNEIO",
                  command=lambda: self.abrir_torneio(controller), **btn_style).pack(pady=10)
        tk.Button(self, text="🔊  CONFIGURAR SONS",
                  command=lambda: controller.show_frame("TelaSons"), **btn_style).pack(pady=10)
        tk.Button(self, text="💬  INTERAÇÕES SOCIAIS",
                  command=lambda: controller.show_frame("TelaInteracoes"), **btn_style).pack(pady=10)
        tk.Button(self, text="🗺  WORLD MAP — GOD WAR",
                  command=lambda: self.abrir_worldmap(), **btn_style).pack(pady=10)
        tk.Button(self, text="SAIR", command=controller.quit,
                  font=("Helvetica", 12, "bold"), bg="#C0392B", fg="white",
                  width=15).pack(side="bottom", pady=40)

    def abrir_worldmap(self):
        import subprocess, sys, os
        worldmap_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "world_map_module", "run_worldmap.py",
        )
        if os.path.exists(worldmap_script):
            subprocess.Popen([sys.executable, worldmap_script])
        else:
            messagebox.showwarning(
                "World Map",
                f"Módulo não encontrado em:\n{worldmap_script}\n\n"
                "Certifique que a pasta 'world_map_module/' está ao lado deste projeto.",
            )

    def abrir_torneio(self, controller):
        try:
            import customtkinter as ctk
            from ui.view_torneio import TournamentWindow

            if controller.tournament_window is not None:
                try:
                    controller.tournament_window.lift()
                    controller.tournament_window.focus_force()
                    return
                except Exception:
                    pass

            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            controller.tournament_window = TournamentWindow()

        except ImportError as e:
            messagebox.showerror("Erro",
                f"CustomTkinter não instalado!\n\nExecute: pip install customtkinter\n\nErro: {e}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir torneio: {e}")


class TelaInteracoes(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.configure(bg=COR_FUNDO)
        tk.Label(self, text="Interações Sociais & Feedback",
                 font=("Helvetica", 24, "bold"), bg=COR_FUNDO, fg="white").pack(pady=50)
        tk.Label(self, text="Módulo em desenvolvimento...\nAqui você verá likes, comentários e evolução da IA.",
                 font=("Helvetica", 12), bg=COR_FUNDO, fg="#BDC3C7").pack(pady=20)
        tk.Button(self, text="Voltar ao Menu", font=("Arial", 12), bg="#E67E22", fg="white",
                  command=lambda: controller.show_frame("MenuPrincipal")).pack(pady=50)


def main():
    app = SistemaApp()
    app.mainloop()


if __name__ == "__main__":
    main()
