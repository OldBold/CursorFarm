"""systems/campaign.py

Infraestrutura pura de campanha.

Funções puras:
- init_campaign_state() -> dict: estado inicial da campanha
- update_campaign(state, dias_avancados) -> dict: retorna novo estado de campanha calculado
- check_win(campaign_state) -> bool
- check_loss(campaign_state) -> bool

Regras mínimas (seguras):
- `weeks_played` incrementa em `dias_avancados // 7` semanas
- `weeks_negative_cash_consecutive` incrementa por semanas avançadas se dinheiro < 0, senão reseta para 0
- check_win: retorna True se `weeks_played >= 52` e dinheiro positivo
- check_loss: retorna True se `weeks_negative_cash_consecutive >= 4`

As regras são deliberadamente simples e não alteram o fluxo do jogo; são seguras
para integração inicial e podem ser refinadas mais tarde.
"""

from typing import Dict, Any

# Configurações de vitória / resgate
WIN_NET_WORTH_MULTIPLIER = 8.0
WIN_WEEKS_POSITIVE_CASH = 12

# Taxas de revenda (porcentagens aplicadas ao valor nominal)
RESALE_FAZENDA_RATIO = 0.8
RESALE_EQUIP_RATIO = 0.5


def init_campaign_state() -> Dict[str, int]:
    return {"weeks_played": 0, "weeks_negative_cash_consecutive": 0}


