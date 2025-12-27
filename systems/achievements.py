"""Catálogo e checagem de conquistas (achievements).

Fornece:
- ACHIEVEMENTS_CATALOG: lista de conquistas (id, key, title, description)
- check_weekly_achievements(state) -> (new_unlocked_ids, eventos_msgs)

A checagem é feita de forma tolerante a ausência de campos no state.
"""
from typing import Dict, Any, List, Tuple
from systems.campaign import compute_net_worth

ACHIEVEMENTS_CATALOG = [
    {"id": "first_fazenda", "title": "Primeira Fazenda", "description": "Comprou a primeira fazenda."},
    {"id": "first_equip", "title": "Primeiro Equipamento", "description": "Comprou seu primeiro equipamento."},
    {"id": "first_harvest", "title": "Primeira Colheita", "description": "Armazenou produto pela primeira vez."},
    {"id": "five_hectares", "title": "5 Hectares", "description": "Possui 5 hectares ou mais em propriedades."},
    {"id": "net_worth_x2", "title": "Patrimônio x2", "description": "Dobrou o patrimônio inicial."},
    {"id": "twelve_weeks_positive", "title": "12 Semanas Positivas", "description": "Manteve saldo positivo por 12 semanas consecutivas."},
]

# Mapear id -> entrada para acesso rápido
_CATALOG_MAP = {c["id"]: c for c in ACHIEVEMENTS_CATALOG}


def _has_pronta_estoque(state: Dict[str, Any]) -> bool:
    estoque = state.get("estoque", []) or []
    return any((l.get("quantidade_kg", 0) or 0) > 0 for l in estoque)


def _total_hectares(state: Dict[str, Any]) -> float:
    fazendas = state.get("fazendas", []) or []
    try:
        return sum(float(f.get("tam", 0) or 0) for f in fazendas)
    except Exception:
        return 0.0


def _initial_net_worth(state: Dict[str, Any]) -> float:
    camp = state.get("campaign", {}) or {}
    return camp.get("initial_net_worth") or 0.0


def achievement_message(aid: str) -> str:
    entry = _CATALOG_MAP.get(aid, {})
    title = entry.get("title", aid)
    desc = entry.get("description", "")
    return f"CONQUISTA DESBLOQUEADA: {title} — {desc}"


def check_weekly_achievements(state: Dict[str, Any]) -> List[str]:
    """Verifica conquistas que devem ser desbloqueadas esta semana.

    Retorna somente a lista de `ids` que deveriam ser desbloqueadas (não persiste).
    O chamador é responsável por persistir e gerar mensagens de log para os ids realmente novos.
    """
    unlocked = set(state.get("unlocked_achievements", []) or [])
    newly = []

    def maybe_unlock(aid: str, cond: bool):
        if cond and aid not in unlocked:
            unlocked.add(aid)
            newly.append(aid)

    # 1) Primeira fazenda
    maybe_unlock("first_fazenda", len(state.get("fazendas", []) or []) >= 1)

    # 2) Primeiro equipamento
    maybe_unlock("first_equip", len(state.get("meus_equipamentos", []) or []) >= 1)

    # 3) Primeira colheita (estoque com quantidade)
    maybe_unlock("first_harvest", _has_pronta_estoque(state))

    # 4) 5 hectares
    maybe_unlock("five_hectares", _total_hectares(state) >= 5)

    # 5) Net worth x2
    initial = _initial_net_worth(state)
    if initial and initial > 0:
        nw = compute_net_worth(state)
        maybe_unlock("net_worth_x2", nw >= initial * 2)

    # 6) 12 semanas positivas consecutivas
    maybe_unlock("twelve_weeks_positive", int(state.get("weeks_positive_cash_consecutive", 0)) >= 12)

    return newly
