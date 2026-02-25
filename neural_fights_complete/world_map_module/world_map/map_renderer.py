"""
NEURAL FIGHTS - World Map Renderer
Coordena todas as camadas visuais:
  1. Background
  2. Território (fill + borda por Natureza)
  3. Selos antigos com rachaduras
  4. Flares de batalha
  5. Labels de zona
  6. Painel esquerdo (God info)
  7. HUD global (stats, zoom, controles)
"""

import math
import pygame
from map_camera import MapCamera
from map_territories import TerritoryManager, Zone
from map_god_registry import WorldStateSync, God
from map_vfx import (
    NatureBorderRenderer, TerritoryFillRenderer,
    BattleFlareRenderer, SealCrackRenderer,
    ParticleSystem, hex_to_rgb, lerp_color, pulse
)


# ── Cores do Tema (do theme.py original) ─────────────────────────────────────
BG_COLOR        = (26,  26,  46)    # #1a1a2e
BG_SECONDARY    = (22,  33,  62)    # #16213e
ACCENT          = (233, 69,  96)    # #e94560
ACCENT_CYAN     = (0,   217, 255)   # #00d9ff
TEXT_COLOR      = (255, 255, 255)
TEXT_DIM        = (136, 146, 176)   # #8892b0
PANEL_BG        = (15,  52,  96)    # #0f3460
WARNING         = (243, 156, 18)    # #f39c12
UNCLAIMED_COLOR = (40,  44,  60)    # Cinza azulado
UNCLAIMED_BORDER= (60,  66,  86)
ANCIENT_BG      = (30,  20,  15)


