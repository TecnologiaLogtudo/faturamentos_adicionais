# -*- coding: utf-8 -*-
"""
NotaFiscalWorkflow - Fluxo de Processamento de Notas Fiscais
Gerencia todo o processo de automação para cada nota fiscal
"""

from .commons import NotaFiscalCommonsMixin
from .step_search import NotaFiscalStepSearchMixin
from .step_selection import NotaFiscalStepSelectionMixin
from .flow_descarga_pedagio import NotaFiscalDescargaPedagioMixin
from .flow_pernoite_reentrega import NotaFiscalPernoiteReentregaMixin
from .step_envios import NotaFiscalStepEnviosMixin
from .step_contrato_frete import NotaFiscalContratoFreteMixin

class NotaFiscalWorkflow(
    NotaFiscalCommonsMixin,
    NotaFiscalStepSearchMixin,
    NotaFiscalStepSelectionMixin,
    NotaFiscalDescargaPedagioMixin,
    NotaFiscalPernoiteReentregaMixin,
    NotaFiscalStepEnviosMixin,
    NotaFiscalContratoFreteMixin,
):
    """Classe para gerenciar o fluxo de notas fiscais"""

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
        self.steps = []
        self.row_checkbox_id = None  # Guardará o ID do checkbox da linha
        self.cotacao_numero = None   # Guardará o número da cotação extraído
        self.cotacao_data = None     # Guardará a data da cotação extraída
        self.current_tag = None
        self.resume_from_tag = None
        self._resume_found = False
        self.last_cte_info = None


    def execute(self, page, data):
        """
        Executa o workflow completo para uma nota fiscal

        Args:
            page: Página do Playwright
            data: Dicionário com dados da nota fiscal

        Returns:
            Dicionário com resultado
        """
        self.steps = []
        self.resume_from_tag = data.get('start_from_tag')
        self._resume_found = False
        nota_fiscal = data.get('nota_fiscal', '')
        tipo_adc = data.get('tipo_adc', '')
        should_expand = data.get('should_expand_filter', True)
        
        self.network_delay = int(data.get('network_delay', 3000))
        self.interaction_delay = int(data.get('interaction_delay', 500))
        self.typing_delay = int(data.get('typing_delay', 75))

        self.gui.log(f"Iniciando processamento - Nota Fiscal: {nota_fiscal}, Tipo: {tipo_adc}")

        # 1. Expandir filtro e inserir nota fiscal
        self.expand_filter_and_search(page, nota_fiscal, should_expand)

        # 2. Aguardar resultados e obter CT-e
        if self._set_tag("step_wait_results"):
            cte_info = self.wait_for_results_and_get_cte(page)
            self.last_cte_info = cte_info
        else:
            cte_info = self.last_cte_info
            if not cte_info:
                raise Exception("Nao ha CT-e salvo para retomar o fluxo")
        self.gui.log(f"CT-e encontrado: {cte_info['number']}")

        # 3. Clicar em Adicionar
        self.click_adicionar(page)

        # 4. Selecionar Preenchimento Manual
        self.select_preenchimento_manual(page)

        # 5. Dependendo do tipo ADC, seguir caminho específico
        tipo_lower = tipo_adc.lower() if tipo_adc else ''
        generated_cte = None

        # Caminho 2: Pernoite, Reentrega, Diária (Com cotação, mas envios simplificados)
        if any(t in tipo_lower for t in ['pernoite', 'reentrega', 'diaria', 'diária']):
            generated_cte = self.process_pernoite_reentrega(page, data, cte_info['number'])
        else:
            # Caminho 1: Descarga, Pedágio (Padrão)
            generated_cte = self.process_descarga_pedagio(page, data, cte_info['number'])

        final_cte_number = generated_cte if generated_cte else cte_info['number']

        return {
            'success': True,
            'cte_number': final_cte_number,
            'steps': self.steps
        }
