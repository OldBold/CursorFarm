"""
data/catalogs.py

Catálogos em memória para o jogo (substitui os CSVs).

Schema esperado para culturas (cada dict):
- nome: str
- preco_venda: float
- kg_hectare: float
- dias_totais: int
- solo_ideal: str
- nivel_req: int
- custo_semente: float
- tipo_armazenagem: str ("Silo" ou "Armazém")
- tipo_cultura: str

Schema esperado para máquinas (cada dict):
- nome: str
- funcao: str
- preco: float
- manutencao: float
- nivel_req: int
- nome_base: str
- valor_bonus: float
- capacidade: int

Este módulo expõe as constantes:
- CULTURAS_CATALOGO: list[dict]
- MAQUINAS_CATALOGO: list[dict]

Notas:
- Os valores finais (preço, custo) são construídos usando a mesma lógica
  presente no monolito original para manter compatibilidade e balanceamento.
"""

from copy import deepcopy

# Dados-base correspondentes aos CSVs originais.
# Cada entrada de cultura contém os campos mínimos necessários para gerar o catálogo.
CULTURAS_BASE = [
    {"Tipo": "Cereais", "NomePlanta": "Trigo", "Nivel": 1, "TempoColheita1": 5, "KgAnoHectar": 1000, "Solo": "Arenoso"},
    {"Tipo": "Leguminosas", "NomePlanta": "Soja", "Nivel": 1, "TempoColheita1": 5, "KgAnoHectar": 1000, "Solo": "Argiloso"},
    {"Tipo": "Leguminosas", "NomePlanta": "Feijão", "Nivel": 1, "TempoColheita1": 3, "KgAnoHectar": 1000, "Solo": "Arenoso"},
    {"Tipo": "Cereais", "NomePlanta": "Arroz", "Nivel": 1, "TempoColheita1": 5, "KgAnoHectar": 1000, "Solo": "Alagado"},
    {"Tipo": "Cereais", "NomePlanta": "Milho", "Nivel": 1, "TempoColheita1": 5, "KgAnoHectar": 1000, "Solo": "Arenoso"},
    {"Tipo": "Frutas", "NomePlanta": "Tomate", "Nivel": 2, "TempoColheita1": 4, "KgAnoHectar": 600, "Solo": "Arenoso"},
    {"Tipo": "Frutas", "NomePlanta": "Banana", "Nivel": 2, "TempoColheita1": 10, "KgAnoHectar": 600, "Solo": "Arenoso"},
    {"Tipo": "Frutas", "NomePlanta": "Café", "Nivel": 2, "TempoColheita1": 10, "KgAnoHectar": 600, "Solo": "Argiloso"},
    {"Tipo": "Raizes", "NomePlanta": "Batata", "Nivel": 2, "TempoColheita1": 4, "KgAnoHectar": 600, "Solo": "Arenoso"},
    {"Tipo": "Raizes", "NomePlanta": "Cebola", "Nivel": 2, "TempoColheita1": 5, "KgAnoHectar": 600, "Solo": "Arenoso"},
    {"Tipo": "Frutas", "NomePlanta": "Laranja", "Nivel": 3, "TempoColheita1": 7, "KgAnoHectar": 500, "Solo": "Arenoso"},
    {"Tipo": "Frutas", "NomePlanta": "Uva", "Nivel": 3, "TempoColheita1": 6, "KgAnoHectar": 500, "Solo": "Pedregoso"},
    {"Tipo": "Leguminosas", "NomePlanta": "Amendoim", "Nivel": 3, "TempoColheita1": 5, "KgAnoHectar": 500, "Solo": "Arenoso"},
    {"Tipo": "Frutas", "NomePlanta": "Maça", "Nivel": 3, "TempoColheita1": 7, "KgAnoHectar": 500, "Solo": "Argiloso"},
    {"Tipo": "Frutas", "NomePlanta": "Limão", "Nivel": 3, "TempoColheita1": 7, "KgAnoHectar": 500, "Solo": "Arenoso"},
    {"Tipo": "Frutas", "NomePlanta": "Morango", "Nivel": 4, "TempoColheita1": 3, "KgAnoHectar": 350, "Solo": "Arenoso"},
    {"Tipo": "Cereais", "NomePlanta": "Cevada", "Nivel": 4, "TempoColheita1": 5, "KgAnoHectar": 350, "Solo": "Arenoso"},
    {"Tipo": "Cereais", "NomePlanta": "Aveia", "Nivel": 4, "TempoColheita1": 5, "KgAnoHectar": 350, "Solo": "Argiloso"},
    {"Tipo": "Raizes", "NomePlanta": "Cenoura", "Nivel": 4, "TempoColheita1": 4, "KgAnoHectar": 350, "Solo": "Arenoso"},
    {"Tipo": "Raizes", "NomePlanta": "Beterraba", "Nivel": 4, "TempoColheita1": 4, "KgAnoHectar": 350, "Solo": "Arenoso"},
    {"Tipo": "Frutas", "NomePlanta": "Cacau", "Nivel": 5, "TempoColheita1": 20, "KgAnoHectar": 180, "Solo": "Argiloso"},
    {"Tipo": "Frutas", "NomePlanta": "Azeitona", "Nivel": 5, "TempoColheita1": 30, "KgAnoHectar": 180, "Solo": "Pedregoso"},
    {"Tipo": "Cereais", "NomePlanta": "Cana de Açucar", "Nivel": 5, "TempoColheita1": 15, "KgAnoHectar": 180, "Solo": "Argiloso"},
    {"Tipo": "Leguminosas", "NomePlanta": "Ervilha", "Nivel": 5, "TempoColheita1": 3, "KgAnoHectar": 180, "Solo": "Argiloso"},
    {"Tipo": "Arbustos", "NomePlanta": "Algodão", "Nivel": 5, "TempoColheita1": 9, "KgAnoHectar": 180, "Solo": "Arenoso"},
]