class MapRenderer:
    """
    Motor de renderização do World Map.
    Instanciado pelo run_worldmap.py e chamado a cada frame.
    """

    PANEL_W = 360   # Largura do painel lateral
    MAP_X   = 360   # Início da área do mapa

    def __init__(self, screen: pygame.Surface,
                 camera: MapCamera,
                 territories: TerritoryManager,
                 world_state: WorldStateSync):
        self.screen      = screen
        self.camera      = camera
        self.territories = territories
        self.world_state = world_state

        self.screen_w = screen.get_width()
        self.screen_h = screen.get_height()

        # Superfície separada para o mapa (sem o painel)
        self.map_surface = pygame.Surface(
            (self.screen_w - self.PANEL_W, self.screen_h), pygame.SRCALPHA)

        self.particles    = ParticleSystem()
        self.battle_flare = BattleFlareRenderer()

        self._init_fonts()
        self._selected_zone: Zone | None = None
        self._time: float = 0.0

    def _init_fonts(self):
        self.font_tiny   = pygame.font.SysFont("consolas", 9)
        self.font_small  = pygame.font.SysFont("consolas", 11)
        self.font_medium = pygame.font.SysFont("consolas", 14, bold=True)
        self.font_large  = pygame.font.SysFont("consolas", 18, bold=True)
        self.font_title  = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_huge   = pygame.font.SysFont("consolas", 28, bold=True)

    # ── Loop Principal ────────────────────────────────────────────────────────

    def update(self, dt: float):
        self._time += dt
        self.camera.update()
        self.particles.update(dt)

    def draw(self):
        # 1. Background geral
        self.screen.fill(BG_COLOR)

        # 2. Renderiza o mapa na sua superfície
        self.map_surface.fill(BG_COLOR)
        self._draw_map_background()
        self._draw_territories()
        self._draw_ancient_seals()
        self._draw_battle_flares()
        self._draw_zone_labels()
        self.particles.draw(self.map_surface)
        self._draw_map_overlay()

        # 3. Blita o mapa na tela principal
        self.screen.blit(self.map_surface, (self.PANEL_W, 0))

        # 4. Painel lateral
        self._draw_panel()

        # 5. HUD global (barra superior)
        self._draw_top_hud()

    # ── Background do Mapa ────────────────────────────────────────────────────

    def _draw_map_background(self):
        """Grade sutil para dar sensação de profundidade."""
        s = self.map_surface
        grid_color = (30, 34, 54)
        grid_world = 100  # A cada 100 world units, uma linha

        # Linhas verticais
        wx = 0
        while wx <= 2000:
            sx, _ = self.camera.world_to_screen(wx, 0)
            sx -= self.PANEL_W  # Ajusta para coordenada da map_surface
            if -2 < sx < s.get_width() + 2:
                pygame.draw.line(s, grid_color, (sx, 0), (sx, s.get_height()), 1)
            wx += grid_world

        # Linhas horizontais
        wy = 0
        while wy <= 1400:
            _, sy = self.camera.world_to_screen(0, wy)
            if -2 < sy < s.get_height() + 2:
                pygame.draw.line(s, grid_color, (0, sy), (s.get_width(), sy), 1)
            wy += grid_world

    # ── Territórios ───────────────────────────────────────────────────────────

    def _draw_territories(self):
        ownership = self.world_state.ownership

        for zone in self.territories.get_all_zones():
            if zone.ancient_seal:
                continue
            if not self.camera.is_polygon_visible(zone.vertices, 100):
                continue

            verts = self._zone_verts_to_map_surface(zone.vertices)
            if not verts:
                continue

            god_id = ownership.get(zone.zone_id)
            god = self.world_state.get_god(god_id) if god_id else None

            if god:
                cp = hex_to_rgb(god.color_primary)
                cs = hex_to_rgb(god.color_secondary)
                nature = god.nature_element
                alpha = 110 if zone != self._selected_zone else 150
                # Fill
                TerritoryFillRenderer.draw(
                    self.map_surface, verts, nature, cp, cs, self._time, alpha)
                # Border
                NatureBorderRenderer.draw(
                    self.map_surface, verts, nature, cp, cs,
                    self._time, self.camera.zoom)
            else:
                # Território não reivindicado
                self._draw_unclaimed(verts, zone)

            # Highlight de seleção
            if zone == self._selected_zone:
                self._draw_selection_highlight(verts)

    def _draw_unclaimed(self, verts, zone: Zone):
        """Território sem dono — cinza com sutíl variação baseada na natureza base."""
        s = pygame.Surface(self.map_surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(s, (*UNCLAIMED_COLOR, 80), verts)
        self.map_surface.blit(s, (0, 0))
        pygame.draw.polygon(self.map_surface, UNCLAIMED_BORDER, verts, 1)

    def _draw_selection_highlight(self, verts):
        """Borda pulsante no território selecionado."""
        glow = int(200 + pulse(self._time, 3) * 55)
        pygame.draw.polygon(self.map_surface, (glow, glow, 100), verts, 3)

    # ── Selos Antigos ─────────────────────────────────────────────────────────

    def _draw_ancient_seals(self):
        for zone in self.territories.get_ancient_seal_zones():
            if not self.camera.is_polygon_visible(zone.vertices, 100):
                continue

            verts = self._zone_verts_to_map_surface(zone.vertices)
            if not verts:
                continue

            seal_data = self.world_state.ancient_seals.get(zone.zone_id, {})
            crack_level = seal_data.get("crack_level", zone.crack_level)
            status      = seal_data.get("status", "sleeping")

            # Fundo escuro do selo
            s = pygame.Surface(self.map_surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(s, (*ANCIENT_BG, 200), verts)
            self.map_surface.blit(s, (0, 0))

            # Borda dourada antiga
            NatureBorderRenderer.draw(
                self.map_surface, verts, "ancient",
                (180, 140, 60), (220, 200, 120), self._time, self.camera.zoom)

            # Rachaduras
            SealCrackRenderer.draw(
                self.map_surface, verts, zone.zone_id,
                crack_level, zone.max_cracks, self._time, self.camera.zoom)

            # Ícone de status
            self._draw_seal_status_icon(verts, zone, status, crack_level)

    def _draw_seal_status_icon(self, verts, zone: Zone, status: str, crack_level: int):
        cx = int(sum(x for x, y in verts) / len(verts))
        cy = int(sum(y for x, y in verts) / len(verts))
        icons = {"sleeping": "😴", "stirring": "👁", "awakened": "⚡"}
        icon = icons.get(status, "?")
        font_size = max(10, int(16 * self.camera.zoom))
        try:
            font = pygame.font.SysFont("segoeuiemoji", font_size)
        except Exception:
            font = self.font_medium
        label = font.render(icon, True, (220, 200, 120))
        self.map_surface.blit(label, label.get_rect(center=(cx, cy)))

    # ── Flares de Batalha ─────────────────────────────────────────────────────

    def _draw_battle_flares(self):
        if not self.world_state.contested:
            return
        for contest in self.world_state.contested:
            god_a = self.world_state.get_god(contest.get("god_a"))
            god_b = self.world_state.get_god(contest.get("god_b"))
            midpoint = contest.get("midpoint", [1000, 700])
            if not god_a or not god_b:
                continue
            sx, sy = self.camera.world_to_screen(midpoint[0], midpoint[1])
            sx -= self.PANEL_W
            if 0 < sx < self.map_surface.get_width() and 0 < sy < self.map_surface.get_height():
                ca = hex_to_rgb(god_a.color_primary)
                cb = hex_to_rgb(god_b.color_primary)
                self.battle_flare.draw(
                    self.map_surface, (sx, sy), ca, cb,
                    self._time, self.camera.zoom, self.particles)

    # ── Labels das Zonas ──────────────────────────────────────────────────────

    def _draw_zone_labels(self):
        if self.camera.zoom < 0.5:
            return  # Muito pequeno para ler

        for zone in self.territories.get_all_zones():
            cx, cy = zone.centroid
            sx, sy = self.camera.world_to_screen(cx, cy)
            sx -= self.PANEL_W

            if not (0 < sx < self.map_surface.get_width() and
                    0 < sy < self.map_surface.get_height()):
                continue

            # Nome da zona
            if self.camera.zoom >= 0.6:
                font_size = max(8, int(10 * self.camera.zoom))
                font = pygame.font.SysFont("consolas", font_size)
                god = self.world_state.get_god_for_zone(zone.zone_id)
                color = TEXT_COLOR if god else TEXT_DIM

                name_surf = font.render(zone.zone_name, True, color)
                shadow    = font.render(zone.zone_name, True, (0, 0, 0))
                nr = name_surf.get_rect(center=(sx, sy))
                self.map_surface.blit(shadow, nr.move(1, 1))
                self.map_surface.blit(name_surf, nr)

            # Nome do deus dono (zoom mais alto)
            if self.camera.zoom >= 1.0:
                god = self.world_state.get_god_for_zone(zone.zone_id)
                if god:
                    font_size2 = max(7, int(9 * self.camera.zoom))
                    font2 = pygame.font.SysFont("consolas", font_size2)
                    gcp = hex_to_rgb(god.color_primary)
                    gsurf = font2.render(f"{god.god_name}", True, gcp)
                    gr = gsurf.get_rect(center=(sx, sy + int(12 * self.camera.zoom)))
                    self.map_surface.blit(gsurf, gr)

    # ── Overlay do Mapa ───────────────────────────────────────────────────────

    def _draw_map_overlay(self):
        """Borda decorativa ao redor da área do mapa."""
        pygame.draw.rect(self.map_surface, PANEL_BG,
                         (0, 0, self.map_surface.get_width(), self.map_surface.get_height()), 2)

        # Mini-texto de zoom e controles no canto inferior direito
        zoom_text = f"ZOOM: {self.camera.zoom:.2f}x"
        zt = self.font_tiny.render(zoom_text, True, TEXT_DIM)
        self.map_surface.blit(zt, (self.map_surface.get_width() - zt.get_width() - 8,
                                   self.map_surface.get_height() - 20))
        hint = "🖱 Scroll=Zoom  Drag=Pan  DblClick=Fly"
        ht = self.font_tiny.render(hint, True, TEXT_DIM)
        self.map_surface.blit(ht, (8, self.map_surface.get_height() - 20))

    # ── Painel Lateral ────────────────────────────────────────────────────────

    def _draw_panel(self):
        panel = pygame.Rect(0, 0, self.PANEL_W, self.screen_h)
        pygame.draw.rect(self.screen, BG_SECONDARY, panel)
        pygame.draw.line(self.screen, PANEL_BG,
                         (self.PANEL_W, 0), (self.PANEL_W, self.screen_h), 2)

        y = 12
        y = self._draw_panel_header(y)
        y = self._draw_selected_zone_info(y)
        y = self._draw_gods_list(y)
        self._draw_panel_controls(y)

    def _draw_panel_header(self, y: int) -> int:
        title = self.font_title.render("⚔ AETHERMOOR", True, ACCENT_CYAN)
        self.screen.blit(title, title.get_rect(centerx=self.PANEL_W // 2, top=y))
        y += title.get_height() + 4

        subtitle = self.font_small.render("World Map — God War", True, TEXT_DIM)
        self.screen.blit(subtitle, subtitle.get_rect(centerx=self.PANEL_W // 2, top=y))
        y += subtitle.get_height() + 12

        # Linha divisória
        pygame.draw.line(self.screen, PANEL_BG, (8, y), (self.PANEL_W - 8, y), 1)
        return y + 10

    def _draw_selected_zone_info(self, y: int) -> int:
        z = self._selected_zone
        if z is None:
            label = self.font_small.render("Click a zone to inspect.", True, TEXT_DIM)
            self.screen.blit(label, (12, y))
            return y + label.get_height() + 8

        # Nome da zona
        zone_name = self.font_large.render(z.zone_name, True, TEXT_COLOR)
        self.screen.blit(zone_name, (12, y))
        y += zone_name.get_height() + 2

        region_label = self.font_small.render(z.region_name, True, TEXT_DIM)
        self.screen.blit(region_label, (12, y))
        y += region_label.get_height() + 8

        # Lore
        for line in self._wrap(z.lore, self.font_small, self.PANEL_W - 24):
            surf = self.font_small.render(line, True, TEXT_DIM)
            self.screen.blit(surf, (12, y))
            y += surf.get_height() + 1
        y += 8

        # Info do deus dono
        god = self.world_state.get_god_for_zone(z.zone_id)
        if god:
            y = self._draw_god_card(y, god, z)
        else:
            if z.ancient_seal:
                seal_data = self.world_state.ancient_seals.get(z.zone_id, {})
                status = seal_data.get("status", "sleeping")
                crack  = seal_data.get("crack_level", 0)
                s1 = self.font_medium.render(f"ANCIENT SEAL", True, WARNING)
                s2 = self.font_small.render(f"Status: {status.upper()}", True, WARNING)
                s3 = self.font_small.render(f"Cracks: {crack}/{z.max_cracks}", True, TEXT_DIM)
                self.screen.blit(s1, (12, y)); y += s1.get_height() + 3
                self.screen.blit(s2, (12, y)); y += s2.get_height() + 3
                self.screen.blit(s3, (12, y)); y += s3.get_height() + 8
            else:
                unc = self.font_medium.render("UNCLAIMED", True, TEXT_DIM)
                self.screen.blit(unc, (12, y))
                y += unc.get_height() + 8

        pygame.draw.line(self.screen, PANEL_BG, (8, y), (self.PANEL_W - 8, y), 1)
        return y + 10

    def _draw_god_card(self, y: int, god: God, zone: Zone) -> int:
        cp = hex_to_rgb(god.color_primary)

        name = self.font_large.render(god.god_name, True, cp)
        self.screen.blit(name, (12, y))
        y += name.get_height() + 2

        nature = self.font_small.render(f"Nature: {god.nature}", True, cp)
        self.screen.blit(nature, (12, y))
        y += nature.get_height() + 4

        # Stats
        territory_pct = self.territories.get_territory_percentage(
            god.god_id, self.world_state.ownership)
        n_zones = len(god.owned_zones)

        stats = [
            ("Followers",  f"{god.follower_count:,}"),
            ("Territory",  f"{territory_pct:.1f}%  ({n_zones} zones)"),
            ("Champion",   god.champion_character_id or "—"),
            ("Source",     god.source),
        ]
        for label_text, value_text in stats:
            label_surf = self.font_small.render(f"{label_text}:", True, TEXT_DIM)
            value_surf = self.font_small.render(value_text, True, TEXT_COLOR)
            self.screen.blit(label_surf, (12, y))
            self.screen.blit(value_surf, (100, y))
            y += label_surf.get_height() + 2

        return y + 8

    def _draw_gods_list(self, y: int) -> int:
        header = self.font_medium.render("ACTIVE GODS", True, ACCENT)
        self.screen.blit(header, (12, y))
        y += header.get_height() + 6

        gods = sorted(self.world_state.get_all_gods(),
                      key=lambda g: -g.follower_count)

        for god in gods[:8]:  # Máximo 8 no painel
            if y > self.screen_h - 120:
                break
            cp = hex_to_rgb(god.color_primary)
            # Barra de cor lateral
            pygame.draw.rect(self.screen, cp, (8, y, 4, 24))

            n_zones = len(god.owned_zones)
            pct = self.territories.get_territory_percentage(
                god.god_id, self.world_state.ownership)

            name_surf = self.font_small.render(
                f"{god.god_name}  [{god.nature}]", True, cp)
            stat_surf = self.font_tiny.render(
                f"  {god.follower_count:,} followers · {pct:.0f}%", True, TEXT_DIM)
            self.screen.blit(name_surf, (18, y))
            y += name_surf.get_height()
            self.screen.blit(stat_surf, (18, y))
            y += stat_surf.get_height() + 6

        return y + 4

    def _draw_panel_controls(self, y: int):
        """Botões de controle (renderizados como texto clicável — a ser conectado ao UI)."""
        bottom = self.screen_h - 8
        controls = [
            ("[HOME]  Fly to world view",  ACCENT_CYAN),
            ("[G] Add new God",             TEXT_DIM),
            ("[R] Reload data",             TEXT_DIM),
        ]
        for text, color in reversed(controls):
            surf = self.font_small.render(text, True, color)
            self.screen.blit(surf, (12, bottom - surf.get_height()))
            bottom -= surf.get_height() + 4

        pygame.draw.line(self.screen, PANEL_BG,
                         (8, bottom), (self.PANEL_W - 8, bottom), 1)

    # ── Top HUD ───────────────────────────────────────────────────────────────

    def _draw_top_hud(self):
        hud_h = 36
        pygame.draw.rect(self.screen, PANEL_BG,
                         (self.PANEL_W, 0, self.screen_w - self.PANEL_W, hud_h))
        pygame.draw.line(self.screen, BG_COLOR,
                         (self.PANEL_W, hud_h), (self.screen_w, hud_h), 1)

        stats = self.world_state.global_stats
        gods    = stats.get("total_gods", 0)
        claimed = stats.get("zones_claimed", 0)
        total   = 24  # Zonas claimáveis (27 - 3 selos)
        contested = stats.get("zones_contested", 0)
        followers = stats.get("total_followers", 0)

        hud_text = (f"  ⚔ NEURAL FIGHTS — GOD WAR   |   "
                    f"Gods: {gods}   Followers: {followers:,}   "
                    f"Zones: {claimed}/{total}   Contested: {contested}")
        t = self.font_medium.render(hud_text, True, TEXT_COLOR)
        self.screen.blit(t, (self.PANEL_W + 8, (hud_h - t.get_height()) // 2))

    # ── Interação ────────────────────────────────────────────────────────────

    def select_zone_at_map_pos(self, map_sx: int, map_sy: int):
        """
        map_sx, map_sy: coordenadas relativas à map_surface.
        Converte para world e detecta zona.
        """
        wx, wy = self.camera.screen_to_world(map_sx + self.PANEL_W, map_sy)
        zone = self.territories.get_zone_at_world_pos(wx, wy)
        self._selected_zone = zone
        return zone

    def set_selected_zone(self, zone: Zone | None):
        self._selected_zone = zone

    def get_selected_zone(self) -> Zone | None:
        return self._selected_zone

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _zone_verts_to_map_surface(self, world_verts: list) -> list:
        """Converte vértices do mundo para coordenadas da map_surface."""
        result = []
        for wx, wy in world_verts:
            sx, sy = self.camera.world_to_screen(wx, wy)
            sx -= self.PANEL_W  # Ajusta para mapa surface
            result.append((sx, sy))
        return result

    @staticmethod
    def _wrap(text: str, font: pygame.font.Font, max_w: int) -> list[str]:
        """Quebra texto em linhas que cabem em max_w pixels."""
        words = text.split()
        lines, line = [], ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines
