"""Coleta e atualização de estatísticas da campanha.

Funções auxiliares para persistir métricas em `state["campaign_stats"]`.
Todas as funções são tolerantes à ausência de campos no state.
"""
from typing import Dict, Any


def init_campaign_stats() -> Dict[str, Any]:
    return {
        "total_revenue": 0.0,
        "total_costs": 0.0,
        "net_profit": 0.0,
        "weeks_positive_cash": 0,
        "weeks_negative_cash": 0,
        "total_harvested_by_culture": {},
        "total_sold_by_culture": {},
        "critical_events_count": {},
    }


def ensure_stats(state: Dict[str, Any]):
    if "campaign_stats" not in state:
        state["campaign_stats"] = init_campaign_stats()
    # weekly accumulators
    if "_week_revenue_acc" not in state:
        state["_week_revenue_acc"] = 0.0
    if "_week_costs_acc" not in state:
        state["_week_costs_acc"] = 0.0


def record_costs(state: Dict[str, Any], amount: float):
    ensure_stats(state)
    try:
        amt = float(amount or 0)
    except Exception:
        amt = 0.0
    # Acumular custos na semana; totals serão atualizados em `week_finalize`
    state["_week_costs_acc"] = state.get("_week_costs_acc", 0.0) + amt


def record_revenue(state: Dict[str, Any], amount: float):
    ensure_stats(state)
    try:
        amt = float(amount or 0)
    except Exception:
        amt = 0.0
    # Acumular receita na semana; totals serão atualizados em `week_finalize`
    state["_week_revenue_acc"] = state.get("_week_revenue_acc", 0.0) + amt


def record_harvested(state: Dict[str, Any], cultura: str, kg: float):
    ensure_stats(state)
    try:
        q = float(kg or 0)
    except Exception:
        q = 0.0
    d = state["campaign_stats"].setdefault("total_harvested_by_culture", {})
    d[cultura] = d.get(cultura, 0.0) + q


def record_sold(state: Dict[str, Any], cultura: str, kg: float, revenue: float):
    ensure_stats(state)
    try:
        q = float(kg or 0)
    except Exception:
        q = 0.0
    d = state["campaign_stats"].setdefault("total_sold_by_culture", {})
    d[cultura] = d.get(cultura, 0.0) + q
    # revenue counted as part of weekly revenue
    record_revenue(state, revenue)


def record_critical_event(state: Dict[str, Any], event_type: str):
    ensure_stats(state)
    d = state["campaign_stats"].setdefault("critical_events_count", {})
    d[event_type] = d.get(event_type, 0) + 1


def week_finalize(state: Dict[str, Any]):
    """Finaliza a semana: atualiza semanas positivas/negativas e limpa acumuladores.

    A avaliação usa `state["dinheiro"]` para determinar se a semana foi positiva.
    """
    ensure_stats(state)
    dinheiro = float(state.get("dinheiro", 0.0) or 0.0)
    stats = state["campaign_stats"]
    if dinheiro >= 0:
        stats["weeks_positive_cash"] = stats.get("weeks_positive_cash", 0) + 1
    else:
        stats["weeks_negative_cash"] = stats.get("weeks_negative_cash", 0) + 1

    # Aplicar acumuladores semanais aos totals
    rev = float(state.get("_week_revenue_acc", 0.0) or 0.0)
    costs = float(state.get("_week_costs_acc", 0.0) or 0.0)
    stats["total_revenue"] = stats.get("total_revenue", 0.0) + rev
    stats["total_costs"] = stats.get("total_costs", 0.0) + costs
    stats["net_profit"] = stats.get("net_profit", 0.0) + (rev - costs)

    # reset weekly accumulators
    state["_week_revenue_acc"] = 0.0
    state["_week_costs_acc"] = 0.0
