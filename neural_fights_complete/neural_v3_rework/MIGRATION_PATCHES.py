"""
NEURAL FIGHTS — View Migration Patches
=======================================
These are the EXACT lines to change in each view file to wire up
the AppState event bus.  Changes are minimal — the existing logic
stays 100% intact.

After these patches, views auto-refresh when data changes from ANY
source (another view, tournament, simulation, etc.) without needing
to navigate away and back.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 1 — ui/view_armas.py
# ═══════════════════════════════════════════════════════════════════════════════
"""
ADD at top of file (after existing imports):
────────────────────────────────────────────
    from data.app_state import AppState

CHANGE __init__ — after `self.setup_ui()`:
──────────────────────────────────────────
    # OLD (nothing — no subscription existed)

    # NEW: subscribe so this view refreshes when characters change
    # (weapon validation needs the current character list)
    AppState.get().subscribe("characters_changed", self._on_chars_changed)

ADD new method to TelaArmas:
────────────────────────────
    def _on_chars_changed(self, _data=None):
        # Refresh any character-dependent UI (e.g. validation previews)
        if hasattr(self, "atualizar_dados"):
            self.atualizar_dados()

CHANGE the save block (around line 1289-1294):
──────────────────────────────────────────────
    # OLD:
    self.controller.lista_armas[self.indice_em_edicao] = nova
    # ...
    self.controller.lista_armas.append(nova)
    salvar_lista_armas(self.controller.lista_armas)

    # NEW (one call replaces the save + the manual list mutation):
    state = AppState.get()
    if self.indice_em_edicao is not None:
        state.update_weapon(self.indice_em_edicao, nova)
    else:
        state.add_weapon(nova)
    # controller.lista_armas is now a live property — no manual sync needed

CHANGE the delete block (around line 1400-1401):
─────────────────────────────────────────────────
    # OLD:
    del self.controller.lista_armas[idx]
    salvar_lista_armas(self.controller.lista_armas)

    # NEW:
    AppState.get().delete_weapon(idx)
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 2 — ui/view_chars.py
# ═══════════════════════════════════════════════════════════════════════════════
"""
ADD at top of file (after existing imports):
────────────────────────────────────────────
    from data.app_state import AppState

CHANGE __init__ — after `self.setup_ui()`:
──────────────────────────────────────────
    # Subscribe so the character list refreshes when weapons change.
    # This is the KEY missing link: forge a weapon → char screen updates instantly.
    AppState.get().subscribe("weapons_changed", self._on_weapons_changed)

ADD new method to TelaPersonagens:
───────────────────────────────────
    def _on_weapons_changed(self, _data=None):
        # Refresh weapon dropdown in the wizard
        if hasattr(self, "atualizar_dados"):
            self.atualizar_dados()

CHANGE the save block (around line 1546-1552):
───────────────────────────────────────────────
    # OLD:
    self.controller.lista_personagens.append(p)
    # or
    self.controller.lista_personagens[self.indice_em_edicao] = p
    salvar_lista_chars(self.controller.lista_personagens)

    # NEW:
    state = AppState.get()
    if self.indice_em_edicao is None:
        state.add_character(p)
    else:
        state.update_character(self.indice_em_edicao, p)

CHANGE the delete block (around line 1571-1572):
─────────────────────────────────────────────────
    # OLD:
    del self.controller.lista_personagens[idx]
    salvar_lista_chars(self.controller.lista_personagens)

    # NEW:
    AppState.get().delete_character(idx)
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 3 — ui/view_luta.py
# ═══════════════════════════════════════════════════════════════════════════════
"""
ADD at top of file (after existing imports):
────────────────────────────────────────────
    from data.app_state import AppState

CHANGE __init__ — after `self.setup_ui()`:
──────────────────────────────────────────
    # Refresh fighter dropdowns whenever chars or weapons change
    AppState.get().subscribe("characters_changed", self._on_data_changed)
    AppState.get().subscribe("weapons_changed",    self._on_data_changed)

ADD new method to TelaLuta:
────────────────────────────
    def _on_data_changed(self, _data=None):
        if hasattr(self, "atualizar_dados"):
            self.atualizar_dados()

CHANGE match config write (wherever match_config.json is written before launching sim):
────────────────────────────────────────────────────────────────────────────────────────
    # OLD (raw json.dump to match_config.json):
    with open(config_path, "w") as f:
        json.dump(config, f, ...)

    # NEW:
    AppState.get().update_match_config(
        p1_nome=p1.nome,
        p2_nome=p2.nome,
        cenario=self.cenario_var.get(),
        best_of=self.best_of_var.get(),
    )
    # AppState handles the disk write atomically
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 4 — tournament/tournament_mode.py
# ═══════════════════════════════════════════════════════════════════════════════
"""
CHANGE load_participants_from_database (around line 91):
──────────────────────────────────────────────────────────
    # OLD:
    personagens = carregar_personagens()

    # NEW:
    from data.app_state import AppState
    personagens = AppState.get().characters

CHANGE setup_next_match (around line 495, raw json.dump to match_config.json):
────────────────────────────────────────────────────────────────────────────────
    # OLD:
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    # NEW:
    from data.app_state import AppState
    AppState.get().update_match_config(**config)

CHANGE save_state / load_state — replace raw json.dump/load with AppState:
────────────────────────────────────────────────────────────────────────────
    # In save_state():
    # OLD: json.dump(state, f, ...)
    # NEW:
    from data.app_state import AppState
    AppState.get().set_tournament_state(state)

    # In load_state():
    # OLD: state = json.load(f)
    # NEW:
    from data.app_state import AppState
    state = AppState.get().tournament_state  # already loaded from disk

CHANGE fight result recording:
────────────────────────────────
    # After each fight completes, call:
    AppState.get().record_fight_result(
        winner=winner_name,
        loser=loser_name,
        duration=fight_duration,
        ko=was_ko,
    )
    # This updates both tournament_state.json AND session_stats in one call.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PATCH 5 — data/database.py  (simplify WorldMap hook)
# ═══════════════════════════════════════════════════════════════════════════════
"""
The existing WorldMap hook in database.py can be replaced by a clean
AppState subscription.  Add this ONCE at app startup (e.g. in main.py):

    from data.app_state import AppState

    def _worldmap_sync(data):
        \"\"\"Called whenever characters or gods change.\"\"\"
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.insert(0, os.path.join(base, "world_map_module", "world_map"))
            from map_god_registry import WorldStateSync
            sync = WorldStateSync(os.path.join(base, "world_map_module", "data"))
            for p in AppState.get().characters:
                if p.god_id:
                    sync.on_character_update(p.nome, p.god_id)
            sync.reload()
        except Exception as e:
            pass  # WorldMap module not present — silent skip

    AppState.get().subscribe("characters_changed", _worldmap_sync)
    AppState.get().subscribe("gods_changed",       _worldmap_sync)

This replaces the _init_worldmap_hook() call in database.py entirely.
The hook fires reactively on every save instead of only at import time.
"""
