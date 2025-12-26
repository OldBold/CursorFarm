def calcular_juros_semanal(valor_devido, juros_semana):
    """
    Calcula o valor dos juros semanais sobre o valor devido.
    Retorna: float
    """
    return valor_devido * juros_semana


def aplicar_juros_semanal(emprestimo):
    """
    Aplica juros semanais ao empréstimo (modifica emprestimo["valor_devido"] in-place).
    """
    juros_da_semana = calcular_juros_semanal(emprestimo["valor_devido"], emprestimo["juros_semana"])
    emprestimo["valor_devido"] += juros_da_semana


def calcular_semanas_restantes(emprestimo, semana_atual):
    """
    Calcula quantas semanas restam até o prazo final do empréstimo.
    Retorna: int
    """
    prazo_final = emprestimo["semana_inicio"] + emprestimo["prazo_semanas"]
    return prazo_final - semana_atual


def verificar_default(emprestimo, semana_atual):
    """
    Verifica se o empréstimo está em default (vencido).
    Retorna: bool
    """
    prazo_final = emprestimo["semana_inicio"] + emprestimo["prazo_semanas"]
    return semana_atual >= prazo_final


def calcular_valor_pagamento_max(valor_pago, valor_devido):
    """
    Limita o valor a ser pago ao valor devido (clamp).
    Retorna: float
    """
    return min(valor_pago, valor_devido)


def processar_pagamento(emprestimo, valor_pago):
    """
    Processa um pagamento no empréstimo.
    Retorna: (quitado: bool, novo_valor_devido: float)
    """
    novo_valor_devido = emprestimo["valor_devido"] - valor_pago
    quitado = novo_valor_devido < 0.01
    emprestimo["valor_devido"] = novo_valor_devido if novo_valor_devido >= 0 else 0.0
    return (quitado, emprestimo["valor_devido"])


def processar_emprestimos_semanal(emprestimos_ativos, semana_atual):
    """
    Processa empréstimos semanalmente: aplica juros e identifica defaults.
    Retorna: dict com:
        - emprestimos_atualizados: list[dict] (emprestimos com juros aplicados)
        - emprestimos_em_default: list[dict] (emprestimos que entraram em default, com info para logs)
        - emprestimos_a_remover: list[dict] (emprestimos em default que devem ser removidos)
    """
    emprestimos_atualizados = []
    emprestimos_em_default = []
    emprestimos_a_remover = []
    
    for emp in emprestimos_ativos:
        # Aplica juros
        aplicar_juros_semanal(emp)
        
        # Verifica default
        if verificar_default(emp, semana_atual):
            emprestimos_a_remover.append(emp)
            emprestimos_em_default.append({
                "emprestimo": emp,
                "valor_devido": emp["valor_devido"],
                "banco": emp["banco"],
                "garantia": emp.get("garantia")
            })
        else:
            emprestimos_atualizados.append(emp)
    
    return {
        "emprestimos_atualizados": emprestimos_atualizados,
        "emprestimos_em_default": emprestimos_em_default,
        "emprestimos_a_remover": emprestimos_a_remover
    }

