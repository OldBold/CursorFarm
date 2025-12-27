import random
from systems.market import atualizar_multiplicadores
from systems.campaign import init_campaign_state, update_campaign


def _get_bonus_velocidade(meus_equipamentos):
    total = 0.0
    for m in meus_equipamentos:
        if m.get("funcao") == "Velocidade" and m.get("funcao") != "Armazenagem":
            total += m.get("valor_bonus", 0.0)
    return min(total, 3.0)


def avancar_semana(state, dias_avancados=7):
    # Se campanha já perdida ou vencida, bloquear avanço temporal
    if state.get("campaign", {}).get("status") in ("LOST", "WON"):
        return state

    state["dia"] = state.get("dia", 0) + dias_avancados
    semana = int(state["dia"] / 7)
    
    eventos = []
    alertas = []
    
    # Atualizar multiplicadores do mercado
    if dias_avancados > 0:
        state["mercado_multiplicadores"] = atualizar_multiplicadores(state.get("mercado_multiplicadores", {}))
    
    # Mudar clima
    climas = ["Sol", "Chuva", "Nublado"]
    if random.random() < 0.1:
        state["clima"] = "Seca Extrema"
    else:
        state["clima"] = random.choice(climas)
    
    # Calcular custos
    nivel = state.get("nivel", 1)
    fazendas = state.get("fazendas", [])
    meus_equipamentos = state.get("meus_equipamentos", [])
    dinheiro = state.get("dinheiro", 0.0)
    
    custo_terra = sum(f["tam"] * (20 * nivel) for f in fazendas)
    custo_maq = sum(m.get("manutencao", 0) for m in meus_equipamentos) * dias_avancados
    total_custo = custo_terra + custo_maq
    state["dinheiro"] = dinheiro - total_custo
    
    if total_custo > 0:
        eventos.append(f"Custos semanais: -R$ {total_custo:,.2f} (Terras: R$ {custo_terra:,.2f}, Maquinário: R$ {custo_maq:,.2f})")
    # Registrar custos para estatísticas
    try:
        from systems.stats import record_costs
        record_costs(state, total_custo)
    except Exception:
        pass
    
    # Calcular crescimento efetivo
    bonus_vel = _get_bonus_velocidade(meus_equipamentos)
    crescimento_efetivo = dias_avancados * (1 + bonus_vel)
    
    if state["clima"] == "Sol":
        crescimento_efetivo *= 1.1
    if state["clima"] == "Seca Extrema":
        crescimento_efetivo *= 0.2
        
        # Lógica de perda de plantação por seca
        if random.random() < 0.10:  # 10% de chance de evento de perda
            seguro_agricola_ativo = state.get("seguro_agricola_ativo", False)
            
            if seguro_agricola_ativo:
                msg = "Seu seguro agrícola protegeu uma plantação da destruição pela seca!"
                alertas.append({"tipo": "info", "titulo": "Seguro Ativado", "mensagem": msg})
                eventos.append(f"SEGURO: {msg}")
            else:
                plantacoes_por_fazenda = state.get("plantacoes_por_fazenda", {})
                fazendas_com_plantacao = [id_fazenda for id_fazenda, lista in plantacoes_por_fazenda.items() if lista]
                if fazendas_com_plantacao:
                    id_fazenda_vitima = random.choice(fazendas_com_plantacao)
                    
                    # Escolhe e remove uma plantação aleatória da fazenda vítima
                    indice_vitima = random.randrange(len(plantacoes_por_fazenda[id_fazenda_vitima]))
                    cultura_perdida = plantacoes_por_fazenda[id_fazenda_vitima].pop(indice_vitima)
                    
                    # Pega o nome da fazenda para o log
                    fazenda_obj = next((f for f in fazendas if f["id"] == id_fazenda_vitima), None)
                    nome_fazenda = fazenda_obj.get("nome_personalizado", fazenda_obj["nome"]) if fazenda_obj else "Fazenda Desconhecida"
                    
                    msg = f"A seca extrema destruiu 1 ha de '{cultura_perdida['nome']}' na fazenda '{nome_fazenda}'!"
                    alertas.append({"tipo": "warning", "titulo": "DESASTRE CLIMÁTICO", "mensagem": msg})
                    eventos.append(f"DESASTRE: {msg}")
                    # registrar evento crítico nas estatísticas
                    try:
                        from systems.stats import record_critical_event
                        record_critical_event(state, "Seca Extrema")
                    except Exception:
                        pass
    
    # Atualizar plantações
    plantas_prontas = 0
    plantacoes_por_fazenda = state.get("plantacoes_por_fazenda", {})
    for plantacao in plantacoes_por_fazenda.values():
        for p in plantacao:
            if p.get("estado") == "Crescendo":
                crescimento_real = crescimento_efetivo
                if not p.get("compativel", True):
                    crescimento_real *= 0.5
                
                p["dias_rest"] -= crescimento_real
                if p["dias_rest"] <= 0:
                    p["estado"] = "PRONTA"
                    plantas_prontas += 1
    
    # Processar salários de gerentes (não chama gerente_colher/gerente_plantar aqui)
    from systems.manager import salario_gerente, deve_pagar_salario, processar_pagamento_salario
    salarios_gerente = state.get("salarios_gerente", {})
    for fazenda in fazendas:
        if fazenda.get("tem_gerente"):
            if deve_pagar_salario(semana):
                salario = salario_gerente(salarios_gerente, fazenda["tam"])
                novo_dinheiro, pagou = processar_pagamento_salario(state["dinheiro"], salario)
                state["dinheiro"] = novo_dinheiro
                if pagou:
                    eventos.append(f"Pagou R$ {salario:,.2f} de salário ao gerente de '{fazenda.get('nome_personalizado', fazenda['nome'])}'.")
                else:
                    eventos.append(f"AVISO: Dinheiro insuficiente para pagar o gerente de '{fazenda.get('nome_personalizado', fazenda['nome'])}'. O gerente pode sair!")
    
    # Atualizar propriedades a venda
    if semana > 0 and semana % 12 == 0:
        semana_anterior = int((state["dia"] - dias_avancados) / 7)
        if semana_anterior < semana:
            from systems.properties import gerar_propriedades_a_venda
            opcoes_base_fazenda = state.get("opcoes_base_fazenda", [])
            tipos_de_solo = state.get("tipos_de_solo", [])
            state["propriedades_a_venda"] = gerar_propriedades_a_venda(state["dia"], opcoes_base_fazenda, tipos_de_solo)
            eventos.append("Novas propriedades disponíveis na imobiliária!")
    
    if plantas_prontas > 0:
        eventos.append(f"Semana {semana}: {plantas_prontas} ha de plantações prontas para colher!")
    
    # Inicializar/Atualizar estado de campanha (weeks_played, weeks_negative_cash_consecutive)
    if "campaign" not in state:
        state["campaign"] = init_campaign_state()
    campaign_state = update_campaign(state, dias_avancados)
    state["campaign"] = campaign_state
    # Expor campos de campanha no topo do estado para acesso rápido
    state["weeks_played"] = campaign_state.get("weeks_played", 0)
    state["weeks_negative_cash_consecutive"] = campaign_state.get("weeks_negative_cash_consecutive", 0)

    # Inicializar lista de conquistas desbloqueadas
    if "unlocked_achievements" not in state:
        state["unlocked_achievements"] = []

    # Checagem de conquistas semanais
    try:
        from systems.achievements import check_weekly_achievements, achievement_message
        newly = check_weekly_achievements(state)
        if newly:
            existing = set(state.get("unlocked_achievements", []) or [])
            unique_new = [n for n in newly if n not in existing]
            if unique_new:
                state["unlocked_achievements"].extend(unique_new)
                for aid in unique_new:
                    eventos.append(achievement_message(aid))
    except Exception:
        # evitar falha de tempo por problema nas conquistas
        pass

    # Finaliza métricas semanais (aplica acumuladores de receita/custo)
    try:
        from systems.stats import week_finalize
        week_finalize(state)
    except Exception:
        pass

    # Se detectamos perda, registrar evento e bloquear próximos avanços
    if campaign_state.get("status") in ("LOST", "WON"):
        status = campaign_state.get("status")
        if not state.get("game_over_logged"):
            if status == "LOST":
                reason = campaign_state.get("lost_reason", "Derrota na campanha.")
                msg = f"GAME OVER: {reason}"
                eventos.append(msg)
                alertas.append({"tipo": "error", "titulo": "GAME OVER", "mensagem": reason})
            else:
                reason = campaign_state.get("won_reason", "Vitória na campanha.")
                msg = f"VITÓRIA DA CAMPANHA: {reason}"
                eventos.append(msg)
                alertas.append({"tipo": "info", "titulo": "VITÓRIA", "mensagem": reason})

            state["game_over_logged"] = True
        # não permitir que o loop continue nas próximas chamadas
        state["eventos"] = eventos
        state["alertas"] = alertas
        return state

    state["eventos"] = eventos
    state["alertas"] = alertas
    return state

