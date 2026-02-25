"""
NEURAL FIGHTS - World Map Camera System
Sistema de câmera estilo Google Maps: pan, zoom, inércia, fly-to.
"""

import math


class MapCamera:
    """
    Câmera com comportamento idêntico ao Google Maps.
    Todas as posições no mundo são em "world units" (0-2000 x, 0-1400 y).
    A câmera converte para screen pixels usando zoom + offset.
    """

    # ── Limites ───────────────────────────────────────────────────────────────
    MIN_ZOOM = 0.25
    MAX_ZOOM = 6.0
    ZOOM_STEP = 1.12          # Fator por scroll tick
    FRICTION  = 0.82          # Desaceleração da inércia (0=para imediato, 1=desliza para sempre)
    FLY_SPEED = 0.10          # Velocidade da animação fly-to (0-1)
    MIN_VEL   = 0.3           # Velocidade mínima antes de parar inércia

    def __init__(self, screen_w: int, screen_h: int,
                 world_w: int = 2000, world_h: int = 1400):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.world_w  = world_w
        self.world_h  = world_h

        # Zoom inicial para encaixar o mundo na tela com margem
        fit_zoom = min(screen_w / world_w, screen_h / world_h) * 0.88
        self.zoom = fit_zoom

        # Centra o mundo na tela
        self.offset_x = (world_w / 2) - (screen_w / 2) / self.zoom
        self.offset_y = (world_h / 2) - (screen_h / 2) / self.zoom

        # ── Estado de Pan ────────────────────────────────────────────────────
        self.dragging          = False
        self._drag_start_sx    = 0        # Posição de tela onde o drag começou
        self._drag_start_sy    = 0
        self._drag_start_ox    = 0.0      # Offset da câmera quando drag começou
        self._drag_start_oy    = 0.0
        self._last_sx          = 0
        self._last_sy          = 0

        # ── Inércia ───────────────────────────────────────────────────────────
        self.vel_x = 0.0
        self.vel_y = 0.0

        # ── Fly-to animado ────────────────────────────────────────────────────
        self.flying          = False
        self._fly_target_ox  = 0.0
        self._fly_target_oy  = 0.0
        self._fly_target_z   = 0.0

    # ── Conversões de Coordenadas ─────────────────────────────────────────────

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        """Converte posição no mundo para posição na tela."""
        sx = (wx - self.offset_x) * self.zoom
        sy = (wy - self.offset_y) * self.zoom
        return (int(sx), int(sy))

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Converte posição na tela para posição no mundo."""
        wx = sx / self.zoom + self.offset_x
        wy = sy / self.zoom + self.offset_y
        return (wx, wy)

    def world_poly_to_screen(self, vertices: list) -> list[tuple[int, int]]:
        """Converte lista de vértices do mundo para screen space. Usado pelo renderer."""
        return [self.world_to_screen(vx, vy) for vx, vy in vertices]

    def world_dist_to_screen(self, world_dist: float) -> float:
        """Converte uma distância em world units para pixels."""
        return world_dist * self.zoom

    # ── Zoom (ancorando no cursor — comportamento Google Maps) ────────────────

    def zoom_at(self, sx: float, sy: float, factor: float):
        """
        Zoom centrado no ponto da tela (sx, sy).
        O ponto do mundo sob o cursor permanece fixo após o zoom.
        """
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))
        if new_zoom == self.zoom:
            return

        # Ponto do mundo sob o cursor ANTES do zoom
        wx, wy = self.screen_to_world(sx, sy)

        self.zoom = new_zoom

        # Reajusta offset para que o ponto do mundo fique sob o cursor
        self.offset_x = wx - sx / self.zoom
        self.offset_y = wy - sy / self.zoom

        # Para inércia ao fazer zoom
        self.vel_x = 0.0
        self.vel_y = 0.0

    def zoom_in(self, sx: float, sy: float):
        self.zoom_at(sx, sy, self.ZOOM_STEP)

    def zoom_out(self, sx: float, sy: float):
        self.zoom_at(sx, sy, 1.0 / self.ZOOM_STEP)

    # ── Pan (drag) ────────────────────────────────────────────────────────────

    def start_drag(self, sx: float, sy: float):
        """Inicia um drag (mouse button down)."""
        self.dragging = True
        self.flying   = False
        self._drag_start_sx = sx
        self._drag_start_sy = sy
        self._drag_start_ox = self.offset_x
        self._drag_start_oy = self.offset_y
        self._last_sx = sx
        self._last_sy = sy
        self.vel_x = 0.0
        self.vel_y = 0.0

    def update_drag(self, sx: float, sy: float):
        """Atualiza pan enquanto o mouse se move."""
        if not self.dragging:
            return
        # Velocidade para inércia
        self.vel_x = (self._last_sx - sx) / self.zoom
        self.vel_y = (self._last_sy - sy) / self.zoom
        self._last_sx = sx
        self._last_sy = sy

        # Calcula novo offset baseado na diferença total do drag
        dx = (sx - self._drag_start_sx) / self.zoom
        dy = (sy - self._drag_start_sy) / self.zoom
        self.offset_x = self._drag_start_ox - dx
        self.offset_y = self._drag_start_oy - dy

    def end_drag(self):
        """Termina o drag — a velocidade vira inércia."""
        self.dragging = False

    # ── Fly-to animado ────────────────────────────────────────────────────────

    def fly_to(self, world_cx: float, world_cy: float, target_zoom: float = None):
        """
        Anima a câmera suavemente para centralizar em (world_cx, world_cy).
        Usado no double-click de um território.
        """
        if target_zoom is None:
            target_zoom = min(self.MAX_ZOOM * 0.65, max(self.zoom * 1.8, 1.5))

        self._fly_target_z  = target_zoom
        self._fly_target_ox = world_cx - (self.screen_w / 2) / target_zoom
        self._fly_target_oy = world_cy - (self.screen_h / 2) / target_zoom
        self.flying = True
        self.vel_x = 0.0
        self.vel_y = 0.0

    def fly_to_world(self):
        """Fly-to para ver o mundo inteiro."""
        fit_zoom = min(self.screen_w / self.world_w, self.screen_h / self.world_h) * 0.88
        self._fly_target_z  = fit_zoom
        self._fly_target_ox = (self.world_w / 2) - (self.screen_w / 2) / fit_zoom
        self._fly_target_oy = (self.world_h / 2) - (self.screen_h / 2) / fit_zoom
        self.flying = True

    # ── Update (chamado todo frame) ────────────────────────────────────────────

    def update(self):
        """Atualiza inércia e fly-to. Chamar uma vez por frame."""
        if self.flying:
            self._update_fly()
        elif not self.dragging:
            self._update_inertia()

    def _update_fly(self):
        """Interpolação suave para o alvo do fly-to."""
        speed = self.FLY_SPEED
        self.offset_x += (self._fly_target_ox - self.offset_x) * speed
        self.offset_y += (self._fly_target_oy - self.offset_y) * speed
        self.zoom     += (self._fly_target_z  - self.zoom    ) * speed

        # Chegou no destino?
        dist = math.hypot(self.offset_x - self._fly_target_ox,
                          self.offset_y - self._fly_target_oy)
        if dist < 0.5 and abs(self.zoom - self._fly_target_z) < 0.002:
            self.offset_x = self._fly_target_ox
            self.offset_y = self._fly_target_oy
            self.zoom     = self._fly_target_z
            self.flying   = False

    def _update_inertia(self):
        """Aplica inércia quando o drag termina."""
        if abs(self.vel_x) < self.MIN_VEL and abs(self.vel_y) < self.MIN_VEL:
            self.vel_x = 0.0
            self.vel_y = 0.0
            return
        self.offset_x += self.vel_x
        self.offset_y += self.vel_y
        self.vel_x *= self.FRICTION
        self.vel_y *= self.FRICTION

    # ── Utilitários ────────────────────────────────────────────────────────────

    def is_world_point_visible(self, wx: float, wy: float, margin: float = 0) -> bool:
        """Verifica se um ponto do mundo está visível na tela."""
        sx, sy = self.world_to_screen(wx, wy)
        return (-margin <= sx <= self.screen_w + margin and
                -margin <= sy <= self.screen_h + margin)

    def is_polygon_visible(self, vertices: list, margin: float = 50) -> bool:
        """Verifica se algum vértice do polígono está visível (culling básico)."""
        return any(self.is_world_point_visible(vx, vy, margin) for vx, vy in vertices)

    @property
    def zoom_label(self) -> str:
        """Label de zoom para debug."""
        return f"{self.zoom:.2f}x"
