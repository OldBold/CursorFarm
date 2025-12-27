import random


def gerar_propriedades_iniciais(dia, opcoes_base_fazenda, tipos_de_solo, rng=None):
    """
    Gera lista de propriedades iniciais para escolha do jogador.
    - Apenas pequenas (Sítio) e médias (Fazenda), excluindo Latifúndio
    - Cada tipo de solo aparece pelo menos uma vez
    - Retorna exatamente 4 propriedades (uma para cada tipo de solo)
    """
    if rng is None:
        rng = random
    
    # Filtrar apenas Sítio (tam=10) e Fazenda (tam=20)
    opcoes_filtradas = [op for op in opcoes_base_fazenda if op["tam"] in [10, 20]]
    
    propriedades = []
    
    # Garantir que cada tipo de solo apareça pelo menos uma vez
    solos_embaralhados = tipos_de_solo.copy()
    rng.shuffle(solos_embaralhados)
    
    for i, solo in enumerate(solos_embaralhados):
        # Para as primeiras propriedades, garantir um de cada solo
        # Depois, escolher aleatoriamente entre Sítio e Fazenda
        base = rng.choice(opcoes_filtradas)
        
        # Lógica de custo
        custo_final = base["custo_base"]
        if solo == "Alagado":
            custo_final *= 0.90
        elif solo == "Pedregoso":
            custo_final *= 0.80
        
        propriedades.append({
            "id": f"prop_inicial_{dia}_{i}",
            "nome": f"{base['tipo']} {solo}",
            "tam": base["tam"],
            "solo": solo,
            "custo": int(custo_final)
        })
    
    # Garante que não haja nomes duplicados
    nomes_vistos = set()
    for prop in propriedades:
        nome_original = prop["nome"]
        contador = 2
        while prop["nome"] in nomes_vistos:
            prop["nome"] = f"{nome_original} {contador}"
            contador += 1
        nomes_vistos.add(prop["nome"])
    
    return propriedades


def gerar_propriedades_a_venda(dia, opcoes_base_fazenda, tipos_de_solo, rng=None):
    """
    Gera lista de propriedades à venda.
    Reproduz a lógica atual: 4-5 propriedades, ajustes de custo, deduplicação de nomes.
    """
    if rng is None:
        rng = random
    
    propriedades = []
    num_propriedades = rng.randint(4, 5)
    
    for i in range(num_propriedades):
        base = rng.choice(opcoes_base_fazenda)
        solo = rng.choice(tipos_de_solo)
        
        # Lógica de custo
        custo_final = base["custo_base"]
        if solo == "Alagado":
            custo_final *= 0.90  # Mais barato por ser mais nichado
        
        propriedades.append({
            "id": f"prop_{dia}_{i}",
            "nome": f"{base['tipo']} {solo}",
            "tam": base["tam"],
            "solo": solo,
            "custo": int(custo_final)
        })
    
    # Garante que não haja nomes duplicados, para evitar confusão na UI
    nomes_vistos = set()
    for prop in propriedades:
        if prop["nome"] in nomes_vistos:
            prop["nome"] += " II"  # Adiciona um diferenciador
        nomes_vistos.add(prop["nome"])
    
    return propriedades


def preco_venda_propriedade(custo_compra):
    """
    Calcula o preço de venda de uma propriedade (85% do custo de compra).
    """
    return custo_compra * 0.85


def pode_vender_fazenda(plantacoes_da_fazenda):
    """
    Verifica se a fazenda pode ser vendida (deve estar vazia).
    Retorna: (bool, motivo: str)
    """
    if len(plantacoes_da_fazenda) > 0:
        return (False, f"ela ainda tem {len(plantacoes_da_fazenda)} ha de plantações.\n\nColha ou aguarde o fim dos ciclos antes de vender.")
    return (True, "")


def pode_comprar_propriedade(dinheiro, custo):
    """
    Verifica se o jogador pode comprar a propriedade.
    Retorna: (bool, motivo: str)
    """
    if dinheiro < custo:
        return (False, "Dinheiro insuficiente para comprar esta propriedade.")
    return (True, "")

