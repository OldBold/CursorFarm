from systems.economy import preco_mercado_atual, margem_percentual


def calcular_capacidade_armazenagem(meus_equipamentos):
    capacidade = {"Silo": 0, "Armazém": 0}
    for m in meus_equipamentos:
        if m.get("funcao") == "Armazenagem":
            if m.get("nome_base") == "Silo":
                capacidade["Silo"] += m.get("capacidade", 0)
            elif m.get("nome_base") == "Armazém":
                capacidade["Armazém"] += m.get("capacidade", 0)
    return capacidade


def calcular_uso_capacidade(estoque, tipo_armazenagem):
    return sum(lote["quantidade_kg"] for lote in estoque if lote["dados_base"].get("tipo_armazenagem") == tipo_armazenagem)


def calcular_espaco_livre(capacidade_total, uso_atual):
    return capacidade_total - uso_atual


def processar_venda_automatica(estoque, mercado_multiplicadores, margem_alvo):
    lotes_para_vender = []
    receita_total = 0
    
    # Iterar de forma segura (de trás para frente para permitir remoção)
    i = len(estoque) - 1
    while i >= 0:
        lote = estoque[i]
        cultura_base = lote["dados_base"]
        
        mult_mercado = mercado_multiplicadores.get(cultura_base["nome"], 1.0)
        preco_mercado_atual_kg = preco_mercado_atual(cultura_base["preco_venda"], mult_mercado)
        
        margem_lucro = margem_percentual(preco_mercado_atual_kg, lote["custo_producao_por_kg"])
        
        if margem_lucro > margem_alvo:
            valor_venda = lote["quantidade_kg"] * preco_mercado_atual_kg
            receita_total += valor_venda
            
            lotes_para_vender.append({
                "indice": i,
                "descricao": f"{lote['quantidade_kg']:,.0f} kg de {cultura_base['nome']}",
                "valor": valor_venda
            })
        
        i -= 1
    
    return {
        "lotes_para_vender": lotes_para_vender,
        "receita_total": receita_total
    }

