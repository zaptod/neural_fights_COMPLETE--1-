"""
NEURAL FIGHTS - Map VFX System
Efeitos visuais baseados na Natureza do deus: mutações de território,
animação de bordas, flares de batalha, rachaduras nos selos antigos.
"""

import math
import random
import pygame


# ── Utilitários de Cor ────────────────────────────────────────────────────────

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def lerp_color(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def with_alpha(color: tuple, alpha: int) -> tuple:
    return (*color[:3], alpha)

def pulse(t: float, speed: float = 1.0) -> float:
    """Valor pulsante entre 0 e 1."""
    return (math.sin(t * speed * math.pi * 2) + 1) / 2


# ── Partículas ────────────────────────────────────────────────────────────────

class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=2):
        self.x = x; self.y = y
        self.vx = vx; self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    @property
    def alive(self) -> bool:
        return self.life > 0

    @property
    def alpha(self) -> int:
        return int(255 * max(0, self.life / self.max_life))


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []

    def emit(self, x, y, color, count=5, speed=30, life=1.5, size=2, direction=None):
        for _ in range(count):
            if direction is not None:
                angle = math.radians(direction + random.uniform(-30, 30))
            else:
                angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(speed * 0.5, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            self.particles.append(Particle(
                x + random.uniform(-5, 5),
                y + random.uniform(-5, 5),
                vx, vy, color,
                random.uniform(life * 0.5, life),
                size
            ))

    def update(self, dt: float):
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles:
            p.update(dt)

    def draw(self, surface: pygame.Surface):
        for p in self.particles:
            if p.size <= 1:
                px, py = int(p.x), int(p.y)
                if 0 <= px < surface.get_width() and 0 <= py < surface.get_height():
                    surface.set_at((px, py), (*p.color[:3], p.alpha))
            else:
                s = pygame.Surface((p.size*2, p.size*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*p.color[:3], p.alpha), (p.size, p.size), p.size)
                surface.blit(s, (int(p.x - p.size), int(p.y - p.size)))


# ── Renderizador de Bordas por Natureza ───────────────────────────────────────

class NatureBorderRenderer:
    """
    Renderiza a borda de um território baseado na Natureza do deus dono.
    Cada natureza tem estilo visual único.
    """

    @staticmethod
    def draw(surface: pygame.Surface, screen_verts: list, nature: str,
             color_primary: tuple, color_secondary: tuple, t: float,
             zoom: float):
        """
        surface: onde desenhar
        screen_verts: polígono em screen pixels
        nature: nature_element do deus
        color_primary/secondary: cores do deus
        t: tempo global (para animações)
        zoom: zoom atual da câmera
        """
        w = max(1, int(2 * zoom))  # Espessura base da borda

        dispatch = {
            "balanced":    NatureBorderRenderer._balance,
            "fire":        NatureBorderRenderer._fire,
            "ice":         NatureBorderRenderer._ice,
            "darkness":    NatureBorderRenderer._darkness,
            "nature":      NatureBorderRenderer._nature,
            "nature_vines":NatureBorderRenderer._nature,
            "chaos":       NatureBorderRenderer._chaos,
            "void":        NatureBorderRenderer._void,
            "greed":       NatureBorderRenderer._greed,
            "fear":        NatureBorderRenderer._fear_spikes,
            "fear_spikes": NatureBorderRenderer._fear_spikes,
            "arcane":      NatureBorderRenderer._arcane,
            "ancient":     NatureBorderRenderer._ancient,
        }
        fn = dispatch.get(nature, NatureBorderRenderer._default)
        fn(surface, screen_verts, color_primary, color_secondary, t, w)

    @staticmethod
    def _default(surface, verts, cp, cs, t, w):
        if len(verts) >= 3:
            pygame.draw.polygon(surface, cp, verts, max(1, w))

    @staticmethod
    def _balance(surface, verts, cp, cs, t, w):
        """Borda que alterna entre as duas cores do Balance."""
        if len(verts) < 3:
            return
        blend = pulse(t, 0.4)
        color = lerp_color(cp, cs, blend)
        pygame.draw.polygon(surface, color, verts, max(2, w + 1))
        # Segunda borda interior mais brilhante
        interior = _shrink_polygon(verts, 3)
        if interior:
            pygame.draw.polygon(surface, lerp_color(cs, cp, blend), interior, 1)

    @staticmethod
    def _fire(surface, verts, cp, cs, t, w):
        """Borda flamejante laranja com jitter."""
        if len(verts) < 3:
            return
        jitter = int(math.sin(t * 12) * 2)
        jv = [(x + jitter, y + int(math.sin(t * 8 + i) * 2))
              for i, (x, y) in enumerate(verts)]
        pygame.draw.polygon(surface, cp, jv, max(2, w + 2))

    @staticmethod
    def _ice(surface, verts, cp, cs, t, w):
        """Borda cristalina azul fria."""
        if len(verts) < 3:
            return
        pygame.draw.polygon(surface, cp, verts, max(2, w + 1))
        # Detalhe geométrico de cristal
        inner = _shrink_polygon(verts, 4)
        if inner:
            pygame.draw.polygon(surface, cs, inner, 1)

    @staticmethod
    def _darkness(surface, verts, cp, cs, t, w):
        """Borda que pulsa entre visível e quase invisível."""
        if len(verts) < 3:
            return
        alpha = int(180 + pulse(t, 0.3) * 75)
        s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(s, (*cp, alpha), verts, max(2, w + 2))
        surface.blit(s, (0, 0))

    @staticmethod
    def _nature(surface, verts, cp, cs, t, w):
        """Borda orgânica verde com ondulação leve."""
        if len(verts) < 3:
            return
        wave = [(x + int(math.sin(t * 3 + i * 0.8) * 2),
                 y + int(math.cos(t * 3 + i * 0.8) * 2))
                for i, (x, y) in enumerate(verts)]
        pygame.draw.polygon(surface, cp, wave, max(2, w + 1))

    @staticmethod
    def _chaos(surface, verts, cp, cs, t, w):
        """Borda que treme aleatoriamente — nunca quieta."""
        if len(verts) < 3:
            return
        seed = int(t * 20)
        random.seed(seed)
        jv = [(x + random.randint(-3, 3), y + random.randint(-3, 3))
              for x, y in verts]
        random.seed()
        color = lerp_color(cp, cs, pulse(t, 5))
        pygame.draw.polygon(surface, color, jv, max(2, w + 2))

    @staticmethod
    def _void(surface, verts, cp, cs, t, w):
        """Borda quase invisível — a escuridão não precisa de bordas."""
        if len(verts) < 3:
            return
        alpha = int(80 + pulse(t, 0.2) * 60)
        s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(s, (*cs, alpha), verts, max(1, w))
        surface.blit(s, (0, 0))

    @staticmethod
    def _greed(surface, verts, cp, cs, t, w):
        """Borda dupla dourada — mais espessa que o necessário."""
        if len(verts) < 3:
            return
        pygame.draw.polygon(surface, cp, verts, max(3, w + 3))
        inner = _shrink_polygon(verts, 3)
        if inner:
            shimmer = lerp_color(cp, (255, 255, 255), pulse(t, 1.5) * 0.4)
            pygame.draw.polygon(surface, shimmer, inner, 1)

    @staticmethod
    def _fear_spikes(surface, verts, cp, cs, t, w):
        """Borda com espinhos que se projetam para fora."""
        if len(verts) < 3:
            return
        pygame.draw.polygon(surface, cp, verts, max(2, w))
        # Adiciona espinhos nos vértices
        spike_len = int(8 * (1 + pulse(t, 1.5) * 0.5))
        cx = sum(x for x, y in verts) / len(verts)
        cy = sum(y for x, y in verts) / len(verts)
        for x, y in verts:
            dx, dy = x - cx, y - cy
            dist = math.hypot(dx, dy)
            if dist > 0:
                nx, ny = dx / dist, dy / dist
                tip_x = int(x + nx * spike_len)
                tip_y = int(y + ny * spike_len)
                pygame.draw.line(surface, cp, (int(x), int(y)), (tip_x, tip_y), max(1, w))

    @staticmethod
    def _arcane(surface, verts, cp, cs, t, w):
        """Borda arcana com brilho pulsante."""
        if len(verts) < 3:
            return
        glow = lerp_color(cp, (255, 255, 255), pulse(t, 0.8) * 0.3)
        pygame.draw.polygon(surface, glow, verts, max(2, w + 2))

    @staticmethod
    def _ancient(surface, verts, cp, cs, t, w):
        """Borda dourada antiga com padrão de selo."""
        if len(verts) < 3:
            return
        glow = lerp_color(cp, (200, 180, 100), pulse(t, 0.5) * 0.5)
        pygame.draw.polygon(surface, glow, verts, max(3, w + 3))


# ── Preenchimento do Território ───────────────────────────────────────────────

class TerritoryFillRenderer:
    """Renderiza o preenchimento interior de um território."""

    @staticmethod
    def draw(surface: pygame.Surface, screen_verts: list, nature: str,
             color_primary: tuple, color_secondary: tuple, t: float,
             alpha_base: int = 100):
        if len(screen_verts) < 3:
            return

        s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        dispatch = {
            "balanced":    TerritoryFillRenderer._balance,
            "fire":        TerritoryFillRenderer._fire,
            "ice":         TerritoryFillRenderer._ice,
            "darkness":    TerritoryFillRenderer._darkness,
            "nature":      TerritoryFillRenderer._nature,
            "nature_vines":TerritoryFillRenderer._nature,
            "chaos":       TerritoryFillRenderer._chaos,
            "void":        TerritoryFillRenderer._void,
            "greed":       TerritoryFillRenderer._greed,
            "fear":        TerritoryFillRenderer._darkness,
            "fear_spikes": TerritoryFillRenderer._darkness,
            "arcane":      TerritoryFillRenderer._arcane,
            "ancient":     TerritoryFillRenderer._ancient,
        }
        fn = dispatch.get(nature, TerritoryFillRenderer._default)
        fn(s, screen_verts, color_primary, color_secondary, t, alpha_base)
        surface.blit(s, (0, 0))

    @staticmethod
    def _default(s, verts, cp, cs, t, a):
        pygame.draw.polygon(s, (*cp, a), verts)

    @staticmethod
    def _balance(s, verts, cp, cs, t, a):
        # Metade esquerda cp, metade direita cs
        pygame.draw.polygon(s, (*cp, a), verts)
        # Overlay pulsante da segunda cor
        overlay_a = int(a * pulse(t, 0.4) * 0.4)
        pygame.draw.polygon(s, (*cs, overlay_a), verts)

    @staticmethod
    def _fire(s, verts, cp, cs, t, a):
        flicker = int(a * (0.7 + pulse(t, 5) * 0.3))
        pygame.draw.polygon(s, (*cp, flicker), verts)

    @staticmethod
    def _ice(s, verts, cp, cs, t, a):
        pygame.draw.polygon(s, (*cp, int(a * 0.7)), verts)
        frost = int(30 * pulse(t, 0.3))
        pygame.draw.polygon(s, (*cs, frost), verts)

    @staticmethod
    def _darkness(s, verts, cp, cs, t, a):
        pygame.draw.polygon(s, (*cp, int(a * 1.2)), verts)

    @staticmethod
    def _nature(s, verts, cp, cs, t, a):
        pygame.draw.polygon(s, (*cp, a), verts)
        pulse_a = int(20 * pulse(t, 0.6))
        pygame.draw.polygon(s, (*cs, pulse_a), verts)

    @staticmethod
    def _chaos(s, verts, cp, cs, t, a):
        color = lerp_color(cp, cs, pulse(t, 3))
        pygame.draw.polygon(s, (*color, a), verts)

    @staticmethod
    def _void(s, verts, cp, cs, t, a):
        pygame.draw.polygon(s, (*cp, int(a * 0.8)), verts)

    @staticmethod
    def _greed(s, verts, cp, cs, t, a):
        shimmer = int(a * (0.8 + pulse(t, 1.5) * 0.2))
        pygame.draw.polygon(s, (*cp, shimmer), verts)

    @staticmethod
    def _arcane(s, verts, cp, cs, t, a):
        pygame.draw.polygon(s, (*cp, a), verts)
        glow_a = int(25 * pulse(t, 0.9))
        pygame.draw.polygon(s, (255, 255, 255, glow_a), verts)

    @staticmethod
    def _ancient(s, verts, cp, cs, t, a):
        pygame.draw.polygon(s, (*cp, int(a * 0.5)), verts)
        crack_a = int(40 * pulse(t, 0.3))
        pygame.draw.polygon(s, (*cs, crack_a), verts)


# ── Flare de Batalha (⚔ CONTESTED) ───────────────────────────────────────────

class BattleFlareRenderer:
    """Renderiza o indicador visual de borda contestada entre dois deuses."""

    def __init__(self):
        self._font_cache: dict = {}

    def get_font(self, size: int) -> pygame.font.Font:
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.SysFont("consolas", size, bold=True)
        return self._font_cache[size]

    def draw(self, surface: pygame.Surface, midpoint_screen: tuple,
             god_a_color: tuple, god_b_color: tuple, t: float, zoom: float,
             particles: ParticleSystem):
        sx, sy = int(midpoint_screen[0]), int(midpoint_screen[1])

        # Emite partículas ocasionalmente
        if random.random() < 0.04:
            c = god_a_color if random.random() < 0.5 else god_b_color
            particles.emit(sx, sy, c, count=3, speed=40, life=1.0, size=2)

        # Linha relâmpago entre os dois lados
        blend = pulse(t, 4)
        flash_color = lerp_color(god_a_color, god_b_color, blend)
        self._draw_lightning(surface, sx, sy, flash_color, t, zoom)

        # Ícone ⚔ e texto CONTESTED
        font_size = max(8, int(11 * zoom))
        font = self.get_font(font_size)
        label = font.render("⚔ CONTESTED", True, flash_color)
        shadow = font.render("⚔ CONTESTED", True, (0, 0, 0))
        rect = label.get_rect(center=(sx, sy - int(12 * zoom)))
        surface.blit(shadow, rect.move(1, 1))
        surface.blit(label, rect)

    @staticmethod
    def _draw_lightning(surface, cx, cy, color, t, zoom):
        """Linha relâmpago simples com jitter."""
        size = max(4, int(6 * zoom))
        for i in range(3):
            angle = t * 8 + i * 2.1
            r = size + int(math.sin(angle) * 2)
            pts = []
            segs = 5
            for s in range(segs):
                a = (s / segs) * math.pi * 2 + t
                jx = cx + int(math.cos(a) * r + random.uniform(-2, 2))
                jy = cy + int(math.sin(a) * r + random.uniform(-2, 2))
                pts.append((jx, jy))
            if len(pts) >= 3:
                pygame.draw.lines(surface, color, True, pts, 1)


# ── Animação de Rachaduras nos Selos ─────────────────────────────────────────

class SealCrackRenderer:
    """Renderiza rachaduras progressivas nos selos dos deuses antigos."""

    CRACK_COLOR_MAP = {
        "seal_of_balance": (  0, 217, 255),   # #00d9ff
        "seal_of_fear":    (122,   0, 170),   # #7a00aa
        "seal_of_greed":   (184, 134,  11),   # #b8860b
    }

    @staticmethod
    def draw(surface: pygame.Surface, screen_verts: list, zone_id: str,
             crack_level: int, max_cracks: int, t: float, zoom: float):
        if crack_level == 0 or not screen_verts:
            return

        color = SealCrackRenderer.CRACK_COLOR_MAP.get(zone_id, (200, 200, 200))
        cx = sum(x for x, y in screen_verts) / len(screen_verts)
        cy = sum(y for x, y in screen_verts) / len(screen_verts)

        ratio = crack_level / max(max_cracks, 1)
        n_cracks = max(1, int(crack_level * 2))

        random.seed(zone_id)  # Seed consistente por zona
        for i in range(n_cracks):
            angle = random.uniform(0, math.pi * 2)
            length = random.uniform(10, 40) * ratio * zoom
            pulse_offset = pulse(t + i * 0.5, 0.8) * 0.3

            # Linha principal da rachadura
            end_x = int(cx + math.cos(angle) * length)
            end_y = int(cy + math.sin(angle) * length)

            alpha = int(180 + pulse_offset * 75)
            s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.line(s, (*color, alpha), (int(cx), int(cy)), (end_x, end_y),
                             max(1, int(2 * zoom)))
            # Ramos menores
            branch_angle = angle + random.uniform(-0.8, 0.8)
            blen = length * 0.5
            bx = int(cx + math.cos(branch_angle) * blen)
            by = int(cy + math.sin(branch_angle) * blen)
            pygame.draw.line(s, (*color, int(alpha * 0.6)),
                             (int(cx), int(cy)), (bx, by),
                             max(1, int(zoom)))
            surface.blit(s, (0, 0))

        random.seed()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _shrink_polygon(verts: list, px: int) -> list:
    """Encolhe um polígono de tela por px pixels (aproximado)."""
    if len(verts) < 3:
        return []
    cx = sum(x for x, y in verts) / len(verts)
    cy = sum(y for x, y in verts) / len(verts)
    result = []
    for x, y in verts:
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy)
        if dist > px:
            ratio = (dist - px) / dist
            result.append((cx + dx * ratio, cy + dy * ratio))
        else:
            result.append((cx, cy))
    return result
