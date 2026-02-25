"""
NEURAL FIGHTS - Módulo Database
Funções de persistência de dados (JSON).
[PHASE 3] Adicionado hook para sincronização com World Map (WorldStateSync).
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Personagem, Arma

# Caminhos dos arquivos de dados - agora dentro de data/
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CHARS = os.path.join(DATA_DIR, "personagens.json")
ARQUIVO_ARMAS = os.path.join(DATA_DIR, "armas.json")
ARQUIVO_MATCH = os.path.join(DATA_DIR, "match_config.json")

# ── [PHASE 3] WorldStateSync Hook ────────────────────────────────────────────
# Hook opcional: ativa automaticamente se o módulo world_map_module estiver presente.
# Não quebra o projeto se ausente.
_world_sync = None
_worldmap_enabled = False

def _init_worldmap_hook():
    """Tenta inicializar o hook do World Map. Falha silenciosamente se ausente."""
    global _world_sync, _worldmap_enabled
    try:
        # Caminho do módulo do World Map (pasta irmã do projeto)
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        worldmap_path = os.path.join(base, "world_map_module", "world_map")
        if worldmap_path not in sys.path:
            sys.path.insert(0, worldmap_path)

        from map_god_registry import WorldStateSync
        worldmap_data = os.path.join(base, "world_map_module", "data")

        if os.path.isdir(worldmap_data):
            _world_sync = WorldStateSync(worldmap_data)
            _worldmap_enabled = True
            print("[WorldMap Hook] Ativo — sincronizando com gods.json")
        else:
            print("[WorldMap Hook] Pasta data/ não encontrada — hook desativado.")
    except Exception as e:
        print(f"[WorldMap Hook] Desativado: {e}")

_init_worldmap_hook()
# ─────────────────────────────────────────────────────────────────────────────


def carregar_json(arquivo):
    if not os.path.exists(arquivo): return []
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return []

def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_armas():
    raw = carregar_json(ARQUIVO_ARMAS)
    return [Arma(**item) for item in raw]

def carregar_personagens():
    raw_chars = carregar_json(ARQUIVO_CHARS)
    raw_armas = carregar_json(ARQUIVO_ARMAS)
    
    lista = []
    for item in raw_chars:
        peso_arma = 0
        nome_arma = item.get("nome_arma", "")
        
        # Busca o peso atualizado da arma
        for a in raw_armas:
            if a["nome"] == nome_arma:
                peso_arma = a["peso"]
                break
        
        p = Personagem(
            item["nome"], item["tamanho"], item["forca"], item["mana"],
            nome_arma, peso_arma,
            item.get("cor_r", 200), item.get("cor_g", 50), item.get("cor_b", 50),
            item.get("classe", "Guerreiro (Força Bruta)"),
            item.get("personalidade", "Aleatório"),
            item.get("god_id", None),       # [PHASE 3] Carrega vínculo divino
        )
        lista.append(p)
    return lista

def salvar_lista_armas(lista):
    salvar_json(ARQUIVO_ARMAS, [a.to_dict() for a in lista])

def salvar_lista_chars(lista):
    """Salva lista de personagens e notifica o WorldStateSync se ativo."""
    dicts = [p.to_dict() for p in lista]
    salvar_json(ARQUIVO_CHARS, dicts)

    # [PHASE 3] Hook do World Map — sincroniza campeões com gods.json
    if _worldmap_enabled and _world_sync:
        try:
            for p in lista:
                if p.god_id:
                    _world_sync.on_character_update(p.nome, p.god_id)
            _world_sync.reload()
        except Exception as e:
            print(f"[WorldMap Hook] Erro ao sincronizar: {e}")


def carregar_arma_por_nome(nome_arma):
    """Carrega uma arma específica pelo nome"""
    armas = carregar_armas()
    for arma in armas:
        if arma.nome == nome_arma:
            return arma
    return None


# [PHASE 3] Funções auxiliares para o wizard de criação de deuses
def get_worldmap_sync():
    """Retorna o WorldStateSync ativo, ou None se indisponível."""
    return _world_sync if _worldmap_enabled else None

def is_worldmap_active():
    """Retorna True se o hook do World Map está ativo."""
    return _worldmap_enabled
