# Plano de Modularização Incremental - Tycoon Fazenda

## Objetivo
Extrair código do arquivo monolítico `monolito.py` para módulos separados, mantendo o comportamento observável idêntico.

## Princípios
- Passos pequenos e revisáveis
- Cada passo deve manter o jogo funcionando
- Não alterar comportamento, textos, UX ou regras de jogo
- Não reformatar código existente

---

## Mapa Rápido: Ordem dos 6 Passos

| Passo | Módulo Criado | Métodos Movidos | Risco | Prioridade |
|-------|---------------|-----------------|-------|------------|
| **1** | `utils.py` | `converter_valor_br` | ⚪ Muito Baixo | ⭐⭐⭐ Alta |
| **2** | `data_loader.py` | `ler_csv_generico`, `carregar_culturas`, `carregar_maquinas` | 🟡 Baixo-Médio | ⭐⭐⭐ Alta |
| **3** | `business_logic.py` | `get_bonus_acumulado`, `atualizar_capacidade_armazenagem`, `get_salario_gerente`, `ganhar_xp` | 🟡 Baixo-Médio | ⭐⭐ Média |
| **4** | `time_processor.py` | `passar_dia`, `_processar_emprestimos`, `processar_vendas_automaticas`, `gerar_novas_propriedades_a_venda` | 🟠 Médio | ⭐⭐ Média |
| **5** | 6 módulos de domínio | Agricultura, Equipamentos, Propriedades, Estoque, Gerentes, Finanças | 🟠 Médio-Alto | ⭐ Baixa |
| **6** | `time_control.py` | `alterar_velocidade`, `loop_temporal` | 🔴 Alto | ⭐ Baixa |

**Métodos que permanecem em `monolito.py`** (neste plano):
- `__init__` e métodos de UI (`montar_aba_*`, `atualizar_ui_geral`, etc.)
- Total: ~17 métodos de UI e orquestração

---

## Módulos Propostos

### 1. `utils.py`
**Responsabilidade**: Funções utilitárias puras sem dependências de estado

**Métodos/Funções:**
- `converter_valor_br(texto)` - função standalone (linhas 11-16)

**Justificativa**: Função independente, sem dependências de `self`, pode ser extraída primeiro com risco zero.

---

### 2. `data_loader.py`
**Responsabilidade**: Carregamento e processamento de dados de arquivos CSV

**Métodos:**
- `ler_csv_generico(nome_arquivo)` (linhas 122-146)
- `carregar_culturas(self)` (linhas 148-194)
- `carregar_maquinas(self)` (linhas 196-244)

**Justificativa**: Lógica de I/O e parsing, relativamente independente. Depende apenas de `self.culturas_catalogo`, `self.maquinas_catalogo` e `self.mercado_multiplicadores`.

**Dependências**: 
- Usa `converter_valor_br` (será importado de `utils`)
- Acessa `self.culturas_catalogo`, `self.maquinas_catalogo`, `self.mercado_multiplicadores`

---

### 3. `game_state.py`
**Responsabilidade**: Classe ou estrutura para gerenciar estado do jogo (dados do jogador, fazendas, plantações, etc.)

**Nota**: Neste passo, NÃO criaremos uma classe separada ainda. Apenas identificaremos quais atributos pertencem ao estado.

**Atributos de Estado Identificados**:
- `dinheiro`, `xp`, `nivel`, `dia`, `clima`
- `fazendas`, `plantacoes_por_fazenda`
- `propriedades_a_venda`
- `emprestimos_ativos`, `seguro_agricola_ativo`
- `meus_equipamentos`, `estoque`
- `capacidade_armazenagem`
- `mercado_multiplicadores`
- `tipos_de_solo`, `opcoes_base_fazenda`, `salarios_gerente`
- `culturas_catalogo`, `maquinas_catalogo`
- `config_gerente`
- `velocidade_atual`, `base_delay`, `job_tempo`

**Justificativa**: Preparação para futura extração, sem mover código ainda.

---

### 4. `business_logic.py`
**Responsabilidade**: Lógica de negócio pura (cálculos, processamento de regras de jogo)

**Métodos:**
- `get_bonus_acumulado(self, tipo_funcao)` (linhas 259-265)
- `atualizar_capacidade_armazenagem(self)` (linhas 246-254)
- `get_salario_gerente(self, fazenda)` (linhas 1046-1047)
- `ganhar_xp(self, valor)` (linhas 1563-1572)

