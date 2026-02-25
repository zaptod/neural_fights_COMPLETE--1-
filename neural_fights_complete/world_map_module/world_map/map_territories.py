"""
NEURAL FIGHTS - Territory System
Carrega world_regions.json, detecta cliques em polígonos, busca vizinhos.
"""

import json
import math
import os
from dataclasses import dataclass, field


@dataclass
class Zone:
    """Uma zona claimável no mapa."""
    zone_id:          str
    zone_name:        str
    lore:             str
    vertices:         list        # [[x,y], ...]  em world units
    centroid:         list        # [cx, cy]
    neighboring_zones: list       # [zone_id, ...]
    ancient_seal:     bool
    base_nature:      str
    region_id:        str
    region_name:      str
    # Campos opcionais para selos antigos
    sealed_god:       str  = None
    crack_level:      int  = 0
    max_cracks:       int  = 5
    is_origin:        bool = False


@dataclass
class Region:
    region_id:   str
    region_name: str
    description: str
    base_nature: str
    zones:       list = field(default_factory=list)  # [Zone, ...]


class TerritoryManager:
    """
    Gerencia todas as zonas e regiões do mundo.
    Responsabilidades:
      - Carregar world_regions.json
      - Hit detection (ponto dentro de polígono)
      - Lookup de vizinhos por zone_id
      - Lookup de zonas por god_id (via world_state)
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.regions:   dict[str, Region] = {}   # region_id → Region
        self.zones:     dict[str, Zone]   = {}   # zone_id   → Zone
        self._load()

    # ── Carregamento ─────────────────────────────────────────────────────────

    def _load(self):
        path = os.path.join(self.data_dir, "world_regions.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for rdata in data["regions"]:
            region = Region(
                region_id   = rdata["region_id"],
                region_name = rdata["region_name"],
                description = rdata.get("description", ""),
                base_nature = rdata.get("base_nature", "balanced"),
            )
            for zdata in rdata["zones"]:
                zone = Zone(
                    zone_id           = zdata["zone_id"],
                    zone_name         = zdata["zone_name"],
                    lore              = zdata.get("lore", ""),
                    vertices          = zdata["vertices"],
                    centroid          = zdata["centroid"],
                    neighboring_zones = zdata.get("neighboring_zones", []),
                    ancient_seal      = zdata.get("ancient_seal", False),
                    base_nature       = zdata.get("base_nature", region.base_nature),
                    region_id         = region.region_id,
                    region_name       = region.region_name,
                    sealed_god        = zdata.get("sealed_god"),
                    crack_level       = zdata.get("crack_level", 0),
                    max_cracks        = zdata.get("max_cracks", 5),
                    is_origin         = zdata.get("is_origin", False),
                )
                region.zones.append(zone)
                self.zones[zone.zone_id] = zone

            self.regions[region.region_id] = region

    # ── Hit Detection ─────────────────────────────────────────────────────────

    def get_zone_at_world_pos(self, wx: float, wy: float) -> Zone | None:
        """
        Retorna a zona que contém o ponto (wx, wy) em world units.
        Usa o algoritmo ray-casting para polígonos arbitrários.
        """
        for zone in self.zones.values():
            if self._point_in_polygon(wx, wy, zone.vertices):
                return zone
        return None

    @staticmethod
    def _point_in_polygon(px: float, py: float, vertices: list) -> bool:
        """
        Ray-casting algorithm.
        Retorna True se (px, py) está dentro do polígono definido por vertices.
        """
        n = len(vertices)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = vertices[i]
            xj, yj = vertices[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    # ── Vizinhos ──────────────────────────────────────────────────────────────

    def get_neighbors(self, zone_id: str) -> list[Zone]:
        """Retorna as zonas vizinhas de uma zona."""
        zone = self.zones.get(zone_id)
        if not zone:
            return []
        return [self.zones[nid] for nid in zone.neighboring_zones if nid in self.zones]

    def get_contested_borders(self, ownership: dict) -> list[dict]:
        """
        Encontra todas as bordas contestadas — pares de zonas vizinhas com donos diferentes.
        ownership: {zone_id: god_id | None}
        Retorna lista de {zone_a, zone_b, god_a, god_b, midpoint}
        """
        seen = set()
        contested = []
        for zone_id, god_a in ownership.items():
            if god_a is None:
                continue
            zone = self.zones.get(zone_id)
            if not zone:
                continue
            for neighbor in self.get_neighbors(zone_id):
                god_b = ownership.get(neighbor.zone_id)
                if god_b is None or god_b == god_a:
                    continue
                # Evita duplicatas (A-B e B-A)
                pair = tuple(sorted([zone_id, neighbor.zone_id]))
                if pair in seen:
                    continue
                seen.add(pair)
                midpoint = self._midpoint(zone.centroid, neighbor.centroid)
                contested.append({
                    "zone_a":   zone_id,
                    "zone_b":   neighbor.zone_id,
                    "god_a":    god_a,
                    "god_b":    god_b,
                    "midpoint": midpoint,
                })
        return contested

    @staticmethod
    def _midpoint(a: list, b: list) -> list:
        return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_zones_owned_by(self, god_id: str, ownership: dict) -> list[Zone]:
        """Retorna todas as zonas de um deus específico."""
        return [self.zones[zid] for zid, gid in ownership.items()
                if gid == god_id and zid in self.zones]

    def get_territory_percentage(self, god_id: str, ownership: dict) -> float:
        """Porcentagem do mundo controlada por um deus (ignora selos antigos)."""
        total = sum(1 for z in self.zones.values() if not z.ancient_seal)
        owned = sum(1 for zid, gid in ownership.items()
                    if gid == god_id and zid in self.zones
                    and not self.zones[zid].ancient_seal)
        return (owned / total * 100) if total > 0 else 0.0

    def get_zone(self, zone_id: str) -> Zone | None:
        return self.zones.get(zone_id)

    def get_all_zones(self) -> list[Zone]:
        return list(self.zones.values())

    def get_ancient_seal_zones(self) -> list[Zone]:
        return [z for z in self.zones.values() if z.ancient_seal]

    def get_claimable_zones(self) -> list[Zone]:
        return [z for z in self.zones.values() if not z.ancient_seal]
