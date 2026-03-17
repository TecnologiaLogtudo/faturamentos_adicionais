# -*- coding: utf-8 -*-
"""
ExcelReader - Módulo de Leitura de Excel
Lê arquivos Excel (xlsx, xls, csv) e extrai dados
"""

from pathlib import Path
import pandas as pd
import os


class ExcelReader:
    """Classe para leitura de arquivos Excel e CSV"""

    def __init__(self):
        """Inicializa o leitor de Excel"""
        self.headers = []
        self.data = []
        self.file_info = None

    def read(self, file_path, uf=None):
        """
        Lê arquivo de planilha

        Args:
            file_path: Caminho do arquivo
            uf: UF selecionada (opcional)

        Returns:
            Dicionário com headers, data e file_info

        Raises:
            Exception: Se houver erro ao processar o arquivo
        """
        file_path = str(file_path)
        extension = self._get_file_extension(file_path)

        # Verificar processamento específico para Bahia
        if uf and uf.strip().lower() == 'bahia':
            return self._process_bahia(file_path)

        if extension == 'csv':
            return self._read_csv(file_path)
        elif extension in ['xlsx', 'xls']:
            return self._read_excel(file_path, extension)
        else:
            raise Exception(f"Formato de arquivo não suportado: {extension}")

    def _get_file_extension(self, filename):
        """Obtém extensão do arquivo"""
        parts = filename.split('.')
        return parts[-1].lower() if parts else ''

    def _process_bahia(self, file_path):
        """
        Processa arquivo específico da Bahia usando process_BA
        Gera um arquivo tratado e o lê em seguida.
        """
        try:
            from core.services.process_BA import process_sheet
            
            # Definir caminho para arquivo tratado (ex: Arquivo_TRATADA.xlsx)
            path = Path(file_path)
            new_filename = f"{path.stem}_TRATADA.xlsx"
            new_path = path.parent / new_filename
            
            # Processar e salvar arquivo tratado
            # O script process_BA consolida as linhas e gera um novo arquivo
            process_sheet(file_path, str(new_path))
            
            # Ler o arquivo tratado como se fosse o arquivo de trabalho
            return self._read_excel(str(new_path), 'xlsx')
            
        except Exception as e:
            raise Exception(f"Erro ao processar planilha da Bahia: {str(e)}")

    def _read_excel(self, file_path, extension):
        """
        Lê arquivo Excel usando openpyxl para preservar formatação

        Args:
            file_path: Caminho do arquivo
            extension: Extensão do arquivo

        Returns:
            Dicionário com dados processados
        """
        try:
            from openpyxl import load_workbook
            
            wb = load_workbook(file_path)
            ws = wb.active
            
            # Ler headers da primeira linha
            self.headers = []
            for cell in ws[1]:
                self.headers.append(cell.value if cell.value is not None else '')
            
            # Ler dados a partir da segunda linha
            self.data = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                self.data.append(list(row))
            
            # Converter valores None para strings vazias
            self.data = [['' if v is None else v for v in row] for row in self.data]

            # Obter informações do arquivo
            file_size = os.path.getsize(file_path)

            self.file_info = {
                'name': Path(file_path).name,
                'size': file_size,
                'extension': extension,
                'rows': len(self.data),
                'columns': len(self.headers),
                'full_path': file_path
            }

            return {
                'headers': self.headers,
                'data': self.data,
                'file_info': self.file_info
            }

        except Exception as e:
            raise Exception(f"Erro ao processar Excel: {str(e)}")

    def _read_csv(self, file_path):
        """
        Lê arquivo CSV

        Args:
            file_path: Caminho do arquivo

        Returns:
            Dicionário com dados processados
        """
        try:
            # Ler arquivo CSV
            df = pd.read_csv(file_path, encoding='utf-8')

            # Pular linhas com 'Nº CTE' preenchido
            cte_col_names = ['Nº CTE', 'nº cte', 'numero cte', 'número cte', 'cte', 'n_cte', 'nºcte']
            cte_column = None
            for col_name in df.columns:
                if col_name.strip().lower() in [c.lower() for c in cte_col_names]:
                    cte_column = col_name
                    break
            
            if cte_column:
                df = df[pd.isna(df[cte_column]) | (df[cte_column] == '')]

            # Converter para listas
            self.headers = df.columns.tolist()
            self.data = df.values.tolist()

            # Converter valores None para strings vazias
            self.data = [['' if v is None else v for v in row] for row in self.data]

            # Obter informações do arquivo
            file_size = os.path.getsize(file_path)

            self.file_info = {
                'name': Path(file_path).name,
                'size': file_size,
                'extension': 'csv',
                'rows': len(self.data),
                'columns': len(self.headers)
            }

            return {
                'headers': self.headers,
                'data': self.data,
                'file_info': self.file_info
            }

        except Exception as e:
            raise Exception(f"Erro ao processar CSV: {str(e)}")

    def find_column_by_name(self, column_names):
        """
        Encontra coluna pelo nome

        Args:
            column_names: Lista de nomes possíveis para a coluna

        Returns:
            Índice da coluna ou -1 se não encontrada
        """
        for name in column_names:
            normalized_name = name.lower().strip()
            for i, header in enumerate(self.headers):
                if header.lower().strip() == normalized_name:
                    return i
        return -1

    def auto_map_columns(self):
        """
        Mapeia colunas automaticamente

        Returns:
            Dicionário com mapeamento encontrado
        """
        mappings = {
            'nota_fiscal': ['NOTA FISCAL', 'nota fiscal', 'nf', 'nº nf'],
            'tipo_adc': ['TIPO ADC', 'tipo adc', 'tipoadc', 'adc', 'tipo adicional', 'tipo'],
            'valor_cte': ['VALOR TT CTE', 'valor tt cte', 'valor_tt_cte', 'valor cte', 'valor_cte', 'valor', 'frete'],
            'senha_ravex': ['SENHA RAVEX', 'senha ravex', 'senha_ravex', 'ravex', 'senha'],
            'transporte': ['Transporte adicional', 'TRANSPORTE ORIGEM', 'transporte origem', 'transporte', 'transporte_de_origem', 'origem'],
            'cte_output': ['Nº CTE', 'nº cte', 'numero cte', 'número cte', 'cte', 'n_cte', 'nºcte']
        }

        result = {}

        for key, names in mappings.items():
            index = self.find_column_by_name(names)
            if index != -1:
                result[key] = index

        return result
    
    def find_closest_column(self, search_term):
        """
        Encontra a coluna mais próxima usando similaridade de strings
        
        Args:
            search_term: Termo de busca
            
        Returns:
            Índice da coluna ou -1 se não encontrada
        """
        from difflib import SequenceMatcher
        
        search_normalized = search_term.lower().strip()
        best_match_idx = -1
        best_match_ratio = 0.5  # Mínimo 50% de similaridade
        
        for i, header in enumerate(self.headers):
            header_normalized = header.lower().strip()
            ratio = SequenceMatcher(None, search_normalized, header_normalized).ratio()
            
            if ratio > best_match_ratio:
                best_match_ratio = ratio
                best_match_idx = i
        
        return best_match_idx

    def get_preview_data(self, max_rows=10):
        """
        Obtém visualização formatada dos dados

        Args:
            max_rows: Número máximo de linhas

        Returns:
            Dicionário com dados de preview
        """
        return {
            'headers': self.headers,
            'rows': self.data[:max_rows],
            'total_rows': len(self.data),
            'total_columns': len(self.headers)
        }

    def get_cell_value(self, row_index, col_index):
        """
        Obtém valor de célula

        Args:
            row_index: Índice da linha
            col_index: Índice da coluna

        Returns:
            Valor da célula ou None
        """
        if 0 <= row_index < len(self.data):
            if 0 <= col_index < len(self.data[row_index]):
                return self.data[row_index][col_index]
        return None

    def set_cell_value(self, row_index, col_index, value):
        """
        Define valor de célula

        Args:
            row_index: Índice da linha
            col_index: Índice da coluna
            value: Novo valor
        """
        if row_index < 0:
            return

        # Garantir que a linha existe
        while len(self.data) <= row_index:
            self.data.append([])

        # Garantir que a coluna existe
        while len(self.data[row_index]) <= col_index:
            self.data[row_index].append('')

        self.data[row_index][col_index] = value