**Justificativa**: Métodos que fazem cálculos puros e processam regras de jogo, sem dependências diretas de UI. Podem trabalhar com estado passado como parâmetro.

**Dependências**: 
- Acessam `self.meus_equipamentos`, `self.fazendas`, etc.
- `ganhar_xp` pode chamar `self.log()` (será resolvido com callback/injeção)

---

### 5. `agriculture_logic.py`
**Responsabilidade**: Lógica específica de agricultura (plantio, colheita, gerentes)

**Métodos:**
- `plantar(self)` (linhas 1318-1381)
- `colher(self, id_fazenda)` (linhas 1468-1561)
- `gerente_colher(self, id_fazenda)` (linhas 1573-1653)
- `gerente_plantar(self, id_fazenda)` (linhas 1655-1723)
- `_ask_vender_ou_armazenar(self, parent, total_kg, tipo_cultura)` (linhas 1441-1466)

**Justificativa**: Grupo coeso de funcionalidades relacionadas a agricultura. Depende de `get_bonus_acumulado`.

**Dependências**: 
- Usa `get_bonus_acumulado("Produtividade")`
- Acessa `self.fazendas`, `self.plantacoes_por_fazenda`, etc.
- Chama `self.log()`, `messagebox`, `self.atualizar_ui_geral()`

---

### 6. `finance_logic.py`
**Responsabilidade**: Lógica financeira (empréstimos, pagamentos)

**Métodos:**
- `abrir_janela_emprestimo(self)` (linhas 499-580)
- `_pegar_emprestimo(self, window, valor_str, limite, juros_mes, banco, tipo_garantia)` (linhas 581-634)
- `pagar_emprestimo(self)` (linhas 636-684)
- `atualizar_aba_financas(self)` (linhas 686-710)

**Justificativa**: Funcionalidades financeiras agrupadas. Tem dependências de UI mas pode ser extraído mantendo referências a `self`.

**Dependências**: 
- Acessa `self.emprestimos_ativos`, `self.dinheiro`, `self.fazendas`, `self.meus_equipamentos`
- Usa `tk.Toplevel`, `messagebox`, `simpledialog`
- Chama `self.log()`, `self.atualizar_ui_geral()`

---

### 7. `property_logic.py`
**Responsabilidade**: Lógica de gestão de propriedades (compra, venda, renomeação)

**Métodos:**
- `comprar_fazenda(self)` (linhas 1217-1247)
- `vender_fazenda(self)` (linhas 1177-1215)
- `renomear_fazenda(self, id_fazenda)` (linhas 1033-1044)
- `atualizar_listas_imobiliaria(self)` (linhas 1249-1271)
- `atualizar_listas_lojas(self)` (linhas 1273-1316)

**Justificativa**: Funcionalidades relacionadas a imóveis agrupadas.

**Dependências**: 
- Acessa `self.fazendas`, `self.propriedades_a_venda`, `self.dinheiro`
- Usa `messagebox`, `simpledialog`
- Chama `self.log()`, `self.atualizar_ui_geral()`

---

### 8. `equipment_logic.py`
**Responsabilidade**: Lógica de equipamentos/máquinas

**Métodos:**
- `comprar_maquina(self)` (linhas 1383-1409)
- `vender_maquina(self)` (linhas 1411-1439)

**Justificativa**: Funcionalidades de compra/venda de equipamentos.

**Dependências**: 
- Acessa `self.maquinas_catalogo`, `self.meus_equipamentos`, `self.nivel`, `self.dinheiro`, `self.fazendas`
- Chama `atualizar_capacidade_armazenagem()`, `self.log()`, `self.atualizar_ui_geral()`

---

### 9. `storage_logic.py`
**Responsabilidade**: Lógica de armazenamento e logística

**Métodos:**
- `vender_lote_estoque(self)` (linhas 1000-1031)
- `atualizar_aba_logistica(self)` (linhas 931-965)
- `mudar_config_gerente(self, event=None)` (linhas 967-971)
- `atualizar_label_gatilho(self, event=None)` (linhas 973-980)
- `atualizar_cores_logistica(self)` (linhas 982-998)

**Justificativa**: Funcionalidades relacionadas a estoque e logística.

**Dependências**: 
- Acessa `self.estoque`, `self.mercado_multiplicadores`, `self.capacidade_armazenagem`
- Usa `messagebox`
- Chama `self.log()`, `self.atualizar_ui_geral()`

---

### 10. `manager_logic.py`
**Responsabilidade**: Lógica de gerentes automáticos

