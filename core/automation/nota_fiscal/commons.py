# -*- coding: utf-8 -*-
"""
Rotinas comuns compartilhadas entre os fluxos de nota fiscal.
Mantém utilidades e etapas reutilizadas em múltiplos caminhos.
"""

class NotaFiscalCommonsMixin:
    """Métodos do workflow para NotaFiscalCommonsMixin."""

    def _split_block_values(self, raw_value):
        """Normaliza valores de bloco em lista única (aceita vírgula, ; e quebra de linha)."""
        if raw_value is None:
            return []

        text = str(raw_value).strip()
        if not text:
            return []

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        for sep in [';', '\n', '|']:
            normalized = normalized.replace(sep, ',')

        parts = [p.strip() for p in normalized.split(',')]

        result = []
        seen = set()
        for item in parts:
            if not item:
                continue

            clean = item[:-2] if item.endswith('.0') else item
            key = clean.lower()
            if key in seen:
                continue

            seen.add(key)
            result.append(clean)

        return result


    def _join_block_values(self, raw_value):
        values = self._split_block_values(raw_value)
        if not values:
            return ""
        return ", ".join(values)


    def _last_block_value(self, raw_value):
        values = self._split_block_values(raw_value)
        if not values:
            return ""
        return values[-1]

    def check_pause(self):
        """Verifica e gerencia o estado de pausa da automação"""
        if hasattr(self.gui, 'state'):
            # Se estiver pausado
            if self.gui.state.get('is_paused', False):
                self.gui.log("⏸ Automação PAUSADA pelo usuário...", level="warning")
                
                # Loop de espera enquanto estiver pausado
                while self.gui.state.get('is_paused', False):
                    # Verificar se a automação foi parada (stop) enquanto estava pausada
                    if not self.gui.state.get('is_running', False):
                        raise Exception("Automação interrompida pelo usuário.")
                    self.delay.custom(500)
                
                self.gui.log("▶ Automação RETOMADA.", level="info")


    def _set_tag(self, tag):
        self.check_pause()
        self.current_tag = tag
        if not self.resume_from_tag:
            return True
        if self._resume_found:
            return True
        if tag == self.resume_from_tag:
            self._resume_found = True
            return True
        return False


    def select_agencia(self, page, uf):
        """
        Etapa 1: Seleciona agência pela UF
        Elemento: <select name="dados_agencias_id">
        Lógica: Clicar e buscar o ultimo texto dos itens da lista igual a "uf" (com mapeamento)
        """
        if not self._set_tag("select_agencia"):
            return
        self.gui.log(f"Etapa 1: Selecionando agência para UF: {uf}")

        # Mapeamento de siglas para nomes completos
        uf_mapping = {
            'PE': 'PERNAMBUCO', 'CE': 'CEARÁ', 'BA': 'BAHIA', 'SP': 'SÃO PAULO',
            'RJ': 'RIO DE JANEIRO', 'MG': 'MINAS GERAIS', 'RS': 'RIO GRANDE DO SUL',
            'PR': 'PARANÁ', 'SC': 'SANTA CATARINA', 'GO': 'GOIÁS', 'MT': 'MATO GROSSO',
            'MS': 'MATO GROSSO DO SUL', 'DF': 'DISTRITO FEDERAL', 'ES': 'ESPÍRITO SANTO',
            'AM': 'AMAZONAS', 'PA': 'PARÁ', 'MA': 'MARANHÃO', 'PB': 'PARAÍBA',
            'RN': 'RIO GRANDE DO NORTE', 'AL': 'ALAGOAS', 'SE': 'SERGIPE',
            'PI': 'PIAUÍ', 'TO': 'TOCANTINS', 'RO': 'RONDÔNIA', 'AC': 'ACRE',
            'RR': 'RORAIMA', 'AP': 'AMAPÁ'
        }

        # Normalizar UF
        uf_clean = uf.strip().upper()
        target_uf = uf_mapping.get(uf_clean, uf_clean)
        
        if target_uf != uf_clean:
            self.gui.log(f"Mapeado UF '{uf}' para '{target_uf}'")

        # Aguardar renderização
        self.delay.custom(self.interaction_delay * 1.5)

        try:
            selector = 'select[name="dados_agencias_id"]'
            page.wait_for_selector(selector, state='visible', timeout=5000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            # Clicar no campo (solicitado pelo usuário)
            try:
                page.click(selector, force=True)
                self.delay.custom(self.interaction_delay)
            except Exception as e:
                self.gui.log(f"Aviso ao clicar no select: {e}", level="warning")
            
            # Obter opções e encontrar a que termina com a UF (case insensitive)
            option_value = page.evaluate('''(target_uf) => {
                const select = document.querySelector('select[name="dados_agencias_id"]');
                if (!select) return null;

                const options = Array.from(select.options);
                // Buscar opção onde o último texto é igual a UF ou contém
                const targetOption = options.find(opt => {
                    const text = opt.text.trim().toUpperCase();
                    const search = target_uf.toUpperCase();
                    return text.endsWith(search) || text.includes(search);
                });
                
                return targetOption ? targetOption.value : null;
            }''', target_uf)

            if option_value:
                page.select_option(selector, option_value)
                self.gui.log(f"✓ Agência selecionada: {option_value} (UF: {target_uf})")
            else:
                # Tentar match exato se falhar
                self.gui.log(f"Tentando seleção direta para UF: {uf}", level="warning")
                try:
                    page.select_option(selector, label=target_uf)
                except:
                    try:
                        page.select_option(selector, label=uf)
                    except:
                        raise Exception(f"Nenhuma agência encontrada para UF: {uf} (Alvo: {target_uf})")
            
            self.delay.custom(self.interaction_delay * 1.5)
            self.steps.append(f"Agência {uf} selecionada")
            
        except Exception as e:
            raise Exception(f"Erro ao selecionar agência (Etapa 1): {str(e)}")


    def select_talao(self, page):
        """
        Etapa 2: Seleciona Talão CT-e
        Elemento: <select name="dados_tiposTaloes_id">
        Lógica: Clicar e selecionar o primeiro valor iniciado com "CT-e"
        """
        if not self._set_tag("select_talao"):
            return
        self.gui.log("Etapa 2: Selecionando Talão CT-e...")

        # Aguardar renderização
        self.delay.custom(self.interaction_delay * 1.5)

        try:
            selector = 'select[name="dados_tiposTaloes_id"]'
            page.wait_for_selector(selector, state='visible', timeout=5000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            # Clicar no campo
            try:
                page.click(selector, force=True)
                self.delay.custom(self.interaction_delay)
            except: pass
            
            # Obter opções e encontrar a primeira que começa com "CT-e"
            option_value = page.evaluate('''() => {
                const select = document.querySelector('select[name="dados_tiposTaloes_id"]');
                if (!select) return null;

                const options = Array.from(select.options);
                const targetOption = options.find(opt => {
                    const text = opt.text.trim();
                    return text.startsWith('CT-e');
                });
                
                return targetOption ? targetOption.value : null;
            }''')

            if option_value:
                page.select_option(selector, option_value)
                self.gui.log(f"✓ Talão CT-e selecionado: {option_value}")
            else:
                raise Exception("Nenhum Talão iniciado com 'CT-e' encontrado")
            
            self.delay.custom(self.interaction_delay * 1.5)
            self.steps.append("Talão CT-e selecionado")
            
        except Exception as e:
            raise Exception(f"Erro ao selecionar talão (Etapa 2): {str(e)}")


    def determinar_identificacao_pedido(self, tipo_adc, uf):
        """
        Determina o texto a ser preenchido na Identificação do Pedido.
        Centraliza a regra de negócio e separa a lógica da Bahia (BA) das demais UFs.
        """
        # 1. Regra prioritária para a Bahia (BA)
        if uf and str(uf).strip().upper() == 'BA':
            return "DESPESAS ADICIONAIS"

        # 2. Regras gerais para as demais UFs
        tipo_lower = str(tipo_adc).lower() if tipo_adc else ""
        
        if tipo_lower.startswith("descarga"):
            return "Descarga"
        elif tipo_lower.startswith("pedagio"):
            return "Pedagio"
        elif tipo_lower.startswith("pernoite") or tipo_lower.startswith("diaria") or tipo_lower.startswith("diária"):
            return "DIARIA NO CLIENTE"
        elif tipo_lower.startswith("reentrega"):
            return "REENTREGA"
        else:
            fallback_val = tipo_adc if tipo_adc else "REENTREGA"
            if tipo_adc:
                self.gui.log(f"Tipo ADC '{tipo_adc}' não mapeado por padrão. Usando valor original: {fallback_val}", level="warning")
            return fallback_val


    def fill_identificacao_custom(self, page, valor):
        """Preenche Identificação do Pedido com valor customizado"""
        if not self._set_tag("fill_identificacao_custom"):
            return
        self.gui.log(f"Preenchendo Identificação do Pedido: {valor}...")
        try:
            selector = 'input[name="dados_complementoPedido"]'
            page.wait_for_selector(selector, state='visible', timeout=5000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            # Limpar e preencher
            page.fill(selector, '')
            self.delay.custom(self.interaction_delay // 2)
            page.locator(selector).type(valor, delay=self.typing_delay)
            
            self.gui.log(f"✓ Identificação preenchida: {valor}")
            self.delay.custom(self.interaction_delay * 1.5)
            self.steps.append(f"Identificação do Pedido: {valor}")
        except Exception as e:
            raise Exception(f"Erro ao preencher Identificação customizada: {str(e)}")


    def select_tipo_cte_complemento(self, page):
        """
        Etapa 4: Seleciona Tipo de CT-e
        Elemento: <select name="dados_tpCTe">
        Lógica: Clicar e selecionar valor "Complemento de valores" (value="1")
        """
        if not self._set_tag("select_tipo_cte_complemento"):
            return
        self.gui.log("Etapa 4: Selecionando Tipo de CT-e: Complemento de valores...")

        # Aguardar renderização
        self.delay.custom(self.interaction_delay * 1.5)

        try:
            selector = 'select[name="dados_tpCTe"]'
            page.wait_for_selector(selector, state='visible', timeout=5000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            # Clicar no campo
            try:
                page.click(selector, force=True)
                self.delay.custom(self.interaction_delay)
            except: pass
            
            # Selecionar value="1" que é "Complemento de valores"
            page.select_option(selector, '1')
            
            self.gui.log(f"✓ Tipo de CT-e: Complemento de valores selecionado")
            self.delay.custom(self.interaction_delay * 1.5)
            self.steps.append("Tipo de CT-e: Complemento de valores")
            
        except Exception as e:
            raise Exception(f"Erro ao selecionar Tipo de CT-e (Etapa 4): {str(e)}")


    def pesquisar_cte_complementar(self, page, cte_number):
        """
        Etapa 5: Pesquisa CT-e complementar
        Campo: <input name="pesquisa_complementou_id">
        Botão: <i name="botaoPesquisa_complementou_id">
        """
        if not self._set_tag("pesquisar_cte_complementar"):
            return
        self.gui.log("Etapa 5: Preenchendo e pesquisando CT-e complementar...")

        self.delay.custom(self.interaction_delay * 1.5)

        try:
            # Preencher campo de pesquisa
            selector_input = 'input[name="pesquisa_complementou_id"]'
            page.wait_for_selector(selector_input, state='visible', timeout=5000)
            page.locator(selector_input).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            # Limpar e preencher com o CT-e
            page.fill(selector_input, '')
            self.delay.custom(self.interaction_delay // 2)
            page.locator(selector_input).type(cte_number, delay=self.typing_delay)
            
            self.gui.log(f"✓ CT-e digitado no campo de pesquisa: {cte_number}")
            self.delay.custom(self.interaction_delay * 2)
            
            # Clicar em Pesquisar
            selector_btn = 'i[name="botaoPesquisa_complementou_id"]'
            try:
                locator = page.locator(selector_btn)
                locator.wait_for(state='visible', timeout=5000)
                locator.scroll_into_view_if_needed()
                self.delay.custom(self.interaction_delay)
                locator.click(force=True, timeout=3000)
                self.gui.log("✓ Botão Pesquisar clicado (Estratégia 1: locator.click)")
            except Exception as e:
                self.gui.log(f"Estratégia 1 falhou: {e}. Tentando com JavaScript.", level="warning")
                try:
                    page.evaluate(f'document.querySelector("{selector_btn}").click()')
                    self.gui.log("✓ Botão Pesquisar clicado (Estratégia 2: JavaScript)")
                except Exception as e2:
                    raise Exception(f"Erro ao clicar no botão Pesquisar (ambas estratégias falharam): {e2}")
            
            self.delay.custom(self.network_delay)  # Aguardar resposta da pesquisa
            self.steps.append(f"CT-e complementar pesquisado: {cte_number}")
            
        except Exception as e:
            raise Exception(f"Erro ao pesquisar CT-e complementar (Etapa 5): {str(e)}")


    def avancar_pagina(self, page):
        """
        Etapa 6: Clica em Avançar
        Botão: <input name="botao_finalizacao" value="Avançar »">
        """
        if not self._set_tag("avancar_pagina"):
            return
        self.gui.log("Etapa 6: Clicando em Avançar...")

        # Aguardar renderização
        self.delay.custom(self.interaction_delay * 1.5)

        try:
            # Seletor exato conforme solicitado: value="Avançar »"
            selector = 'input[name="botao_finalizacao"][value="Avançar »"]'
            
            # Fallback para contains caso o encoding do » dê problema
            if not page.is_visible(selector):
                 self.gui.log("Seletor exato não visível, tentando parcial...", level="debug")
                 selector = 'input[name="botao_finalizacao"][value*="Avançar"]'

            page.wait_for_selector(selector, state='visible', timeout=5000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            page.click(selector, force=True)
            
            self.gui.log(f"✓ Botão Avançar clicado")
            
            # Aguardar carregamento da próxima página
            self.gui.log("Aguardando próxima página carregar...")
            page.wait_for_load_state('networkidle', timeout=10000)
            self.delay.custom(self.network_delay)
            
            self.gui.log(f"✓ Próxima página carregada")
            self.steps.append("Avançou para próxima página")
            
        except Exception as e:
            raise Exception(f"Erro ao clicar Avançar (Etapa 6): {str(e)}")


    def click_pesquisar_natureza(self, page):
        """
        Etapa 7: Clica em Pesquisar na seção Natureza da Operação
        Botão: <i name="botaoPesquisa_cfops_id" class="fa-solid fa-magnifying-glass">
        """
        if not self._set_tag("click_pesquisar_natureza"):
            return
        self.gui.log("Etapa 7: Clicando em Pesquisar (Natureza da Operação)...")

        self.delay.custom(self.interaction_delay * 1.5)

        try:
            selector_btn = 'i[name="botaoPesquisa_cfops_id"]'
            selector_cfop = 'select[name="dados_cfops_id"]'

            page.wait_for_selector(selector_btn, state='visible', timeout=15000)
            page.locator(selector_btn).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)

            def _cfop_carregado():
                return page.evaluate('''() => {
                    const sel = document.querySelector('select[name="dados_cfops_id"]');
                    if (!sel) return false;

                    const hasNonEmptyOption = Array.from(sel.options || []).some(opt =>
                        (opt.value || '').toString().trim() !== '' &&
                        (opt.textContent || '').toString().trim() !== ''
                    );
                    const hasSelectedValue = (sel.value || '').toString().trim() !== '';

                    return hasNonEmptyOption || hasSelectedValue;
                }''')

            clicked = False
            for tentativa in range(1, 4):
                try:
                    page.locator(selector_btn).click(force=True, timeout=7000)
                    clicked = True
                    self.gui.log(f"Clique no botão Pesquisar (Natureza) realizado (tentativa {tentativa})")
                except Exception as click_error:
                    self.gui.log(
                        f"Falha no clique padrão (tentativa {tentativa}): {click_error}. Tentando JavaScript.",
                        level="warning"
                    )
                    try:
                        page.evaluate('document.querySelector(\'i[name="botaoPesquisa_cfops_id"]\')?.click()')
                        clicked = True
                        self.gui.log(f"Clique via JavaScript realizado (tentativa {tentativa})")
                    except Exception as js_error:
                        self.gui.log(f"Falha no clique via JavaScript (tentativa {tentativa}): {js_error}", level="warning")

                if not clicked:
                    continue

                try:
                    page.wait_for_selector(selector_cfop, state='visible', timeout=10000)
                except Exception:
                    pass

                self.delay.custom(self.network_delay)
                if _cfop_carregado():
                    self.gui.log("✓ Botão Pesquisar (Natureza) confirmado por carregamento do campo Natureza da Operação")
                    self.steps.append("Pesquisou Natureza da Operação")
                    return

                self.gui.log(
                    f"Botão clicado, mas campo Natureza ainda sem valor/opções válidas (tentativa {tentativa}).",
                    level="warning"
                )
                self.delay.custom(self.interaction_delay)

            raise Exception("Clique em Pesquisar (Natureza) não confirmou carregamento do campo dados_cfops_id após 3 tentativas.")
            
        except Exception as e:
            raise Exception(f"Erro ao clicar Pesquisar (Natureza): {str(e)}")


    def preencher_frete_valor(self, page, valor_cte):
        """
        Etapa 8: Preenche Frete Valor
        Campo: <input name="dados_valorFrete">
        Valor: Da coluna "VALOR TT CTE"
        """
        if not self._set_tag("preencher_frete_valor"):
            return
        self.gui.log("Etapa 8: Preenchendo Frete Valor...")

        self.delay.custom(self.interaction_delay * 1.5)

        try:
            selector = 'input[name="dados_valorFrete"]'
            page.wait_for_selector(selector, state='visible', timeout=5000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            # Limpar campo existente
            page.fill(selector, '')
            self.delay.custom(self.interaction_delay // 2)
            
            # Formatar valor (substituir ponto por vírgula)
            valor_formatado = str(valor_cte).replace('.', ',')
            
            # Preencher com novo valor
            page.locator(selector).type(valor_formatado, delay=self.typing_delay)
            
            self.gui.log(f"✓ Frete Valor preenchido: {valor_formatado}")
            self.delay.custom(self.interaction_delay * 1.5)
            self.steps.append(f"Frete Valor: {valor_formatado}")
            
        except Exception as e:
            raise Exception(f"Erro ao preencher Frete Valor: {str(e)}")


    def preencher_senha_ravex(self, page, senha_ravex, uf=None):
        """
        Etapa 9: Preenche Senha Ravex
        Campo: <input name="dados_tagsCTe[ravex]">
        Valor: Da coluna "Senha Ravex"
        Regra BA: usa apenas o último valor do bloco
        """
        if not self._set_tag("preencher_senha_ravex"):
            return
        self.gui.log("Etapa 9: Preenchendo Senha Ravex...")

        self.delay.custom(self.interaction_delay * 1.5)

        try:
            selector = 'input[name="dados_tagsCTe[ravex]"]'
            page.wait_for_selector(selector, state='visible', timeout=15000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)

            is_bahia = str(uf).strip().upper() == 'BA' if uf else False
            senha_para_preencher = self._last_block_value(senha_ravex) if is_bahia else self._join_block_values(senha_ravex)

            if is_bahia:
                self.gui.log(f"UF BA detectada: usando última Senha Ravex do bloco ({senha_para_preencher})")
            
            # Limpar campo
            page.fill(selector, '')
            self.delay.custom(self.interaction_delay // 2)
            
            # Preencher com senha
            try:
                page.fill(selector, str(senha_para_preencher), timeout=90000)
            except Exception:
                page.locator(selector).type(str(senha_para_preencher), delay=self.typing_delay, timeout=90000)
            
            self.gui.log(f"✓ Senha Ravex preenchida")
            self.delay.custom(self.interaction_delay * 1.5)
            self.steps.append("Senha Ravex preenchida")
            
        except Exception as e:
            raise Exception(f"Erro ao preencher Senha Ravex: {str(e)}")


    def preencher_observacao_conhecimento(self, page, tipo_adc, nota_fiscal, senha_ravex, transporte):
        """
        Etapa 10: Preenche Observação Conhecimento
        Campo: <textarea name="dados_observacaoConhecimento">
        Formato: f"Referente {tipo_adc} NF {nota_fiscal}
                   Senha {senha_ravex}
                   Transporte {transporte}"
        """
        if not self._set_tag("preencher_observacao_conhecimento"):
            return
        self.gui.log("Etapa 10: Preenchendo Observação Conhecimento...")

        self.delay.custom(self.interaction_delay * 1.5)

        try:
            selector = 'textarea[name="dados_observacaoConhecimento"]'
            page.wait_for_selector(selector, state='visible', timeout=15000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            # Construir observação formatada
            nota_fiscal_texto = self._join_block_values(nota_fiscal)
            senha_ravex_texto = self._join_block_values(senha_ravex)
            transporte_texto = self._join_block_values(transporte)

            observacao = (
                f"Referente {tipo_adc} NF {nota_fiscal_texto}\n"
                f"Senha {senha_ravex_texto}\n"
                f"Transporte {transporte_texto}"
            )
            
            # Limpar campo
            page.fill(selector, '')
            self.delay.custom(self.interaction_delay // 2)
            
            # Preencher observação
            try:
                page.fill(selector, observacao, timeout=90000)
            except Exception:
                page.locator(selector).type(observacao, delay=self.typing_delay, timeout=90000)
            
            self.gui.log(f"✓ Observação Conhecimento preenchida")
            self.delay.custom(self.interaction_delay * 1.5)
            self.steps.append("Observação Conhecimento preenchida")
            
        except Exception as e:
            raise Exception(f"Erro ao preencher Observação: {str(e)}")


    def salvar_formulario(self, page):
        """
        Etapa 11: Clica em Salvar e aguarda mudança de URL
        Botão: <input name="botao_finalizacao" value="Salvar">
        """
        if not self._set_tag("salvar_formulario"):
            return
        self.gui.log("Etapa 11: Clicando em Salvar...")

        self.delay.custom(self.interaction_delay * 1.5)

        try:
            selector = 'input[name="botao_finalizacao"][value="Salvar"]'
            page.wait_for_selector(selector, state='visible', timeout=5000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            page.click(selector, force=True)
            
            self.gui.log(f"✓ Botão Salvar clicado")
            
            # Aguardar mudança de URL
            self.gui.log("Aguardando mudança de URL após salvar...")
            self.delay.custom(self.network_delay)
            
            try:
                page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                self.gui.log("Continuando após timeout de carregamento", level="warning")
            
            self.gui.log(f"✓ Formulário salvo com sucesso")
            self.steps.append("Formulário salvo")
            
        except Exception as e:
            raise Exception(f"Erro ao salvar formulário: {str(e)}")


    def preencher_tabela_frete(self, page):
        """
        Seleciona Tabela de Frete (Caminho 2)
        Campo: select[name="dados_freteMinimo_tabela"]
        Valor: "A"
        """
        if not self._set_tag("preencher_tabela_frete"):
            return
        self.gui.log("Selecionando Tabela de Frete...")
        try:
            selector = 'select[name="dados_freteMinimo_tabela"]'
            page.wait_for_selector(selector, state='visible', timeout=5000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            page.select_option(selector, 'A')
            self.gui.log("✓ Tabela selecionada: A")
            self.delay.custom(self.interaction_delay)
        except Exception as e:
            raise Exception(f"Erro ao selecionar Tabela de Frete: {e}")


    def preencher_tipo_carga(self, page):
        """
        Seleciona Tipo de Carga (Caminho 2)
        Campo: select[name="dados_freteMinimo_tipoCarga"]
        Valor: "FRI" (3 - Frigorificada)
        """
        if not self._set_tag("preencher_tipo_carga"):
            return
        self.gui.log("Selecionando Tipo de Carga...")
        try:
            selector = 'select[name="dados_freteMinimo_tipoCarga"]'
            page.wait_for_selector(selector, state='visible', timeout=5000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            page.select_option(selector, 'FRI')
            self.gui.log("✓ Tipo de Carga selecionado: Frigorificada")
            self.delay.custom(self.interaction_delay)
        except Exception as e:
            raise Exception(f"Erro ao selecionar Tipo de Carga: {e}")
