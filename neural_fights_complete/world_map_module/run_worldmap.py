"""
NEURAL FIGHTS - World Map Entry Point
1920×1080 · Google Maps Camera · God War Visualization

Controles:
  Scroll Wheel     → Zoom (ancorando no cursor)
  Left Click+Drag  → Pan
  Left Click       → Selecionar zona
  Double Click     → Fly-to zona
  [G]              → Abrir painel de criação de deus
  [HOME]           → Fly-to mundo inteiro
  [R]              → Recarregar dados do disco
  [ESC]            → Fechar painel / Sair
  [F11]            → Fullscreen toggle
"""

import sys
import os
import pygame

# Adiciona o diretório world_map ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "world_map"))

from map_camera     import MapCamera
from map_territories import TerritoryManager
from map_god_registry import WorldStateSync
from map_renderer   import MapRenderer
from map_ui         import GodCreationPanel

# ── Configuração ──────────────────────────────────────────────────────────────
SCREEN_W   = 1920
SCREEN_H   = 1080
TITLE      = "Neural Fights — Aethermoor World Map"
FPS        = 60
DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
PANEL_W    = 360    # Largura do painel lateral


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)

    # Tenta criar janela 1920x1080; cai para resolução disponível
    info = pygame.display.Info()
    w = min(SCREEN_W, info.current_w)
    h = min(SCREEN_H, info.current_h)

    flags = pygame.RESIZABLE
    screen = pygame.display.set_mode((w, h), flags)
    clock  = pygame.time.Clock()
    fullscreen = False

    # ── Sistemas ──────────────────────────────────────────────────────────────
    camera      = MapCamera(w - PANEL_W, h, world_w=2000, world_h=1400)
    territories = TerritoryManager(DATA_DIR)
    world_state = WorldStateSync(DATA_DIR)

    # Sincroniza bordas contestadas iniciais
    contested = territories.get_contested_borders(world_state.ownership)
    world_state.on_contested_borders_update(contested)

    renderer = MapRenderer(screen, camera, territories, world_state)
    god_panel = GodCreationPanel(w, h, world_state, territories)

    # ── Estado de Interação ───────────────────────────────────────────────────
    dragging         = False
    drag_start_pos   = (0, 0)
    last_click_time  = 0
    last_click_pos   = (0, 0)
    DOUBLE_CLICK_MS  = 300

    print(f"[NeuralFights] World Map iniciado — {w}x{h}")
    print(f"[NeuralFights] {len(territories.zones)} zonas carregadas")
    print(f"[NeuralFights] {len(world_state.gods)} deuses ativos")

    # ── Game Loop ─────────────────────────────────────────────────────────────
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # ── Eventos ───────────────────────────────────────────────────────────
        for event in pygame.event.get():

            # Painel de criação tem prioridade nos eventos
            if god_panel.handle_event(event):
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if not god_panel.visible:
                        running = False
                continue

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_g:
                    god_panel.open("CREATE")
                elif event.key == pygame.K_HOME:
                    camera.fly_to_world()
                elif event.key == pygame.K_r:
                    world_state.reload()
                    contested = territories.get_contested_borders(world_state.ownership)
                    world_state.on_contested_borders_update(contested)
                    print("[NeuralFights] Dados recarregados.")
                elif event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                    new_w, new_h = screen.get_size()
                    camera.screen_w = new_w - PANEL_W
                    camera.screen_h = new_h
                    renderer.screen = screen
                    renderer.screen_w = new_w
                    renderer.screen_h = new_h
                    renderer.map_surface = pygame.Surface(
                        (new_w - PANEL_W, new_h), pygame.SRCALPHA)

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                new_w, new_h = event.size
                camera.screen_w = new_w - PANEL_W
                camera.screen_h = new_h
                renderer.screen = screen
                renderer.screen_w = new_w
                renderer.screen_h = new_h
                renderer.map_surface = pygame.Surface(
                    (new_w - PANEL_W, new_h), pygame.SRCALPHA)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                # Só interage com o mapa se não estiver no painel
                if mx > PANEL_W:
                    map_mx = mx - PANEL_W

                    if event.button == 1:  # Botão esquerdo
                        dragging = False
                        camera.start_drag(mx, my)

                        # Detecção de double-click
                        now = pygame.time.get_ticks()
                        dist = ((mx - last_click_pos[0])**2 + (my - last_click_pos[1])**2)**0.5
                        if now - last_click_time < DOUBLE_CLICK_MS and dist < 10:
                            # Double click → fly to zona
                            wx, wy = camera.screen_to_world(mx, my)
                            zone = territories.get_zone_at_world_pos(wx, wy)
                            if zone:
                                camera.fly_to(zone.centroid[0], zone.centroid[1])
                        last_click_time = now
                        last_click_pos  = (mx, my)
                        drag_start_pos  = (mx, my)

                    elif event.button == 3:  # Botão direito
                        renderer.set_selected_zone(None)

                    elif event.button == 4:  # Scroll up → zoom in
                        camera.zoom_in(mx, my)

                    elif event.button == 5:  # Scroll down → zoom out
                        camera.zoom_out(mx, my)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    mx, my = event.pos
                    # Se não arrastou → é um click simples → seleciona zona
                    dist = ((mx - drag_start_pos[0])**2 + (my - drag_start_pos[1])**2)**0.5
                    if dist < 5 and mx > PANEL_W:
                        map_mx = mx - PANEL_W
                        renderer.select_zone_at_map_pos(map_mx, my)
                    camera.end_drag()

            elif event.type == pygame.MOUSEMOTION:
                if event.buttons[0]:  # Botão esquerdo pressionado
                    mx, my = event.pos
                    dist = ((mx - drag_start_pos[0])**2 + (my - drag_start_pos[1])**2)**0.5
                    if dist > 4:
                        dragging = True
                        camera.update_drag(mx, my)

        # ── Update ────────────────────────────────────────────────────────────
        renderer.update(dt)
        god_panel.update(dt)

        # Atualiza bordas contestadas periodicamente (a cada ~5s seria suficiente,
        # aqui fazemos a cada frame por simplicidade — otimizar se necessário)
        contested = territories.get_contested_borders(world_state.ownership)
        if contested != world_state.contested:
            world_state.on_contested_borders_update(contested)

        # ── Render ────────────────────────────────────────────────────────────
        renderer.draw()
        god_panel.draw(screen)

        pygame.display.flip()

    pygame.quit()
    print("[NeuralFights] World Map encerrado.")


if __name__ == "__main__":
    main()
