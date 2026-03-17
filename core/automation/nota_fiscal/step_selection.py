# -*- coding: utf-8 -*-
"""
Etapas de seleção inicial (Adicionar + Preenchimento Manual).
"""

class NotaFiscalStepSelectionMixin:
    """Métodos do workflow para NotaFiscalStepSelectionMixin."""

    def click_adicionar(self, page):
        """Clica em Adicionar"""
        self.gui.log("Clicando em Adicionar...")

        # Aguardar renderização
        self.delay.custom(self.interaction_delay)

        # Usar o seletor específico (ID _boop) para evitar ambiguidade e erros de timeout
        add_selector = '#_boop img[title="Adicionar"]'
        
        try:
            page.wait_for_selector(add_selector, state='visible', timeout=5000)
            if not self._set_tag("adicionar.click"):
                return
            page.click(add_selector, force=True)
            
            self.gui.log(f"✓ Botão Adicionar clicado")
        except Exception as e:
            # Fallback: Tentar clicar no primeiro link dentro de _boop se a imagem falhar
            try:
                if not self._set_tag("adicionar.click_fallback"):
                    return
                page.click('#_boop > a', force=True)
                self.gui.log(f"✓ Botão Adicionar clicado (fallback)")
            except Exception as e2:
                raise Exception(f"Erro ao clicar em Adicionar: {e}")

        self.delay.custom(self.interaction_delay * 3)
        self.steps.append("Clicou em Adicionar")


    def select_preenchimento_manual(self, page):
        """Seleciona Preenchimento Manual"""
        self.gui.log("Selecionando Preenchimento Manual...")

        # Aguardar página carregar
        try:
            page.wait_for_load_state('networkidle', timeout=8000)
        except:
            self.gui.log("Continuando sem networkidle", level="warning")

        self.delay.custom(self.interaction_delay * 2)

        # Usar o seletor exato fornecido: span:has-text("Preenchimento Manual")
        manual_selector = 'span:has-text("Preenchimento Manual")'
        
        try:
            page.wait_for_selector(manual_selector, state='visible', timeout=5000)
            page.locator(manual_selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            if not self._set_tag("preenchimento_manual.click"):
                return
            page.click(manual_selector, force=True)
            self.gui.log(f"✓ Preenchimento Manual selecionado")
        except Exception as e:
            raise Exception(f"Erro ao selecionar Preenchimento Manual: {e}")

        self.delay.custom(self.network_delay)
        self.steps.append("Selecionou Preenchimento Manual")