**Métodos:**
- `contratar_gerente(self, id_fazenda)` (linhas 1049-1062)
- `demitir_gerente(self, id_fazenda)` (linhas 1064-1084)
- `escolher_cultura_para_gerente(self, id_fazenda)` (linhas 1086-1146)
- `abrir_configuracao_gerente(self, id_fazenda)` (linhas 1148-1175)

**Justificativa**: Funcionalidades de gestão de gerentes agrupadas.

**Dependências**: 
- Acessa `self.fazendas`, `self.salarios_gerente`, `self.culturas_catalogo`, `self.nivel`
- Usa `tk.Toplevel`, `messagebox`, `simpledialog`
- Chama `self.log()`, `self.atualizar_ui_geral()`

---

### 11. `time_control.py`
**Responsabilidade**: Controle de tempo e loop temporal

**Métodos:**
- `alterar_velocidade(self, mult)` (linhas 715-733)
- `loop_temporal(self)` (linhas 735-745)

**Justificativa**: Sistema de controle de tempo isolado.

**Dependências**: 
- Acessa `self.velocidade_atual`, `self.base_delay`, `self.job_tempo`, `self.root`
- Chama `self.passar_dia()`

---

### 12. `ui_components.py`
**Responsabilidade**: Montagem e atualização de componentes de UI

**Métodos:**
- `mostrar_tela_inicial(self)` (linhas 2104-2108)
- `mostrar_tela_imobiliaria(self)` (linhas 270-357)
- `_atualizar_custo_inicial(self)` (linhas 320-334)
- `confirmar_e_iniciar(self)` (linhas 336-356)
- `iniciar_jogo(self, fazenda_inicial, equipamentos_iniciais)` (linhas 358-378)
- `criar_interface_principal(self)` (linhas 380-450)
- `montar_aba_agricultura(self)` (linhas 750-787)
- `montar_aba_maquinas(self)` (linhas 789-821)
- `montar_aba_imobiliaria(self)` (linhas 823-858)
- `montar_aba_mercado(self)` (linhas 860-879)
- `montar_aba_logistica(self)` (linhas 881-929)
- `montar_aba_financas(self)` (linhas 452-497)
- `atualizar_ui_geral(self)` (linhas 1906-2057)
- `atualizar_aba_mercado(self)` (linhas 2059-2089)
- `log(self, t)` (linhas 2091-2098)
- `salvar_e_fechar(self)` (linhas 2100-2102)
- `iniciar_de_save(self)` (linhas 2110-2112)

**Justificativa**: Todos os métodos relacionados à criação e atualização de interface gráfica.

**Dependências**: 
- Fortemente acoplado ao resto do sistema
- Acessa praticamente todos os atributos de estado
- Usa `tkinter` extensivamente

---

## Ordem de Extração (6 Passos)

### PASSO 1: Extrair Função Utilitária (MAIS SEGURO)
**Objetivo**: Extrair função standalone sem dependências

**Ação**:
- Criar `utils.py` com `converter_valor_br()`
- Em `monolito.py`, substituir definição por `from utils import converter_valor_br`
- Remover definição local

**Métodos Movidos**:
- `converter_valor_br()` → `utils.py`

**Teste**: Verificar se o jogo roda normalmente e carrega culturas/máquinas corretamente.

**Risco**: ⚪ Muito Baixo (função pura, sem estado)

---

### PASSO 2: Extrair Carregamento de Dados
**Objetivo**: Mover lógica de I/O e parsing para módulo separado

**Ação**:
- Criar `data_loader.py` como módulo (não classe)
- Mover `ler_csv_generico()`, `carregar_culturas()`, `carregar_maquinas()` como funções que recebem `self` ou criam classes auxiliares
- Em `monolito.py`, importar e adaptar chamadas

**Estratégia**:
- Criar classe `DataLoader` que recebe referência ao jogo ou apenas processa dados
- OU manter métodos na classe principal mas movê-los para um módulo que será mixado

**Métodos Movidos**:
- `ler_csv_generico()` → `data_loader.py`
- `carregar_culturas()` → `data_loader.py`  
- `carregar_maquinas()` → `data_loader.py`

**Teste**: Verificar se catálogos carregam corretamente e culturas/máquinas aparecem nas interfaces.

**Risco**: 🟡 Baixo-Médio (depende de estado mas é isolável)

---

### PASSO 3: Extrair Utilitários de Cálculo
**Objetivo**: Mover funções de cálculo que não dependem de UI

