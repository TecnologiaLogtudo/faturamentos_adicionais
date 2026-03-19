# -*- coding: utf-8 -*-
"""
Fluxo alternativo para Pernoite/Reentrega/Diária (Caminho 2).
"""

class NotaFiscalPernoiteReentregaMixin:
    """Métodos do workflow para NotaFiscalPernoiteReentregaMixin."""

    def process_pernoite_reentrega(self, page, data, cte_number):
        """
        Processa Caminho 2 - Pernoite/Reentrega
        """
        tipo_adc = data.get('tipo_adc', '')
        uf = data.get('uf', '')
        nota_fiscal = data.get('nota_fiscal', '')
        valor_cte = data.get('valor_cte', '')
        senha_ravex = data.get('senha_ravex', '')
        transporte = data.get('transporte', '')

        self.gui.log(f"Processando Caminho 2 - {tipo_adc}...")

        try:
            # PRIMEIRA PÁGINA
            # Etapa 1: Selecionar agência
            self.select_agencia(page, uf)

            # Etapa 2: Selecionar Talão
            self.select_talao(page)

            # Etapa 3: Identificação do Pedido (Mapeamento Específico)
            identificacao = self.determinar_identificacao_pedido(tipo_adc, uf)

            self.fill_identificacao_custom(page, identificacao)

            # Etapa 4: Tipo de CT-e
            self.select_tipo_cte_complemento(page)

            # Etapa 5: Pesquisar CT-e complementar
            self.pesquisar_cte_complementar(page, cte_number)

            # NOVO: Tarefa Paralela (Cotações)
            # Executa em uma nova página (aba) conforme solicitado
            self.run_cotacoes_task(page.context, senha_ravex)

            # NOVO: Preencher cotação e pesquisar
            self.preencher_cotacao_e_pesquisar(page)

            # Etapa 6: Avançar
            self.avancar_pagina(page)

            # SEGUNDA PÁGINA (Reaproveitando lógica do Caminho 1)
            self.click_pesquisar_natureza(page)
            
            # NOVOS PASSOS: Tabela e Tipo de Carga
            self.preencher_tabela_frete(page)
            self.preencher_tipo_carga(page)
            
            self.preencher_frete_valor(page, valor_cte)
            self.preencher_senha_ravex(page, senha_ravex)
            self.preencher_observacao_conhecimento(page, tipo_adc, nota_fiscal, senha_ravex, transporte)
            
            # Substituído 'clicar_avancar_final' por 'salvar_formulario' para evitar ir para contratos
            self.salvar_formulario(page)

            # Caminho 2: Envios desabilitado. Apenas extrai o CT-e da tabela.
            generated_cte = self.extrair_cte_da_tabela(page)

            final_cte = generated_cte or cte_number
            self.gui.log(
                f"✓ Caminho 2 ({tipo_adc}) completado com sucesso - CT-e: {final_cte}",
                level="success",
            )
            self.steps.append(f"Processou {tipo_adc} completado - CT-e: {final_cte}")
            
            return final_cte

        except Exception as e:
            raise Exception(f"Erro ao processar {tipo_adc} (Caminho 2): {str(e)}")


    def run_cotacoes_task(self, context, senha_ravex):
        """
        Executa a tarefa de Cotações em paralelo (nova aba)
        """
        if not self._set_tag("run_cotacoes_task"):
            return
        self.gui.log("Iniciando tarefa paralela: Cotações Frete...")
        
        try:
            # Abrir nova página (aba)
            page_cotacoes = context.new_page()
            url_cotacoes = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=transp_cotacoesFrete&menu=s"
            
            self.gui.log(f"Abrindo URL Cotações: {url_cotacoes}")
            page_cotacoes.goto(url_cotacoes, wait_until='domcontentloaded')
            
            # Expandir filtro
            self.gui.log("Expandindo filtro Cotações...")
            try:
                expand_btn = page_cotacoes.wait_for_selector('i.fa-chevron-up, .expand-btn', timeout=5000)
                if expand_btn:
                    expand_btn.click()
                    self.delay.custom(self.interaction_delay)
            except:
                self.gui.log("Filtro Cotações pode já estar expandido ou não encontrado", level="debug")

            # Limpar campos
            self.gui.log("Limpando campos do filtro...")
            
            # Lista de selects para limpar (selecionar vazio)
            selects_to_clear = [
                'busca_cliente', 'busca_agencia', 'busca_status', 
                'busca_possuiConhecimento', 'busca_possuiOC', 'busca_minhasCotacoes'
            ]
            
            for name in selects_to_clear:
                try:
                    sel = page_cotacoes.locator(f'select[name="{name}"]')
                    if sel.is_visible():
                        sel.select_option('')
                except: pass

            # Lista de inputs para limpar
            inputs_to_clear = [
                'pesquisa_busca_cliente', 'busca_nro', 'busca_contatos'
            ]
            
            for name in inputs_to_clear:
                try:
                    inp = page_cotacoes.locator(f'input[name="{name}"]')
                    if inp.is_visible():
                        inp.fill('')
                except: pass

            self.delay.custom(self.interaction_delay)

            # Preencher Número com Senha Ravex
            self.gui.log(f"Preenchendo Número com Senha Ravex: {senha_ravex}")
            try:
                page_cotacoes.fill('input[name="busca_nro"]', str(senha_ravex))
            except Exception as e:
                self.gui.log(f"Erro ao preencher número na cotação: {e}", level="warning")

            self.delay.custom(self.interaction_delay)

            # Clicar em Filtrar
            self.gui.log("Clicando em Filtrar (Cotações)...")
            try:
                page_cotacoes.click('input[value="Filtrar"]', force=True)
                self.delay.custom(self.interaction_delay * 2) # Aguardar um pouco o clique surtir efeito
            except Exception as e:
                self.gui.log(f"Erro ao clicar Filtrar na cotação: {e}", level="warning")

            # Extrair número da cotação
            self.gui.log("Aguardando e extraindo número da cotação...")
            try:
                # Aguardar tabela carregar (td[swni="no_cliente"])
                page_cotacoes.wait_for_selector('td[swni="no_cliente"]', state='visible', timeout=10000)
                
                # Extrair valor
                cotacao_numero = page_cotacoes.evaluate('''() => {
                    const cells = Array.from(document.querySelectorAll('td[swni="no_cliente"]'));
                    for (const cell of cells) {
                        const text = cell.textContent.trim();
                        // Procura por uma célula que contenha apenas números, para evitar o cabeçalho.
                        if (text && /^\\d+$/.test(text)) {
                            return text;
                        }
                    }
                    return null;
                }''')
                
                # Extrair data da cotação (td[swni="emissao"])
                cotacao_data = page_cotacoes.evaluate('''() => {
                    const cells = Array.from(document.querySelectorAll('td[swni="emissao"]'));
                    for (const cell of cells) {
                        const text = cell.textContent.trim();
                        // Ignora a célula do cabeçalho verificando o texto
                        if (text.toLowerCase() !== 'emissão' && text.toLowerCase() !== 'emissao' && text) {
                            return text;
                        }
                    }
                    return null;
                }''')

                if cotacao_data:
                    self.gui.log(f"✓ Data Cotação capturada: {cotacao_data}")
                    self.cotacao_data = cotacao_data

                if cotacao_numero:
                    self.gui.log(f"✓ Cotação capturada: {cotacao_numero}")
                    self.cotacao_numero = cotacao_numero
                else:
                    self.gui.log("Valor da cotação não encontrado", level="warning")
            except Exception as e:
                self.gui.log(f"Erro na extração da cotação: {e}", level="warning")

            self.gui.log("Tarefa Cotações finalizada. Fechando aba...")
            
            # Fechar a página para liberar recursos
            page_cotacoes.close()
            
            self.gui.log("✓ Aba Cotações fechada")

        except Exception as e:
            self.gui.log(f"Erro na tarefa paralela Cotações: {str(e)}", level="error")
            # Não lançamos exceção aqui para não parar o fluxo principal, apenas logamos erro


    def preencher_cotacao_e_pesquisar(self, page):
        """
        Preenche o número da cotação e pesquisa
        Campo: <input name="pesquisa_pedidos_id">
        Botão: <i name="botaoPesquisa_pedidos_id">
        """
        if not self._set_tag("preencher_cotacao_e_pesquisar"):
            return
        if not self.cotacao_numero:
            self.gui.log("Nenhum número de cotação capturado para preencher.", level="warning")
            return

        self.gui.log(f"Preenchendo cotação: {self.cotacao_numero}...")
        
        try:
            page.bring_to_front()
            
            selector_input = 'input[name="pesquisa_pedidos_id"]'
            page.wait_for_selector(selector_input, state='visible', timeout=5000)
            page.locator(selector_input).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            # Limpar e preencher
            page.fill(selector_input, '')
            self.delay.custom(self.interaction_delay // 2)
            page.locator(selector_input).type(self.cotacao_numero, delay=self.typing_delay)
            
            self.gui.log(f"✓ Cotação digitada: {self.cotacao_numero}")
            self.delay.custom(self.interaction_delay)
            
            # Clicar em Pesquisar
            selector_btn = 'i[name="botaoPesquisa_pedidos_id"]'
            page.wait_for_selector(selector_btn, state='visible', timeout=5000)
            page.click(selector_btn, force=True)
            
            self.gui.log("✓ Botão Pesquisar cotação clicado")
            self.delay.custom(self.network_delay) # Aguardar pesquisa
            self.steps.append(f"Cotação pesquisada: {self.cotacao_numero}")
            
        except Exception as e:
            raise Exception(f"Erro ao preencher/pesquisar cotação: {str(e)}")
