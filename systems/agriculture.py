from systems.economy import producao_kg, custo_medio_por_kg


def validar_plantio(nivel, dinheiro, fazenda, plantacao_atual, culturas_selecionadas):
    """
    Valida se o plantio pode ser realizado.
    Retorna: (ok: bool, erro_msg: str, custo_total: float, novas_plantas_dados: list)
    """
    custo_total = 0
    novas_plantas_dados = []
    
    for dados in culturas_selecionadas:
        if nivel < dados["nivel_req"]:
            return (False, f"A cultura '{dados['nome']}' exige Nível {dados['nivel_req']}.", 0, [])
        custo_total += dados["custo_semente"]
        novas_plantas_dados.append(dados)
    
    # Verificar espaço
    livre = fazenda["tam"] - len(plantacao_atual)
    if len(novas_plantas_dados) > livre:
        nome_fazenda = fazenda.get("nome_personalizado", fazenda["nome"])
        return (False, f"Espaço insuficiente na fazenda '{nome_fazenda}'.\nEspaço livre: {livre} ha.", 0, [])
    
    # Verificar dinheiro
    if dinheiro < custo_total:
        return (False, f"Dinheiro insuficiente. Custo do plantio: R$ {custo_total:,.2f}", 0, [])
    
    return (True, "", custo_total, novas_plantas_dados)


def criar_plantacoes(novas_plantas_dados, solo_fazenda):
    """
    Cria os dicts de plantação com campos idênticos aos atuais.
    Retorna: list[dict]
    """
    novas_plantacoes = []
    for p_dados in novas_plantas_dados:
        compativel = (p_dados["solo_ideal"] == "Qualquer" or p_dados["solo_ideal"] == solo_fazenda)
        novas_plantacoes.append({
            "nome": p_dados["nome"],
            "dias_rest": p_dados["dias_totais"],
            "total": p_dados["dias_totais"],
            "compativel": compativel,
            "dados_base": p_dados,
            "estado": "Crescendo"
        })
    return novas_plantacoes


def colheita_lotes(plantacao_alvo, indices_prontas, bonus_prod):
    """
    Calcula produção e custo/kg para plantações prontas.
    Retorna: (lotes: list[dict], indices_para_remover: list[int])
    """
    lotes_a_colher = []
    indices_para_remover = []
    
    for idx in indices_prontas:
        if idx < len(plantacao_alvo):
            p = plantacao_alvo[idx]
            if p.get("estado") == "PRONTA":
                # Calcula produção
                kg_produzido = producao_kg(p["dados_base"]["kg_hectare"], bonus_prod, p["compativel"])
                
                # Calcula custo de produção por kg
                # Usando o custo da semente como base para o custo de produção do lote.
                custo_total_lote = p["dados_base"]["custo_semente"]
                custo_por_kg = custo_medio_por_kg(custo_total_lote, kg_produzido)
                
                lotes_a_colher.append({
                    "dados_base": p["dados_base"],
                    "quantidade_kg": kg_produzido,
                    "custo_producao_por_kg": custo_por_kg,
                    "compativel": p.get("compativel", True)
                })
                indices_para_remover.append(idx)
    
    return (lotes_a_colher, indices_para_remover)


def agrupar_colheita(lotes):
    """
    Agrupa lotes em um único (simplificação do colher atual).
    Retorna: (cultura_base: dict, total_kg: float, custo_medio_kg: float, nome_cultura: str, tipo_armazenagem: str)
    """
    if not lotes:
        return (None, 0, 0, "", "")
    
    # Agrupa todos os lotes em um só (simplificação)
    primeiro_lote = lotes[0]
    cultura_base = primeiro_lote["dados_base"]
    nome_cultura = cultura_base["nome"]
    tipo_armazenagem = cultura_base["tipo_armazenagem"]
    
    total_kg_colhido = sum(lote["quantidade_kg"] for lote in lotes)
    # Média ponderada do custo
    custo_total_colheita = sum(lote["quantidade_kg"] * lote["custo_producao_por_kg"] for lote in lotes)
    custo_medio_por_kg_val = custo_medio_por_kg(custo_total_colheita, total_kg_colhido)
    
    return (cultura_base, total_kg_colhido, custo_medio_por_kg_val, nome_cultura, tipo_armazenagem)