**Ação**:
- Criar `business_logic.py`
- Mover `get_bonus_acumulado()`, `atualizar_capacidade_armazenagem()`, `get_salario_gerente()`, `ganhar_xp()`
- Criar classe `GameCalculations` ou manter como funções que recebem estado
- Em `monolito.py`, importar e chamar através de instância ou delegar

**Métodos Movidos**:
- `get_bonus_acumulado()` → `business_logic.py`
- `atualizar_capacidade_armazenagem()` → `business_logic.py`
- `get_salario_gerente()` → `business_logic.py`
- `ganhar_xp()` → `business_logic.py`

**Nota**: `gerar_novas_propriedades_a_venda()` será movido no passo 4 junto com processamento temporal, pois é chamado durante `passar_dia()`.

**Teste**: Verificar cálculos de bônus, capacidade de armazenagem, salários e XP.

**Risco**: 🟡 Baixo-Médio (lógica pura, mas acessa atributos de self)

---

### PASSO 4: Extrair Lógica de Processamento Temporal
**Objetivo**: Isolar processamento automático de eventos (tempo, empréstimos, vendas)

**Ação**:
- Criar `time_processor.py`
- Mover `passar_dia()`, `_processar_emprestimos()`, `processar_vendas_automaticas()`, `gerar_novas_propriedades_a_venda()`
- Criar classe `TimeProcessor` que recebe referência ao jogo
- Manter métodos como delegação em `JogoFazenda` que chamam o processador

**Métodos Movidos**:
- `passar_dia()` → `time_processor.py`
- `_processar_emprestimos()` → `time_processor.py`
- `processar_vendas_automaticas()` → `time_processor.py`
- `gerar_novas_propriedades_a_venda()` → `time_processor.py`

**Teste**: Verificar avanço de tempo, processamento de empréstimos, vendas automáticas, geração de propriedades.

**Risco**: 🟠 Médio (acessa muitos atributos de estado e chama métodos de UI)

---

### PASSO 5: Extrair Lógicas de Domínio (Agricultura, Equipamentos, Propriedades)
**Objetivo**: Mover funcionalidades agrupadas por domínio

**Ação**:
- Criar `agriculture_logic.py`, `equipment_logic.py`, `property_logic.py`, `storage_logic.py`, `manager_logic.py`, `finance_logic.py`
- Mover métodos correspondentes para cada módulo
- Criar classes que recebem referência ao jogo principal (composição)
- Manter delegação na classe principal

**Métodos Movidos por Módulo**:

**agriculture_logic.py**:
- `plantar()`
- `colher()`
- `gerente_colher()`
- `gerente_plantar()`
- `_ask_vender_ou_armazenar()`

**equipment_logic.py**:
- `comprar_maquina()`
- `vender_maquina()`

**property_logic.py**:
- `comprar_fazenda()`
- `vender_fazenda()`
- `renomear_fazenda()`
- `atualizar_listas_imobiliaria()`
- `atualizar_listas_lojas()`

**storage_logic.py**:
- `vender_lote_estoque()`
- `atualizar_aba_logistica()`
- `mudar_config_gerente()`
- `atualizar_label_gatilho()`
- `atualizar_cores_logistica()`

**manager_logic.py**:
- `contratar_gerente()`
- `demitir_gerente()`
- `escolher_cultura_para_gerente()`
- `abrir_configuracao_gerente()`

**finance_logic.py**:
- `abrir_janela_emprestimo()`
- `_pegar_emprestimo()`
- `pagar_emprestimo()`
- `atualizar_aba_financas()`

**Teste**: Testar cada funcionalidade: plantio, colheita, compra/venda de máquinas, compra/venda de propriedades, estoque, gerentes, empréstimos.

**Risco**: 🟠 Médio-Alto (métodos têm muitas dependências de UI e estado)

---

### PASSO 6: Extrair Controle de Tempo e Preparar UI (MAIS ARRISCADO)
**Objetivo**: Isolar controle de tempo e preparar terreno para extração de UI (opcional)

**Ação**:
- Criar `time_control.py` com `TimeController`
- Mover `alterar_velocidade()`, `loop_temporal()`
- Manter delegação na classe principal
- (Opcional) Preparar estrutura para extração de UI em passos futuros

**Métodos Movidos**:
- `alterar_velocidade()` → `time_control.py`
- `loop_temporal()` → `time_control.py`

**Nota**: Os métodos de UI (`montar_aba_*`, `atualizar_ui_geral`, etc.) permanecem na classe principal neste plano. Podem ser extraídos em uma segunda fase se necessário.

