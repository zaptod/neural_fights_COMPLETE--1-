# Neural Fights — World Map Module
## `neural_worldmap/`

Módulo standalone de visualização do **God War** em Aethermoor.

---

## 🚀 Como Executar

```bash
# A partir da raiz do projeto
pip install pygame
python neural_worldmap/run_worldmap.py
```

---

## 🎮 Controles

| Input | Ação |
|-------|------|
| `Scroll Wheel` | Zoom (âncora no cursor — Google Maps style) |
| `Left Click + Drag` | Pan pelo mapa |
| `Left Click` | Selecionar zona (mostra info no painel) |
| `Double Click` | Fly-to animado para a zona |
| `Right Click` | Deselecionar |
| `[G]` | Abrir painel de criação de deus |
| `[HOME]` | Fly-to para visão do mundo inteiro |
| `[R]` | Recarregar dados do disco (hot-reload) |
| `[F11]` | Fullscreen toggle |
| `[ESC]` | Fechar painel / Sair |

---

## 📁 Estrutura

```
neural_worldmap/
├── run_worldmap.py              ← Entry point principal
├── DATABASE_HOOK_GUIDE.py       ← Guia de integração com o projeto existente
├── data/
│   ├── world_regions.json       ← 27 zonas com polígonos de Aethermoor
│   ├── gods.json                ← Registry de deuses (audience + protagonistas)
│   └── world_state.json         ← Estado atual (quem controla o quê)
└── world_map/
    ├── __init__.py
    ├── map_camera.py            ← Sistema de câmera Google Maps
    ├── map_territories.py       ← Polígonos, hit detection, vizinhos
    ├── map_god_registry.py      ← CRUD de deuses, WorldStateSync, API stubs
    ├── map_vfx.py               ← Efeitos visuais por Natureza (13 estilos)
    ├── map_renderer.py          ← Motor de renderização completo
    └── map_ui.py                ← Painel de criação de deuses
```

---

## 🗺️ O Mundo: Aethermoor

| Região | Zonas | Natureza Base |
|--------|-------|---------------|
| The Void Ridge | Shattered Peak, Ashen Wastes, Dead Crown | Chaos |
| The Verdant Reach | Elderwood Grove, Thornwall, Misty Highlands | Nature |
| The Iron Heartlands | Iron Gate, Anvil Plains, Warrior's Rest | Balanced |
| The Ember Barrens | Char Fields, Cinder Pit, Dragonfault | Fire |
| The Bone Marches | Bleached Path, Grave Hollow, Widow's Pass | Darkness |
| **The Crown Districts** | **Slum District** ⭐, Merchant Quarter, High Citadel | Balanced |
| The Tidal Expanse | Drowned Shore, Salt Flats, Deep Current | Void |
| The Golden Reaches | Gilded Road, Dusthaven, Old Crossing | Greed |
| **The Sunken Archive** | Seal of Fear 😴, Seal of Balance ⚡, Seal of Greed 👁 | Ancient |

⭐ = Local de origem de Caleb  
🔒 = Zonas de selos antigos (não claimáveis pela audiência)

---

## ⚡ Adicionar um Deus (Audiência)

### Via Interface [G]:
1. Pressione `[G]` no mapa
2. Preencha nome, Natureza, contagem de seguidores
3. Clique "⚡ SUMMON GOD"

### Via código:
```python
from world_map.map_god_registry import WorldStateSync

ws = WorldStateSync("neural_worldmap/data")
god = ws.create_god(
    god_name       = "NightKing_77",
    nature         = "Fear",
    nature_element = "fear",
    source         = "tiktok_comment",
)
ws.on_zone_claimed("iron_gate", god.god_id)
```

### Via JSON direto (`gods.json`):
```json
{
  "god_id": "god_nightking_7742",
  "god_name": "NightKing_77",
  "nature": "Fear",
  "nature_element": "fear",
  "follower_count": 342,
  "color_primary": "#2d0040",
  "color_secondary": "#7a00aa",
  "owned_zones": ["iron_gate", "ashen_wastes"]
}
```
Pressione `[R]` no mapa para recarregar.

---

## 🎨 Efeitos Visuais por Natureza

| Natureza | Borda | Fill | Animação |
|----------|-------|------|----------|
| Balance | Alterna entre 2 cores | Split pulsante | Oscilação contínua |
| Fire | Jitter flamejante | Flickering laranja | Tremor rítmico |
| Ice | Cristalina dupla | Frost overlay | Pulso frio |
| Darkness | Pulsa e desvanece | Quase sólido escuro | Aparece/desaparece |
| Nature | Ondulação orgânica | Verde pulsante | Wave senoidal |
| Chaos | Tremor aleatório | Cor instável | Nunca quieta |
| Void | Quase invisível | Escuridão profunda | Implode para o centro |
| Greed | Dupla dourada | Shimmer dourado | Brilho pulsante |
| Fear | Espinhos nos vértices | Roxo escuro | Espinhos crescem |
| Arcane | Glow branco | Overlay arcano | Pulso mágico |

---

## 🔌 Integração com o Projeto Existente

Veja `DATABASE_HOOK_GUIDE.py` para as modificações necessárias em:
- `data/database.py` — Hook automático ao salvar personagem
- `models/characters.py` — Campo `god_id`  
- `ui/main.py` — Botão "World Map" no menu principal

---

## 🔮 Próximas Fases

- **Fase 3**: God Creation Wizard completo no `view_chars.py`
- **Fase 4**: CTk sidebar integrada ao menu principal
- **Fase 5**: VFX avançados (partículas por região, seal crack events)
- **Fase 6**: API stub → TikTok/YouTube comment import real
