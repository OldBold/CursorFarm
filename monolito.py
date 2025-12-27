import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import os
import random
from utils import converter_valor_br, formatar_moeda
from systems.market import atualizar_multiplicadores
from systems.economy import preco_mercado_atual, margem_percentual, producao_kg, custo_medio_por_kg
from systems.time_engine import avancar_semana
from systems.storage import calcular_capacidade_armazenagem, calcular_uso_capacidade, calcular_espaco_livre, processar_venda_automatica
from systems.agriculture import validar_plantio, criar_plantacoes, colheita_lotes, agrupar_colheita
from systems.properties import gerar_propriedades_a_venda, gerar_propriedades_iniciais, preco_venda_propriedade, pode_vender_fazenda, pode_comprar_propriedade
from systems.manager import salario_gerente, deve_pagar_salario, processar_pagamento_salario, selecionar_culturas_disponiveis, escolher_cultura_para_plantar
from systems.finance import processar_emprestimos_semanal, calcular_semanas_restantes, calcular_valor_pagamento_max, processar_pagamento

# ==========================================
# CLASSE PRINCIPAL
# ==========================================
class JogoFazenda:
    def __init__(self, root):
        self.root = root
        self.root.title("Tycoon Fazenda v1.2 - Controle de Tempo")
        self.root.geometry("600x425") # Aumentei um pouco a altura
        
        # Configurar estilos de UI
        self._configurar_estilos_ui()
        
        # --- ESTADO DO JOGADOR ---
        self.dinheiro = 0
        self.xp = 0
        self.nivel = 1
        self.dia = 1
        self.clima = "Ameno"
        self.fazendas = []
        self.plantacoes_por_fazenda = {}
        self.propriedades_a_venda = [] # NOVO: Lista dinâmica
        self.emprestimos_ativos = []
        self.seguro_agricola_ativo = False
        
        # Tipos de solo e opções de fazenda são centralizados em data.catalogs
        from data.catalogs import TIPOS_DE_SOLO, OPCOES_BASE_FAZENDA, SALARIOS_GERENTE
        from copy import deepcopy

        self.tipos_de_solo = deepcopy(TIPOS_DE_SOLO)
        self.opcoes_base_fazenda = deepcopy(OPCOES_BASE_FAZENDA)
        self.salarios_gerente = deepcopy(SALARIOS_GERENTE)
        
        # --- CONTROLE DE TEMPO (NOVO) ---
        self.velocidade_atual = 0  # 0 = Pausa
        self.base_delay = 5000     # 5 segundos = 1 semana no modo normal
        self.job_tempo = None      # Armazena o ID do agendamento para poder cancelar
        
        # Listas de Dados
        self.culturas_catalogo = []
        self.maquinas_catalogo = [] 
        
        # Referências de Widgets da UI
        self.notebook_fazendas = None
        self.trees_fazenda = {}
        self.mapa_tabs_fazendas = {} # NOVO: Mapeia tab_id -> farm_id
        self.botoes_gerente_fazenda = {}
        
        # Inventário
        self.meus_equipamentos = []
        self.mercado_multiplicadores = {}

        # --- ARMAZENAGEM E LOGÍSTICA (NOVO) ---
        self.estoque = [] # Lista de lotes armazenados
        self.capacidade_armazenagem = {"Silo": 0, "Armazém": 0}
        self.config_gerente = {
            "acao_colheita": "Sempre Vender" # Opções: "Sempre Vender", "Sempre Armazenar"
        }
        self.gatilho_venda_automatica_ativo = tk.BooleanVar(value=False)
        self.gatilho_venda_automatica_margem = tk.DoubleVar(value=20.0)
        
        # --- CARREGAMENTO ---
        self.carregar_culturas()
        self.carregar_maquinas()
        
        self.gerar_novas_propriedades_a_venda() # Gera a lista inicial
        self.mostrar_tela_inicial()

    def _configurar_estilos_ui(self):
        """
        Configura estilos globais de UI para melhorar acessibilidade e legibilidade.
        Centraliza configuração de fontes para widgets tk e ttk.
        """
        # Criar e configurar Style ttk
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Catálogo de fontes (separado de self.styles para evitar conflitos com cores)
        self.ui_fonts = {
            'font_titulo': ("Arial", 20, "bold"),
            'font_subtitulo': ("Arial", 14, "bold"),
            'font_corpo': ("Arial", 11),
            'font_botao': ("Arial", 11, "bold"),
            'font_tree': ("Arial", 11),
            'font_mono': ("Courier", 11)
        }
        
        # Aplicar defaults globais para widgets tk (reduz necessidade de font= em cada widget)
        self.root.option_add("*Font", self.ui_fonts['font_corpo'])
        self.root.option_add("*Button.Font", self.ui_fonts['font_botao'])
        self.root.option_add("*Label.Font", self.ui_fonts['font_corpo'])
        self.root.option_add("*Entry.Font", self.ui_fonts['font_corpo'])
        self.root.option_add("*Text.Font", self.ui_fonts['font_mono'])
        self.root.option_add("*Listbox.Font", self.ui_fonts['font_corpo'])
        
        # Configurar estilos ttk usando fontes do catálogo
        self.style.configure("TLabel", font=self.ui_fonts['font_corpo'])
        self.style.configure("TButton", font=self.ui_fonts['font_botao'], padding=[8, 4])
        self.style.configure("TCheckbutton", font=self.ui_fonts['font_corpo'])
        self.style.configure("TRadiobutton", font=self.ui_fonts['font_corpo'])
        self.style.configure("TCombobox", font=self.ui_fonts['font_corpo'])
        self.style.configure("TNotebook", font=self.ui_fonts['font_corpo'])
        self.style.configure("TNotebook.Tab", font=self.ui_fonts['font_botao'], padding=[12, 6])
        self.style.configure("Treeview", font=self.ui_fonts['font_tree'])
        self.style.configure("Treeview.Heading", font=self.ui_fonts['font_botao'])
        self.style.configure("TLabelframe", font=self.ui_fonts['font_subtitulo'])
        self.style.configure("TLabelframe.Label", font=self.ui_fonts['font_subtitulo'])

    def _configurar_ordenacao_treeview(self, tree, colunas_numericas=None):
        """
        Configura ordenação por coluna em uma Treeview.
        colunas_numericas: lista de nomes de colunas que devem ser ordenadas numericamente.
        """
        if colunas_numericas is None:
            colunas_numericas = []
        
        def _ordenar_coluna(tree, col, reverse):
            items = [(tree.set(item, col), item) for item in tree.get_children('')]
            
            # Tenta converter para número se a coluna estiver na lista de numéricas
            try:
                if col in colunas_numericas:
                    items.sort(key=lambda t: float(t[0].replace('$', '').replace('.', '').replace(',', '.').replace('%', '').strip() or 0), reverse=reverse)
                else:
                    items.sort(key=lambda t: t[0].lower(), reverse=reverse)
            except (ValueError, AttributeError):
                items.sort(key=lambda t: str(t[0]).lower(), reverse=reverse)
            
            for index, (val, item) in enumerate(items):
                tree.move(item, '', index)
            
            # Inverte a ordem na próxima vez
            tree.heading(col, command=lambda: _ordenar_coluna(tree, col, not reverse))
        
        # Configura o comando de ordenação para cada coluna
        for col in tree['columns']:
            tree.heading(col, command=lambda c=col: _ordenar_coluna(tree, c, False))
    
    def _aplicar_filtro_treeview(self, tree, texto_filtro):
        """
        Filtra itens de uma Treeview baseado em texto (mostra apenas itens que correspondem).
        """
        texto_filtro = texto_filtro.lower().strip()
        
        # Coleta todos os itens antes de fazer qualquer mudança
        todos_itens = list(tree.get_children())
        
        if not texto_filtro:
            # Mostra todos os itens reatachando-os
            for item in todos_itens:
                if tree.exists(item):
                    try:
                        tree.detach(item)
                        tree.reattach(item, '', 'end')
                    except:
                        pass
        else:
            # Separa itens que correspondem
            itens_visiveis = []
            
            for item in todos_itens:
                if not tree.exists(item):
                    continue
                valores = [tree.set(item, col) for col in tree['columns']]
                texto_completo = ' '.join(str(v) for v in valores).lower()
                
                if texto_filtro in texto_completo:
                    itens_visiveis.append(item)
                else:
                    # Oculta o item
                    try:
                        tree.detach(item)
                    except:
                        pass
            
            # Reatacha apenas os itens visíveis na ordem original
            for item in itens_visiveis:
                try:
                    tree.detach(item)
                    tree.reattach(item, '', 'end')
                except:
                    pass

    def gerar_novas_propriedades_a_venda(self, logar_evento=False):
        self.propriedades_a_venda = gerar_propriedades_a_venda(self.dia, self.opcoes_base_fazenda, self.tipos_de_solo)
        
        if logar_evento:
            self.log("Novas propriedades disponíveis na imobiliária!")

    # ------------------------------------------------------------------
    # CARREGAMENTO DE DADOS
    # ------------------------------------------------------------------
    def carregar_culturas(self):
        # Carrega catálogo de culturas a partir do módulo de catálogos (substitui CSV)
        from data.catalogs import CULTURAS_CATALOGO
        from copy import deepcopy

        self.culturas_catalogo = deepcopy(CULTURAS_CATALOGO)
        for cultura in self.culturas_catalogo:
            self.mercado_multiplicadores[cultura["nome"]] = 1.0


    def carregar_maquinas(self):
        # Carrega catálogo de máquinas a partir do módulo de catálogos (substitui CSV)
        from data.catalogs import MAQUINAS_CATALOGO
        from copy import deepcopy

        self.maquinas_catalogo = deepcopy(MAQUINAS_CATALOGO)

    def atualizar_capacidade_armazenagem(self):
        self.capacidade_armazenagem = calcular_capacidade_armazenagem(self.meus_equipamentos)

    # ------------------------------------------------------------------
    # UTILITÁRIOS
    # ------------------------------------------------------------------
    def get_bonus_acumulado(self, tipo_funcao):
        total = 0.0
        for m in self.meus_equipamentos:
            # A função de Armazenagem não entra como bônus percentual
            if m["funcao"] == tipo_funcao and m["funcao"] != "Armazenagem":
                total += m["valor_bonus"]
        return total

    # ------------------------------------------------------------------
    # FLUXO DE TELAS
    # ------------------------------------------------------------------
    def mostrar_tela_imobiliaria(self):
        self.root.geometry("960x480")
        for w in self.root.winfo_children(): w.destroy()

        self.dinheiro_inicial_base = 75000
        self.propriedade_selecionada_var = tk.StringVar(value=None)
        self.vars_maquinas_iniciais = []

        tk.Label(self.root, text="Escolha sua Propriedade e Equipamentos", font=self.ui_fonts['font_titulo']).pack(pady=10)
        self.lbl_dinheiro_inicial = tk.Label(self.root, text="", font=self.ui_fonts['font_subtitulo'], fg="#2E8B57")
        self.lbl_dinheiro_inicial.pack(pady=(0, 10))

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        frame_propriedades = tk.LabelFrame(main_frame, text="1. Escolha a Propriedade", font=self.ui_fonts['font_subtitulo'])
        frame_propriedades.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Gerar propriedades iniciais (apenas pequenas e médias, todos os solos)
        self.propriedades_iniciais = gerar_propriedades_iniciais(self.dia, self.opcoes_base_fazenda, self.tipos_de_solo)
        
        for op in self.propriedades_iniciais:
            rb = tk.Radiobutton(frame_propriedades, 
                                text=f"{op['nome']} - {formatar_moeda(op['custo'], 0)}\n({op['tam']} ha, solo {op['solo']})",
                                variable=self.propriedade_selecionada_var,
                                value=op['nome'],
                                command=self._atualizar_custo_inicial,
                                anchor="w", justify="left",
                                font=self.ui_fonts['font_corpo'], indicatoron=0,
                                selectcolor="#C0E0C0")
            rb.pack(fill="x", padx=10, pady=5)

        frame_equipamentos = tk.LabelFrame(main_frame, text="2. Escolha seus Equipamentos Iniciais (Nível 1)", font=self.ui_fonts['font_subtitulo'])
        frame_equipamentos.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        maquinas_nivel_1 = [m for m in self.maquinas_catalogo if m["nivel_req"] == 1]
        for maq in maquinas_nivel_1:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(frame_equipamentos, 
                                 text=f"{maq['nome']} ({formatar_moeda(maq['preco'], 0)})", 
                                 variable=var, 
                                 font=self.ui_fonts['font_corpo'],
                                 command=self._atualizar_custo_inicial)
            chk.pack(anchor="w", padx=10)
            self.vars_maquinas_iniciais.append({"var": var, "maq": maq})

        btn_iniciar = tk.Button(self.root, text="Confirmar Escolhas e Iniciar Campanha", 
                                font=("Arial", 14, "bold"), bg="#4CAF50", fg="white",
                                command=self.confirmar_e_iniciar)
        btn_iniciar.pack(fill="x", padx=10, pady=(10, 10))

        self._atualizar_custo_inicial()

    def _atualizar_custo_inicial(self):
        custo_maquinas = sum(item['maq']['preco'] for item in self.vars_maquinas_iniciais if item['var'].get())
        custo_propriedade = 0
        nome_propriedade = self.propriedade_selecionada_var.get()
        if nome_propriedade != "None":
            propriedade = next((p for p in self.propriedades_iniciais if p['nome'] == nome_propriedade), None)
            if propriedade:
                custo_propriedade = propriedade['custo']

        custo_total = custo_maquinas + custo_propriedade
        saldo = self.dinheiro_inicial_base - custo_total
        
        self.lbl_dinheiro_inicial.config(
            text=f"Capital: {formatar_moeda(self.dinheiro_inicial_base)} | Custo Total: {formatar_moeda(custo_total)} | Saldo Restante: {formatar_moeda(saldo)}"
        )

    def confirmar_e_iniciar(self):
        nome_propriedade = self.propriedade_selecionada_var.get()
        if nome_propriedade == "None":
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Seleção Incompleta", "Por favor, escolha uma propriedade para começar.")
            return
            
        fazenda_selecionada = next((p for p in self.propriedades_iniciais if p['nome'] == nome_propriedade), None)
        if not fazenda_selecionada:
            return

        # Verificar compatibilidade do solo com culturas nível 1
        solo_escolhido = fazenda_selecionada["solo"]
        culturas_nivel_1 = [c for c in self.culturas_catalogo if c["nivel_req"] == 1]
        solos_compatíveis_nivel_1 = set()
        
        for cultura in culturas_nivel_1:
            solo_ideal = cultura.get("solo_ideal", "Qualquer")
            if solo_ideal != "Qualquer":
                solos_compatíveis_nivel_1.add(solo_ideal)
        
        if solo_escolhido not in solos_compatíveis_nivel_1:
            # Solo incompatível - avisar e permitir refazer escolha
            solos_compatíveis_str = ", ".join(sorted(solos_compatíveis_nivel_1))
            msg = f"Atenção: O solo '{solo_escolhido}' não é compatível com nenhuma cultura de nível 1.\n\n"
            msg += f"Solos compatíveis com culturas nível 1: {solos_compatíveis_str}.\n\n"
            msg += "Você terá mais dificuldade no início do jogo.\n\n"
            msg += "Deseja refazer sua escolha?"
            
            if self._pausar_e_exibir_dialogo(messagebox.askyesno, "Solo Incompatível", msg, icon="warning"):
                return  # Retorna para permitir nova escolha
        
        fazenda_inicial = fazenda_selecionada.copy()
        
        # --- NOMEAÇÃO ---
        novo_nome = simpledialog.askstring("Nomear Propriedade", "Dê um nome para sua nova propriedade:", initialvalue=fazenda_inicial["nome"])
        if novo_nome:
            fazenda_inicial["nome_personalizado"] = novo_nome
        else:
            fazenda_inicial["nome_personalizado"] = fazenda_inicial["nome"]

        equipamentos = [item['maq'] for item in self.vars_maquinas_iniciais if item['var'].get()]
        self.iniciar_jogo(fazenda_inicial, equipamentos)

    def iniciar_jogo(self, fazenda_inicial, equipamentos_iniciais):
        fazenda_inicial["tem_gerente"] = False
        fazenda_inicial["gerente_cultura"] = "Automatica"
        self.fazendas = [fazenda_inicial]
        self.plantacoes_por_fazenda = {
            fazenda_inicial['id']: []
        }
        self.meus_equipamentos.extend(equipamentos_iniciais)
        self.atualizar_capacidade_armazenagem() # NOVO
        
        custo_propriedade = fazenda_inicial['custo']
        custo_maquinas = sum(m['preco'] for m in equipamentos_iniciais)
        custo_total = custo_propriedade + custo_maquinas
        self.dinheiro = 75000 - custo_total
        
        if self.dinheiro < 0:
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Investimento Excedido", "Capital insuficiente.")
            self.mostrar_tela_imobiliaria()
            return

        self.criar_interface_principal()

    def criar_interface_principal(self):
        self.root.geometry("1200x680")
        self.root.protocol("WM_DELETE_WINDOW", self.salvar_e_fechar)
        for w in self.root.winfo_children(): w.destroy()
        
        # --- HUD ---
        frame_topo = tk.Frame(self.root, bg="#333", pady=5)
        frame_topo.pack(fill="x")
        self.lbl_nivel = tk.Label(frame_topo, text=f"⭐ Nível {self.nivel}", font=self.ui_fonts['font_subtitulo'], bg="#333", fg="gold")
        self.lbl_nivel.pack(side="left", padx=15)
        self.lbl_dinheiro = tk.Label(frame_topo, text=formatar_moeda(self.dinheiro), font=self.ui_fonts['font_subtitulo'], bg="#333", fg="#90EE90")
        self.lbl_dinheiro.pack(side="left", padx=15)

        # --- CONTROLE DE TEMPO ---
        frame_tempo_controles = tk.Frame(frame_topo, bg="#333")
        frame_tempo_controles.pack(side="right", padx=10)

        self.lbl_tempo = tk.Label(frame_tempo_controles, text="", font=self.ui_fonts['font_corpo'], bg="#333", fg="white")
        self.lbl_tempo.pack(side="top", anchor="e")

        frame_botoes_tempo = tk.Frame(frame_tempo_controles, bg="#333")
        frame_botoes_tempo.pack(side="bottom", pady=(5,0))
        
        btn_config = {'font': self.ui_fonts['font_botao'], 'width': 10, 'height': 1}
        self.btns_tempo = {}

        b_pausa = tk.Button(frame_botoes_tempo, text="⏸ Pausar", bg="#ffcccc", command=lambda: self.alterar_velocidade(0), **btn_config)
        b_1x = tk.Button(frame_botoes_tempo, text="▶ 1x", command=lambda: self.alterar_velocidade(1), **btn_config)
        b_4x = tk.Button(frame_botoes_tempo, text="⏩ 4x", command=lambda: self.alterar_velocidade(4), **btn_config)
        b_8x = tk.Button(frame_botoes_tempo, text="🚀 8x", command=lambda: self.alterar_velocidade(8), **btn_config)

        b_pausa.pack(side="left", padx=2)
        b_1x.pack(side="left", padx=2)
        b_4x.pack(side="left", padx=2)
        b_8x.pack(side="left", padx=2)

        self.btns_tempo[0] = b_pausa
        self.btns_tempo[1] = b_1x
        self.btns_tempo[4] = b_4x
        self.btns_tempo[8] = b_8x

        # --- ABAS ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=5)
        self.tab_agro = tk.Frame(self.notebook)
        self.notebook.add(self.tab_agro, text="  🌱 Agricultura  ")
        self.montar_aba_agricultura()
        self.tab_maq = tk.Frame(self.notebook)
        self.notebook.add(self.tab_maq, text="  🚜 Equipamentos  ")
        self.montar_aba_maquinas()
        self.tab_imob = tk.Frame(self.notebook)
        self.notebook.add(self.tab_imob, text="  🏞️ Terras  ")
        self.montar_aba_imobiliaria()

        self.tab_mercado = tk.Frame(self.notebook)
        self.notebook.add(self.tab_mercado, text="  📈 Mercado  ")
        self.montar_aba_mercado()

        self.tab_logistica = tk.Frame(self.notebook)
        self.notebook.add(self.tab_logistica, text="  📦 Logística  ")
        self.montar_aba_logistica()

        self.tab_financas = tk.Frame(self.notebook)
        self.notebook.add(self.tab_financas, text="  💰 Finanças  ")
        self.montar_aba_financas()
        self.tab_stats = tk.Frame(self.notebook)
        self.notebook.add(self.tab_stats, text="  📊 Estatísticas  ")
        self.montar_aba_estatisticas()
        
        self.txt_log = tk.Text(self.root, height=5, bg="#f0f0f0", state="disabled")
        self.txt_log.pack(fill="x", padx=10, pady=(0,10))
        
        self.atualizar_ui_geral()
        self.alterar_velocidade(0) # Inicia Pausado

    def montar_aba_financas(self):
        paned = tk.PanedWindow(self.tab_financas, orient="vertical")
        paned.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Frame superior com Resumo, Seguro e Empréstimos ---
        frame_top = tk.Frame(paned)
        paned.add(frame_top, height=140)

        lf_resumo = tk.LabelFrame(frame_top, text="Resumo Geral", padx=10, pady=5)
        lf_resumo.pack(side="left", fill="y", padx=(0, 5))
        tk.Label(lf_resumo, text="Receita:").grid(row=0, column=0, sticky="w")
        tk.Label(lf_resumo, text="Custos:").grid(row=1, column=0, sticky="w")
        tk.Label(lf_resumo, text="Saldo:").grid(row=2, column=0, sticky="w")

        lf_acoes = tk.LabelFrame(frame_top, text="Ações Financeiras", padx=10, pady=10)
        lf_acoes.pack(side="left", fill="both", expand=True)

        btn_emprestimo = tk.Button(lf_acoes, text="Pedir Empréstimo", font=self.ui_fonts['font_botao'], bg="#87CEEB", command=self.abrir_janela_emprestimo)
        btn_emprestimo.pack(pady=5, fill="x")

        self.btn_seguro = tk.Button(lf_acoes, text="Contratar Seguro Agrícola", font=self.ui_fonts['font_botao'])
        self.btn_seguro.pack(pady=5, fill="x")
        
        # --- Frame para a lista de Empréstimos Ativos ---
        lf_emprestimos = tk.LabelFrame(paned, text="Empréstimos Ativos", padx=10, pady=5)
        paned.add(lf_emprestimos)

        cols = ('id', 'Banco', 'Valor Devido', 'Juros', 'Garantia', 'Prazo')
        self.tree_emprestimos = ttk.Treeview(lf_emprestimos, columns=cols, show="headings", selectmode="browse")
        self.tree_emprestimos.column("id", width=0, stretch=tk.NO)
        self.tree_emprestimos.heading('Banco', text='Banco')
        self.tree_emprestimos.heading('Valor Devido', text='Valor Devido')
        self.tree_emprestimos.heading('Juros', text='Juros (a.m.)')
        self.tree_emprestimos.heading('Garantia', text='Garantia')
        self.tree_emprestimos.heading('Prazo', text='Prazo')
        self.tree_emprestimos.pack(fill="both", expand=True, side="left")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(lf_emprestimos, orient="vertical", command=self.tree_emprestimos.yview)
        self.tree_emprestimos.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        frame_botoes = tk.Frame(lf_emprestimos)
        frame_botoes.pack(fill="x", pady=(5,0), side="bottom")
        
        tk.Button(frame_botoes, text="Amortizar/Pagar", font=self.ui_fonts['font_botao'], bg="#90EE90", command=self.pagar_emprestimo).pack(side="right")

    def abrir_janela_emprestimo(self):
        win = tk.Toplevel(self.root)
        win.title("Pedir Empréstimo")
        win.geometry("800x450")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Opções de Empréstimo Disponíveis", font=self.ui_fonts['font_subtitulo']).pack(pady=10)

        main_frame = tk.Frame(win)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # --- Opção 1: Banco Agro ---
        valor_total_fazendas = sum(f['custo'] for f in self.fazendas)
        limite_agro = valor_total_fazendas * 0.50
        
        lf_agro = tk.LabelFrame(main_frame, text="Banco Agro", font=self.ui_fonts['font_subtitulo'], fg="#006400", padx=10, pady=5)
        lf_agro.pack(fill="x", pady=5)
        
        desc_agro = "Juros: 2% ao mês (0.5% por semana)\n" \
                    f"Limite: {formatar_moeda(limite_agro)} (50% do valor de suas fazendas)\n" \
                    "Garantia: Uma de suas fazendas (aleatória)\n" \
                    "Prazo para quitar: 12 semanas"
        tk.Label(lf_agro, text=desc_agro, font=self.ui_fonts['font_corpo'], justify="left").pack(anchor="w")

        frame_input_agro = tk.Frame(lf_agro)
        frame_input_agro.pack(fill="x", pady=5)
        tk.Label(frame_input_agro, text="Valor: $", font=self.ui_fonts['font_corpo']).pack(side="left")
        entry_agro = tk.Entry(frame_input_agro, font=self.ui_fonts['font_corpo'])
        entry_agro.pack(side="left", fill="x", expand=True)
        
        btn_agro = tk.Button(frame_input_agro, text="Pegar", command=lambda e=entry_agro: self._pegar_emprestimo(
            win, e.get(), limite_agro, 0.02, "Banco Agro", "fazenda"
        ))
        btn_agro.pack(side="right", padx=5)
        if not self.fazendas: btn_agro.config(state="disabled")

        # --- Opção 2: Banco Popular ---
        limite_popular = 30000.0
        lf_popular = tk.LabelFrame(main_frame, text="Banco Popular", font=self.ui_fonts['font_subtitulo'], fg="#4682B4", padx=10, pady=5)
        lf_popular.pack(fill="x", pady=5)

        desc_popular = "Juros: 5% ao mês (1.25% por semana)\n" \
                       f"Limite: {formatar_moeda(limite_popular)} (fixo)\n" \
                       "Garantia: Nenhuma (afeta reputação se não pago)\n" \
                       "Prazo para quitar: 24 semanas"
        tk.Label(lf_popular, text=desc_popular, font=self.ui_fonts['font_corpo'], justify="left").pack(anchor="w")

        frame_input_popular = tk.Frame(lf_popular)
        frame_input_popular.pack(fill="x", pady=5)
        tk.Label(frame_input_popular, text="Valor: $", font=self.ui_fonts['font_corpo']).pack(side="left")
        entry_popular = tk.Entry(frame_input_popular, font=self.ui_fonts['font_corpo'])
        entry_popular.pack(side="left", fill="x", expand=True)
        btn_popular = tk.Button(frame_input_popular, text="Pegar", font=self.ui_fonts['font_botao'], command=lambda e=entry_popular: self._pegar_emprestimo(
            win, e.get(), limite_popular, 0.05, "Banco Popular", "nenhuma"
        ))
        btn_popular.pack(side="right", padx=5)

        # --- Opção 3: Fintech Rural ---
        valor_total_maquinas = sum(m['preco'] for m in self.meus_equipamentos)
        limite_fintech = valor_total_maquinas * 0.80
        
        lf_fintech = tk.LabelFrame(main_frame, text="Fintech Rural", font=self.ui_fonts['font_subtitulo'], fg="#8B4513", padx=10, pady=5)
        lf_fintech.pack(fill="x", pady=5)
        
        desc_fintech = "Juros: 12% ao mês (3% por semana)\n" \
                       f"Limite: {formatar_moeda(limite_fintech)} (80% do valor de suas máquinas)\n" \
                       "Garantia: Todos os seus equipamentos\n" \
                       "Prazo para quitar: 12 semanas"
        tk.Label(lf_fintech, text=desc_fintech, font=self.ui_fonts['font_corpo'], justify="left").pack(anchor="w")

        frame_input_fintech = tk.Frame(lf_fintech)
        frame_input_fintech.pack(fill="x", pady=5)
        tk.Label(frame_input_fintech, text="Valor: $", font=self.ui_fonts['font_corpo']).pack(side="left")
        entry_fintech = tk.Entry(frame_input_fintech, font=self.ui_fonts['font_corpo'])
        entry_fintech.pack(side="left", fill="x", expand=True)
        btn_fintech = tk.Button(frame_input_fintech, text="Pegar", font=self.ui_fonts['font_botao'], command=lambda e=entry_fintech: self._pegar_emprestimo(
            win, e.get(), limite_fintech, 0.12, "Fintech Rural", "maquinas"
        ))
        btn_fintech.pack(side="right", padx=5)
        if not self.meus_equipamentos: btn_fintech.config(state="disabled")

    def _pegar_emprestimo(self, window, valor_str, limite, juros_mes, banco, tipo_garantia):
        try:
            valor = float(valor_str)
        except (ValueError, TypeError):
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Valor Inválido", "Por favor, insira um número válido.", parent=window)
            return

        if valor <= 0:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Valor Inválido", "O valor do empréstimo deve ser positivo.", parent=window)
            return

        if valor > limite:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Limite Excedido", f"O valor pedido excede seu limite de {formatar_moeda(limite)} com o {banco}.", parent=window)
            return

        garantia_data = None
        garantia_desc = "Nenhuma"
        
        if tipo_garantia == "fazenda":
            if not self.fazendas:
                self._pausar_e_exibir_dialogo(messagebox.showerror, "Sem Garantia", "Você não possui fazendas para usar como garantia no Banco Agro.", parent=window)
                return
            fazenda_garantia = random.choice(self.fazendas)
            garantia_data = {"tipo": "fazenda", "id": fazenda_garantia["id"]}
            garantia_desc = f"Fazenda '{fazenda_garantia.get('nome_personalizado', fazenda_garantia['nome'])}'"
            
        elif tipo_garantia == "maquinas":
            if not self.meus_equipamentos:
                self._pausar_e_exibir_dialogo(messagebox.showerror, "Sem Garantia", "Você não possui equipamentos para usar como garantia na Fintech Rural.", parent=window)
                return
            garantia_data = {"tipo": "maquinas"}
            garantia_desc = "Todos os Equipamentos"
        
        prazo_semanas = 24 if tipo_garantia == "nenhuma" else 12
        semana_atual = self.dia // 7

        novo_emprestimo = {
            "id": f"emp_{self.dia}_{random.randint(100,999)}",
            "banco": banco,
            "valor_inicial": valor,
            "valor_devido": valor,
            "juros_semana": juros_mes / 4,
            "semana_inicio": semana_atual,
            "prazo_semanas": prazo_semanas,
            "garantia": garantia_data,
            "garantia_desc": garantia_desc
        }

        self.emprestimos_ativos.append(novo_emprestimo)
        self.dinheiro += valor
        
        self.log(f"Pegou empréstimo de {formatar_moeda(valor)} com {banco}. Garantia: {garantia_desc}.")
        self.atualizar_ui_geral()
        window.destroy()

    def pagar_emprestimo(self):
        sel = self.tree_emprestimos.selection()
        if not sel:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Nenhuma Seleção", "Selecione um empréstimo na lista para pagar.")
            return

        id_emprestimo = sel[0]
        emprestimo_alvo = next((e for e in self.emprestimos_ativos if e["id"] == id_emprestimo), None)

        if not emprestimo_alvo:
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Erro", "Empréstimo não encontrado. A lista pode estar desatualizada.")
            self.atualizar_ui_geral()
            return
            
        valor_devido = emprestimo_alvo["valor_devido"]
        
        valor_pagar_str = simpledialog.askstring("Pagar Empréstimo", 
                                                 f"Banco: {emprestimo_alvo['banco']}\nValor devido: {formatar_moeda(valor_devido)}\n\nQuanto você deseja pagar?",
                                                 parent=self.root)
        
        if not valor_pagar_str: return

        try:
            valor_pago = float(valor_pagar_str)
        except ValueError:
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Valor Inválido", "Por favor, digite um número.")
            return

        if valor_pago <= 0:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Valor Inválido", "O valor a ser pago deve ser positivo.")
            return
            
        if valor_pago > self.dinheiro:
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Sem Dinheiro", "Você não tem dinheiro suficiente para fazer este pagamento.")
            return
        
        # Calcular valor máximo de pagamento (clamp)
        valor_pago = calcular_valor_pagamento_max(valor_pago, valor_devido)

        self.dinheiro -= valor_pago
        quitado, _ = processar_pagamento(emprestimo_alvo, valor_pago)
        
        if quitado:
            self.emprestimos_ativos.remove(emprestimo_alvo)
            self.log(f"Empréstimo com {emprestimo_alvo['banco']} foi quitado! (Pagamento final: {formatar_moeda(valor_pago)})")
        else:
            self.log(f"Amortizou {formatar_moeda(valor_pago)} do empréstimo com {emprestimo_alvo['banco']}.")

        self.atualizar_ui_geral()

    def atualizar_aba_financas(self):
        if not hasattr(self, 'tree_emprestimos'): return
        for i in self.tree_emprestimos.get_children(): self.tree_emprestimos.delete(i)

        self.tree_emprestimos.tag_configure('vencendo', foreground='orange', font=self.ui_fonts['font_botao'])
        self._configurar_ordenacao_treeview(self.tree_emprestimos, colunas_numericas=['Valor Devido'])

        semana_atual = self.dia // 7
        for emp in self.emprestimos_ativos:
            semanas_restantes = calcular_semanas_restantes(emp, semana_atual)
            
            prazo_str = f"{semanas_restantes} sem."
            
            tags = ()
            if semanas_restantes <= 4:
                tags = ('vencendo',)

            self.tree_emprestimos.insert("", "end", iid=emp["id"], tags=tags, values=(
                emp["id"], # Oculto
                emp["banco"],
                formatar_moeda(emp['valor_devido']),
                f"{emp['juros_semana']*4*100:.1f}%",
                emp["garantia_desc"],
                prazo_str
            ))

    # ------------------------------------------------------------------
    # LÓGICA DE TEMPO AUTOMÁTICA
    # ------------------------------------------------------------------
    def _pausar_e_exibir_dialogo(self, dialog_func, *args, **kwargs):
        """
        Pausa o jogo, exibe um diálogo e retoma a velocidade anterior.
        Garante que o jogo fica pausado enquanto o diálogo estiver aberto.
        """
        velocidade_anterior = self.velocidade_atual
        
        # Pausa o jogo se não estiver já pausado
        if velocidade_anterior > 0:
            self.velocidade_atual = 0
            # Cancela loop temporal se existir
            if self.job_tempo is not None:
                self.root.after_cancel(self.job_tempo)
                self.job_tempo = None
        
        try:
            # Exibe o diálogo (bloqueia até ser fechado)
            return dialog_func(*args, **kwargs)
        finally:
            # Restaura velocidade anterior após o diálogo fechar
            if velocidade_anterior > 0 and velocidade_anterior != self.velocidade_atual:
                self.alterar_velocidade(velocidade_anterior)
    
    def alterar_velocidade(self, mult):
        self.velocidade_atual = mult
        
        # Cancela loop anterior se existir para não acumular
        if self.job_tempo is not None:
            self.root.after_cancel(self.job_tempo)
            self.job_tempo = None
        
        # Atualiza visual dos botões
        for k, btn in self.btns_tempo.items():
            if k == mult:
                btn.config(relief="sunken", bg="#90EE90") # Botão pressionado fica verde
            else:
                btn.config(relief="raised", bg="SystemButtonFace")
                if k == 0: btn.config(bg="#ffcccc") # Mantém pausa levemente vermelho se inativo

        # Se não for pausa, inicia o loop
        if mult > 0:
            self.loop_temporal()

    def loop_temporal(self):
        # 1. Executa a lógica de passar a semana
        self.passar_dia()
        
        # 2. Verifica se o jogo ainda está rodando (se não foi pausado no meio do processo)
        if self.velocidade_atual > 0:
            # Calcula o delay: 3000ms dividido pelo multiplicador
            delay = int(self.base_delay / self.velocidade_atual)
            
            # Agenda a próxima execução
            self.job_tempo = self.root.after(delay, self.loop_temporal)

    # ------------------------------------------------------------------
    # MONTAGEM DAS ABAS (INALTERADO)
    # ------------------------------------------------------------------
    def montar_aba_agricultura(self):
        paned = tk.PanedWindow(self.tab_agro, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        frame_seeds = tk.LabelFrame(paned, text="Sementes")
        paned.add(frame_seeds, width=500)
        
        colunas = ("Nome", "Nvl", "Solo", "Ciclo", "Custo", "Venda Atual")
        self.tree_agro = ttk.Treeview(frame_seeds, columns=colunas, show="headings", selectmode="extended")
        self.tree_agro.heading("Nome", text="Cultura")
        self.tree_agro.heading("Nvl", text="Lv.")
        self.tree_agro.heading("Solo", text="Solo")
        self.tree_agro.heading("Ciclo", text="Dias")
        self.tree_agro.heading("Custo", text="Custo Plantio")
        self.tree_agro.heading("Venda Atual", text="Receita/ha (Mercado)")
        self.tree_agro.column("Nvl", width=30)
        self.tree_agro.column("Solo", width=60)
        self.tree_agro.column("Ciclo", width=40)
        self.tree_agro.column("Custo", width=100, anchor="e")
        self.tree_agro.column("Venda Atual", width=120, anchor="e")
        
        self.tree_agro.tag_configure('bloqueado', foreground='#999999')
        self._configurar_ordenacao_treeview(self.tree_agro, colunas_numericas=["Nvl", "Ciclo", "Custo", "Venda Atual"])
        self.tree_agro.pack(fill="both", expand=True)
        
        # Filtro simples
        frame_filtro_agro = tk.Frame(frame_seeds)
        frame_filtro_agro.pack(fill="x", pady=(5, 0))
        tk.Label(frame_filtro_agro, text="Filtrar:").pack(side="left", padx=(0, 5))
        self.entry_filtro_agro = tk.Entry(frame_filtro_agro)
        self.entry_filtro_agro.pack(side="left", fill="x", expand=True)
        self.entry_filtro_agro.bind('<KeyRelease>', lambda e: self._aplicar_filtro_treeview(self.tree_agro, self.entry_filtro_agro.get()))

        frame_botoes_agro = tk.Frame(frame_seeds)
        frame_botoes_agro.pack(fill="x")
        tk.Button(frame_botoes_agro, text="Plantar na Fazenda Selecionada", font=self.ui_fonts['font_botao'], bg="#90EE90", command=self.plantar).pack(side="right", fill="x", expand=True)
        
        frame_farm = tk.LabelFrame(paned, text="Minhas Fazendas")
        paned.add(frame_farm)

        # Este label mostrará um resumo de todas as fazendas
        self.lbl_slots_disponiveis = tk.Label(frame_farm, text="", font=("Arial", 11, "bold"))
        self.lbl_slots_disponiveis.pack(pady=2, fill='x')
        
        # O notebook que conterá uma aba para cada fazenda
        self.notebook_fazendas = ttk.Notebook(frame_farm)
        self.notebook_fazendas.pack(fill="both", expand=True, padx=5, pady=5)

    def montar_aba_maquinas(self):
        paned = tk.PanedWindow(self.tab_maq, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        frame_loja = tk.LabelFrame(paned, text="Catálogo")
        paned.add(frame_loja, width=650)
        
        cols = ("Nome", "Nvl", "Efeito", "Custo", "Manut")
        self.tree_maq_loja = ttk.Treeview(frame_loja, columns=cols, show="headings")
        self.tree_maq_loja.heading("Nome", text="Modelo")
        self.tree_maq_loja.heading("Nvl", text="Lv.")
        self.tree_maq_loja.heading("Efeito", text="Efeito")
        self.tree_maq_loja.heading("Custo", text="Preço")
        self.tree_maq_loja.heading("Manut", text="Manut./Sem")
        self.tree_maq_loja.column("Nvl", width=30)
        self.tree_maq_loja.column("Efeito", width=120)
        
        self.tree_maq_loja.tag_configure('bloqueado', foreground='#999999')
        self.tree_maq_loja.pack(fill="both", expand=True)
        
        tk.Button(frame_loja, text="Comprar", font=self.ui_fonts['font_botao'], bg="#87CEEB", command=self.comprar_maquina).pack(fill="x")
        
        frame_garagem = tk.LabelFrame(paned, text="Minha Garagem")
        paned.add(frame_garagem)
        
        self.lbl_resumo_maquinas = tk.Label(frame_garagem, text="Resumo de Bônus Ativos:", font=("Arial", 11, "bold"), fg="#333")
        self.lbl_resumo_maquinas.pack(pady=(5,0))
        self.lbl_limite_maquinas = tk.Label(frame_garagem, text="Garagem: 0 / 0", font=("Arial", 11, "bold"), fg="#333")
        self.lbl_limite_maquinas.pack(pady=(0,5))
        
        self.lista_garagem = tk.Listbox(frame_garagem, selectmode="extended", font=self.ui_fonts['font_corpo'])
        self.lista_garagem.pack(fill="both", expand=True)
        tk.Button(frame_garagem, text="Vender", font=self.ui_fonts['font_botao'], bg="#FF6347", command=self.vender_maquina).pack(fill="x")

    def montar_aba_imobiliaria(self):
        paned_imob = tk.PanedWindow(self.tab_imob, orient="horizontal")
        paned_imob.pack(fill="both", expand=True, padx=5, pady=5)

        # --- PAINEL DE COMPRA ---
        frame_loja = tk.LabelFrame(paned_imob, text="Propriedades Disponíveis (Compra)")
        paned_imob.add(frame_loja, width=600)
        
        cols_loja = ("Nome", "Tamanho", "Solo", "Custo")
        self.tree_imob_loja = ttk.Treeview(frame_loja, columns=cols_loja, show="headings", selectmode="browse")
        self.tree_imob_loja.heading("Nome", text="Propriedade")
        self.tree_imob_loja.heading("Tamanho", text="Tamanho (ha)")
        self.tree_imob_loja.heading("Solo", text="Tipo de Solo")
        self.tree_imob_loja.heading("Custo", text="Preço")
        self.tree_imob_loja.column("Tamanho", width=80, anchor="e")
        self.tree_imob_loja.column("Solo", width=100)
        self.tree_imob_loja.column("Custo", width=90, anchor="e")
        self.tree_imob_loja.pack(fill="both", expand=True)
        tk.Button(frame_loja, text="Comprar Propriedade Selecionada", font=self.ui_fonts['font_botao'], bg="#87CEEB", command=self.comprar_fazenda).pack(fill="x", pady=(5,0))

        # --- PAINEL DE VENDA ---
        frame_venda = tk.LabelFrame(paned_imob, text="Minhas Propriedades (Venda)")
        paned_imob.add(frame_venda)

        cols_venda = ("id", "Nome", "Tamanho", "Ocupação", "Valor Venda")
        self.tree_imob_venda = ttk.Treeview(frame_venda, columns=cols_venda, show="headings", selectmode="browse")
        self.tree_imob_venda.column("id", width=0, stretch=tk.NO) # Coluna oculta
        self.tree_imob_venda.heading("Nome", text="Propriedade")
        self.tree_imob_venda.heading("Tamanho", text="Tamanho (ha)")
        self.tree_imob_venda.heading("Ocupação", text="Ocupado")
        self.tree_imob_venda.heading("Valor Venda", text="Valor Venda")
        self.tree_imob_venda.column("Tamanho", width=80, anchor="e")
        self.tree_imob_venda.column("Ocupação", width=80, anchor="c")
        self.tree_imob_venda.column("Valor Venda", width=100, anchor="e")
        self.tree_imob_venda.pack(fill="both", expand=True)
        tk.Button(frame_venda, text="Vender Propriedade Selecionada", font=self.ui_fonts['font_botao'], bg="#FF6347", command=self.vender_fazenda).pack(fill="x", pady=(5,0))

    def montar_aba_mercado(self):
        frame_mercado = tk.LabelFrame(self.tab_mercado, text="Preços de Venda das Culturas")
        frame_mercado.pack(fill="both", expand=True, padx=10, pady=5)

        colunas = ('Cultura', 'Preco Base', 'Tendencia', 'Preco Atual')
        self.tree_mercado = ttk.Treeview(frame_mercado, columns=colunas, show="headings")
        self.tree_mercado.heading('Cultura', text='Cultura')
        self.tree_mercado.heading('Preco Base', text='Preço Base (p/ kg)')
        self.tree_mercado.heading('Tendencia', text='Tendência')
        self.tree_mercado.heading('Preco Atual', text='Preço Atual (p/ kg)')

        self.tree_mercado.column('Preco Base', width=120, anchor='e')
        self.tree_mercado.column('Tendencia', width=100, anchor='c')
        self.tree_mercado.column('Preco Atual', width=120, anchor='e')
        
        self.tree_mercado.tag_configure('alta', foreground='green')
        self.tree_mercado.tag_configure('baixa', foreground='red')
        self._configurar_ordenacao_treeview(self.tree_mercado, colunas_numericas=['Preco Base', 'Preco Atual'])
        
        # Filtro simples
        frame_filtro_mercado = tk.Frame(frame_mercado)
        frame_filtro_mercado.pack(fill="x", pady=(5, 0))
        tk.Label(frame_filtro_mercado, text="Filtrar:").pack(side="left", padx=(0, 5))
        self.entry_filtro_mercado = tk.Entry(frame_filtro_mercado)
        self.entry_filtro_mercado.pack(side="left", fill="x", expand=True)
        self.entry_filtro_mercado.bind('<KeyRelease>', lambda e: self._aplicar_filtro_treeview(self.tree_mercado, self.entry_filtro_mercado.get()))

        self.tree_mercado.pack(fill="both", expand=True)


    def montar_aba_logistica(self):
        paned = tk.PanedWindow(self.tab_logistica, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=5, pady=5)

        # --- PAINEL DE ESTOQUE ---
        frame_estoque = tk.LabelFrame(paned, text="Meu Estoque")
        paned.add(frame_estoque, width=700)
        
        cols = ('id', 'Cultura', 'Qtd (kg)', 'Custo/kg', 'Preço Mercado', 'Margem Est. (%)')
        self.tree_estoque = ttk.Treeview(frame_estoque, columns=cols, show="headings", selectmode="browse")
        self.tree_estoque.column("id", width=0, stretch=tk.NO) # Oculto
        self.tree_estoque.heading('Cultura', text='Cultura')
        self.tree_estoque.heading('Qtd (kg)', text='Qtd (kg)')
        self.tree_estoque.heading('Custo/kg', text='Custo/kg')
        self.tree_estoque.heading('Preço Mercado', text='Preço Mercado')
        self.tree_estoque.heading('Margem Est. (%)', text='Margem Est. (%)')
        self.tree_estoque.column('Qtd (kg)', anchor='e')
        self.tree_estoque.column('Custo/kg', anchor='e')
        self.tree_estoque.column('Preço Mercado', anchor='e')
        self.tree_estoque.column('Margem Est. (%)', anchor='e')
        self.tree_estoque.tag_configure('alta', foreground='green')
        self._configurar_ordenacao_treeview(self.tree_estoque, colunas_numericas=['Qtd (kg)', 'Custo/kg', 'Preço Mercado', 'Margem Est. (%)'])
        self.tree_estoque.pack(fill="both", expand=True)
        
        # Filtro simples
        frame_filtro_estoque = tk.Frame(frame_estoque)
        frame_filtro_estoque.pack(fill="x", pady=(5, 0))
        tk.Label(frame_filtro_estoque, text="Filtrar:").pack(side="left", padx=(0, 5))
        self.entry_filtro_estoque = tk.Entry(frame_filtro_estoque)
        self.entry_filtro_estoque.pack(side="left", fill="x", expand=True)
        self.entry_filtro_estoque.bind('<KeyRelease>', lambda e: self._aplicar_filtro_treeview(self.tree_estoque, self.entry_filtro_estoque.get()))
        
        tk.Button(frame_estoque, text="Vender Lote Selecionado", font=self.ui_fonts['font_botao'], bg="#FF6347", command=self.vender_lote_estoque).pack(fill="x", pady=(5,0))

        # --- PAINEL DE CONTROLES ---
        frame_controles = tk.LabelFrame(paned, text="Controles e Automação")
        paned.add(frame_controles)

        # Controles do Gerente
        frame_gerente = tk.LabelFrame(frame_controles, text="Ação Padrão do Gerente")
        frame_gerente.pack(fill="x", padx=10, pady=10)
        
        tk.Label(frame_gerente, text="Ao colher, o gerente deve:").pack(pady=(5,2))
        self.combo_gerente_colheita = ttk.Combobox(frame_gerente, values=["Sempre Vender", "Sempre Armazenar"], state="readonly")
        self.combo_gerente_colheita.pack(pady=(2,10), padx=10, fill="x")
        self.combo_gerente_colheita.bind("<<ComboboxSelected>>", self.mudar_config_gerente)


        # Gatilho de Venda Automática
        frame_gatilho = tk.LabelFrame(frame_controles, text="Gatilho de Venda Automática")
        frame_gatilho.pack(fill="x", padx=10, pady=10)

        tk.Checkbutton(frame_gatilho, text="Ativar venda automática de lotes", font=self.ui_fonts['font_corpo'], variable=self.gatilho_venda_automatica_ativo).pack(anchor="w", padx=5)
        
        self.lbl_gatilho_margem = tk.Label(frame_gatilho, text="", font=self.ui_fonts['font_corpo'])
        self.lbl_gatilho_margem.pack(pady=(5,0))

        self.scale_gatilho_venda = tk.Scale(frame_gatilho, from_=0, to=100, orient="horizontal", variable=self.gatilho_venda_automatica_margem, command=self.atualizar_label_gatilho)
        self.scale_gatilho_venda.pack(fill="x", padx=5, pady=(0,10))

    def atualizar_aba_logistica(self):
        if not hasattr(self, 'tree_estoque'): return
        
        # Limpa a árvore
        for i in self.tree_estoque.get_children(): self.tree_estoque.delete(i)
        
        # Popula com dados do estoque
        for i, lote in enumerate(self.estoque):
            cultura_base = lote["dados_base"]
            
            # Calcula preço de mercado e margem
            mult_mercado = self.mercado_multiplicadores.get(cultura_base["nome"], 1.0)
            preco_mercado_atual_kg = preco_mercado_atual(cultura_base["preco_venda"], mult_mercado)
            
            margem_lucro = margem_percentual(preco_mercado_atual_kg, lote["custo_producao_por_kg"])

            tags = ()
            if margem_lucro > self.gatilho_venda_automatica_margem.get():
                tags = ('alta',) if self.gatilho_venda_automatica_ativo.get() else ()

            self.tree_estoque.insert("", "end", iid=str(i), tags=tags, values=(
                i, # ID oculto
                cultura_base["nome"],
                f"{lote['quantidade_kg']:,.0f}",
                formatar_moeda(lote['custo_producao_por_kg']),
                formatar_moeda(preco_mercado_atual_kg),
                f"{margem_lucro:.1f}%"
            ))
        
        # Reaplicar filtro se existir
        if hasattr(self, 'entry_filtro_estoque') and self.entry_filtro_estoque.get():
            self._aplicar_filtro_treeview(self.tree_estoque, self.entry_filtro_estoque.get())

        # Atualiza controles
        self.combo_gerente_colheita.set(self.config_gerente["acao_colheita"])
        self.atualizar_label_gatilho()


    def mudar_config_gerente(self, event=None):
        nova_config = self.combo_gerente_colheita.get()
        if nova_config in ["Sempre Vender", "Sempre Armazenar"]:
            self.config_gerente["acao_colheita"] = nova_config
            self.log(f"Configuração do gerente alterada para: {nova_config}")

    def atualizar_label_gatilho(self, event=None):
        if hasattr(self, 'lbl_gatilho_margem'):
            margem = self.gatilho_venda_automatica_margem.get()
            self.lbl_gatilho_margem.config(text=f"Vender lotes com lucro > {margem:.0f}%")
            # A chamada para atualizar_aba_logistica() foi movida para evitar recursão infinita
            # e será chamada explicitamente quando necessário.
            if event: # Apenas atualiza a cor da treeview se for uma ação do usuário
                self.atualizar_cores_logistica()

    def atualizar_cores_logistica(self):
        if not hasattr(self, 'tree_estoque'): return
        for iid in self.tree_estoque.get_children():
            item = self.tree_estoque.item(iid)
            values = item['values']
            if not values: continue

            margem_str = str(values[5]).replace('%', '')
            try:
                margem_lucro = float(margem_str)
                if margem_lucro > self.gatilho_venda_automatica_margem.get() and self.gatilho_venda_automatica_ativo.get():
                    self.tree_estoque.item(iid, tags=('alta',))
                else:
                    self.tree_estoque.item(iid, tags=())
            except (ValueError, IndexError):
                self.tree_estoque.item(iid, tags=())


    def vender_lote_estoque(self):
        sel = self.tree_estoque.selection()
        if not sel:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Nenhum Lote", "Selecione um lote do estoque para vender.")
            return

        item_id = int(self.tree_estoque.item(sel[0])["values"][0])
        
        # Como a lista pode mudar, precisamos re-encontrar o lote certo se formos vender múltiplos
        if item_id >= len(self.estoque):
             self._pausar_e_exibir_dialogo(messagebox.showerror, "Erro", "O lote selecionado não existe mais. A lista foi atualizada.")
             self.atualizar_ui_geral()
             return

        lote = self.estoque[item_id]
        
        cultura_base = lote["dados_base"]
        mult_mercado = self.mercado_multiplicadores.get(cultura_base["nome"], 1.0)
        preco_mercado_atual_kg = preco_mercado_atual(cultura_base["preco_venda"], mult_mercado)
        
        valor_venda_total = lote["quantidade_kg"] * preco_mercado_atual_kg
        custo_total = lote["quantidade_kg"] * lote["custo_producao_por_kg"]
        lucro = valor_venda_total - custo_total

        msg = f"Vender {lote['quantidade_kg']:,.0f} kg de {cultura_base['nome']} por {formatar_moeda(valor_venda_total)}?\nLucro estimado: {formatar_moeda(lucro)}"
        if self._pausar_e_exibir_dialogo(messagebox.askyesno, "Confirmar Venda", msg):
            self.dinheiro += valor_venda_total
            self.log(f"Vendeu lote de {cultura_base['nome']} do estoque. Receita: {formatar_moeda(valor_venda_total)}.")
            
            self.estoque.pop(item_id)
            self.atualizar_ui_geral()


    def renomear_fazenda(self, id_fazenda):
        fazenda_alvo = next((f for f in self.fazendas if f["id"] == id_fazenda), None)
        if not fazenda_alvo:
            return

        nome_antigo = fazenda_alvo.get("nome_personalizado", fazenda_alvo["nome"])
        novo_nome = simpledialog.askstring("Renomear Propriedade", f"Digite o novo nome para '{nome_antigo}':", initialvalue=nome_antigo)

        if novo_nome and novo_nome != nome_antigo:
            fazenda_alvo["nome_personalizado"] = novo_nome
            self.log(f"A propriedade '{nome_antigo}' foi renomeada para '{novo_nome}'.")
            self.atualizar_ui_geral()

    def get_salario_gerente(self, fazenda):
        return salario_gerente(self.salarios_gerente, fazenda["tam"])

    def contratar_gerente(self, id_fazenda):
        fazenda_alvo = next((f for f in self.fazendas if f["id"] == id_fazenda), None)
        if not fazenda_alvo: return

        # Verificar nível mínimo
        if self.nivel < 2:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Nível Insuficiente", "Contratar gerentes está disponível apenas a partir do nível 2.")
            return

        salario = self.get_salario_gerente(fazenda_alvo)
        if salario == 0:
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Erro", "Tamanho de fazenda não compatível com a contratação de gerentes.")
            return

        msg = f"Contratar um gerente para '{fazenda_alvo.get('nome_personalizado', fazenda_alvo['nome'])}' custará {formatar_moeda(salario)} a cada 4 semanas. Deseja continuar?"
        if self._pausar_e_exibir_dialogo(messagebox.askyesno, "Contratar Gerente", msg):
            fazenda_alvo["tem_gerente"] = True
            self.log(f"Gerente contratado para {fazenda_alvo.get('nome_personalizado', fazenda_alvo['nome'])}.")
            self.atualizar_ui_geral()

    def demitir_gerente(self, id_fazenda):
        fazenda_alvo = next((f for f in self.fazendas if f["id"] == id_fazenda), None)
        if not fazenda_alvo: return

        if not fazenda_alvo.get("tem_gerente"):
             self._pausar_e_exibir_dialogo(messagebox.showinfo, "Informação", "Esta fazenda não possui um gerente.")
             return

        salario = self.get_salario_gerente(fazenda_alvo)
        custo_demissao = salario * 0.5

        msg = f"Demitir o gerente de '{fazenda_alvo.get('nome_personalizado', fazenda_alvo['nome'])}' terá um custo de {formatar_moeda(custo_demissao)}. Deseja continuar?"
        if self._pausar_e_exibir_dialogo(messagebox.askyesno, "Demitir Gerente", msg):
            if self.dinheiro < custo_demissao:
                self._pausar_e_exibir_dialogo(messagebox.showerror, "Sem Dinheiro", "Você não tem dinheiro suficiente para pagar a demissão.")
                return
            
            self.dinheiro -= custo_demissao
            fazenda_alvo["tem_gerente"] = False
            self.log(f"Gerente de {fazenda_alvo.get('nome_personalizado', fazenda_alvo['nome'])} foi demitido.")
            self.atualizar_ui_geral()

    def escolher_cultura_para_gerente(self, id_fazenda):
        fazenda_alvo = next((f for f in self.fazendas if f["id"] == id_fazenda), None)
        if not fazenda_alvo: return

        win = tk.Toplevel(self.root)
        win.title(f"Definir Cultura para Gerente")
        win.geometry("400x350")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text=f"Selecione a cultura que o gerente da fazenda\n'{fazenda_alvo.get('nome_personalizado')}' deverá plantar.", font=self.ui_fonts['font_corpo'], justify="center").pack(pady=10)

        listbox = tk.Listbox(win, exportselection=False, font=self.ui_fonts['font_corpo'])
        listbox.pack(fill="both", expand=True, padx=10, pady=5)

        # Adiciona a opção automática
        listbox.insert("end", "Modo Automático (padrão)")
        listbox.itemconfig("end", {'bg':'#D3D3D3'})


        culturas_disponiveis = [c for c in self.culturas_catalogo if self.nivel >= c["nivel_req"]]
        culturas_disponiveis.sort(key=lambda c: c["nome"])
        
        for cultura in culturas_disponiveis:
            listbox.insert("end", f"{cultura['nome']}")

        # Pré-selecionar a opção atual
        cultura_atual = fazenda_alvo.get("gerente_cultura", "Automatica")
        if cultura_atual == "Automatica":
            listbox.selection_set(0)
        else:
            for i, cultura in enumerate(culturas_disponiveis):
                if cultura["nome"] == cultura_atual:
                    listbox.selection_set(i + 1) # +1 por causa do modo automático
                    break

        def on_ok():
            selecionado = listbox.curselection()
            if not selecionado:
                win.destroy()
                return

            index = selecionado[0]
            if index == 0:
                fazenda_alvo["gerente_cultura"] = "Automatica"
                self.log(f"Gerente de '{fazenda_alvo.get('nome_personalizado')}' definido para o modo de plantio automático.")
            else:
                cultura_selecionada = culturas_disponiveis[index - 1]
                fazenda_alvo["gerente_cultura"] = cultura_selecionada["nome"]
                self.log(f"Gerente de '{fazenda_alvo.get('nome_personalizado')}' irá focar em plantar '{cultura_selecionada['nome']}'.")
            
            self.atualizar_ui_geral()
            win.destroy()

        def on_cancel():
            win.destroy()

        frame_botoes = tk.Frame(win)
        frame_botoes.pack(fill='x', padx=10, pady=10)
        tk.Button(frame_botoes, text="Confirmar", font=self.ui_fonts['font_botao'], command=on_ok, bg="#90EE90").pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(frame_botoes, text="Cancelar", font=self.ui_fonts['font_botao'], command=on_cancel).pack(side="right", fill="x", expand=True, padx=5)

    def abrir_configuracao_gerente(self, id_fazenda):
        fazenda_alvo = next((f for f in self.fazendas if f["id"] == id_fazenda), None)
        if not fazenda_alvo: return

        # Verificar nível mínimo
        if self.nivel < 2:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Nível Insuficiente", "Contratar gerentes está disponível apenas a partir do nível 2.")
            return

        # Se não tiver gerente, pergunta se quer contratar
        if not fazenda_alvo.get("tem_gerente"):
            self.contratar_gerente(id_fazenda)
            return

        # Se JÁ tem gerente, abre o menu de opções
        win = tk.Toplevel(self.root)
        win.title(f"Gerenciar '{fazenda_alvo.get('nome_personalizado')}'")
        win.geometry("350x200")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="O que você deseja fazer?", font=("Arial", 14)).pack(pady=15)

        def demitir_e_fechar():
            win.destroy() # Fecha a janela de config ANTES de abrir o messagebox de demissão
            self.demitir_gerente(id_fazenda)

        def definir_cultura_e_fechar():
            win.destroy()
            self.escolher_cultura_para_gerente(id_fazenda)

        tk.Button(win, text="Definir Cultura de Plantio", font=self.ui_fonts['font_botao'], command=definir_cultura_e_fechar, height=2).pack(fill="x", padx=20, pady=5)
        tk.Button(win, text="Demitir Gerente", font=self.ui_fonts['font_botao'], command=demitir_e_fechar, bg="#FF9999", height=2).pack(fill="x", padx=20, pady=5)

    def vender_fazenda(self):
        sel = self.tree_imob_venda.selection()
        if not sel:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Nenhuma Seleção", "Selecione uma de suas propriedades para vender.")
            return
            
        item_selecionado = self.tree_imob_venda.item(sel[0])
        id_fazenda = item_selecionado['values'][0]
        fazenda_alvo = next((f for f in self.fazendas if f["id"] == id_fazenda), None)
        
        if not fazenda_alvo:
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Erro", "Não foi possível encontrar a fazenda para vender.")
            return

        nome_exibido = fazenda_alvo.get("nome_personalizado", fazenda_alvo["nome"])
        # 1. Verificar se a fazenda está vazia
        plantacoes_na_fazenda = self.plantacoes_por_fazenda.get(id_fazenda, [])
        pode_vender, motivo = pode_vender_fazenda(plantacoes_na_fazenda)
        if not pode_vender:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Venda Bloqueada", f"Você não pode vender a fazenda '{nome_exibido}' porque {motivo}")
            return

        # 2. Calcular o preço de venda e confirmar
        preco_venda = preco_venda_propriedade(fazenda_alvo["custo"])
        msg = f"Tem certeza que deseja vender a propriedade '{nome_exibido}' por {formatar_moeda(preco_venda)} (85% do valor de compra)?"
        
        if self._pausar_e_exibir_dialogo(messagebox.askyesno, "Confirmar Venda de Propriedade", msg):
            # 3. Executar a venda
            self.dinheiro += preco_venda
            
            # Remove a fazenda da lista do jogador
            self.fazendas = [f for f in self.fazendas if f["id"] != id_fazenda]
            
            # Remove o registro de plantações (mesmo que vazio)
            if id_fazenda in self.plantacoes_por_fazenda:
                del self.plantacoes_por_fazenda[id_fazenda]
            
            # A UI será completamente atualizada na chamada geral
            self.log(f"Você vendeu a propriedade '{nome_exibido}' por {formatar_moeda(preco_venda)}.")
            self.atualizar_ui_geral()

    def comprar_fazenda(self):
        sel = self.tree_imob_loja.selection()
        if not sel: return
        
        nome_fazenda = self.tree_imob_loja.item(sel[0])['values'][0]
        dados_fazenda = next((f for f in self.propriedades_a_venda if f["nome"] == nome_fazenda), None)
        
        if not dados_fazenda: 
            self._pausar_e_exibir_dialogo(messagebox.showinfo, "Propriedade Indisponível", "Esta propriedade não está mais disponível para compra.")
            self.atualizar_ui_geral()
            return

        pode_comprar, motivo = pode_comprar_propriedade(self.dinheiro, dados_fazenda["custo"])
        if not pode_comprar:
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Sem Dinheiro", motivo)
            return
        
        if self._pausar_e_exibir_dialogo(messagebox.askyesno, "Confirmar Compra", f"Tem certeza que deseja comprar a propriedade '{nome_fazenda}' por {formatar_moeda(dados_fazenda['custo'])}?"):
            
            nova_fazenda = dados_fazenda.copy()
            nova_fazenda["tem_gerente"] = False
            nova_fazenda["gerente_cultura"] = "Automatica"
            novo_nome = simpledialog.askstring("Nomear Propriedade", "Dê um nome para sua nova propriedade:", initialvalue=nova_fazenda["nome"])
            if novo_nome:
                nova_fazenda["nome_personalizado"] = novo_nome
            else:
                nova_fazenda["nome_personalizado"] = nova_fazenda["nome"]

            self.dinheiro -= nova_fazenda["custo"]
            self.fazendas.append(nova_fazenda) 
            self.plantacoes_por_fazenda[nova_fazenda["id"]] = []
            self.log(f"Parabéns! Você comprou a propriedade '{nova_fazenda['nome_personalizado']}'.")
            self.atualizar_ui_geral()

    def atualizar_listas_imobiliaria(self):
        # Limpa as duas listas
        for i in self.tree_imob_loja.get_children(): self.tree_imob_loja.delete(i)
        for i in self.tree_imob_venda.get_children(): self.tree_imob_venda.delete(i)

        # Popula a lista de PROPRIEDADES À VENDA (para comprar)
        ids_fazendas_possuidas = [f["id"] for f in self.fazendas]
        for f in self.propriedades_a_venda:
            # A verificação por ID previne que uma propriedade comprada e renomeada apareça na lista de compra
            if f["id"] not in ids_fazendas_possuidas:
                self.tree_imob_loja.insert("", "end",
                                           values=(f["nome"], f["tam"], f["solo"], formatar_moeda(f['custo'], 0)))

        # Popula a lista de MINHAS PROPRIEDADES (para vender)
        for f in self.fazendas:
            nome_exibido = f.get("nome_personalizado", f["nome"])
            valor_venda = preco_venda_propriedade(f["custo"])
            ocupacao = f"{len(self.plantacoes_por_fazenda.get(f['id'], []))}/{f['tam']} ha"
            self.tree_imob_venda.insert("", "end",
                                        values=(f["id"], nome_exibido, f["tam"], ocupacao, formatar_moeda(valor_venda, 0)))

    # ------------------------------------------------------------------
    # LÓGICA DE JOGO (INALTERADA)
    # ------------------------------------------------------------------
    def atualizar_listas_lojas(self):
        # Salva seleções
        sel_agro_nomes = [self.tree_agro.item(i)['values'][0] for i in self.tree_agro.selection()]
        sel_maq_nomes = [self.tree_maq_loja.item(i)['values'][0] for i in self.tree_maq_loja.selection()]

        for i in self.tree_agro.get_children(): self.tree_agro.delete(i)
        for i in self.tree_maq_loja.get_children(): self.tree_maq_loja.delete(i)
        
        # Repopula e restaura seleção
        ids_para_selecionar_agro = []
        for c in self.culturas_catalogo:
            bloqueado = self.nivel < c["nivel_req"]
            tag = ('bloqueado',) if bloqueado else ()
            
            multiplicador = self.mercado_multiplicadores.get(c["nome"], 1.0)
            preco_venda_kg_atual = c["preco_venda"] * multiplicador
            receita_ha = c["kg_hectare"] * preco_venda_kg_atual

            item_id = self.tree_agro.insert("", "end", 
                                  values=(c["nome"], c["nivel_req"], c["solo_ideal"], int(c["dias_totais"]), formatar_moeda(c['custo_semente'], 0), formatar_moeda(receita_ha, 0)),
                                  tags=tag)
            if c["nome"] in sel_agro_nomes:
                ids_para_selecionar_agro.append(item_id)

        if ids_para_selecionar_agro:
            self.tree_agro.selection_set(ids_para_selecionar_agro)
        
        # Reaplicar filtro se existir
        if hasattr(self, 'entry_filtro_agro') and self.entry_filtro_agro.get():
            self._aplicar_filtro_treeview(self.tree_agro, self.entry_filtro_agro.get())

        ids_para_selecionar_maq = []
        for m in self.maquinas_catalogo:
            bloqueado = self.nivel < m["nivel_req"]
            tag = ('bloqueado',) if bloqueado else ()
            
            if m["funcao"] == "Armazenagem":
                txt_efeito = f"Capacidade: {m['capacidade'] // 1000} t"
            else:
                txt_efeito = f"{m['funcao']} +{int(m['valor_bonus']*100)}%"

            item_id = self.tree_maq_loja.insert("", "end", 
                                      values=(m["nome"], m["nivel_req"], txt_efeito, formatar_moeda(m['preco'], 0), formatar_moeda(m['manutencao'], 1)),
                                      tags=tag)
            if m["nome"] in sel_maq_nomes:
                ids_para_selecionar_maq.append(item_id)

        if ids_para_selecionar_maq:
            self.tree_maq_loja.selection_set(ids_para_selecionar_maq)
        
        # Reaplicar filtro se existir
        if hasattr(self, 'entry_filtro_maq') and self.entry_filtro_maq.get():
            self._aplicar_filtro_treeview(self.tree_maq_loja, self.entry_filtro_maq.get())

    def plantar(self):
        # 1. Identificar a fazenda selecionada na UI
        if not self.notebook_fazendas or not self.notebook_fazendas.tabs():
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Nenhuma Fazenda", "Você precisa comprar uma propriedade antes de plantar.")
            return
            
        aba_selecionada_id = self.notebook_fazendas.select()
        if not aba_selecionada_id:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Selecione uma Fazenda", "Selecione a aba da fazenda onde deseja plantar.")
            return

        id_fazenda_alvo = self.mapa_tabs_fazendas.get(aba_selecionada_id)
        if not id_fazenda_alvo:
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Erro de Interface", "Não foi possível identificar a fazenda selecionada. Tente reiniciar o jogo.")
            return

        fazenda_alvo = next((f for f in self.fazendas if f["id"] == id_fazenda_alvo), None)
        plantacao_alvo = self.plantacoes_por_fazenda.get(id_fazenda_alvo)

        if not fazenda_alvo or plantacao_alvo is None:
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Erro Interno", "Não foi possível encontrar os dados da fazenda selecionada.")
            return

        # 2. Obter sementes selecionadas no catálogo
        sel_sementes = self.tree_agro.selection()
        if not sel_sementes:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Nenhuma Semente", "Selecione uma ou mais sementes no catálogo para plantar.")
            return

        # Obter dados das culturas selecionadas
        culturas_selecionadas = []
        for item in sel_sementes:
            nome = self.tree_agro.item(item)['values'][0]
            dados = next(c for c in self.culturas_catalogo if c["nome"] == nome)
            culturas_selecionadas.append(dados)

        # 3. Validar plantio (lógica pura)
        ok, erro_msg, custo_total, novas_plantas_dados = validar_plantio(
            self.nivel, self.dinheiro, fazenda_alvo, plantacao_alvo, culturas_selecionadas
        )
        
        if not ok:
            if "exige Nível" in erro_msg:
                self._pausar_e_exibir_dialogo(messagebox.showwarning, "Nível Insuficiente", erro_msg)
            elif "Espaço insuficiente" in erro_msg:
                self._pausar_e_exibir_dialogo(messagebox.showerror, "Sem Espaço", erro_msg)
            elif "Dinheiro insuficiente" in erro_msg:
                self._pausar_e_exibir_dialogo(messagebox.showerror, "Sem Dinheiro", erro_msg)
            return
            
        # 4. Executar o plantio na fazenda correta
        self.dinheiro -= custo_total
        novas_plantacoes = criar_plantacoes(novas_plantas_dados, fazenda_alvo["solo"])
        plantacao_alvo.extend(novas_plantacoes)
            
        self.log(f"Plantou {len(novas_plantas_dados)} ha em '{fazenda_alvo.get('nome_personalizado', fazenda_alvo['nome'])}'. Custo: {formatar_moeda(custo_total)}")
        self.atualizar_ui_geral()

    def comprar_maquina(self):
        sel = self.tree_maq_loja.selection()
        if not sel: return
        nome = self.tree_maq_loja.item(sel[0])['values'][0]
        dados = next(m for m in self.maquinas_catalogo if m["nome"] == nome)

        # A verificação de limite de garagem só se aplica a máquinas que não são de armazenagem
        if dados["funcao"] != "Armazenagem":
            total_ha = sum(f["tam"] for f in self.fazendas)
            limite_maquinas = max(2, total_ha // 10)
            slots_usados = len([m for m in self.meus_equipamentos if m['funcao'] != 'Armazenagem'])

            if slots_usados >= limite_maquinas:
                self._pausar_e_exibir_dialogo(messagebox.showwarning, "Garagem Cheia", f"Sua garagem para máquinas produtivas está cheia! Limite atual: {limite_maquinas} slots.\n\nCompre mais terras para aumentar sua capacidade. Silos e Armazéns não ocupam slots.")
                return

        if self.nivel < dados["nivel_req"]:
            self._pausar_e_exibir_dialogo(messagebox.showwarning, "Bloqueado", f"Exige Nível {dados['nivel_req']}.")
            return
        if self.dinheiro >= dados["preco"]:
            self.dinheiro -= dados["preco"]
            self.meus_equipamentos.append(dados)
            self.atualizar_capacidade_armazenagem()
            self.log(f"Comprou {nome}!")
            self.atualizar_ui_geral()
        else:
            self._pausar_e_exibir_dialogo(messagebox.showerror, "Caro", "Dinheiro insuficiente.")

    def vender_maquina(self):
        indices_selecionados = self.lista_garagem.curselection()
        if not indices_selecionados: return

        total_venda = 0
        nomes_maquinas = []
        
        for idx in indices_selecionados:
            maquina = self.meus_equipamentos[idx]
            nomes_maquinas.append(maquina["nome"])
            total_venda += maquina["preco"] * 0.85

        qtd_itens = len(nomes_maquinas)
        if qtd_itens == 1:
            msg_confirm = f"Vender '{nomes_maquinas[0]}' por {formatar_moeda(total_venda)} (85% do valor de compra)?"
        else:
            msg_confirm = f"Vender {qtd_itens} itens selecionados por um total de {formatar_moeda(total_venda)}?"

        confirmado = self._pausar_e_exibir_dialogo(messagebox.askyesno, "Confirmar Venda", msg_confirm)

        if confirmado:
            # É crucial remover pelos índices em ordem reversa para não bagunçar a lista
            for idx in sorted(indices_selecionados, reverse=True):
                self.meus_equipamentos.pop(idx)
            
            self.atualizar_capacidade_armazenagem() # NOVO
            self.dinheiro += total_venda
            self.log(f"Vendeu {qtd_itens} equipamento(s) por {formatar_moeda(total_venda)}.")
            self.atualizar_ui_geral()

    def _ask_vender_ou_armazenar(self, parent, total_kg, tipo_cultura):
        result = tk.StringVar()
        dialog = tk.Toplevel(parent)
        dialog.title("Ação de Colheita")
        dialog.geometry("350x150")
        dialog.transient(parent)
        dialog.grab_set()

        msg = f"Colheita de {total_kg:,.0f} kg de {tipo_cultura}.\nO que deseja fazer?"
        tk.Label(dialog, text=msg, font=self.ui_fonts['font_corpo']).pack(pady=20)

        def set_result(res):
            result.set(res)
            dialog.destroy()

        frame_botoes = tk.Frame(dialog)
        frame_botoes.pack(fill="x", expand=True, padx=20)

        btn_vender = tk.Button(frame_botoes, text="Vender Agora", font=self.ui_fonts['font_botao'], command=lambda: set_result("vender"), bg="#90EE90", height=2)
        btn_vender.pack(side="left", fill="x", expand=True, padx=5)
        
        btn_armazenar = tk.Button(frame_botoes, text="Armazenar", font=self.ui_fonts['font_botao'], command=lambda: set_result("armazenar"), bg="#ADD8E6", height=2)
        btn_armazenar.pack(side="right", fill="x", expand=True, padx=5)

        dialog.wait_window()
        return result.get()

    def colher(self, id_fazenda):
        tree = self.trees_fazenda.get(id_fazenda)
        if not tree: return
        
        plantacao_alvo = self.plantacoes_por_fazenda.get(id_fazenda)
        fazenda_alvo = next((f for f in self.fazendas if f["id"] == id_fazenda), None)
        if plantacao_alvo is None or not fazenda_alvo: return
        
        nome_exibido = fazenda_alvo.get("nome_personalizado", fazenda_alvo["nome"])
        
        # Obter índices de todas as plantações PRONTAS (sem necessidade de seleção)
        indices_prontas = [i for i, p in enumerate(plantacao_alvo) if p.get("estado") == "PRONTA"]
        if not indices_prontas: return
        
        bonus_prod = self.get_bonus_acumulado("Produtividade")

        # Calcular lotes de colheita (lógica pura)
        lotes_a_colher, indices_para_remover = colheita_lotes(plantacao_alvo, indices_prontas, bonus_prod)

        if not lotes_a_colher: return

        # Agrupar colheita (lógica pura)
        cultura_base, total_kg_colhido, custo_medio_por_kg_val, nome_cultura, tipo_armazenagem = agrupar_colheita(lotes_a_colher)

        # Verifica espaço no armazenamento
        capacidade_total = self.capacidade_armazenagem.get(tipo_armazenagem, 0)
        uso_atual = calcular_uso_capacidade(self.estoque, tipo_armazenagem)
        espaco_livre = calcular_espaco_livre(capacidade_total, uso_atual)

        acao = "vender"
        if espaco_livre >= total_kg_colhido:
            if capacidade_total > 0: # Só pergunta se houver algum armazém/silo
                acao = self._ask_vender_ou_armazenar(self.root, total_kg_colhido, nome_cultura)
                if not acao: # Janela fechada
                    return
            # Se não tem capacidade, a ação padrão é vender
        else:
            self._pausar_e_exibir_dialogo(messagebox.showinfo, "Armazenamento Cheio", f"Espaço insuficiente no {tipo_armazenagem}. A colheita será vendida diretamente.")

        # Executa a ação
        if acao == "armazenar":
            novo_lote_estoque = {
                "dados_base": cultura_base,
                "quantidade_kg": total_kg_colhido,
                "custo_producao_por_kg": custo_medio_por_kg_val,
                "dia_armazenado": self.dia
            }
            self.estoque.append(novo_lote_estoque)
            self.log(f"{total_kg_colhido:,.0f} kg de {nome_cultura} foram armazenados no {tipo_armazenagem}.")
            # atualizar estatísticas: colheita registrada
            try:
                from systems.stats import record_harvested
                record_harvested(self.__dict__, nome_cultura, total_kg_colhido)
            except Exception:
                pass

        elif acao == "vender":
            multiplicador_mercado = self.mercado_multiplicadores.get(nome_cultura, 1.0)
            preco_venda_kg = preco_mercado_atual(cultura_base["preco_venda"], multiplicador_mercado)

            # Calcular receita base e receita advinda dos bônus de equipamentos
            receita_base = 0.0
            receita_bonus = 0.0
            for lote in lotes_a_colher:
                comp = lote.get("compativel", True)
                base_kg = lote["dados_base"]["kg_hectare"] * (0.6 if not comp else 1.0)
                produced_kg = lote["quantidade_kg"]
                bonus_kg = max(0.0, produced_kg - base_kg)
                receita_base += base_kg * preco_venda_kg
                receita_bonus += bonus_kg * preco_venda_kg

            receita_total = receita_base + receita_bonus

            self.dinheiro += receita_total
            self.ganhar_xp(receita_total / 150) # XP por vender
            self.log(f"Colheita vendida em '{nome_exibido}': receita base {formatar_moeda(receita_base)}, Bônus Equipamentos {formatar_moeda(receita_bonus)}, total {formatar_moeda(receita_total)}.")
            # atualizar estatísticas: colheita e venda
            try:
                from systems.stats import record_harvested, record_sold
                # registrar que foi colhido e vendido
                record_harvested(self.__dict__, nome_cultura, total_kg_colhido)
                record_sold(self.__dict__, nome_cultura, total_kg_colhido, receita_total)
            except Exception:
                pass

        # Remove as plantações colhidas da fazenda
        for i in sorted(indices_para_remover, reverse=True):
            plantacao_alvo.pop(i)
            
        self.atualizar_ui_geral()

    def ganhar_xp(self, valor):
        self.xp += valor
        req = int(2500 * (1.5**(self.nivel - 1)))
        nivel_anterior = self.nivel
        while self.xp >= req:
            self.nivel += 1
            self.xp -= req
            self._pausar_e_exibir_dialogo(messagebox.showinfo, "LEVEL UP!", f"Nível {self.nivel}!\nNovos itens liberados.")
            self.atualizar_listas_lojas()
            req = int(2500 * (1.5**(self.nivel - 1)))
        
        # Avisar sobre gerentes ao atingir nível 2
        if nivel_anterior < 2 and self.nivel >= 2:
            msg = "🎉 Você desbloqueou a opção de contratar gerentes!\n\n"
            msg += "Gerentes podem gerenciar suas fazendas automaticamente:\n"
            msg += "• Colhem plantações prontas automaticamente\n"
            msg += "• Plantam culturas automaticamente\n"
            msg += "• Podem focar em uma cultura específica ou trabalhar automaticamente\n\n"
            msg += "Acesse a opção 'Contratar Gerente' nas abas de suas fazendas."
            self._pausar_e_exibir_dialogo(messagebox.showinfo, "Nova Funcionalidade Desbloqueada", msg)

    def gerente_colher(self, id_fazenda):
        plantacao_alvo = self.plantacoes_por_fazenda.get(id_fazenda)
        fazenda_alvo = next((f for f in self.fazendas if f["id"] == id_fazenda), None)
        if not plantacao_alvo or not fazenda_alvo: return

        lotes_a_colher = []
        indices_para_remover = []
        bonus_prod = self.get_bonus_acumulado("Produtividade")

        for i, p in enumerate(plantacao_alvo):
            if p["estado"] == "PRONTA":
                kg_produzido = producao_kg(p["dados_base"]["kg_hectare"], bonus_prod, p["compativel"])

                custo_total_lote = p["dados_base"]["custo_semente"]
                custo_por_kg = custo_medio_por_kg(custo_total_lote, kg_produzido)

                lotes_a_colher.append({
                    "dados_base": p["dados_base"],
                    "quantidade_kg": kg_produzido,
                    "custo_producao_por_kg": custo_por_kg
                })
                indices_para_remover.append(i)
        
        if not lotes_a_colher: return

        # Agrupar lotes por nome da cultura
        from collections import defaultdict
        colheitas_agrupadas = defaultdict(lambda: {"total_kg": 0, "custo_total": 0, "dados_base": None})

        for lote in lotes_a_colher:
            nome = lote["dados_base"]["nome"]
            colheitas_agrupadas[nome]["total_kg"] += lote["quantidade_kg"]
            colheitas_agrupadas[nome]["custo_total"] += lote["quantidade_kg"] * lote["custo_producao_por_kg"]
            if not colheitas_agrupadas[nome]["dados_base"]:
                colheitas_agrupadas[nome]["dados_base"] = lote["dados_base"]

        # Processar cada grupo de colheita
        nome_exibido = fazenda_alvo.get("nome_personalizado", fazenda_alvo["nome"])
        total_ha_colhido = len(indices_para_remover)
        log_msgs = []

        for nome_cultura, dados_colheita in colheitas_agrupadas.items():
            cultura_base = dados_colheita["dados_base"]
            total_kg = dados_colheita["total_kg"]
            custo_medio_kg = custo_medio_por_kg(dados_colheita["custo_total"], total_kg)
            
            acao = self.config_gerente["acao_colheita"]
            
            if acao == "Sempre Armazenar":
                tipo_armazenagem = cultura_base["tipo_armazenagem"]
                capacidade_total = self.capacidade_armazenagem.get(tipo_armazenagem, 0)
                uso_atual = calcular_uso_capacidade(self.estoque, tipo_armazenagem)
                espaco_livre = calcular_espaco_livre(capacidade_total, uso_atual)
                
                if espaco_livre >= total_kg:
                    self.estoque.append({
                        "dados_base": cultura_base,
                        "quantidade_kg": total_kg,
                        "custo_producao_por_kg": custo_medio_kg,
                        "dia_armazenado": self.dia
                    })
                    log_msgs.append(f"armazenou {total_kg:,.0f} kg de {nome_cultura}")
                else:
                    acao = "Sempre Vender" # Fallback para vender se não houver espaço
                    log_msgs.append(f"tentou armazenar {nome_cultura}, mas o {tipo_armazenagem} está cheio")

            if acao == "Sempre Vender":
                mult_mercado = self.mercado_multiplicadores.get(nome_cultura, 1.0)
                preco_venda_kg = preco_mercado_atual(cultura_base["preco_venda"], mult_mercado)
                receita_bruta = total_kg * preco_venda_kg
                self.dinheiro += receita_bruta
                self.ganhar_xp(receita_bruta / 150)
                log_msgs.append(f"vendeu {total_kg:,.0f} kg de {nome_cultura} por {formatar_moeda(receita_bruta)}")

        # Finalizar
        if log_msgs:
            self.log(f"Gerente de '{nome_exibido}' colheu {total_ha_colhido} ha e " + ", ".join(log_msgs) + ".")

        for i in sorted(indices_para_remover, reverse=True):
            plantacao_alvo.pop(i)

    def gerente_plantar(self, id_fazenda):
        fazenda_alvo = next((f for f in self.fazendas if f["id"] == id_fazenda), None)
        plantacao_alvo = self.plantacoes_por_fazenda.get(id_fazenda)
        if fazenda_alvo is None or plantacao_alvo is None: return

        espacos_livres = fazenda_alvo["tam"] - len(plantacao_alvo)
        if espacos_livres <= 0: return

        # Selecionar culturas disponíveis (lógica pura)
        culturas_disponiveis = selecionar_culturas_disponiveis(self.culturas_catalogo, self.nivel, fazenda_alvo["solo"])
        
        if not culturas_disponiveis: return

        # NOVA LÓGICA: Verificar se há uma cultura definida para o gerente
        cultura_foco_nome = fazenda_alvo.get("gerente_cultura", "Automatica")
        log_cultura_especifica = False
        if cultura_foco_nome != "Automatica":
            log_cultura_especifica = True
            cultura_foco_obj = next((c for c in culturas_disponiveis if c["nome"] == cultura_foco_nome), None)
            if cultura_foco_obj:
                # Se a cultura foco está disponível, o gerente só plantará ela
                culturas_disponiveis = [cultura_foco_obj]
            else:
                # Se a cultura definida não é válida (ex: solo incompatível, nível baixo), o gerente não planta nada
                return

        # Estratégia do gerente: plantar a cultura de maior nível que ele pode pagar (ou a única disponível se definida)
        culturas_disponiveis.sort(key=lambda c: c["nivel_req"], reverse=True)

        plantios_feitos = 0
        custo_total = 0
        nome_cultura_plantada = ""
        culturas_para_plantar = []

        for _ in range(espacos_livres):
            melhor_cultura = escolher_cultura_para_plantar(culturas_disponiveis, self.dinheiro, custo_total, cultura_foco_nome)
            
            if not melhor_cultura:
                break # Não pode pagar por nenhuma semente disponível

            # Acumular para plantar
            custo_total += melhor_cultura["custo_semente"]
            nome_cultura_plantada = melhor_cultura["nome"]
            culturas_para_plantar.append(melhor_cultura)
            plantios_feitos += 1

        if plantios_feitos > 0:
            self.dinheiro -= custo_total
            
            # Criar plantações usando função do módulo agriculture
            novas_plantacoes = criar_plantacoes(culturas_para_plantar, fazenda_alvo["solo"])
            plantacao_alvo.extend(novas_plantacoes)
            
            nome_exibido = fazenda_alvo.get("nome_personalizado", fazenda_alvo["nome"])
            
            log_msg = f"Gerente de '{nome_exibido}' plantou {plantios_feitos} ha"
            if log_cultura_especifica:
                log_msg += f" de '{nome_cultura_plantada}'"
            log_msg += f". Custo: {formatar_moeda(custo_total)}."
            self.log(log_msg)

    def passar_dia(self):
        dias_avancados = 7
        
        # Montar state
        state = {
            "dia": self.dia,
            "nivel": self.nivel,
            "clima": self.clima,
            "fazendas": self.fazendas,
            "plantacoes_por_fazenda": self.plantacoes_por_fazenda,
            "meus_equipamentos": self.meus_equipamentos,
            "mercado_multiplicadores": self.mercado_multiplicadores,
            "seguro_agricola_ativo": self.seguro_agricola_ativo,
            "salarios_gerente": self.salarios_gerente,
            "opcoes_base_fazenda": self.opcoes_base_fazenda,
            "tipos_de_solo": self.tipos_de_solo,
            "dinheiro": self.dinheiro,
        }
        
        # Chamar função pura
        state = avancar_semana(state, dias_avancados)
        
        # Escrever campos de volta em self
        # Sincronizar estatísticas e conquistas geradas pela engine de tempo
        if "campaign_stats" in state:
            self.campaign_stats = state["campaign_stats"]
        if "unlocked_achievements" in state:
            self.unlocked_achievements = state["unlocked_achievements"]
        # Se a campanha foi perdida, garantir notificação UI imediata (apenas uma vez).
        camp = state.get("campaign", {})
        if camp.get("status") == "LOST":
            eventos_tmp = state.get("eventos", [])
            # Evitar dupla notificação se o evento GAME OVER já estiver nas mensagens
            if not any(str(e).startswith("GAME OVER") for e in eventos_tmp):
                self.log(f"GAME OVER: {camp.get('lost_reason', 'Derrota na campanha.')}")
            # Marcar localmente que já notificamos a UI para evitar repetir
            setattr(self, "_game_over_notified", True)

        self.dia = state["dia"]
        self.clima = state["clima"]
        self.dinheiro = state["dinheiro"]
        self.mercado_multiplicadores = state["mercado_multiplicadores"]
        self.plantacoes_por_fazenda = state["plantacoes_por_fazenda"]
        if "propriedades_a_venda" in state:
            self.propriedades_a_venda = state["propriedades_a_venda"]
        
        # Processar eventos e alertas
        eventos = state.get("eventos", [])
        alertas = state.get("alertas", [])
        
        for evento in eventos:
            self.log(evento)
        
        for alerta in alertas:
            if alerta["tipo"] == "info":
                self._pausar_e_exibir_dialogo(messagebox.showinfo, alerta["titulo"], alerta["mensagem"])
            elif alerta["tipo"] == "warning":
                self._pausar_e_exibir_dialogo(messagebox.showwarning, alerta["titulo"], alerta["mensagem"])
        
        # --- LÓGICA DO GERENTE (ações automáticas) ---
        semana = int(self.dia / 7)
        for fazenda in self.fazendas:
            if fazenda.get("tem_gerente"):
                # Ações do gerente
                self.gerente_colher(fazenda["id"])
                self.gerente_plantar(fazenda["id"])
        
        self.processar_vendas_automaticas()
        self._processar_emprestimos()
        self.atualizar_ui_geral()

    def _processar_emprestimos(self):
        semana_atual = self.dia // 7
        
        # Processar empréstimos (lógica pura)
        resultado = processar_emprestimos_semanal(self.emprestimos_ativos, semana_atual)
        
        # Atualizar lista de empréstimos
        self.emprestimos_ativos = resultado["emprestimos_atualizados"]
        
        # Processar defaults (aplicar garantias e mensagens)
        for default_info in resultado["emprestimos_em_default"]:
            emp = default_info["emprestimo"]
            banco = default_info["banco"]
            garantia = default_info["garantia"]
            valor_devido = default_info["valor_devido"]
            
            self.log(f"!!! INADIMPLENTE !!! Empréstimo com {banco} no valor de {formatar_moeda(valor_devido)} não foi pago no prazo.")

            if not garantia or garantia.get("tipo") == "nenhuma":
                self.log(f"Sua reputação foi afetada por não pagar o {banco}.")
                continue

            if garantia["tipo"] == "fazenda":
                id_fazenda = garantia["id"]
                fazenda_perdida = next((f for f in self.fazendas if f["id"] == id_fazenda), None)
                if fazenda_perdida:
                    nome_fazenda = fazenda_perdida.get('nome_personalizado', fazenda_perdida['nome'])
                    self.fazendas = [f for f in self.fazendas if f["id"] != id_fazenda]
                    if id_fazenda in self.plantacoes_por_fazenda:
                        del self.plantacoes_por_fazenda[id_fazenda]
                    
                    msg = f"Você não pagou o empréstimo do {banco} a tempo e perdeu a fazenda '{nome_fazenda}'!"
                    self._pausar_e_exibir_dialogo(messagebox.showerror, "PERDA DE GARANTIA", msg)
                    self.log(f"GARANTIA EXECUTADA: {msg}")
                else:
                    self.log(f"O {banco} tentou tomar sua fazenda, mas ela não existe mais.")

            elif garantia["tipo"] == "maquinas":
                if self.meus_equipamentos:
                    msg = f"Você não pagou o empréstimo da {banco} e perdeu TODOS os seus equipamentos!"
                    self._pausar_e_exibir_dialogo(messagebox.showerror, "PERDA DE GARANTIA", msg)
                    self.log(f"GARANTIA EXECUTADA: {msg}")
                    self.meus_equipamentos.clear()
                    self.atualizar_capacidade_armazenagem()
                else:
                    self.log(f"A {banco} tentou tomar seus equipamentos, mas você não os tinha mais.")

    def processar_vendas_automaticas(self):
        if not self.gatilho_venda_automatica_ativo.get():
            return

        margem_alvo = self.gatilho_venda_automatica_margem.get()
        
        resultado = processar_venda_automatica(self.estoque, self.mercado_multiplicadores, margem_alvo)
        
        lotes_para_vender = resultado["lotes_para_vender"]
        receita_total = resultado["receita_total"]
        
        if lotes_para_vender:
            # Ordenar por índice em ordem decrescente para remover corretamente
            lotes_para_vender.sort(key=lambda x: x["indice"], reverse=True)
            lotes_vendidos = []
            
            for lote_info in lotes_para_vender:
                self.dinheiro += lote_info["valor"]
                lotes_vendidos.append(lote_info["descricao"])
                self.estoque.pop(lote_info["indice"])
            
            self.log(f"Venda automática ativada: {', '.join(lotes_vendidos)} vendidos por {formatar_moeda(receita_total)}.")

    def atualizar_ui_geral(self):
        self.lbl_nivel.config(text=f"⭐ Nível {self.nivel} (XP: {int(self.xp)})")
        self.lbl_dinheiro.config(text=formatar_moeda(self.dinheiro))
        semana = self.dia // 7
        ano = max(1, (semana - 1) // 52 + 1)
        semana_no_ano = (semana - 1) % 52 + 1 if semana > 0 else 1
        self.lbl_tempo.config(text=f"Ano {ano}, Semana {semana_no_ano} | {self.clima}")

        total_ha = sum(f["tam"] for f in self.fazendas)
        ocupado_ha = sum(len(p) for p in self.plantacoes_por_fazenda.values())
        disponivel_ha = total_ha - ocupado_ha
        cor = "#1E8449" if disponivel_ha > 0 else "#C0392B"
        self.lbl_slots_disponiveis.config(text=f"Espaço Total: {total_ha} ha | Ocupado: {ocupado_ha} ha | Livre: {disponivel_ha} ha", fg=cor)
        
        self.atualizar_listas_lojas() 
        self.atualizar_listas_imobiliaria()
        self.atualizar_aba_mercado()
        self.atualizar_aba_logistica()
        self.atualizar_aba_financas()
        self.atualizar_aba_estatisticas()

    def montar_aba_estatisticas(self):
        frame = self.tab_stats
        lf = tk.LabelFrame(frame, text="Estatísticas da Campanha", padx=10, pady=10)
        lf.pack(fill="both", expand=True, padx=5, pady=5)

        self.txt_stats = tk.Text(lf, height=15, state="disabled", bg="#ffffff")
        self.txt_stats.pack(fill="both", expand=True)

    def atualizar_aba_estatisticas(self):
        # Ler stats do state (self.__dict__ já é compatível)
        stats = self.__dict__.get("campaign_stats") or {}
        lines = []
        lines.append(f"Lucro acumulado: {stats.get('net_profit', 0.0):,.2f}")
        lines.append(f"Receita total: {stats.get('total_revenue', 0.0):,.2f}")
        lines.append(f"Custos totais: {stats.get('total_costs', 0.0):,.2f}")
        lines.append("")
        lines.append(f"Semanas no azul: {stats.get('weeks_positive_cash', 0)}")
        lines.append(f"Semanas no vermelho: {stats.get('weeks_negative_cash', 0)}")
        lines.append("")
        # Top 3 culturas por produção
        harvested = stats.get('total_harvested_by_culture', {}) or {}
        sorted_h = sorted(harvested.items(), key=lambda x: x[1], reverse=True)
        lines.append("Top culturas por produção (kg):")
        for nome, val in sorted_h[:3]:
            lines.append(f" - {nome}: {val:,.0f} kg")

        self.txt_stats.config(state="normal")
        self.txt_stats.delete("1.0", "end")
        self.txt_stats.insert("1.0", "\n".join(lines))
        self.txt_stats.config(state="disabled")
        
        # --- ATUALIZAÇÃO DAS ABAS DE FAZENDA ---
        if self.notebook_fazendas:
            # 1. Obter IDs das fazendas e abas atuais
            ids_fazendas_atuais = {f["id"] for f in self.fazendas}
            
            # 2. Remover abas de fazendas que foram vendidas
            for tab_id, farm_id in list(self.mapa_tabs_fazendas.items()):
                if farm_id not in ids_fazendas_atuais:
                    self.notebook_fazendas.forget(tab_id)
                    del self.mapa_tabs_fazendas[tab_id]
                    if farm_id in self.trees_fazenda:
                        del self.trees_fazenda[farm_id]
                    if farm_id in self.botoes_gerente_fazenda:
                        del self.botoes_gerente_fazenda[farm_id]
            
            # 3. Adicionar abas para novas fazendas e atualizar as existentes
            for fazenda in self.fazendas:
                id_fazenda = fazenda["id"]
                
                # Atualizar texto da aba
                nome_exibido = fazenda.get("nome_personalizado", fazenda["nome"])
                tab_text = f" {nome_exibido} ({fazenda['solo']}) "
                if fazenda.get("tem_gerente"):
                    cultura_gerente = fazenda.get("gerente_cultura", "Automatica")
                    if cultura_gerente == "Automatica":
                        tab_text = f"💼 Auto |{tab_text}"
                    else:
                        # Pega as 3 primeiras letras da cultura
                        nome_curto = cultura_gerente[:3].upper()
                        tab_text = f"💼 {nome_curto} |{tab_text}"
                
                tab_id = next((tid for tid, fid in self.mapa_tabs_fazendas.items() if fid == id_fazenda), None)

                if not tab_id:
                    # Cria uma nova aba
                    frame_aba = tk.Frame(self.notebook_fazendas)
                    self.notebook_fazendas.add(frame_aba, text=tab_text)
                    tab_id = self.notebook_fazendas.tabs()[-1] # Pega o ID do widget da aba recém-criada
                    self.mapa_tabs_fazendas[tab_id] = id_fazenda

                    # Frame para botões dentro da aba
                    frame_botoes = tk.Frame(frame_aba)
                    frame_botoes.pack(side="bottom", fill="x", pady=2)

                    # Treeview para as plantações
                    colunas = ("Cultura", "Status", "Valor Bruto")
                    tree = ttk.Treeview(frame_aba, columns=colunas, show="headings", selectmode="extended")
                    tree.heading("Cultura", text="Cultura")
                    tree.heading("Status", text="Estado")
                    tree.heading("Valor Bruto", text="Venda Bruta Est.")
                    tree.pack(side="top", fill="both", expand=True)
                    self.trees_fazenda[id_fazenda] = tree
                    
                    # Botões
                    btn_colher = tk.Button(frame_botoes, text=f"Colher em {nome_exibido}", font=self.ui_fonts['font_botao'], bg="gold", command=lambda f_id=id_fazenda: self.colher(f_id))
                    btn_colher.pack(side="left", fill="x", expand=True)
                    
                    btn_renomear = tk.Button(frame_botoes, text="Renomear", font=self.ui_fonts['font_botao'], command=lambda f_id=id_fazenda: self.renomear_fazenda(f_id))
                    btn_renomear.pack(side="right", padx=5)

                    btn_gerente = tk.Button(frame_botoes, text="", font=self.ui_fonts['font_botao'], command=lambda f_id=id_fazenda: self.abrir_configuracao_gerente(f_id))
                    btn_gerente.pack(side="right", padx=5)
                    self.botoes_gerente_fazenda[id_fazenda] = btn_gerente
                    # Configurar estado inicial baseado no nível (será atualizado logo após)
                else:
                    self.notebook_fazendas.tab(tab_id, text=tab_text)

                # Atualizar botão do gerente
                if id_fazenda in self.botoes_gerente_fazenda:
                    btn = self.botoes_gerente_fazenda[id_fazenda]
                    if self.nivel < 2:
                        # Desabilitar botão se nível < 2
                        btn.config(text="Contratar Gerente (Nível 2)", bg="#CCCCCC", state="disabled")
                    elif fazenda.get("tem_gerente"):
                        btn.config(text="Gerenciar...", bg="#ADD8E6", state="normal")
                    else:
                        btn.config(text="Contratar Gerente", bg="#ADD8E6", state="normal")

            # 4. Popular/Atualizar todas as árvores de plantação
            for id_fazenda, tree in self.trees_fazenda.items():
                sel_indices = [tree.index(i) for i in tree.selection()]
                for i in tree.get_children(): tree.delete(i)
                
                plantacao = self.plantacoes_por_fazenda.get(id_fazenda, [])
                ids_para_selecionar = []
                for i, p in enumerate(plantacao):
                    if p["estado"] == "PRONTA":
                        status = ">>> PRONTA <<<"
                    else:
                        total = p["total"]
                        rest = max(0, p["dias_rest"])
                        prog = 100 - (rest / total * 100) if total > 0 else 0
                        status = f"{prog:.0f}% (~{int(rest/7)+1} sem)"
                    
                    val = p["dados_base"]["kg_hectare"] * p["dados_base"]["preco_venda"]
                    bonus_prod = min(self.get_bonus_acumulado("Produtividade"), 2.5)
                    val *= (1 + bonus_prod)

                    item_id = tree.insert("", "end", values=(p["nome"], status, f"{val:.0f}"))
                    if i in sel_indices:
                        ids_para_selecionar.append(item_id)

                if ids_para_selecionar:
                    tree.selection_set(ids_para_selecionar)
        
        # --- ATUALIZAÇÃO DA GARAGEM ---
        # Salva a seleção da garagem
        sel_garagem_indices = self.lista_garagem.curselection()
        
        self.lista_garagem.delete(0, "end")
        for m in self.meus_equipamentos:
            if m["funcao"] == "Armazenagem":
                texto_item = f"{m['nome']} (Capacidade: {m['capacidade'] // 1000} t)"
            else:
                texto_item = f"{m['nome']} ({m['funcao']} +{int(m['valor_bonus']*100)}%)"
            self.lista_garagem.insert("end", texto_item)
        
        # Restaura a seleção da garagem
        if sel_garagem_indices:
            for i in sel_garagem_indices:
                if i < self.lista_garagem.size():
                    self.lista_garagem.selection_set(i)
        
        # Atualiza resumo de bônus e limite de máquinas
        total_ha = sum(f["tam"] for f in self.fazendas)
        limite_maquinas = max(2, total_ha // 10)
        slots_usados = len([m for m in self.meus_equipamentos if m['funcao'] != 'Armazenagem'])
        self.lbl_limite_maquinas.config(text=f"Garagem (Máquinas): {slots_usados} / {limite_maquinas}")

        b_prod = int(self.get_bonus_acumulado("Produtividade")*100)
        b_vel = int(self.get_bonus_acumulado("Velocidade")*100)
        silo_t = self.capacidade_armazenagem['Silo'] // 1000
        armazem_t = self.capacidade_armazenagem['Armazém'] // 1000
        
        txt_resumo = f"Bônus: Prod +{b_prod}% | Vel +{b_vel}% | Silos: {silo_t} t | Armazéns: {armazem_t} t"
        self.lbl_resumo_maquinas.config(text=txt_resumo)

    def atualizar_aba_mercado(self):
        if not hasattr(self, 'tree_mercado'): return
        for i in self.tree_mercado.get_children(): self.tree_mercado.delete(i)

        culturas_ordenadas = sorted(self.culturas_catalogo, key=lambda c: c['nome'])

        for cultura in culturas_ordenadas:
            nome = cultura["nome"]
            preco_base = cultura["preco_venda"]
            
            multiplicador = self.mercado_multiplicadores.get(nome, 1.0)
            preco_atual = preco_mercado_atual(preco_base, multiplicador)
            
            tendencia_val = (multiplicador - 1.0) * 100
            
            if tendencia_val > 0.5:
                tendencia_str = f"+{tendencia_val:.1f}%"
                tag = 'alta'
            elif tendencia_val < -0.5:
                tendencia_str = f"{tendencia_val:.1f}%"
                tag = 'baixa'
            else:
                tendencia_str = "Estável"
                tag = ''
                
            self.tree_mercado.insert("", "end", tags=(tag,), values=(
                nome,
                formatar_moeda(preco_base),
                tendencia_str,
                formatar_moeda(preco_atual)
            ))
        
        # Reaplicar filtro se existir
        if hasattr(self, 'entry_filtro_mercado') and self.entry_filtro_mercado.get():
            self._aplicar_filtro_treeview(self.tree_mercado, self.entry_filtro_mercado.get())

    def log(self, t):
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", f"> {t}\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    # ==========================================
    # SISTEMA DE SALVAMENTO (REMOVIDO)
    # ==========================================
    def salvar_e_fechar(self):
        # A funcionalidade de salvar foi removida. A janela simplesmente fecha.
        self.root.destroy()

    def mostrar_tela_inicial(self):
        for w in self.root.winfo_children(): w.destroy()
        tk.Label(self.root, text="Tycoon Fazenda", font=("Arial", 36, "bold")).pack(pady=(50, 20))
        btn_novo = tk.Button(self.root, text="Novo Jogo", font=("Arial", 16, "bold"), command=self.mostrar_tela_imobiliaria)
        btn_novo.pack(pady=10, ipadx=20, ipady=10)
    
    def iniciar_de_save(self):
        # A funcionalidade de carregar jogo foi removida.
        pass


if __name__ == "__main__":
    root = tk.Tk()
    app = JogoFazenda(root)
    root.mainloop()