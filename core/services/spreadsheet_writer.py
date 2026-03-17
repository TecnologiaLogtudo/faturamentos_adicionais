# -*- coding: utf-8 -*-
"""
SpreadsheetWriter - Módulo de Escrita de Planilha
Salva dados de volta em arquivos Excel e CSV
"""

from pathlib import Path
import pandas as pd
from datetime import datetime
import os


class SpreadsheetWriter:
    """Classe para escrita de arquivos Excel e CSV"""

    def __init__(self):
        """Inicializa o escritor de planilhas"""
        self.modified_data = None

    def update_cell(self, data, row_index, col_index, value):
        """
        Atualiza célula na planilha

        Args:
            data: Lista de dados
            row_index: Índice da linha
            col_index: Índice da coluna
            value: Novo valor

        Returns:
            True se bem-sucedido, False caso contrário
        """
        if not data or row_index < 0:
            return False

        # Garantir que a linha existe
        while len(data) <= row_index:
            data.append([])

        # Garantir que a coluna existe
        while len(data[row_index]) <= col_index:
            data[row_index].append('')

        data[row_index][col_index] = value
        self.modified_data = data

        return True

    def update_cells(self, data, updates):
        """
        Atualiza múltiplas células

        Args:
            data: Lista de dados
            updates: Lista de atualizações [{'row': idx, 'col': idx, 'value': val}, ...]
        """
        for update in updates:
            self.update_cell(data, update['row'], update['col'], update['value'])
        self.modified_data = data

    def export_to_excel(self, headers, data, filename=None):
        """
        Exporta dados para Excel

        Args:
            headers: Lista de cabeçalhos
            data: Lista de linhas de dados
            filename: Nome do arquivo (opcional)

        Returns:
            Nome do arquivo exportado
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y-%m-%d')
            filename = f"resultados_{timestamp}.xlsx"

        # Criar DataFrame
        df = pd.DataFrame(data, columns=headers)

        # Exportar para Excel
        df.to_excel(filename, index=False, engine='openpyxl')

        return filename

    def export_to_csv(self, headers, data, filename=None):
        """
        Exporta dados para CSV

        Args:
            headers: Lista de cabeçalhos
            data: Lista de linhas de dados
            filename: Nome do arquivo (opcional)

        Returns:
            Nome do arquivo exportado
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y-%m-%d')
            filename = f"resultados_{timestamp}.csv"

        # Criar DataFrame
        df = pd.DataFrame(data, columns=headers)

        # Exportar para CSV
        df.to_csv(filename, index=False, encoding='utf-8')

        return filename

    def export_results(self, results, filename):
        """
        Exporta resultados para Excel

        Args:
            results: Lista de resultados
            filename: Nome do arquivo

        Returns:
            Nome do arquivo exportado
        """
        # Preparar dados
        headers = ['Status', 'Nota Fiscal', 'Tipo ADC', 'Nº CTE', 'Mensagem', 'Data/Hora']
        data = [
            [
                r.get('status', '-').upper(),
                r.get('nota_fiscal', '-'),
                r.get('tipo_adc', '-'),
                r.get('cte_number', '-'),
                r.get('message', '-'),
                r.get('timestamp', '-')
            ]
            for r in results
        ]

        return self.export_to_excel(headers, data, filename)

    def export_results_csv(self, results, filename):
        """
        Exporta resultados para CSV

        Args:
            results: Lista de resultados
            filename: Nome do arquivo

        Returns:
            Nome do arquivo exportado
        """
        # Preparar dados
        headers = ['Status', 'Nota Fiscal', 'Tipo ADC', 'Nº CTE', 'Mensagem', 'Data/Hora']
        data = [
            [
                r.get('status', '-').upper(),
                r.get('nota_fiscal', '-'),
                r.get('tipo_adc', '-'),
                r.get('cte_number', '-'),
                r.get('message', '-'),
                r.get('timestamp', '-')
            ]
            for r in results
        ]

        return self.export_to_csv(headers, data, filename)

    def create_results_report(self, results):
        """
        Cria relatório de resultados

        Args:
            results: Lista de resultados

        Returns:
            Dicionário com relatório
        """
        report = {
            'generated_at': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'summary': {
                'total': len(results),
                'success': sum(1 for r in results if r.get('status') == 'success'),
                'error': sum(1 for r in results if r.get('status') == 'error'),
                'pending': sum(1 for r in results if r.get('status') == 'pending')
            },
            'results': results
        }

        if report['summary']['total'] > 0:
            report['summary']['success_rate'] = round(
                report['summary']['success'] / report['summary']['total'] * 100, 2
            )
        else:
            report['summary']['success_rate'] = 0

        return report

    def export_detailed_report(self, results, original_headers, original_data, filename=None):
        """
        Exporta relatório detalhado com múltiplas sheets

        Args:
            results: Lista de resultados
            original_headers: Cabeçalhos originais da planilha
            original_data: Dados originais da planilha
            filename: Nome do arquivo (opcional)

        Returns:
            Nome do arquivo exportado
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y-%m-%d')
            filename = f"relatorio_detalhado_{timestamp}.xlsx"

        report = self.create_results_report(results)

        # Criar Excel writer
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Sheet de relatório
            report_headers = ['Status', 'Nota Fiscal', 'Tipo ADC', 'Nº CTE', 'Mensagem', 'Data/Hora']
            report_data = [
                [
                    r.get('status', '-').upper(),
                    r.get('nota_fiscal', '-'),
                    r.get('tipo_adc', '-'),
                    r.get('cte_number', '-'),
                    r.get('message', '-'),
                    r.get('timestamp', '-')
                ]
                for r in results
            ]
            report_df = pd.DataFrame(report_data, columns=report_headers)
            report_df.to_excel(writer, sheet_name='Relatório', index=False)

            # Sheet de dados originais
            original_df = pd.DataFrame(original_data, columns=original_headers)
            original_df.to_excel(writer, sheet_name='Dados Originais', index=False)

            # Sheet de resumo
            summary_headers = ['Métrica', 'Valor']
            summary_data = [
                ['Total de Registros', report['summary']['total']],
                ['Sucessos', report['summary']['success']],
                ['Erros', report['summary']['error']],
                ['Pendentes', report['summary']['pending']],
                ['Taxa de Sucesso', f"{report['summary']['success_rate']}%"],
                ['Gerado em', report['generated_at']]
            ]
            summary_df = pd.DataFrame(summary_data, columns=summary_headers)
            summary_df.to_excel(writer, sheet_name='Resumo', index=False)

        return filename

    def get_modified_data(self):
        """Obtém dados modificados"""
        return self.modified_data

    def clear_modified_data(self):
        """Limpa dados modificados"""
        self.modified_data = None

    def save_dataframe(self, df, filename):
        """
        Salva DataFrame diretamente

        Args:
            df: DataFrame do pandas
            filename: Nome do arquivo

        Returns:
            Nome do arquivo salvo
        """
        ext = Path(filename).suffix.lower()

        if ext == '.xlsx':
            df.to_excel(filename, index=False, engine='openpyxl')
        elif ext == '.csv':
            df.to_csv(filename, index=False, encoding='utf-8')
        else:
            raise ValueError(f"Formato não suportado: {ext}")

        return filename
