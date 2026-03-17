# -*- coding: utf-8 -*-
"""
Etapa de busca da nota fiscal e extração inicial do CT-e.
"""

class NotaFiscalStepSearchMixin:
    """Métodos do workflow para NotaFiscalStepSearchMixin."""

    def expand_filter_and_search(self, page, nota_fiscal, should_expand=True):
        """Expande filtro e pesquisa nota fiscal"""

        # Aguardar página carregar completamente
        try:
            if not self._set_tag("expand_filter.wait_load"):
                return
            page.wait_for_load_state('networkidle', timeout=8000)
        except:
            self.gui.log("Continuando sem networkidle", level="warning")

        if not self._set_tag("expand_filter.delay_before_check"):
            return
        self.delay.custom(self.interaction_delay)

        # Verificação precisa do estado do filtro baseada na classe CSS
        # Se a div tiver a classe 'rg-busca-rapida-close', o filtro está fechado.
        if not self._set_tag("expand_filter.check_state"):
            return
        is_filter_closed = page.evaluate('''() => {
            const filterDiv = document.querySelector('div.rg-busca-rapida');
            if (filterDiv && filterDiv.classList.contains('rg-busca-rapida-close')) {
                return true;
            }
            return false;
        }''')

        if is_filter_closed:
            self.gui.log("Filtro detectado como FECHADO (classe .rg-busca-rapida-close). Expandindo...")
            # Clicar no botão de expandir
            expand_selectors = [
                'i.fa-chevron-up',
                'i[class*="chevron"]',
                '.expand-btn',
                '[class*="expand"]',
                'div.rg-busca-rapida'  # Tenta clicar na própria div se os ícones falharem
            ]

            for selector in expand_selectors:
                try:
                    if page.is_visible(selector):
                        if not self._set_tag(f"expand_filter.open:{selector}"):
                            return
                        page.click(selector, force=True)
                        self.gui.log(f"Clicou para expandir usando: {selector}")
                        # Pequena pausa para animação
                        self.delay.custom(500)
                        break
                except:
                    continue
        else:
            self.gui.log("Filtro detectado como ABERTO. Prosseguindo.")

        if not self._set_tag("expand_filter.delay_before_fill"):
            return
        self.delay.custom(self.interaction_delay * 2)

        # Como para a UF BA a nota_fiscal pode conter várias notas separadas por vírgula,
        # extraímos apenas a última nota fiscal para não dar erro na pesquisa do LogTudo.
        nf_search = nota_fiscal.split(',')[-1].strip() if nota_fiscal else ""

        # Preencher campo N.º Doc. Ref.
        self.gui.log(f"Preenchendo Nota Fiscal para pesquisa: {nf_search}")
        
        try:
            if not self._set_tag("expand_filter.wait_nf_input"):
                return
            page.wait_for_selector('input[name="busca_nDoc"]', state='visible', timeout=5000)
            locator = page.locator('input[name="busca_nDoc"]')
            locator.scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            # Limpar o campo primeiro
            if not self._set_tag("expand_filter.clear_nf"):
                return
            locator.fill('')
            self.delay.custom(self.interaction_delay // 2)
            
            # Preencher com a nova nota fiscal
            self.gui.log(f"Digitando valor da Nota Fiscal: {nf_search}...")
            if not self._set_tag("expand_filter.fill_nf"):
                return
            locator.fill(nf_search)
            self.gui.log(f"Nota Fiscal preenchida: {nf_search}")
        except Exception as e:
            raise Exception(f"Erro ao preencher nota fiscal: {e}")

        if not self._set_tag("expand_filter.delay_before_filter"):
            return
        self.delay.custom(self.interaction_delay * 2)

        # Clicar em Filtrar
        self.gui.log("Clicando em Filtrar...")
        try:
            filter_selector = 'input[type="submit"][value="Filtrar"]'
            if not self._set_tag("expand_filter.wait_filter_button"):
                return
            filter_btn = page.wait_for_selector(filter_selector, state='visible', timeout=5000)
            if filter_btn:
                page.locator(filter_selector).scroll_into_view_if_needed()
                self.delay.custom(self.interaction_delay)
                if not self._set_tag("expand_filter.click_filter"):
                    return
                filter_btn.click(force=True)
                self.gui.log("Botão Filtrar clicado")
        except:
            try:
                # Via JavaScript como fallback
                self.gui.log("Tentando clicar Filtrar via JavaScript...")
                if not self._set_tag("expand_filter.click_filter_js"):
                    return
                page.evaluate('document.querySelector("input[value=\\"Filtrar\\"]").click()')
            except Exception as e:
                raise Exception(f"Erro ao clicar Filtrar: {e}")

        # Aguardar resultados
        self.gui.log("Aguardando resultados da pesquisa...")
        if not self._set_tag("expand_filter.wait_results"):
            return
        self.delay.custom(self.network_delay)
        self.steps.append(f"Pesquisou nota fiscal: {nf_search}")


    def wait_for_results_and_get_cte(self, page):
        """
        Aguarda resultados da tabela e extrai os dados dela.
        """
        if not self._set_tag("results.wait_table"):
            return {'number': None, 'id': None, 'row': None}
        self.gui.log("Aguardando resultados da tabela...")

        # 1. Aguardar que a tabela de resultados apareça
        try:
            page.wait_for_selector('tbody tr', state='visible', timeout=15000)
            self.gui.log("Tabela de resultados carregada.")
        except Exception as e:
            raise Exception(f"Timeout aguardando tabela de resultados: {e}")

        # 2. Obter dados da linha correta (validando conteúdo)
        self.gui.log("Extraindo dados da linha...")
        try:
            if not self._set_tag("results.extract_row"):
                return {'number': None, 'id': None, 'row': None}
            result = page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('tbody tr'));
                let targetRow = null;
                
                // Procurar linha de dados válida
                for (const row of rows) {
                    if (row.classList.contains('cabec')) continue;
                    
                    const noCell = row.querySelector('td[swni="no"]');
                    if (noCell) {
                        const text = noCell.textContent.trim();
                        // Ignorar cabeçalho
                        if (text && text !== 'N.º' && text !== 'Nº') {
                            targetRow = row;
                            break;
                        }
                    }
                }
                
                if (!targetRow) {
                    // Fallback para segunda linha se existir
                    if (rows.length > 1) targetRow = rows[1];
                    else if (rows.length === 1) targetRow = rows[0];
                    else return { error: "Nenhuma linha de dados válida encontrada" };
                }
                
                const noCellElement = targetRow.querySelector('td[swni="no"]');
                const cteNumber = noCellElement ? noCellElement.textContent.trim() : null;
                
                const checkboxElement = targetRow.querySelector('input[type="checkbox"][name="id"]');
                const checkboxId = checkboxElement ? checkboxElement.value : null;
                
                const talaoElement = targetRow.querySelector('td[swni="talao"]');
                const talaoValue = talaoElement ? talaoElement.textContent.trim() : null;
                
                const clienteElement = targetRow.querySelector('td[swni="cliente__nome"]');
                const clienteValue = clienteElement ? clienteElement.textContent.trim() : null;
                
                const dataElement = targetRow.querySelector('td[swni="data_de_emissao"]');
                const dataValue = dataElement ? dataElement.textContent.trim() : null;
                
                return {
                    cteNumber: cteNumber,
                    checkboxId: checkboxId,
                    talao: talaoValue,
                    cliente: clienteValue,
                    data: dataValue,
                    error: null
                };
            }''')
        except Exception as e:
            raise Exception(f"Erro ao extrair dados da linha via page.evaluate: {str(e)}")

        # Validar resultado
        if result.get('error'):
            raise Exception(f"Erro ao processar linha no JS: {result['error']}")
        
        cte_number = result.get('cteNumber')
        checkbox_id = result.get('checkboxId')
        
        if not cte_number or cte_number == '':
            raise Exception("Não foi possível encontrar número CT-e na linha (td[swni='no'] vazio)")
        
        # Validação extra para garantir que não pegamos o cabeçalho
        if cte_number in ['N.º', 'Nº', 'No', 'Numero']:
             raise Exception(f"Erro: O valor extraído parece ser um cabeçalho: '{cte_number}'")

        if not checkbox_id or checkbox_id == '':
            raise Exception("Não foi possível encontrar ID do checkbox na linha")

        self.row_checkbox_id = checkbox_id
        
        self.gui.log(f"✓ CT-e extraído: {cte_number}")
        self.gui.log(f"✓ ID da linha guardado: {checkbox_id}")
        self.gui.log(f"  - Talão: {result.get('talao', 'N/A')}")
        self.gui.log(f"  - Cliente: {result.get('cliente', 'N/A')}")
        self.gui.log(f"  - Data: {result.get('data', 'N/A')}")
        self.steps.append(f"CT-e obtido: {cte_number} (ID: {checkbox_id})")

        return {'number': cte_number, 'id': checkbox_id, 'row': None}
