"""
NEURAL FIGHTS - God Creation & Management UI
Painel overlay de criação de deuses, renderizado em Pygame.
Interface modal que aparece sobre o mapa quando [G] é pressionado.
"""

import pygame
from map_god_registry import WorldStateSync, God, NATURE_COLORS, hex_to_rgb
from map_territories import TerritoryManager
from map_vfx import pulse


# Cores do tema
BG         = (16,  21,  38)
BG2        = (22,  33,  62)
PANEL      = (15,  52,  96)
ACCENT     = (233, 69,  96)
CYAN       = (0,   217, 255)
TEXT       = (255, 255, 255)
DIM        = (136, 146, 176)
SUCCESS    = (0,   180, 100)
WARNING    = (243, 156, 18)
FIELD_BG   = (30,  40,  70)
FIELD_ACTIVE = (40, 55, 95)


NATURES = [
    ("balanced",  "⚖  Balance"),
    ("fire",      "🔥 Fire"),
    ("ice",       "❄  Ice"),
    ("darkness",  "🌑 Darkness"),
    ("nature",    "🌿 Nature"),
    ("chaos",     "🌀 Chaos"),
    ("void",      "🕳  Void"),
    ("greed",     "💰 Greed"),
    ("fear",      "💀 Fear"),
    ("arcane",    "✨ Arcane"),
    ("blood",     "🩸 Blood"),
    ("time",      "⏳ Time"),
    ("gravity",   "🪐 Gravity"),
]