# Máquinas base correspondentes ao Implementos.csv
MAQUINAS_BASE = [
    {"nome_base": "Tratores", "funcao": "Produtividade", "nivel": 1},
    {"nome_base": "Reboque", "funcao": "Velocidade", "nivel": 1},
    {"nome_base": "Pulverizador", "funcao": "Produtividade", "nivel": 2},
    {"nome_base": "Armazém", "funcao": "Armazenagem", "nivel": 2},
    {"nome_base": "Arado", "funcao": "Produtividade", "nivel": 3},
    {"nome_base": "Silo", "funcao": "Armazenagem", "nivel": 3},
    {"nome_base": "Plantadeira", "funcao": "Produtividade", "nivel": 4},
    {"nome_base": "Colheitadeiras", "funcao": "Velocidade", "nivel": 4},
    {"nome_base": "Drones", "funcao": "Produtividade", "nivel": 5},
    {"nome_base": "Ordenhadeira", "funcao": "Produtividade", "nivel": 5},
    {"nome_base": "Irrigadores", "funcao": "Produtividade", "nivel": 5},
]


def _build_culturas_catalogo():
    FATOR_RECEITA_POR_DIA = 50
    BONUS_DIARIO_POR_RISCO = 0.001
    DIAS_BASE_RISCO = 30

    culturas = []
    for linha in CULTURAS_BASE:
        nome = linha["NomePlanta"].strip()
        kg = float(linha["KgAnoHectar"])
        meses = float(linha["TempoColheita1"])
        dias_totais = int(meses * 30)

        fator_bonus_risco = 0
        if dias_totais > DIAS_BASE_RISCO:
            dias_excedentes = dias_totais - DIAS_BASE_RISCO
            fator_bonus_risco = dias_excedentes * BONUS_DIARIO_POR_RISCO

        fator_receita_ajustado = FATOR_RECEITA_POR_DIA * (1 + fator_bonus_risco)
        receita_total_esperada = dias_totais * fator_receita_ajustado
        preco_venda_calculado = receita_total_esperada / kg if kg else 0
        custo = max(100, receita_total_esperada * 0.50)

        tipo_cultura = linha.get("Tipo", "").strip()
        if tipo_cultura in ["Cereais", "Leguminosas"]:
            tipo_armazenagem = "Silo"
        else:
            tipo_armazenagem = "Armazém"

        culturas.append({
            "nome": nome,
            "preco_venda": preco_venda_calculado,
            "kg_hectare": kg,
            "dias_totais": dias_totais,
            "solo_ideal": linha.get("Solo", "Qualquer").strip(),
            "nivel_req": int(linha.get("Nivel", 1)),
            "custo_semente": custo,
            "tipo_armazenagem": tipo_armazenagem,
            "tipo_cultura": tipo_cultura,
        })

    return culturas


def _build_maquinas_catalogo():
    tiers = [
        {"sufixo": "Padrão", "mult_preco": 1.0, "bonus": 0.10, "taxa_manut": 0.010, "capacidade": 1000 * 1000},
        {"sufixo": "Pro",    "mult_preco": 2.5, "bonus": 0.35, "taxa_manut": 0.005, "capacidade": 3000 * 1000},
        {"sufixo": "Ultra",  "mult_preco": 5.0, "bonus": 0.80, "taxa_manut": 0.002, "capacidade": 8000 * 1000}
    ]

    maquinas = []
    for base in MAQUINAS_BASE:
        nome_base = base["nome_base"]
        funcao = base.get("funcao", "Produtividade")
        nivel_base = int(base.get("nivel", 1))
        preco_base_ref = 4000 * nivel_base

        for i, tier in enumerate(tiers):
            nome_final = f"{nome_base} {tier['sufixo']}"
            preco_final = preco_base_ref * tier['mult_preco']
            manutencao_diaria = preco_final * tier['taxa_manut']

            maq_data = {
                "nome": nome_final,
                "funcao": funcao,
                "preco": preco_final,
                "manutencao": manutencao_diaria,
                "nivel_req": nivel_base + i,
                "nome_base": nome_base,
            }

            if funcao == "Armazenagem":
                maq_data["valor_bonus"] = 0
                maq_data["capacidade"] = tier["capacidade"]
            else:
                maq_data["valor_bonus"] = tier["bonus"]
                maq_data["capacidade"] = 0

            maquinas.append(maq_data)

    return maquinas


# Exportar catálogos prontos (deepcopy para evitar mutações acidentais pelo importador)
CULTURAS_CATALOGO = deepcopy(_build_culturas_catalogo())
MAQUINAS_CATALOGO = deepcopy(_build_maquinas_catalogo())

__all__ = ["CULTURAS_CATALOGO", "MAQUINAS_CATALOGO"]

# Outros dados compartilhados pelo jogo
TIPOS_DE_SOLO = ["Arenoso", "Argiloso", "Alagado", "Pedregoso"]

OPCOES_BASE_FAZENDA = [
    {"tipo": "Sítio", "tam": 10, "custo_base": 20000},
    {"tipo": "Fazenda", "tam": 20, "custo_base": 30000},
    {"tipo": "Latifúndio", "tam": 50, "custo_base": 50000},
]

SALARIOS_GERENTE = {
    10: 4000,
    20: 7000,
    50: 12000,
}

__all__ += ["TIPOS_DE_SOLO", "OPCOES_BASE_FAZENDA", "SALARIOS_GERENTE"]
