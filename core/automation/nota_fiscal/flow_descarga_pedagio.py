# -*- coding: utf-8 -*-
"""
Fluxo principal para Descarga/Pedágio (Caminho 1).
"""

class NotaFiscalDescargaPedagioMixin:
    """Métodos do workflow para NotaFiscalDescargaPedagioMixin."""

    def process_descarga_pedagio(self, page, data, cte_number):
        """
        Processa caminho Descarga/Pedagio - Caminho 1
        
        Etapas:
        1. Selecionar Agência pela UF
        2. Selecionar Talão (CT-e)
        3. Preencher Identificação do Pedido (Descarga ou Pedagio)
        4. Selecionar Tipo de CT-e (Complemento de valores)
        5. Preencher e pesquisar CT-e complementar
        6. Clicar Avançar e aguardar próxima página
        7. Clicar Pesquisar em Natureza da Operação
        8. Preencher Frete Valor
        9. Preencher Senha Ravex
        10. Preencher Observação Conhecimento
        11. Salvar e aguardar mudança de URL
        12-15. Executar Envios (marcar checkbox, clicar CT-e, clicar Executar, extrair número)
        """
        tipo_adc = data.get('tipo_adc', '')
        uf = data.get('uf', '')
        nota_fiscal = data.get('nota_fiscal', '')
        valor_cte = data.get('valor_cte', '')
        senha_ravex = data.get('senha_ravex', '')
        transporte = data.get('transporte', '')

        self.gui.log(f"Processando Caminho 1 - {tipo_adc}...")

        try:
            # PRIMEIRA PÁGINA
            # Etapa 1: Selecionar agência pela UF
            self.select_agencia(page, uf)

            # Etapa 2: Selecionar Talão CT-e
            self.select_talao(page)

            # Etapa 3: Preencher Identificação do Pedido (Descarga ou Pedagio)
            self.fill_identificacao_pedido(page, tipo_adc, uf)

            # Etapa 4: Selecionar Tipo de CT-e (Complemento de valores)
            self.select_tipo_cte_complemento(page)

            # Etapa 5: Preencher e pesquisar CT-e complementar
            self.pesquisar_cte_complementar(page, cte_number)

            # Etapa 6: Clicar Avançar
            self.avancar_pagina(page)

            # SEGUNDA PÁGINA
            # Etapa 7: Clicar Pesquisar em Natureza da Operação
            self.click_pesquisar_natureza(page)

            # Etapa 8: Preencher Frete Valor
            self.preencher_frete_valor(page, valor_cte)

            # Etapa 9: Preencher Senha Ravex
            self.preencher_senha_ravex(page, senha_ravex)

            # Etapa 10: Preencher Observação Conhecimento
            self.preencher_observacao_conhecimento(page, tipo_adc, nota_fiscal, senha_ravex, transporte)

            # Etapa 11: Salvar
            self.salvar_formulario(page)

            # ETAPA DE ENVIOS (Simplificada para Caminho 1)
            if data.get('execute_envios', True):
                generated_cte = self.process_envios_caminho_1(page)
            else:
                self.gui.log("Etapa de Envios pulada (opção desmarcada).")
                generated_cte = self.extrair_cte_da_tabela(page)

            final_cte = generated_cte or cte_number
            self.gui.log(
                f"✓ Caminho 1 ({tipo_adc}) completado com sucesso - CT-e: {final_cte}",
                level="success",
            )
            self.steps.append(f"Processou {tipo_adc} completado - CT-e: {final_cte}")
            
            return final_cte

        except Exception as e:
            raise Exception(f"Erro ao processar {tipo_adc}: {str(e)}")


    def fill_identificacao_pedido(self, page, tipo_adc, uf):
        """
        Etapa 3: Preenche Identificação do Pedido
        Elemento: <input name="dados_complementoPedido">
        """
        if not self._set_tag("fill_identificacao_pedido"):
            return
        self.gui.log("Etapa 3: Preenchendo Identificação do Pedido...")

        # Determinar valor usando a regra de negócios centralizada
        valor = self.determinar_identificacao_pedido(tipo_adc, uf)

        try:
            selector = 'input[name="dados_complementoPedido"]'
            page.wait_for_selector(selector, state='visible', timeout=5000)
            page.locator(selector).scroll_into_view_if_needed()
            self.delay.custom(self.interaction_delay)
            
            # Limpar e preencher
            page.fill(selector, '')
            self.delay.custom(self.interaction_delay // 2)
            page.locator(selector).type(valor, delay=self.typing_delay)
            
            self.gui.log(f"✓ Identificação do Pedido preenchida: {valor}")
            self.delay.custom(self.interaction_delay * 1.5)
            self.steps.append(f"Identificação do Pedido: {valor}")
            
        except Exception as e:
            raise Exception(f"Erro ao preencher Identificação do Pedido (Etapa 3): {str(e)}")


    def preencher_observacao(self, page, data, identificacao):
        """Preenche observação"""
        self.gui.log("Preenchendo observação...")

        try:
            observacao_input = page.wait_for_selector(
                'textarea[name="dados_observacaoConhecimento"]', state='visible', timeout=5000
            )

            if observacao_input:
                observacao = (f"Referente {identificacao} NF {data.get('nota_fiscal', '')} "
                            f"Senha {data.get('senha_ravex', '')} "
                            f"Transporte {data.get('transporte', '')}")

                observacao_input.click(click_count=3)
                observacao_input.fill(observacao)
        except Exception as e:
            self.gui.log(f"Erro ao preencher observação: {e}", level="warning")

        self.delay.standard()