class TextField:
    """Campo de texto interativo simples em Pygame."""
    def __init__(self, rect: pygame.Rect, placeholder: str = ""):
        self.rect = rect
        self.placeholder = placeholder
        self.text = ""
        self.active = False
        self.cursor_visible = True
        self._cursor_timer = 0.0

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key not in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_TAB):
                if len(self.text) < 32:
                    self.text += event.unicode
            return True
        return False

    def update(self, dt: float):
        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0
            self.cursor_visible = not self.cursor_visible

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        color = FIELD_ACTIVE if self.active else FIELD_BG
        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        pygame.draw.rect(surface, PANEL if not self.active else CYAN, self.rect, 1, border_radius=4)

        if self.text:
            t = font.render(self.text, True, TEXT)
        else:
            t = font.render(self.placeholder, True, DIM)
        surface.blit(t, (self.rect.x + 8, self.rect.y + (self.rect.h - t.get_height()) // 2))

        if self.active and self.cursor_visible and self.text:
            tw = font.size(self.text)[0]
            cx = self.rect.x + 8 + tw + 2
            cy1 = self.rect.y + 6
            cy2 = self.rect.y + self.rect.h - 6
            pygame.draw.line(surface, CYAN, (cx, cy1), (cx, cy2), 1)


class GodCreationPanel:
    """
    Painel modal de criação de deuses.
    Abre sobre o mapa quando o usuário pressiona [G].
    Possui dois modos:
      - CREATE: Cria um novo deus
      - CLAIM:  Atribui um deus existente a uma zona selecionada
    """

    W = 520
    H = 580

    def __init__(self, screen_w: int, screen_h: int,
                 world_state: WorldStateSync,
                 territories: TerritoryManager):
        self.screen_w    = screen_w
        self.screen_h    = screen_h
        self.world_state = world_state
        self.territories = territories

        self.visible = False
        self.mode    = "CREATE"   # "CREATE" ou "CLAIM"
        self._time   = 0.0
        self._msg    = ""
        self._msg_timer = 0.0

        # Posição central
        self.ox = (screen_w - self.W) // 2
        self.oy = (screen_h - self.H) // 2

        self._init_widgets()

    def _init_widgets(self):
        ox, oy = self.ox, self.oy
        p = 20  # Padding

        self.font_title  = pygame.font.SysFont("consolas", 18, bold=True)
        self.font_label  = pygame.font.SysFont("consolas", 12, bold=True)
        self.font_body   = pygame.font.SysFont("consolas", 12)
        self.font_small  = pygame.font.SysFont("consolas", 10)
        self.font_btn    = pygame.font.SysFont("consolas", 13, bold=True)

        # Campos de texto
        self.field_name = TextField(
            pygame.Rect(ox + p, oy + 80, self.W - p*2, 36),
            placeholder="God name (e.g. NightKing_77)"
        )
        self.field_nature_display = None  # Mostrado como dropdown
        self.field_followers = TextField(
            pygame.Rect(ox + p, oy + 210, self.W - p*2, 36),
            placeholder="Follower count (e.g. 1247)"
        )
        self.field_champion = TextField(
            pygame.Rect(ox + p, oy + 300, self.W - p*2, 36),
            placeholder="Champion character ID (optional)"
        )
        self.field_lore = TextField(
            pygame.Rect(ox + p, oy + 390, self.W - p*2, 36),
            placeholder="Lore / description (optional)"
        )

        # Seleção de natureza
        self.selected_nature_idx = 0
        self._nature_rects = []

        # Botões
        btn_y = oy + self.H - 56
        self.btn_create = pygame.Rect(ox + p, btn_y, 180, 40)
        self.btn_cancel = pygame.Rect(ox + self.W - p - 120, btn_y, 120, 40)

        # Seleção de source
        self.selected_source_idx = 0
        self.sources = ["manual", "tiktok_comment", "youtube_comment"]
        self.source_labels = ["📋 Manual", "🎵 TikTok", "▶  YouTube"]

    def open(self, mode: str = "CREATE"):
        self.visible = True
        self.mode = mode
        self.field_name.text = ""
        self.field_followers.text = "0"
        self.field_champion.text = ""
        self.field_lore.text = ""
        self.selected_nature_idx = 0
        self._msg = ""

    def close(self):
        self.visible = False

    def handle_event(self, event) -> bool:
        """Retorna True se o evento foi consumido pelo painel."""
        if not self.visible:
            return False

        # Fecha com ESC
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True

        # Campos de texto
        for field in [self.field_name, self.field_followers,
                       self.field_champion, self.field_lore]:
            field.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            # Botão Criar
            if self.btn_create.collidepoint(mx, my):
                self._submit()
                return True

            # Botão Cancelar
            if self.btn_cancel.collidepoint(mx, my):
                self.close()
                return True

            # Seleção de natureza
            for i, rect in enumerate(self._nature_rects):
                if rect.collidepoint(mx, my):
                    self.selected_nature_idx = i
                    return True

            # Seleção de source
            for i, rect in enumerate(getattr(self, "_source_rects", [])):
                if rect.collidepoint(mx, my):
                    self.selected_source_idx = i
                    return True

            # Bloqueia cliques fora do painel
            panel_rect = pygame.Rect(self.ox, self.oy, self.W, self.H)
            if not panel_rect.collidepoint(mx, my):
                self.close()
            return True

        return self.visible  # Bloqueia todos os eventos enquanto visível

    def _submit(self):
        name = self.field_name.text.strip()
        if not name:
            self._show_msg("❌ God name is required.", error=True)
            return

        nature_el, _ = NATURES[self.selected_nature_idx]
        nature_display = NATURES[self.selected_nature_idx][1].strip()

        try:
            followers = int(self.field_followers.text or "0")
        except ValueError:
            followers = 0

        source = self.sources[self.selected_source_idx]

        god = self.world_state.create_god(
            god_name       = name,
            nature         = nature_display.split()[-1],
            nature_element = nature_el,
            source         = source,
        )
        if self.field_champion.text.strip():
            god.champion_character_id = self.field_champion.text.strip()
        if self.field_lore.text.strip():
            god.lore_description = self.field_lore.text.strip()
        god.follower_count = followers
        self.world_state.save_all()

        self._show_msg(f"✔ {god.god_name} has risen as God of {god.nature}.", error=False)

    def _show_msg(self, msg: str, error: bool = False):
        self._msg = msg
        self._msg_error = error
        self._msg_timer = 3.0

    def update(self, dt: float):
        if not self.visible:
            return
        self._time += dt
        for field in [self.field_name, self.field_followers,
                       self.field_champion, self.field_lore]:
            field.update(dt)
        if self._msg_timer > 0:
            self._msg_timer -= dt

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        ox, oy = self.ox, self.oy
        p = 20

        # Overlay semi-transparente
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Painel principal
        panel_rect = pygame.Rect(ox, oy, self.W, self.H)
        pygame.draw.rect(surface, BG2, panel_rect, border_radius=8)
        pygame.draw.rect(surface, CYAN if self.mode == "CREATE" else ACCENT,
                         panel_rect, 2, border_radius=8)

        # Header
        title_text = "⚡ NEW GOD RISES" if self.mode == "CREATE" else "⚔ CLAIM TERRITORY"
        title = self.font_title.render(title_text, True, CYAN)
        surface.blit(title, title.get_rect(centerx=ox + self.W // 2, top=oy + p))

        # GOD NAME
        self._label(surface, "GOD NAME", ox + p, oy + 64)
        self.field_name.draw(surface, self.font_body)

        # NATURE
        self._label(surface, "NATURE", ox + p, oy + 130)
        self._draw_nature_grid(surface, ox + p, oy + 148)

        # FOLLOWERS
        self._label(surface, "FOLLOWER COUNT", ox + p, oy + 194)
        self.field_followers.draw(surface, self.font_body)

        # CHAMPION
        self._label(surface, "CHAMPION CHARACTER ID", ox + p, oy + 284)
        self.field_champion.draw(surface, self.font_body)

        # LORE
        self._label(surface, "LORE / DESCRIPTION", ox + p, oy + 374)
        self.field_lore.draw(surface, self.font_body)

        # SOURCE
        self._label(surface, "SOURCE", ox + p, oy + 444)
        self._draw_source_selector(surface, ox + p, oy + 462)

        # Botões
        self._draw_btn(surface, self.btn_create, "⚡ SUMMON GOD", CYAN)
        self._draw_btn(surface, self.btn_cancel, "CANCEL", DIM)

        # Mensagem de feedback
        if self._msg and self._msg_timer > 0:
            alpha = min(255, int(self._msg_timer * 255))
            color = ACCENT if getattr(self, "_msg_error", False) else SUCCESS
            msg_surf = self.font_body.render(self._msg, True, color)
            surface.blit(msg_surf, msg_surf.get_rect(
                centerx=ox + self.W // 2, top=self.btn_create.top - 24))

    def _label(self, surface, text, x, y):
        surf = self.font_label.render(text, True, DIM)
        surface.blit(surf, (x, y))

    def _draw_nature_grid(self, surface, x, y):
        self._nature_rects = []
        cols = 5
        btn_w = (self.W - 40) // cols
        btn_h = 24

        for i, (elem, label) in enumerate(NATURES):
            col = i % cols
            row = i // cols
            rx = x + col * btn_w
            ry = y + row * (btn_h + 4)
            rect = pygame.Rect(rx, ry, btn_w - 4, btn_h)
            self._nature_rects.append(rect)

            colors = NATURE_COLORS.get(elem, ("#8892b0", "#ffffff"))
            cp = hex_to_rgb(colors[0])

            selected = (i == self.selected_nature_idx)
            bg_color = (*cp, 180) if selected else (*cp, 50)

            s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            s.fill(bg_color)
            surface.blit(s, rect.topleft)
            pygame.draw.rect(surface, cp, rect, 1 if not selected else 2)

            font_size = 9
            font = pygame.font.SysFont("consolas", font_size)
            txt = font.render(label.split()[-1], True, TEXT if selected else DIM)
            surface.blit(txt, txt.get_rect(center=rect.center))

    def _draw_source_selector(self, surface, x, y):
        self._source_rects = []
        w = 140
        h = 28
        for i, label in enumerate(self.source_labels):
            rect = pygame.Rect(x + i * (w + 8), y, w, h)
            self._source_rects.append(rect)
            selected = (i == self.selected_source_idx)
            color = CYAN if selected else PANEL
            pygame.draw.rect(surface, color, rect, border_radius=4)
            pygame.draw.rect(surface, CYAN if selected else DIM, rect, 1, border_radius=4)
            font = pygame.font.SysFont("consolas", 11)
            txt = font.render(label, True, TEXT if selected else DIM)
            surface.blit(txt, txt.get_rect(center=rect.center))

    def _draw_btn(self, surface, rect, text, color):
        pygame.draw.rect(surface, PANEL, rect, border_radius=6)
        pygame.draw.rect(surface, color, rect, 2, border_radius=6)
        txt = self.font_btn.render(text, True, color)
        surface.blit(txt, txt.get_rect(center=rect.center))
