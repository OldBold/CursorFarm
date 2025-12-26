def salario_gerente(salarios_gerente, tam_fazenda):
    """
    Retorna o salário do gerente baseado no tamanho da fazenda.
    """
    return salarios_gerente.get(tam_fazenda, 0)


def deve_pagar_salario(semana_atual):
    """
    Verifica se deve pagar salário nesta semana (a cada 4 semanas).
    Retorna: bool
    """
    return semana_atual > 0 and semana_atual % 4 == 0


def processar_pagamento_salario(dinheiro, salario):
    """
    Processa o pagamento do salário.
    Retorna: (novo_dinheiro: float, pagou_bool: bool)
    """
    if dinheiro >= salario:
        return (dinheiro - salario, True)
    return (dinheiro, False)


def selecionar_culturas_disponiveis(culturas_catalogo, nivel, solo_fazenda):
    """
    Filtra culturas disponíveis baseado em nível e solo.
    Retorna: list[dict]
    """
    return [
        c for c in culturas_catalogo 
        if nivel >= c["nivel_req"] and (c["solo_ideal"] == solo_fazenda or c["solo_ideal"] == "Qualquer")
    ]


def escolher_cultura_para_plantar(culturas_disponiveis, dinheiro_disponivel, custo_acumulado, cultura_foco_nome):
    """
    Escolhe a melhor cultura para plantar baseado na estratégia do gerente.
    Se cultura_foco_nome != "Automatica", só tenta essa cultura.
    Senão, escolhe a cultura de maior nível que consegue pagar.
    Retorna: cultura dict ou None
    """
    if cultura_foco_nome != "Automatica":
        # Modo foco: só planta a cultura definida
        cultura_foco_obj = next((c for c in culturas_disponiveis if c["nome"] == cultura_foco_nome), None)
        if cultura_foco_obj and dinheiro_disponivel >= custo_acumulado + cultura_foco_obj["custo_semente"]:
            return cultura_foco_obj
        return None
    
    # Modo automático: escolhe a melhor que pode pagar (maior nível primeiro)
    culturas_ordenadas = sorted(culturas_disponiveis, key=lambda c: c["nivel_req"], reverse=True)
    for cultura in culturas_ordenadas:
        if dinheiro_disponivel >= custo_acumulado + cultura["custo_semente"]:
            return cultura
    
    return None