**Teste**: Verificar controles de velocidade (pausa, 1x, 4x, 8x) e avanço temporal automático.

**Risco**: 🔴 Alto (fortemente acoplado ao loop de eventos do tkinter)

---

## Estratégia de Implementação

### Para cada passo:
1. **Criar novo arquivo de módulo**
2. **Copiar código** (sem reformatação)
3. **Adaptar imports** necessários
4. **Manter delegação** na classe principal (métodos chamam módulo externo)
5. **Testar funcionalidade** específica
6. **Verificar comportamento geral** do jogo
7. **Commit** (se usando controle de versão)

### Padrão de Delegação:
```python
# Em monolito.py (mantido)
def get_bonus_acumulado(self, tipo_funcao):
    return business_logic.get_bonus_acumulado(self.meus_equipamentos, tipo_funcao)
```

OU (se usando composição):
```python
# Em monolito.py
def __init__(self, root):
    # ...
    self.business_logic = BusinessLogic(self)  # Passa referência

# Uso
def alguma_coisa(self):
    bonus = self.business_logic.get_bonus_acumulado("Produtividade")
```

---

## Resumo por Módulo

| Módulo | Métodos/Funções | Qtd | Linhas Aprox. | Dependências | Passo |
|--------|----------------|-----|---------------|--------------|-------|
| `utils.py` | `converter_valor_br` | 1 | 6 | Nenhuma | 1 |
| `data_loader.py` | `ler_csv_generico`, `carregar_culturas`, `carregar_maquinas` | 3 | ~120 | `utils`, estado (catálogos) | 2 |
| `business_logic.py` | `get_bonus_acumulado`, `atualizar_capacidade_armazenagem`, `get_salario_gerente`, `ganhar_xp` | 4 | ~40 | Estado (equipamentos, fazendas) | 3 |
| `time_processor.py` | `passar_dia`, `_processar_emprestimos`, `processar_vendas_automaticas`, `gerar_novas_propriedades_a_venda` | 4 | ~200 | Estado, métodos de UI | 4 |
| `agriculture_logic.py` | `plantar`, `colher`, `gerente_colher`, `gerente_plantar`, `_ask_vender_ou_armazenar` | 5 | ~400 | Estado, UI, `business_logic` | 5 |
| `equipment_logic.py` | `comprar_maquina`, `vender_maquina` | 2 | ~60 | Estado, UI, `business_logic` | 5 |
| `property_logic.py` | `comprar_fazenda`, `vender_fazenda`, `renomear_fazenda`, `atualizar_listas_imobiliaria`, `atualizar_listas_lojas` | 5 | ~150 | Estado, UI | 5 |
| `storage_logic.py` | `vender_lote_estoque`, `atualizar_aba_logistica`, `mudar_config_gerente`, `atualizar_label_gatilho`, `atualizar_cores_logistica` | 5 | ~100 | Estado, UI | 5 |
| `manager_logic.py` | `contratar_gerente`, `demitir_gerente`, `escolher_cultura_para_gerente`, `abrir_configuracao_gerente` | 4 | ~130 | Estado, UI | 5 |
| `finance_logic.py` | `abrir_janela_emprestimo`, `_pegar_emprestimo`, `pagar_emprestimo`, `atualizar_aba_financas` | 4 | ~220 | Estado, UI | 5 |
| `time_control.py` | `alterar_velocidade`, `loop_temporal` | 2 | ~30 | Estado, `time_processor` | 6 |
| `monolito.py` (restante) | `__init__`, UI, inicialização, orquestração | ~17 | ~800 | Todos os módulos | - |

**Total**: 56 métodos/funções (incluindo `__init__` e função standalone)

---

## Notas Importantes

1. **UI permanece no monolito inicialmente**: Os métodos de montagem de UI (`montar_aba_*`, `atualizar_ui_geral`) permanecem na classe principal por enquanto, pois são fortemente acoplados.

2. **Estado compartilhado**: O estado do jogo permanece como atributos de `JogoFazenda`. Em passos futuros, pode ser extraído para uma classe `GameState`.

3. **Callbacks**: Métodos que chamam `self.log()` ou `self.atualizar_ui_geral()` podem receber callbacks ou manter referência ao jogo principal.

4. **Testabilidade**: Após a modularização, cada módulo pode ser testado isoladamente.

5. **Reversibilidade**: Cada passo deve ser facilmente reversível se houver problemas.

