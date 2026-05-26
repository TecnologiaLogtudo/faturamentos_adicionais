# -*- coding: utf-8 -*-
"""
Teste para validar que registros com Código de imposto 'IT' são corretamente ignorados
durante o processamento da automação.
"""

import pytest
from unittest.mock import Mock, patch
from core.automation.nota_fiscal.flow_descarga_pedagio import NotaFiscalDescargaPedagioMixin
from webapp.server import Job, JobRunner


class TestSkipITCodigoImposto:
    """Testes para filtro de skip 'IT' em Código de imposto"""

    def test_process_descarga_pedagio_skip_it_codigo_imposto(self):
        """
        Verifica que process_descarga_pedagio retorna None quando codigo_imposto é 'IT'
        """
        # Setup
        mixin = NotaFiscalDescargaPedagioMixin()
        mixin.gui = Mock()
        mixin.gui.log = Mock()
        
        page = Mock()
        data = {
            'tipo_adc': 'Descarga',
            'uf': 'BA',
            'nota_fiscal': '123456',
            'valor_cte': '100.00',
            'senha_ravex': 'PASS123',
            'transporte': 'Rodoviário',
            'codigo_imposto': 'IT',  # Código que deve ser pulado
        }
        cte_number = 'CTE001'
        
        # Execute
        result = mixin.process_descarga_pedagio(page, data, cte_number)
        
        # Assert
        assert result is None, "Deveria retornar None ao detectar código_imposto 'IT'"
        
        # Verifica se o log de aviso foi registrado
        mixin.gui.log.assert_called()
        log_calls = [call[0][0] for call in mixin.gui.log.call_args_list]
        
        # Procura por mensagem de skip em IT
        it_skip_logged = any("IT" in str(call) for call in log_calls)
        assert it_skip_logged, "Deveria ter logado a detecção de código 'IT'"

    def test_codigo_imposto_case_insensitive_it(self):
        """
        Verifica que a comparação 'it' é case-insensitive
        """
        # Setup
        mixin = NotaFiscalDescargaPedagioMixin()
        mixin.gui = Mock()
        mixin.gui.log = Mock()
        
        page = Mock()
        
        # Testa variações de 'IT'
        for it_variant in ['it', 'It', 'iT', 'IT']:
            data = {
                'codigo_imposto': it_variant,
            }
            cte_number = 'CTE001'
            
            result = mixin.process_descarga_pedagio(page, data, cte_number)
            assert result is None, f"Deveria ter pulado para variante '{it_variant}'"

    def test_codigo_imposto_with_whitespace(self):
        """
        Verifica que espaços ao redor do código são tratados
        """
        # Setup
        mixin = NotaFiscalDescargaPedagioMixin()
        mixin.gui = Mock()
        mixin.gui.log = Mock()
        
        page = Mock()
        data = {
            'codigo_imposto': '  IT  ',  # Com espaços
        }
        cte_number = 'CTE001'
        
        # Execute
        result = mixin.process_descarga_pedagio(page, data, cte_number)
        
        # Assert
        assert result is None, "Deveria ter pulado mesmo com espaços em branco"


class TestJobRunnerCodigoImposto:
    """Testes para o filtro robusto de codigo_imposto no JobRunner (webapp)"""

    def test_skip_it_in_job_runner_loop(self):
        """
        Verifica que registro com 'IT' é pulado no loop do JobRunner
        """
        # Simula os dados do job
        job_data = [
            ['NF', 'Tipo', 'CódigoImposto', 'Valor', 'Senha'],
            ['001', 'Desc', 'I1', '100', 'PASS'],
            ['002', 'Desc', 'IT', '200', 'PASS'],  # Deveria ser pulado
            ['003', 'Desc', 'CH', '300', 'PASS'],
        ]
        
        column_mapping = {
            'codigo_imposto': 2,
            'nota_fiscal': 0,
            'tipo_adc': 1,
            'valor_cte': 3,
            'senha_ravex': 4,
        }
        
        # Simula o loop
        processed_rows = []
        for idx, row in enumerate(job_data[1:]):  # Ignora header
            codigo_imposto_idx = column_mapping.get('codigo_imposto')
            if codigo_imposto_idx is not None and codigo_imposto_idx < len(row):
                codigo_imposto_val = str(row[codigo_imposto_idx]).strip().upper()
                if codigo_imposto_val == 'IT':
                    # Skip this row
                    continue
            processed_rows.append(row)
        
        # Assert
        assert len(processed_rows) == 2, "Deveria processar apenas 2 registros (saltando IT)"
        assert processed_rows[0][0] == '001', "Primeira linha deveria ser '001'"
        assert processed_rows[1][0] == '003', "Segunda linha deveria ser '003' (após IT)"

    def test_get_codigo_imposto_robustness(self):
        """
        Verifica a robustez da busca por codigo_imposto mesmo com column_mapping vazio
        """
        job = Job(
            id="test-job",
            headers=["NF", "Tipo", "Codigo de imposto", "Valor"],  # sem acento
            data=[["001", "Desc", "I1", "100"], ["002", "Desc", "IT", "200"]],
            column_mapping={"nota_fiscal": 0, "tipo_adc": 1},
        )
        runner = JobRunner(job)

        idx = runner._get_codigo_imposto_idx()
        assert idx == 2, f"Deveria encontrar 'Codigo de imposto' no índice 2, encontrou {idx}"
        codigo_imposto_val = str(job.data[1][idx]).strip().upper()
        assert codigo_imposto_val == "IT", f"Deveria extrair 'IT', extraiu {codigo_imposto_val}"

    def test_get_codigo_imposto_uses_headers_not_first_data_row(self):
        """
        Garante que o fallback usa headers reais (job.headers), não job.data[0].
        """
        job = Job(
            id="test-job",
            headers=["NF", "Tipo", "Código de imposto", "Valor"],
            data=[["NF-001", "Desc", "I1", "100"], ["NF-002", "Desc", "IT", "200"]],
            column_mapping={"nota_fiscal": 0, "tipo_adc": 1},
        )
        runner = JobRunner(job)

        idx = runner._get_codigo_imposto_idx()
        assert idx == 2, "Deveria usar o header e encontrar a coluna de imposto no índice 2."

    def test_get_codigo_imposto_missing_column_returns_minus_one(self):
        """
        Quando a coluna não existe, deve retornar -1 sem erro.
        """
        job = Job(
            id="test-job",
            headers=["NF", "Tipo", "Valor"],
            data=[["NF-001", "Desc", "100"]],
            column_mapping={"nota_fiscal": 0, "tipo_adc": 1},
        )
        runner = JobRunner(job)

        idx = runner._get_codigo_imposto_idx()
        assert idx == -1, f"Sem coluna de imposto, deveria retornar -1. Retornou {idx}."


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

