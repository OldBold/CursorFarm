def preco_mercado_atual(preco_base, multiplicador):
    return preco_base * multiplicador


def margem_percentual(preco_venda_kg, custo_por_kg):
    if custo_por_kg == 0:
        return 0
    return ((preco_venda_kg / custo_por_kg) - 1) * 100


def producao_kg(kg_hectare, bonus_prod, compativel):
    kg = kg_hectare
    if not compativel:
        kg *= 0.6
    kg *= (1 + bonus_prod)
    return kg


def custo_medio_por_kg(custo_total, total_kg):
    if total_kg == 0:
        return 0
    return custo_total / total_kg