def update_campaign(state: Dict[str, Any], dias_avancados: int) -> Dict[str, int]:
    """Retorna um novo dicionário de estado de campanha baseado no state global.

    Não modifica `state` in-place (função pura).
    """
    weeks = int(dias_avancados // 7)
    camp = dict(state.get("campaign", init_campaign_state()))

    prev_weeks = int(camp.get("weeks_played", 0))
    camp["weeks_played"] = prev_weeks + weeks

    dinheiro = state.get("dinheiro", 0.0)
    if dinheiro < 0:
        camp["weeks_negative_cash_consecutive"] = camp.get("weeks_negative_cash_consecutive", 0) + weeks
    else:
        camp["weeks_negative_cash_consecutive"] = 0

    # semanas consecutivas com dinheiro positivo (para condição de vitória)
    if dinheiro > 0:
        camp["weeks_positive_cash_consecutive"] = camp.get("weeks_positive_cash_consecutive", 0) + weeks
    else:
        camp["weeks_positive_cash_consecutive"] = 0

    # Calcular patrimônio líquido atual e inicial (baseline)
    nw = compute_net_worth(state)
    camp_current_initial = camp.get("initial_net_worth")
    # Preencher baseline exatamente uma vez. Se não houver hook, usar fallback.
    # Usar prev_weeks para garantir que capturamos o momento logo após o estado
    # ficar jogável (antes de incrementar weeks_played).
    if not camp_current_initial and prev_weeks == 0:
        camp["initial_net_worth"] = nw
    else:
        if camp_current_initial:
            camp["initial_net_worth"] = camp_current_initial

    # Avaliar condição de perda com base no estado atual
    lost, reason = check_loss(camp, state)
    if lost:
        camp["status"] = "LOST"
        camp["lost_reason"] = reason
        return camp

    # Avaliar condição de vitória com base no patrimônio relativo e semanas positivas
    initial = camp.get("initial_net_worth") or 0
    if initial > 0:
        if nw >= initial * WIN_NET_WORTH_MULTIPLIER and camp.get("weeks_positive_cash_consecutive", 0) >= WIN_WEEKS_POSITIVE_CASH:
            camp["status"] = "WON"
            camp["won_reason"] = (
                f"Patrimônio atingiu {nw:,.2f}, meta {WIN_NET_WORTH_MULTIPLIER}x do inicial ({initial:,.2f}) "
                f"e {camp.get('weeks_positive_cash_consecutive',0)} semanas positivas consecutivas."
            )
            return camp

    return camp


def check_win(campaign_state: Dict[str, int], state: Dict[str, Any] = None) -> bool:
    """Condição de vitória simples.

    Por padrão, vitória ocorre após 52 semanas com saldo positivo.
    """
    weeks = int(campaign_state.get("weeks_played", 0))
    if weeks < 52:
        return False
    if state is None:
        return True
    return state.get("dinheiro", 0) > 0


def check_loss(campaign_state: Dict[str, int]) -> bool:
    """Condição de derrota simples: 4 semanas consecutivas com saldo negativo.

    NOTE: this function kept for compatibility but the richer form
    `check_loss(campaign_state, state)` is used to consider game state
    (no means of recovery).
    """
    return int(campaign_state.get("weeks_negative_cash_consecutive", 0)) >= 4


def compute_net_worth(state: Dict[str, Any]) -> float:
    """Calcula patrimônio líquido estimado baseado em campos conhecidos do state.

    Fontes consideradas (tolerantes a ausência):
    - `dinheiro`
    - valor de revenda das `fazendas` (campo `preco` ou `valor`) * RESALE_FAZENDA_RATIO
    - valor de revenda dos `meus_equipamentos` (campo `preco` ou `valor`) * RESALE_EQUIP_RATIO
    - valor do `estoque` usando custo de produção por kg * quantidade
    """
    total = 0.0
    total += float(state.get("dinheiro", 0.0) or 0.0)

    # Fazendas
    fazendas = state.get("fazendas", []) or []
    for f in fazendas:
        val = f.get("preco", f.get("valor", 0)) or 0
        try:
            total += float(val) * RESALE_FAZENDA_RATIO
        except Exception:
            pass

    # Equipamentos
    equipamentos = state.get("meus_equipamentos", []) or []
    for m in equipamentos:
        val = m.get("preco", m.get("valor", 0)) or 0
        try:
            total += float(val) * RESALE_EQUIP_RATIO
        except Exception:
            pass

    # Estoque
    estoque = state.get("estoque", []) or []
    for lote in estoque:
        kg = float(lote.get("quantidade_kg", 0) or 0)
        custo_kg = lote.get("custo_producao_por_kg", lote.get("custo_medio_por_kg", 0)) or 0
        try:
            total += kg * float(custo_kg)
        except Exception:
            pass

    return float(total)


def _no_means_of_recovery(state: Dict[str, Any]) -> bool:
    """Retorna True se o jogador não tem meios óbvios de recuperação.

    Regras (seguras):
    - sem fazendas (`fazendas` vazio) OR
    - não há plantações PRONTAS em nenhuma fazenda E não há estoque vendável
    """
    fazendas = state.get("fazendas", [])
    if not fazendas:
        return True

    # Considerar apenas plantações que já estão prontas para colheita como
    # meios imediatos de recuperação. Plantações em crescimento não são
    # contadas aqui (são futuras possibilidades, não recuperação imediata).
    plantacoes_por_fazenda = state.get("plantacoes_por_fazenda", {})
    has_prontas = any(
        any(p.get("estado") == "PRONTA" for p in lista)
        for lista in plantacoes_por_fazenda.values()
    )

    estoque = state.get("estoque", [])
    has_estoque_vendavel = any((lote.get("quantidade_kg", 0) or 0) > 0 for lote in estoque)

    if not has_prontas and not has_estoque_vendavel:
        return True

    return False


def check_loss(campaign_state: Dict[str, int], state: Dict[str, Any]) -> (bool, str):
    """Avalia se a campanha está perdida considerando campanha e estado do jogo.

    Retorna tupla (lost: bool, reason: str).
    """
    # 1) semanas negativas consecutivas >= 4
    if int(campaign_state.get("weeks_negative_cash_consecutive", 0)) >= 4:
        # verificar meios de recuperação — somente declarar derrota se não houver meios
        if _no_means_of_recovery(state):
            return True, "Saldo negativo por várias semanas e sem meios de recuperação."
        # se houver meios óbvios de recuperação (estoque pronto ou plantações PRONTAS), não declarar perda automática
        return False, ""

    # 2) sem meios de recuperação imediatos + dinheiro negativo
    if state.get("dinheiro", 0) < 0 and _no_means_of_recovery(state):
        return True, "Dinheiro negativo e sem recursos/estoque para recuperação."

    return False, ""
