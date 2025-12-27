CATALOGS USAGE & EDITING
=========================

Este documento descreve como os catálogos de culturas e equipamentos estão armazenados
no projeto e instruções rápidas para editar/validar durante testes manuais.

Arquivos relevantes
- `data/catalogs.py` — módulo Python que contém `CULTURAS_CATALOGO` e `MAQUINAS_CATALOGO`.

Por que migramos dos CSVs
- Evita parsing de arquivos em runtime; melhora performance e previsibilidade.
- Mantemos a lógica de cálculo (preço, custo) no módulo para preservar balanceamento.

Schema esperado
- Culturas (cada item):
  - `nome` (str)
  - `preco_venda` (float)
  - `kg_hectare` (float)
  - `dias_totais` (int)
  - `solo_ideal` (str)
  - `nivel_req` (int)
  - `custo_semente` (float)
  - `tipo_armazenagem` ("Silo"|"Armazém")
  - `tipo_cultura` (str)

- Máquinas (cada item):
  - `nome` (str)
  - `funcao` (str)
  - `preco` (float)
  - `manutencao` (float)
  - `nivel_req` (int)
  - `nome_base` (str)
  - `valor_bonus` (float)
  - `capacidade` (int)

Como editar
1. Editar `data/catalogs.py` diretamente: altere `CULTURAS_BASE` ou `MAQUINAS_BASE` conforme necessário.
2. As funções internas `_build_culturas_catalogo()` e `_build_maquinas_catalogo()` geram os valores finais.
3. Após editar, rode os testes e o smoke:

    python -m unittest discover -s tests -p "test_*.py" -v
    python tools/smoke_default.py

Checklist de validação manual
- [ ] Abrir a tela principal e verificar se culturas aparecem na imobiliária.
- [ ] Abrir a garagem e verificar listagem de equipamentos (texto e bônus exibidos).
- [ ] Plantar e colher uma cultura para validar `preco_venda` e mensagens de log (ver `logs/smoke_report.txt`).
- [ ] Executar smoke test e garantir sem warnings.

Notas de compatibilidade
- Não renomeie chaves dos dicts; o resto do código (`monolito.py`, `systems/*`) depende desses nomes.
- Se for necessário restaurar CSVs, mantenha o `data_loader.py` em histórico git; a migração já está commitada.

Contato
- Se precisar que eu aplique mudanças nos catálogos, me avise e eu faço em um PR/branch separado.
