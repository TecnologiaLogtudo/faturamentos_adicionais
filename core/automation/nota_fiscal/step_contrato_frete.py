# -*- coding: utf-8 -*-
"""
Etapa de contrato de frete e confirmação de popups.
"""

class NotaFiscalContratoFreteMixin:
    """Métodos do workflow para NotaFiscalContratoFreteMixin."""

    def handle_ok_popup(self, page):
        """
        Verifica se um popup com botão 'OK' aparece e o fecha.
        A verificação é feita com um timeout curto para não atrasar o fluxo.
        """
        if not self._set_tag("handle_ok_popup"):
            return
        self.gui.log("Verificando se há popups de confirmação...")
        try:
            # Seletor para o botão OK dentro do popup
            ok_button_selector = 'span.ui-button-text:has-text("OK")'

            # Aguarda o botão aparecer por um período curto
            locator = page.locator(ok_button_selector)
            locator.wait_for(state='visible', timeout=5000)  # Espera até 5 segundos

            self.gui.log("Popup de confirmação 'OK' encontrado. Clicando...")
            locator.click()
            self.gui.log("✓ Botão 'OK' do popup clicado.")
            
            # Aguarda um pouco para o popup fechar e a página estabilizar
            self.delay.network()

        except Exception:
            # Se o popup não aparecer, um timeout ocorrerá, o que é esperado.
            self.gui.log("Nenhum popup de confirmação encontrado, continuando...", level="debug")
