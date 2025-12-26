# tools/smoke_default.py
from __future__ import annotations

import sys
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from systems.finance import processar_emprestimos_semanal


def semana_atual_from_dia(dia: int) -> int:
    return dia // 7


def _apply_default_side_effects_no_ui(state: dict, default_info: dict) -> None:
    """
    default_info: item de 'emprestimos_em_default', com chaves:
      - banco
      - garantia (pode ser None)
      - emprestimo (dict)
      - valor_devido
    """
    banco = default_info.get("banco")
    garantia = default_info.get("garantia")

    # Sem garantia
    if not garantia or garantia.get("tipo") == "nenhuma":
        state.setdefault("logs", []).append(f"DEFAULT: reputação afetada por não pagar {banco}")
        return

    # Perde fazenda
    if garantia["tipo"] == "fazenda":
        id_fazenda = garantia["id"]
        state["fazendas"] = [f for f in state.get("fazendas", []) if f.get("id") != id_fazenda]

        plantacoes = state.get("plantacoes_por_fazenda", {})
        if id_fazenda in plantacoes:
            del plantacoes[id_fazenda]
        state["plantacoes_por_fazenda"] = plantacoes

        state.setdefault("logs", []).append(f"DEFAULT: perdeu fazenda {id_fazenda} no {banco}")
        return

    # Perde máquinas
    if garantia["tipo"] == "maquinas":
        state["meus_equipamentos"] = []
        state.setdefault("logs", []).append(f"DEFAULT: perdeu equipamentos no {banco}")
        return

    state.setdefault("logs", []).append(f"DEFAULT: garantia desconhecida {garantia}")


def _make_base_state() -> dict:
    return {
        "dia": 7 * 10,  # dia inicial (semana 10)
        "dinheiro": 100_000.0,
        "nivel": 1,
        "fazendas": [
            {"id": "faz1", "nome": "Fazenda 1", "nome_personalizado": "Faz 1", "tam": 10},
            {"id": "faz2", "nome": "Fazenda 2", "nome_personalizado": "Faz 2", "tam": 20},
        ],
        "plantacoes_por_fazenda": {
            "faz1": [{"nome": "Soja", "estado": "Crescendo"}],
            "faz2": [{"nome": "Milho", "estado": "Crescendo"}],
        },
        "meus_equipamentos": [
            {"nome": "Trator", "funcao": "Produtividade"},
            {"nome": "Silo", "funcao": "Armazenagem"},
        ],
        "emprestimos_ativos": [],
        "logs": [],
    }


def _process_week(state: dict) -> int:
    """
    Avança 1 semana (dia += 7), processa empréstimos via systems.finance,
    aplica "efeitos colaterais" do default no state (sem UI).
    Retorna quantidade de defaults ocorridos na semana.
    """
    state["dia"] += 7
    semana = semana_atual_from_dia(state["dia"])

    result = processar_emprestimos_semanal(state["emprestimos_ativos"], semana)

    # Atualiza lista de empréstimos ativos
    state["emprestimos_ativos"] = result["emprestimos_atualizados"]

    # Aplica defaults (efeitos colaterais simulados)
    defaults = result["emprestimos_em_default"]
    for d in defaults:
        _apply_default_side_effects_no_ui(state, d)

    return len(defaults)


def _run_case(case_name: str, state: dict, max_steps: int = 5) -> None:
    print(f"\n=== CASE: {case_name} ===")
    for step in range(1, max_steps + 1):
        defaults = _process_week(state)
        semana = semana_atual_from_dia(state["dia"])
        print(f"step={step} semana={semana} ativos={len(state['emprestimos_ativos'])} defaults={defaults}")
        if not state["emprestimos_ativos"]:
            break


def main() -> int:
    # Caso 1: garantia fazenda (prazo 1 semana => entra em default na próxima semana)
    st1 = _make_base_state()
    s_ini = semana_atual_from_dia(st1["dia"])
    st1["emprestimos_ativos"] = [
        {
            "id": "emp_fazenda",
            "banco": "Banco Agro",
            "valor_devido": 10_000.0,
            "juros_semana": 0.02 / 4,
            "semana_inicio": s_ini,
            "prazo_semanas": 1,
            "garantia": {"tipo": "fazenda", "id": "faz1"},
            "garantia_desc": "Fazenda Faz 1",
        }
    ]
    _run_case("garantia_fazenda", st1)
    assert all(f["id"] != "faz1" for f in st1["fazendas"]), "faz1 deveria ter sido removida no default"
    assert "faz1" not in st1["plantacoes_por_fazenda"], "plantacoes de faz1 deveriam ter sido removidas"
    assert len(st1["emprestimos_ativos"]) == 0, "empréstimo deveria ter sido removido (default)"

    # Caso 2: garantia maquinas
    st2 = _make_base_state()
    s_ini = semana_atual_from_dia(st2["dia"])
    st2["emprestimos_ativos"] = [
        {
            "id": "emp_maquinas",
            "banco": "Fintech Rural",
            "valor_devido": 8_000.0,
            "juros_semana": 0.12 / 4,
            "semana_inicio": s_ini,
            "prazo_semanas": 1,
            "garantia": {"tipo": "maquinas"},
            "garantia_desc": "Todos equipamentos",
        }
    ]
    _run_case("garantia_maquinas", st2)
    assert len(st2["meus_equipamentos"]) == 0, "equipamentos deveriam ter sido removidos no default"
    assert len(st2["emprestimos_ativos"]) == 0, "empréstimo deveria ter sido removido (default)"

    # Caso 3: sem garantia
    st3 = _make_base_state()
    s_ini = semana_atual_from_dia(st3["dia"])
    st3["emprestimos_ativos"] = [
        {
            "id": "emp_sem_garantia",
            "banco": "Banco Popular",
            "valor_devido": 5_000.0,
            "juros_semana": 0.05 / 4,
            "semana_inicio": s_ini,
            "prazo_semanas": 1,
            "garantia": None,
            "garantia_desc": "Nenhuma",
        }
    ]
    fazendas_antes = deepcopy(st3["fazendas"])
    equips_antes = deepcopy(st3["meus_equipamentos"])
    _run_case("sem_garantia", st3)
    assert st3["fazendas"] == fazendas_antes, "sem garantia não deve remover fazendas"
    assert st3["meus_equipamentos"] == equips_antes, "sem garantia não deve remover equipamentos"
    assert len(st3["emprestimos_ativos"]) == 0, "empréstimo deveria ter sido removido (default)"

    print("\nOK: smoke_default passou.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
