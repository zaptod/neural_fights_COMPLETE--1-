"""
NEURAL FIGHTS - God Registry & WorldStateSync
Fonte única de verdade: sincroniza gods.json ↔ world_state.json ↔ personagens.json.
Camada API-ready: suporta Manual e stub para TikTok/YouTube futuro.
"""

import json
import os
import time
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Paleta de Naturezas ───────────────────────────────────────────────────────
# Mapeia element name → (cor primária, cor secundária)
NATURE_COLORS: dict[str, tuple[str, str]] = {
    "balanced":  ("#00d9ff", "#e94560"),
    "fire":      ("#ff6600", "#ff2200"),
    "ice":       ("#87ceeb", "#4af0ff"),
    "darkness":  ("#4b0082", "#1a001a"),
    "nature":    ("#228b22", "#00ff44"),
    "chaos":     ("#9932cc", "#ff00ff"),
    "void":      ("#1a1a2e", "#7700ff"),
    "greed":     ("#b8860b", "#ffd700"),
    "fear":      ("#2d0040", "#7a00aa"),
    "arcane":    ("#6495ed", "#c0c0ff"),
    "blood":     ("#8b0000", "#ff3333"),
    "time":      ("#c0c0c0", "#fffaf0"),
    "gravity":   ("#2c3e50", "#7f8c8d"),
    "ancient":   ("#3d2b1f", "#c9a96e"),
}

NATURE_BORDER_STYLE: dict[str, str] = {
    "balanced": "balance",
    "fire":     "fire",
    "ice":      "ice",
    "darkness": "darkness",
    "nature":   "nature_vines",
    "chaos":    "chaos",
    "void":     "void",
    "greed":    "greed",
    "fear":     "fear_spikes",
    "arcane":   "arcane",
    "blood":    "blood",
    "time":     "arcane",
    "gravity":  "void",
}


@dataclass
class God:
    god_id:               str
    god_name:             str
    nature:               str
    nature_element:       str
    follower_count:       int        = 0
    color_primary:        str        = "#8892b0"
    color_secondary:      str        = "#ffffff"
    champion_character_id: Optional[str] = None
    owned_zones:          list       = field(default_factory=list)
    is_ancient:           bool       = False
    is_player_god:        bool       = False
    is_protagonist:       bool       = False
    registered_at:        str        = ""
    source:               str        = "manual"
    api_source:           Optional[str] = None
    border_style:         str        = "balanced"
    lore_description:     str        = ""

    @property
    def color_primary_rgb(self) -> tuple[int, int, int]:
        return _hex_to_rgb(self.color_primary)

    @property
    def color_secondary_rgb(self) -> tuple[int, int, int]:
        return _hex_to_rgb(self.color_secondary)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# Public alias — imported by map_ui.py and map_renderer.py
hex_to_rgb = _hex_to_rgb


