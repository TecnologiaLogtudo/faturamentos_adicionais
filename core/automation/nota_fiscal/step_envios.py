# -*- coding: utf-8 -*-
"""
Etapa de envios: marcar linha, executar CT-e e extrair resultado.
"""

class NotaFiscalStepEnviosMixin:
    """Métodos do workflow para NotaFiscalStepEnviosMixin."""

    def extrair_cte_da_tabela(self, page):
        """
        Extrai o número do CT-e da tabela de resultados (grid).
        Usado quando a etapa de envios não é executada.
        """
        self.check_pause()
        self.gui.log("Extraindo número do CT-e da tabela...")
        try:
            # Aguardar que a tabela esteja visível
            page.wait_for_selector('td[swni="no"]', state='visible', timeout=10000)
            
            generated_cte = page.evaluate('''() => {
                // Procurar todas as células td[swni="no"] na tabela
                const noCells = Array.from(document.querySelectorAll('td[swni="no"]'));
                let lastNumericCell = null;
                
                // Encontrar a última célula que contém apenas dígitos (ignorando cabeçalhos)
                for (const cell of noCells) {
                    const text = cell.textContent.trim();
                    if (/^\d+$/.test(text)) {
                        lastNumericCell = cell;
                    }
                }
                
                // Retornar o conteúdo da última célula numérica encontrada
                if (lastNumericCell) {
                    return lastNumericCell.textContent.trim();
                } else {
                    return null;
                }
            }''')
            
            if generated_cte:
                self.gui.log(f"✓ CT-e extraído: {generated_cte}")
                return generated_cte
            else:
                self.gui.log("CT-e não encontrado na tabela.", level="warning")
                return None
                
        except Exception as e:
            self.gui.log(f"Erro ao extrair CT-e da tabela: {e}", level="warning")
            return None


    def process_envios_caminho_1(self, page):
        """
        Processa a etapa de envio simplificada para o Caminho 1.
        Clica em Executar e extrai o número do CT-e gerado.
        """
        self.check_pause()
        self.gui.log("Iniciando processo de envio (Caminho 1)...")

        # 1. Clicar em Executar
        try:
            exec_selector = 'input[value="Executar"][name="btS"]'
            self.gui.log("Clicando em Executar...")
            page.wait_for_selector(exec_selector, state='visible', timeout=10000)
            page.locator(exec_selector).click(force=True)
            self.gui.log("✓ Botão Executar clicado.")
        except Exception as e:
            # Fallback se o primeiro seletor falhar
            try:
                self.gui.log("Tentando clicar em Executar com fallback...", level="warning")
                page.evaluate('document.querySelector("input[value=\\"Executar\\"]").click()')
                self.gui.log("✓ Botão Executar clicado (fallback).")
            except Exception as e2:
                raise Exception(f"Erro ao clicar no botão Executar: {e2}")

        # 2. Aguardar resultado e extrair número
        try:
            self.gui.log("Aguardando confirmação de processamento...")
            
            processed_cell_selector = 'td:has-text("Processado")'
            success_message_selector = 'p.regular-small-text:has-text("Conhecimento inserido com sucesso.")'

            # Wait for either of the selectors to be visible
            page.wait_for_selector(f"{processed_cell_selector}, {success_message_selector}", timeout=60000)
            self.gui.log("✓ Confirmação de processamento encontrada.")

            self.delay.custom(self.interaction_delay * 2)

            generated_cte = page.evaluate('''() => {
                // Procurar todas as células td[swni="no"] na tabela
                const noCells = Array.from(document.querySelectorAll('td[swni="no"]'));
                let lastNumericCell = null;
                
                // Encontrar a última célula que contém apenas dígitos (ignorando cabeçalhos)
                for (const cell of noCells) {
                    const text = cell.textContent.trim();
                    if (/^\d+$/.test(text)) {
                        lastNumericCell = cell;
                    }
                }
                
                // Retornar o conteúdo da última célula numérica encontrada
                if (lastNumericCell) {
                    return lastNumericCell.textContent.trim();
                } else {
                    return null;
                }
            }''')

            if not generated_cte:
                raise Exception("Não foi possível extrair o número do CT-e gerado após o processamento.")

            self.gui.log(f"✓ CT-e gerado (Caminho 1): {generated_cte}", level="success")
            return generated_cte

        except Exception as e:
            raise Exception(f"Erro ao aguardar processamento ou extrair número do CT-e: {e}")


    def select_row_by_id(self, checkbox_id):
        """
        Marca o checkbox usando o ID guardado da etapa anterior.
        
        Tenta múltiplas estratégias de click:
        1. Click direto no input[type="checkbox"]
        2. Click na <span class="sw-label-check"> (rótulo visual)
        3. Click usando locator.click()
        4. Marcar usando JavaScript (fallback)
        
        O checkbox_id foi extraído na etapa de wait_for_results_and_get_cte()
        e guardado em self.row_checkbox_id.
        """
        try:
            page = self.controller.page
            
            self.gui.log(f"Etapa 12: Marcando checkbox com ID {checkbox_id}...")
            
            # Tentar múltiplas estratégias de click
            checkbox_selector = f'input[type="checkbox"][name="id"][value="{checkbox_id}"]'
            label_selector = f'input[type="checkbox"][name="id"][value="{checkbox_id}"] + span.sw-label-check'
            
            # Estratégia 1: Validar elemento e tentar click direto
            try:
                self.gui.log(f"  Tentativa 1: Click direto no input...")
                page.wait_for_selector(checkbox_selector, state='visible', timeout=3000)
                page.locator(checkbox_selector).scroll_into_view_if_needed()
                self.delay.custom(self.interaction_delay)
                page.click(checkbox_selector, force=True)
                self.gui.log(f"✓ Checkbox marcado (ID: {checkbox_id}) - Estratégia 1")
                self.steps.append(f"Checkbox marcado (ID: {checkbox_id})")
                self.delay.network()
                return
            except Exception as e1:
                self.gui.log(f"  Tentativa 1 falhou: {str(e1)}", level="debug")
            
            # Estratégia 2: Tentar clicar no label (span.sw-label-check)
            try:
                self.gui.log(f"  Tentativa 2: Click no rótulo (span.sw-label-check)...")
                page.wait_for_selector(label_selector, state='visible', timeout=3000)
                page.locator(label_selector).scroll_into_view_if_needed()
                self.delay.custom(self.interaction_delay)
                page.click(label_selector, force=True)
                self.gui.log(f"✓ Checkbox marcado (ID: {checkbox_id}) - Estratégia 2")
                self.steps.append(f"Checkbox marcado (ID: {checkbox_id})")
                self.delay.network()
                return
            except Exception as e2:
                self.gui.log(f"  Tentativa 2 falhou: {str(e2)}", level="debug")
            
            # Estratégia 3: Tentar usando locator.click() ao invés de page.click()
            try:
                self.gui.log(f"  Tentativa 3: Click usando locator...")
                locator = page.locator(checkbox_selector)
                locator.wait_for(state='visible', timeout=3000)
                locator.scroll_into_view_if_needed()
                self.delay.custom(self.interaction_delay)
                locator.click(force=True)
                self.gui.log(f"✓ Checkbox marcado (ID: {checkbox_id}) - Estratégia 3")
                self.steps.append(f"Checkbox marcado (ID: {checkbox_id})")
                self.delay.network()
                return
            except Exception as e3:
                self.gui.log(f"  Tentativa 3 falhou: {str(e3)}", level="debug")
            
            # Estratégia 4: Fallback - Marcar usando JavaScript (força bruta)
            try:
                self.gui.log(f"  Tentativa 4: Marcar usando JavaScript...")
                result = page.evaluate(f'''() => {{
                    const checkbox = document.querySelector('input[type="checkbox"][name="id"][value="{checkbox_id}"]');
                    if (!checkbox) {{
                        return {{ success: false, error: "Checkbox não encontrado" }};
                    }}
                    
                    // Marcar checkbox
                    checkbox.checked = true;
                    
                    // Disparar eventos para garantir que a aplicação detecte
                    checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    checkbox.dispatchEvent(new Event('click', {{ bubbles: true }}));
                    checkbox.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    return {{ success: true, error: null }};
                }}''')
                
                if result.get('success'):
                    self.gui.log(f"✓ Checkbox marcado (ID: {checkbox_id}) - Estratégia 4 (JavaScript)")
                    self.steps.append(f"Checkbox marcado (ID: {checkbox_id})")
                    self.delay.network()
                    return
                else:
                    raise Exception(f"JavaScript falhou: {result.get('error')}")
            except Exception as e4:
                self.gui.log(f"  Tentativa 4 falhou: {str(e4)}", level="debug")
            
            # Se chegou aqui, todas as estratégias falharam
            raise Exception(f"Todas as estratégias falharam. Checkbox com ID {checkbox_id} não pode ser clicado")
            
        except Exception as e:
            raise Exception(f"Erro ao marcar checkbox com ID {checkbox_id}: {str(e)}")
    

    def click_cte_button(self):
        """
        Clica no botão CT-e para visualizar/processar o CT-e.
        
        Seleciona img[title="CT-e"].
        """
        try:
            page = self.controller.page
            
            self.gui.log("Etapa 13: Clicando em botão CT-e...")
            
            # Seletor para botão CT-e
            cte_button_selector = "img[title='CT-e']"
            
            # Validar elemento
            page.wait_for_selector(cte_button_selector, state='visible', timeout=5000)
            page.locator(cte_button_selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            page.click(cte_button_selector, force=True)
            
            self.gui.log(f"✓ Botão CT-e clicado")
            self.steps.append("CT-e clicado")
            self.delay.network()
            
        except Exception as e:
            raise Exception(f"Erro ao clicar em CT-e: {str(e)}")
    

    def click_executar_button(self):
        """
        Clica no botão Executar para gerar/transmitir CT-e.
        
        Seleciona input[type="button"][name="btS"][value="Executar"].
        """
        try:
            page = self.controller.page
            
            self.gui.log("Etapa 14: Clicando em botão Executar...")
            
            # Seletor para botão Executar
            executar_button_selector = "input[type='button'][name='btS'][value='Executar']"
            
            # Validar elemento
            page.wait_for_selector(executar_button_selector, state='visible', timeout=5000)
            page.locator(executar_button_selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            page.click(executar_button_selector, force=True)
            
            self.gui.log(f"✓ Botão Executar clicado")
            self.steps.append("Executar clicado")
            
            # Aguardar processamento do CT-e
            self.gui.log("Aguardando processamento do CT-e...")
            self.delay.page_load()  # 2s
            self.delay.network()      # 3s
            
        except Exception as e:
            raise Exception(f"Erro ao clicar em Executar: {str(e)}")
    

    def get_cte_number_from_row(self, checkbox_id):
        """
        Extrai o número do CT-e da linha correspondente ao checkbox selecionado.
        
        Busca a linha que contém o checkbox com o ID fornecido e extrai td[swni="no"].
        """
        try:
            page = self.controller.page
            
            self.gui.log("Etapa 15: Extraindo número do CT-e da linha...")
            
            # Aguardar elemento estar pronto
            self.delay.custom(self.interaction_delay * 1.5)
            
            # Extrair usando JavaScript para garantir precisão
            result = page.evaluate(f'''() => {{
                // Encontrar checkbox pelo ID
                const checkbox = document.querySelector('input[type="checkbox"][name="id"][value="{checkbox_id}"]');
                
                if (!checkbox) {{
                    return {{ error: "Checkbox com ID {checkbox_id} não encontrado" }};
                }}
                
                // Ir para a linha do checkbox
                const row = checkbox.closest('tr');
                
                if (!row) {{
                    return {{ error: "Linha do checkbox não encontrada" }};
                }}
                
                // Extrair número CT-e (td[swni="no"])
                const noCellElement = row.querySelector('td[swni="no"]');
                const cteNumber = noCellElement ? noCellElement.textContent.trim() : null;
                
                if (!cteNumber) {{
                    return {{ error: "Número CT-e não encontrado na linha" }};
                }}
                
                return {{ cteNumber: cteNumber, error: null }};
            }}''')
            
            # Validar resultado
            if result.get('error'):
                raise Exception(f"Erro ao extrair CT-e: {result['error']}")
            
            cte_text = result.get('cteNumber')
            
            if not cte_text or cte_text.isspace():
                raise Exception("Número CT-e vazio ou não encontrado")
            
            self.gui.log(f"✓ CT-e número extraído: {cte_text}")
            self.steps.append(f"CT-e extraído: {cte_text}")
            
            return cte_text
            
        except Exception as e:
            raise Exception(f"Erro ao extrair número CT-e: {str(e)}")
