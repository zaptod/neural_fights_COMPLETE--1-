"""
NEURAL FIGHTS - Database Hook Patch
========================================
Este arquivo mostra EXATAMENTE o que adicionar ao database.py existente
para integrar o World Map via LiveDB Hook.

NÃO substitui database.py — mostra apenas as modificações necessárias.
As linhas marcadas com [NOVO] devem ser adicionadas ao arquivo original.

Siga este guia e adicione ao neural_v3_rework/data/database.py:
"""

# ============================================================
# PASSO 1: No TOPO do database.py, adicione este import
# ============================================================

"""
[NOVO] Adicione após os imports existentes:

import sys
import os

# Hook do World Map (opcional — só ativa se o módulo estiver presente)
_WORLDMAP_ENABLED = False
_world_sync = None

def _init_worldmap_hook():
    global _WORLDMAP_ENABLED, _world_sync
    try:
        worldmap_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "neural_worldmap", "world_map")
        if worldmap_path not in sys.path:
            sys.path.insert(0, worldmap_path)
        from map_god_registry import WorldStateSync
        data_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "neural_worldmap", "data")
        _world_sync = WorldStateSync(data_dir)
        _WORLDMAP_ENABLED = True
        print("[WorldMap] Hook ativo — sincronizando com gods.json")
    except Exception as e:
        print(f"[WorldMap] Hook desativado: {e}")

_init_worldmap_hook()
"""


# ============================================================
# PASSO 2: Na função salvar_personagem() (ou equivalente),
#          adicione o hook APÓS salvar o JSON:
# ============================================================

"""
[NOVO] Adicione ao final da função que salva personagens:

def salvar_personagem(personagem: dict) -> bool:
    # ... código existente de salvar no JSON ...

    # [NOVO] Hook do World Map
    global _world_sync, _WORLDMAP_ENABLED
    if _WORLDMAP_ENABLED and _world_sync:
        god_id = personagem.get("god_id")
        char_id = personagem.get("id") or personagem.get("nome")
        if god_id:
            try:
                _world_sync.on_character_update(char_id, god_id)
            except Exception as e:
                print(f"[WorldMap] Hook error: {e}")

    return True
"""


# ============================================================
# PASSO 3: Adicione o campo god_id ao personagens.json
#          (schema de exemplo)
# ============================================================

PERSONAGEM_SCHEMA_ADICOES = {
    # Adicionar este campo a cada personagem no personagens.json:
    "god_id": None,   # None = mortal sem deus | "caleb_01" = id do deus

    # Exemplo de personagem completo com o novo campo:
    "_exemplo_personagem_atualizado": {
        "id": "char_001",
        "nome": "Caleb",
        "classe": "Guerreiro (Força Bruta)",
        "forca": 85,
        # ... outros campos existentes ...
        "god_id": "caleb_01"   # [NOVO]
    }
}


# ============================================================
# PASSO 4: Adicione o campo god_id ao characters.py (dataclass)
# ============================================================

"""
[NOVO] Em neural_v3_rework/models/characters.py, adicione ao dataclass Personagem:

@dataclass
class Personagem:
    # ... campos existentes ...

    # [NOVO] Vínculo com o sistema de deuses
    god_id: str = None    # ID do deus que este personagem serve
"""


# ============================================================
# PASSO 5: Adicione botão no main.py da UI
# ============================================================

"""
[NOVO] Em neural_v3_rework/ui/main.py, adicione um botão:

def _criar_botoes(self):
    # ... botões existentes ...

    # [NOVO] Botão World Map
    btn_worldmap = ctk.CTkButton(
        self.frame_botoes,
        text="🗺  WORLD MAP",
        command=self._abrir_worldmap,
        fg_color="#0f3460",
        hover_color="#1a4a80",
        border_color="#00d9ff",
        border_width=1,
    )
    btn_worldmap.pack(fill="x", pady=4)

def _abrir_worldmap(self):
    import subprocess, sys, os
    worldmap_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "neural_worldmap", "run_worldmap.py")
    subprocess.Popen([sys.executable, worldmap_path])
"""


# ============================================================
# RESUMO DAS MODIFICAÇÕES
# ============================================================

MODIFICATION_SUMMARY = """
Arquivos a modificar no projeto existente:
==========================================

1. neural_v3_rework/data/database.py
   → Adicionar _init_worldmap_hook() no topo
   → Adicionar hook na função de salvar personagem

2. neural_v3_rework/models/characters.py
   → Adicionar campo: god_id: str = None

3. neural_v3_rework/data/personagens.json
   → Adicionar "god_id": null em cada personagem existente

4. neural_v3_rework/ui/main.py
   → Adicionar botão "🗺 WORLD MAP" no menu principal

Novos arquivos (criados pelo worldmap):
========================================

neural_worldmap/
├── run_worldmap.py          ← Entry point (python run_worldmap.py)
├── data/
│   ├── world_regions.json   ← 27 zonas de Aethermoor
│   ├── gods.json            ← Registry de deuses
│   └── world_state.json     ← Estado atual do território
└── world_map/
    ├── map_camera.py        ← Google Maps camera
    ├── map_territories.py   ← Polígonos + hit detection
    ├── map_god_registry.py  ← Sincronização de dados
    ├── map_vfx.py           ← Efeitos por Natureza
    ├── map_renderer.py      ← Renderização principal
    └── map_ui.py            ← Painel de criação de deuses
"""

if __name__ == "__main__":
    print(MODIFICATION_SUMMARY)
