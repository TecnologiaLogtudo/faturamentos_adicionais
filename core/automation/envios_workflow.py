# -*- coding: utf-8 -*-
"""
EnviosWorkflow - Fluxo de Envios
Gerencia a seleção e execução de CT-e na seção de envios
"""
import time


class EnviosWorkflow:
    """Classe para gerenciar o fluxo de envios"""

    def __init__(self, delay, gui, error_handler):
        """
        Inicializa o workflow

        Args:
            delay: Instância de Delay
            gui: Referência para a interface (para logs)
            error_handler: Instância de ErrorHandler
        """
        self.delay = delay
        self.gui = gui
        self.error_handler = error_handler
        self.selected_row = None

    def execute(self, page, cte_number):
        """
        Executa o workflow de envios

        Args:
            page: Página do Playwright
            cte_number: Número do CT-e

        Returns:
            Número do CT-e gerado
        """
        self.gui.log("Iniciando processo de envios...")

        # 1. Navegar para seção de envios (se necessário)
        self.navigate_to_envios(page)

        # 2. Selecionar segunda linha (data mais avançada)
        self.select_second_row(page)

        # 3. Marcar checkbox
        self.check_row(page)

        # 4. Clicar em CT-e
        self.click_cte(page)

        # 5. Clicar em Executar
        self.click_executar(page)

        # 6. Copiar número do CT-e gerado
        generated_cte = self.get_generated_cte_number(page)

        self.gui.log(f"CT-e gerado: {generated_cte}")

        return generated_cte

    def navigate_to_envios(self, page):
        """Navega para seção de envios"""
        current_url = page.url()

        if 'trans_conhecimento' in current_url and 'envios' in current_url:
            self.gui.log("Já na página de envios")
            self.delay.standard()
            return

        # Tentar encontrar link/aba de envios
        envios_selectors = [
            'a[href*="envios"]',
            'button:has-text("Envios")',
            '.nav-link:has-text("Envios")'
        ]

        for selector in envios_selectors:
            try:
                element = page.wait_for_selector(selector, state='visible', timeout=2000)
                if element:
                    self.gui.log("Navegando para envios...")
                    element.click()
                    self.delay.page_load()
                    return
            except:
                continue

        # Navegar diretamente
        envios_url = current_url + '&tab=envios'
        page.goto(envios_url, wait_until='networkidle')
        self.delay.page_load()

    def select_second_row(self, page):
        """Seleciona segunda linha de dados"""
        self.gui.log("Selecionando segunda linha...")

        self.delay.standard()

        # Esperar tabela carregar
        page.wait_for_selector('tbody', state='visible', timeout=10000)

        self.delay.standard()

        # Obter todas as linhas de dados (excluindo cabeçalho)
        rows = page.query_selector_all('tbody tr:not(.cabec)')

        if len(rows) < 2:
            self.gui.log(f"Apenas {len(rows)} linha(s) encontrada(s), usando primeira linha", level="warning")
            self.selected_row = rows[0] if rows else None
        else:
            self.selected_row = rows[1]  # Segunda linha (índice 1)
            self.gui.log(f"Segunda linha selecionada (de {len(rows)} total)")

    def check_row(self, page):
        """Marca checkbox da linha"""
        self.gui.log("Marcando checkbox...")

        if not self.selected_row:
            raise Exception("Nenhuma linha selecionada")

        self.delay.standard()

        # Encontrar checkbox na linha
        try:
            checkbox = self.selected_row.query_selector('input[type="checkbox"]')

            if checkbox:
                is_checked = checkbox.is_checked()

                if not is_checked:
                    checkbox.click()
                    self.gui.log("Checkbox marcado")
                else:
                    self.gui.log("Checkbox já estava marcado")
            else:
                # Tentar por nome/id
                row_check = page.query_selector('input[name="id"]:not([style*="display: none"])')

                if row_check:
                    is_checked = row_check.is_checked()

                    if not is_checked:
                        row_check.click()
                        self.gui.log("Checkbox marcado")
                else:
                    raise Exception("Checkbox não encontrado na linha")
        except Exception as e:
            self.gui.log(f"Erro ao marcar checkbox: {e}", level="warning")

    def click_cte(self, page):
        """Clica em CT-e"""
        self.gui.log("Clicando em CT-e...")

        cte_selectors = [
            'img[title="CT-e"]',
            'button:has-text("CT-e")',
            '.btn-cte',
            'a:has-text("CT-e")',
            'img[src*="cte"]'
        ]

        for selector in cte_selectors:
            try:
                cte_button = page.wait_for_selector(selector, state='visible', timeout=5000)
                if cte_button:
                    cte_button.click()
                    self.gui.log("Botão CT-e clicado")
                    break
            except:
                continue
        else:
            raise Exception("Botão CT-e não encontrado")

        self.delay.standard()

    def click_executar(self, page):
        """Clica em Executar"""
        self.gui.log("Clicando em Executar...")

        try:
            executar_btn = page.wait_for_selector(
                'input[value="Executar"]', state='visible', timeout=5000
            )

            if executar_btn:
                executar_btn.click()
            else:
                page.evaluate('document.querySelector("input[value=\\"Executar\\"]").click()')
        except Exception as e:
            self.gui.log(f"Erro ao clicar em executar: {e}", level="warning")

        # Aguardar processamento
        self.gui.log("Aguardando processamento do CT-e...")
        self.delay.custom(3000)
        page.wait_for_load_state('networkidle')

    def get_generated_cte_number(self, page):
        """Obtém número do CT-e gerado"""
        self.gui.log("Obtendo número do CT-e gerado...")

        self.delay.standard()

        # O CT-e gerado aparece na segunda linha
        cte_number = page.evaluate('''() => {
            // Método 1: Procurar na linha selecionada
            const selectedCheckbox = document.querySelector('input[type="checkbox"]:checked');
            if (selectedCheckbox) {
                const row = selectedCheckbox.closest('tr');
                if (row) {
                    const cells = row.querySelectorAll('td[swni="no"]');
                    if (cells.length > 0) return cells[0].textContent.trim();
                }
            }

            // Método 2: Procurar na segunda linha de dados
            const rows = document.querySelectorAll('tbody tr:not(.cabec)');
            if (rows.length >= 2) {
                const secondRow = rows[1];
                const noCell = secondRow.querySelector('td[swni="no"]');
                if (noCell) return noCell.textContent.trim();
                const cells = secondRow.querySelectorAll('td');
                if (cells.length >= 3) return cells[2].textContent.trim();
            }

            // Método 3: Procurar elemento com valor recente
            const recentCells = document.querySelectorAll('tbody td[swni="no"]');
            if (recentCells.length > 0) return recentCells[recentCells.length - 1].textContent.trim();

            return null;
        }''')

        if not cte_number:
            # Tentar método alternativo
            alternative_cte = page.evaluate('''() => {
                const dacteLinks = document.querySelectorAll('a[onclick*="verDacte"], img[onclick*="verDacte"]');
                if (dacteLinks.length > 0) {
                    const lastLink = dacteLinks[dacteLinks.length - 1];
                    const onclick = lastLink.getAttribute('onclick') || '';
                    const match = onclick.match(/ids=([^&"']+)/);
                    if (match) return match[1];
                }

                const checkboxes = document.querySelectorAll('input[name="id"][title]');
                if (checkboxes.length > 0) return checkboxes[checkboxes.length - 1].getAttribute('title');

                return null;
            }''')

            if alternative_cte:
                self.gui.log(f"CT-e encontrado via método alternativo: {alternative_cte}")
                return alternative_cte

            raise Exception("Não foi possível encontrar número do CT-e gerado")

        self.gui.log(f"CT-e extraído: {cte_number}")
        return cte_number

    def check_cte_status(self, page):
        """Verifica status do CT-e"""
        status_info = page.evaluate('''() => {
            const statusElements = document.querySelectorAll('[class*="status"], [class*="transmit"]');

            for (const el of statusElements) {
                const text = el.textContent.toLowerCase();
                if (text.includes('transmitido') || text.includes('autorizado') || text.includes('processado') || text.includes('sucesso')) {
                    return { status: 'transmitted', message: el.textContent.trim() };
                }
                if (text.includes('erro') || text.includes('rejeitado')) {
                    return { status: 'error', message: el.textContent.trim() };
                }
                if (text.includes('pendente') || text.includes('processando')) {
                    return { status: 'pending', message: el.textContent.trim() };
                }
            }

            const transmitIcon = document.querySelector('img[title*="transmitido"], img[title*="CT-e transmitido"]');
            if (transmitIcon) {
                return { status: 'transmitted', message: 'CT-e transmitido com sucesso' };
            }

            return { status: 'unknown', message: 'Status não identificado' };
        }''')

        return status_info

    def wait_for_cte_transmission(self, page, max_wait=30000):
        """Aguarda CT-e ser transmitido"""
        self.gui.log("Aguardando transmissão do CT-e...")

        import time
        start_time = time.time()

        while time.time() - start_time < max_wait / 1000:
            status = self.check_cte_status(page)

            if status['status'] == 'transmitted':
                self.gui.log("CT-e transmitido!", level="success")
                return True

            if status['status'] == 'error':
                self.gui.log(f"Erro na transmissão: {status['message']}", level="error")
                return False

            self.delay.custom(1000)

        self.gui.log("Timeout aguardando transmissão", level="warning")
        return False

    def clear_selection(self, page):
        """Limpa seleção"""
        checkboxes = page.query_selector_all('input[type="checkbox"]:checked')

        for checkbox in checkboxes:
            try:
                checkbox.click()
            except:
                pass