class WorldStateSync:
    """
    Fonte única de verdade para o estado do mundo.

    Responsabilidades:
      - Carregar e salvar gods.json + world_state.json
      - Receber notificações de mudanças (hook do database.py)
      - Calcular estatísticas globais
      - Stub para API futura (TikTok/YouTube comments)
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.gods:      dict[str, God] = {}        # god_id → God
        self.ownership: dict[str, str | None] = {} # zone_id → god_id | None
        self.contested: list[dict]             = []
        self.ancient_seals: dict               = {}
        self.global_stats:  dict               = {}
        self._load_all()

    # ── Carregamento ─────────────────────────────────────────────────────────

    def _load_all(self):
        self._load_gods()
        self._load_world_state()

    def _load_gods(self):
        path = os.path.join(self.data_dir, "gods.json")
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.gods = {}
        for g in data.get("gods", []):
            god = God(
                god_id               = g["god_id"],
                god_name             = g["god_name"],
                nature               = g["nature"],
                nature_element       = g["nature_element"],
                follower_count       = g.get("follower_count", 0),
                color_primary        = g.get("color_primary", "#8892b0"),
                color_secondary      = g.get("color_secondary", "#ffffff"),
                champion_character_id= g.get("champion_character_id"),
                owned_zones          = g.get("owned_zones", []),
                is_ancient           = g.get("is_ancient", False),
                is_player_god        = g.get("is_player_god", False),
                is_protagonist       = g.get("is_protagonist", False),
                registered_at        = g.get("registered_at", ""),
                source               = g.get("source", "manual"),
                api_source           = g.get("api_source"),
                border_style         = g.get("border_style", "balanced"),
                lore_description     = g.get("lore_description", ""),
            )
            self.gods[god.god_id] = god

    def _load_world_state(self):
        path = os.path.join(self.data_dir, "world_state.json")
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.ownership    = data.get("zone_ownership", {})
        self.contested    = data.get("contested_borders", [])
        self.ancient_seals= data.get("ancient_seals", {})
        self.global_stats = data.get("global_stats", {})

    # ── Persistência ──────────────────────────────────────────────────────────

    def save_all(self):
        self._save_gods()
        self._save_world_state()

    def _save_gods(self):
        path = os.path.join(self.data_dir, "gods.json")
        gods_list = []
        for god in self.gods.values():
            gods_list.append({
                "god_id":               god.god_id,
                "god_name":             god.god_name,
                "nature":               god.nature,
                "nature_element":       god.nature_element,
                "follower_count":       god.follower_count,
                "color_primary":        god.color_primary,
                "color_secondary":      god.color_secondary,
                "champion_character_id":god.champion_character_id,
                "owned_zones":          god.owned_zones,
                "is_ancient":           god.is_ancient,
                "is_player_god":        god.is_player_god,
                "is_protagonist":       god.is_protagonist,
                "registered_at":        god.registered_at,
                "source":               god.source,
                "api_source":           god.api_source,
                "border_style":         god.border_style,
                "lore_description":     god.lore_description,
            })
        # Preserva ancient_gods do arquivo original
        try:
            with open(path, "r", encoding="utf-8") as f:
                original = json.load(f)
            ancient = original.get("ancient_gods", [])
        except Exception:
            ancient = []
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"_meta": {"version":"1.0"}, "gods": gods_list, "ancient_gods": ancient},
                      f, indent=2, ensure_ascii=False)

    def _save_world_state(self):
        path = os.path.join(self.data_dir, "world_state.json")
        self._recalc_global_stats()
        data = {
            "_meta": {"last_updated": datetime.now().isoformat()},
            "zone_ownership":  self.ownership,
            "contested_borders": self.contested,
            "ancient_seals":   self.ancient_seals,
            "global_stats":    self.global_stats,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _recalc_global_stats(self):
        claimed = sum(1 for v in self.ownership.values() if v is not None)
        total_followers = sum(g.follower_count for g in self.gods.values())
        self.global_stats = {
            "total_gods":       len(self.gods),
            "total_followers":  total_followers,
            "zones_claimed":    claimed,
            "zones_contested":  len(self.contested),
            "war_intensity":    min(1.0, len(self.contested) / 10),
        }

    # ── Hooks de Mudança (chamados pelo database.py modificado) ───────────────

    def on_character_update(self, char_id: str, god_id: str | None):
        """
        Chamado pelo database.py quando um personagem é salvo com god_id.
        Atualiza o campeão do deus correspondente.
        """
        if god_id and god_id in self.gods:
            self.gods[god_id].champion_character_id = char_id
            self._save_world_state()

    def on_zone_claimed(self, zone_id: str, god_id: str):
        """
        Chamado quando um deus reivindica uma zona.
        Atualiza ownership e lista de zonas do deus.
        """
        prev_god = self.ownership.get(zone_id)
        if prev_god and prev_god in self.gods:
            if zone_id in self.gods[prev_god].owned_zones:
                self.gods[prev_god].owned_zones.remove(zone_id)
        self.ownership[zone_id] = god_id
        if god_id in self.gods and zone_id not in self.gods[god_id].owned_zones:
            self.gods[god_id].owned_zones.append(zone_id)
        self.save_all()

    def on_zone_released(self, zone_id: str):
        """Remove um deus de uma zona."""
        prev_god = self.ownership.get(zone_id)
        if prev_god and prev_god in self.gods:
            if zone_id in self.gods[prev_god].owned_zones:
                self.gods[prev_god].owned_zones.remove(zone_id)
        self.ownership[zone_id] = None
        self.save_all()

    def on_follower_update(self, god_id: str, count: int):
        """
        API stub: atualiza contagem de seguidores.
        Futuramente chamado pela integração TikTok/YouTube.
        """
        if god_id in self.gods:
            self.gods[god_id].follower_count = count
            self.save_all()

    def on_contested_borders_update(self, contested: list[dict]):
        """Atualiza bordas contestadas (chamado pelo TerritoryManager)."""
        self.contested = contested
        self._save_world_state()

    def on_seal_crack(self, seal_zone_id: str, new_crack_level: int):
        """Incrementa o nível de crack de um selo antigo."""
        if seal_zone_id in self.ancient_seals:
            self.ancient_seals[seal_zone_id]["crack_level"] = new_crack_level
            self.save_all()

    # ── God CRUD ──────────────────────────────────────────────────────────────

    def create_god(self, god_name: str, nature: str, nature_element: str,
                   source: str = "manual", api_source: str = None) -> God:
        """Cria um novo deus e salva."""
        god_id = f"god_{god_name.lower().replace(' ', '_')}_{int(time.time()) % 10000}"
        colors = NATURE_COLORS.get(nature_element, ("#8892b0", "#ffffff"))
        border = NATURE_BORDER_STYLE.get(nature_element, "balanced")
        god = God(
            god_id         = god_id,
            god_name       = god_name,
            nature         = nature,
            nature_element = nature_element,
            color_primary  = colors[0],
            color_secondary= colors[1],
            border_style   = border,
            registered_at  = datetime.now().isoformat(),
            source         = source,
            api_source     = api_source,
        )
        self.gods[god_id] = god
        self.save_all()
        return god

    def update_god(self, god_id: str, **kwargs):
        """Atualiza campos de um deus existente."""
        if god_id not in self.gods:
            return
        god = self.gods[god_id]
        for key, value in kwargs.items():
            if hasattr(god, key):
                setattr(god, key, value)
        self.save_all()

    def delete_god(self, god_id: str):
        """Remove um deus e libera suas zonas."""
        if god_id not in self.gods:
            return
        for zone_id, gid in list(self.ownership.items()):
            if gid == god_id:
                self.ownership[zone_id] = None
        del self.gods[god_id]
        self.save_all()

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_god(self, god_id: str) -> God | None:
        return self.gods.get(god_id)

    def get_god_for_zone(self, zone_id: str) -> God | None:
        god_id = self.ownership.get(zone_id)
        return self.gods.get(god_id) if god_id else None

    def get_all_gods(self) -> list[God]:
        return list(self.gods.values())

    def reload(self):
        """Recarrega do disco — para hot-reload durante desenvolvimento."""
        self._load_all()

    # ── API Stub (Futuro) ─────────────────────────────────────────────────────

    def import_gods_from_csv(self, csv_path: str):
        """
        STUB: Importa deuses de um CSV (colado dos comentários do TikTok).
        Formato esperado: nome,nature
        """
        # TODO: Implementar quando a coleta de comentários estiver pronta
        raise NotImplementedError("CSV import: a implementar na Fase 6")

    def sync_from_tiktok_api(self, video_id: str):
        """STUB: Sincroniza seguidores/deuses via TikTok API."""
        raise NotImplementedError("TikTok API: a implementar na Fase 6")

    def sync_from_youtube_api(self, video_id: str):
        """STUB: Sincroniza seguidores/deuses via YouTube API."""
        raise NotImplementedError("YouTube API: a implementar na Fase 6")
