# tools/smoke_default.py
from __future__ import annotations

import os
import sys
import json
import math
import random
from datetime import datetime
from typing import Any, Dict, List, Tuple

# Garantir que a raiz do projeto esteja no sys.path (para importar "systems")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _ensure_dirs() -> None:
    os.makedirs("logs", exist_ok=True)


def _is_finite_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def _assert(condition: bool, msg: str) -> None:
    if not condition:
        raise AssertionError(msg)


def _default_state(seed: int = 123) -> Dict[str, Any]:
    """
    Estado mínimo para rodar avancar_semana() sem UI.
    Ajuste somente se seu time_engine exigir novas chaves.
    """
    rng = random.Random(seed)

    fazendas = [
        {"id": 1, "nome": "Sítio Inicial", "nome_personalizado": "Sítio Inicial", "tam": 10, "tem_gerente": False},
    ]

    plantacoes_por_fazenda = {
        1: [
            {
                "nome": "Trigo",
                "estado": "Crescendo",
                "dias_rest": 14.0,
                "compativel": True,
            }
        ]
    }

    return {
        "dia": 1,
        "nivel": 1,
        "dinheiro": 50_000.0,
        "clima": "Ameno",
        "fazendas": fazendas,
        "plantacoes_por_fazenda": plantacoes_por_fazenda,
        "meus_equipamentos": [],
        "mercado_multiplicadores": {},
        "salarios_gerente": {10: 4000, 20: 7000, 50: 12000},
        "opcoes_base_fazenda": [
            {"tipo": "Sítio", "tam": 10, "custo_base": 20000},
            {"tipo": "Fazenda", "tam": 20, "custo_base": 30000},
            {"tipo": "Latifúndio", "tam": 50, "custo_base": 50000},
        ],
        "tipos_de_solo": ["Arenoso", "Argiloso", "Alagado", "Pedregoso"],
        "propriedades_a_venda": [],
        "emprestimos_ativos": [],
        "seguro_agricola_ativo": False,
        "rng_seed": seed,
        "eventos": [],
        "alertas": [],
        "_smoke_rng_sample": rng.random(),
    }


def _validate_state(state: Dict[str, Any], week: int) -> List[str]:
    warnings: List[str] = []

    _assert("dinheiro" in state, f"[W{week}] state sem 'dinheiro'")
    _assert(_is_finite_number(state["dinheiro"]), f"[W{week}] dinheiro inválido: {state.get('dinheiro')}")

    _assert("dia" in state, f"[W{week}] state sem 'dia'")
    _assert(_is_finite_number(state["dia"]), f"[W{week}] dia inválido: {state.get('dia')}")
    _assert(state["dia"] >= 0, f"[W{week}] dia negativo: {state['dia']}")

    fazendas = state.get("fazendas", [])
    _assert(isinstance(fazendas, list), f"[W{week}] fazendas não é list")
    for f in fazendas:
        _assert(isinstance(f, dict), f"[W{week}] fazenda não é dict: {f}")
        _assert("id" in f and "tam" in f, f"[W{week}] fazenda sem id/tam: {f}")
        _assert(_is_finite_number(f["tam"]) and f["tam"] >= 0, f"[W{week}] tam inválido: {f}")

    ppf = state.get("plantacoes_por_fazenda", {})
    _assert(isinstance(ppf, dict), f"[W{week}] plantacoes_por_fazenda não é dict")
    for fid, lista in ppf.items():
        if not isinstance(lista, list):
            warnings.append(f"[W{week}] plantacoes_por_fazenda[{fid}] não é list")
            continue
        for p in lista:
            if not isinstance(p, dict):
                warnings.append(f"[W{week}] plantacao inválida (não dict) em fazenda {fid}: {p}")
                continue
            if "dias_rest" in p and not _is_finite_number(p["dias_rest"]):
                warnings.append(f"[W{week}] dias_rest inválido em fazenda {fid}: {p.get('dias_rest')}")

    ev = state.get("eventos", [])
    al = state.get("alertas", [])
    if not isinstance(ev, list):
        warnings.append(f"[W{week}] eventos não é list")
    if not isinstance(al, list):
        warnings.append(f"[W{week}] alertas não é list")

    return warnings


def run(weeks: int = 52, seed: int = 123) -> Tuple[Dict[str, Any], List[str], List[str]]:
    from systems.time_engine import avancar_semana

    state = _default_state(seed=seed)
    warnings: List[str] = []
    trace: List[str] = []

    for w in range(1, weeks + 1):
        warnings.extend(_validate_state(state, w))
        state = avancar_semana(state, dias_avancados=7)

        semana_num = int(state.get("dia", 0) / 7)
        dinheiro = state.get("dinheiro", None)
        clima = state.get("clima", "")
        prontas = 0
        for lista in state.get("plantacoes_por_fazenda", {}).values():
            for p in lista:
                if isinstance(p, dict) and p.get("estado") == "PRONTA":
                    prontas += 1

        trace.append(f"W{w:03d} | semana={semana_num:03d} | dinheiro={dinheiro} | clima={clima} | prontas={prontas}")

    warnings.extend(_validate_state(state, weeks))
    return state, warnings, trace


def main() -> int:
    _ensure_dirs()
    weeks = 52
    seed = 123

    if len(sys.argv) >= 2:
        try:
            weeks = int(sys.argv[1])
        except ValueError:
            pass
    if len(sys.argv) >= 3:
        try:
            seed = int(sys.argv[2])
        except ValueError:
            pass

    started = datetime.now()
    report_path = os.path.join("logs", "smoke_report.txt")

    try:
        final_state, warnings, trace = run(weeks=weeks, seed=seed)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("SMOKE DEFAULT REPORT\n")
            f.write(f"started: {started.isoformat()}\n")
            f.write(f"weeks: {weeks}\n")
            f.write(f"seed: {seed}\n")
            f.write(f"project_root: {PROJECT_ROOT}\n")
            f.write("\n--- TRACE (last 25) ---\n")
            for line in trace[-25:]:
                f.write(line + "\n")

            f.write("\n--- WARNINGS ---\n")
            if warnings:
                for w in warnings[:200]:
                    f.write(w + "\n")
                if len(warnings) > 200:
                    f.write(f"... ({len(warnings) - 200} warnings omitted)\n")
            else:
                f.write("none\n")

            f.write("\n--- FINAL STATE (keys) ---\n")
            f.write(", ".join(sorted(final_state.keys())) + "\n")

            f.write("\n--- FINAL STATE (subset) ---\n")
            subset = {k: final_state.get(k) for k in ["dia", "nivel", "dinheiro", "clima"]}
            f.write(json.dumps(subset, ensure_ascii=False, indent=2) + "\n")

        print(f"[OK] smoke_default finalizado. Relatório em: {report_path}")
        return 0

    except Exception as e:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("SMOKE DEFAULT REPORT - FAILED\n")
            f.write(f"started: {started.isoformat()}\n")
            f.write(f"weeks: {weeks}\n")
            f.write(f"seed: {seed}\n")
            f.write(f"project_root: {PROJECT_ROOT}\n")
            f.write("\n--- ERROR ---\n")
            f.write(repr(e) + "\n")

        print(f"[FAIL] smoke_default falhou. Veja: {report_path}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
