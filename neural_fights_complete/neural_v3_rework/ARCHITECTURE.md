# NEURAL FIGHTS — Data Architecture

## The Problem (Before)

```
TelaArmas ──save──► controller.lista_armas ──► salvar_lista_armas() ──► armas.json
                          ↑
              recarregar_dados() (only on screen switch)
                          ↓
TelaPersonagens ◄── controller.lista_personagens ◄── carregar_personagens()

TelaLuta        reads controller.lista_personagens (possibly stale)
TournamentMode  calls carregar_personagens() directly (bypasses controller)
WorldMap hook   fires at import time only
match_config    written as raw JSON by 3 different places
```

**Root causes:**
- Data lived in 3 places: disk, controller lists, and local view copies — any could be stale
- No notification system — saves were silent
- `recarregar_dados()` hit disk on every navigation even when nothing changed
- Tournament, simulation, and UI all wrote `match_config.json` independently


## The Solution (After)

```
                    ┌──────────────────────────────────┐
                    │           AppState               │
                    │         (singleton)              │
                    │                                  │
                    │  .weapons      → armas.json      │
                    │  .characters   → personagens.json│
                    │  .match_config → match_config.json│
                    │  .tournament   → tournament_state.json│
                    │  .gods         → gods.json        │
                    └──────────┬───────────────────────┘
                               │  pub/sub event bus
              ┌────────────────┼────────────────────────┐
              ▼                ▼                         ▼
        TelaArmas       TelaPersonagens            TelaLuta
     subscribes to     subscribes to            subscribes to
   "weapons_changed"  "weapons_changed"        "characters_changed"
                      "characters_changed"     "weapons_changed"
                                                         │
                                                         ▼
                                                TournamentMode
                                             subscribes to
                                           "tournament_changed"

WorldMap: subscribes to "characters_changed" + "gods_changed"
```


## File Map

```
data/
├── app_state.py          ← NEW: central store + event bus
├── __init__.py           ← UPDATED: exports AppState + legacy shims
├── database.py           ← UNCHANGED: kept for legacy compat
├── personagens.json      ← unchanged format
├── armas.json            ← unchanged format
├── match_config.json     ← unchanged format
├── tournament_state.json ← unchanged format
└── gods.json             ← NEW: Neural Fights world state (Gods, territories)

ui/
├── main.py               ← UPDATED: controller.lista_* are now live properties
├── view_armas.py         ← patch: subscribe + use state.update_weapon()
├── view_chars.py         ← patch: subscribe + use state.update_character()
├── view_luta.py          ← patch: subscribe + use state.update_match_config()
└── view_torneio.py       ← patch: subscribe to tournament_changed
```


## Quick Reference

```python
from data.app_state import AppState
state = AppState.get()

# Read
state.weapons                        # list[Arma]
state.characters                     # list[Personagem]
state.match_config                   # dict (copy)
state.tournament_state               # dict (copy)

# Lookup
state.get_character("Caleb")         # Personagem | None
state.get_weapon("Espada Sombria")   # Arma | None
state.get_characters_by_god("god_balance")  # list[Personagem]
state.character_names()              # list[str]
state.weapon_names()                 # list[str]

# Mutate (auto-saves + notifies)
state.add_weapon(arma)
state.update_weapon(idx, arma)
state.delete_weapon(idx)

state.add_character(personagem)
state.update_character(idx, personagem)
state.delete_character(idx)

state.update_match_config(p1_nome="Caleb", p2_nome="Bjorn", cenario="Arena")

state.record_fight_result("Caleb", "Bjorn", duration=42.3, ko=True)

# Neural Fights / Lore
state.register_god("god_balance", "The Goddess of Balance", "Balance",
                   color=(180, 160, 255))
state.claim_territory("zone_01", "The Broken City", "god_balance",
                       visual_theme={"color": "#9B7FCC", "texture": "cracked_scales"})
state.set_character_god("Caleb", "god_balance")

# Subscribe
def on_weapons_update(weapons):
    print(f"Weapons updated: {len(weapons)} total")

state.subscribe("weapons_changed", on_weapons_update)
state.unsubscribe("weapons_changed", on_weapons_update)

# Available events:
#   "weapons_changed"       data = list[Arma]
#   "characters_changed"    data = list[Personagem]
#   "match_config_changed"  data = dict
#   "tournament_changed"    data = dict
#   "gods_changed"          data = dict
#   "territory_changed"     data = {"territory_id": ..., "god_id": ...}
#   "session_stats_changed" data = dict
#   "any"                   callback(event_name, data)
```


## Disk Safety

All writes use an **atomic rename** pattern:
```python
write to  file.json.tmp
os.replace(file.json.tmp, file.json)   # atomic — no corrupt files
```
If the process crashes mid-write, the old file is untouched.


## Migration Priority

| File | Effort | Impact |
|------|--------|--------|
| `data/__init__.py` | Done | Unblocks everything |
| `data/app_state.py` | Done | Core store |
| `ui/main.py` | Done | controller.lista_* are now live |
| `ui/view_luta.py` | ~10 lines | match_config IPC fixed |
| `tournament/tournament_mode.py` | ~20 lines | tournament state centralized |
| `ui/view_armas.py` | ~15 lines | auto-refresh in chars screen |
| `ui/view_chars.py` | ~15 lines | auto-refresh weapon dropdown |
| WorldMap hook | ~10 lines | reactive instead of import-time |

See `MIGRATION_PATCHES.py` for exact line-by-line changes.
