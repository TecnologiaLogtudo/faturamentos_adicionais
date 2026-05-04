import pandas as pd
import re
import warnings
import os

from core.utils.logger import Logger

# Ignorar avisos chatos do openpyxl sobre estilos padrão do Excel
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# Instancia o logger
logger = Logger()

def limpar_chave(valor):
    """Garante que números de transporte como 12345.0 virem '12345' para não errar o cruzamento."""
    if pd.isna(valor):
        return ""
    txt = str(valor).strip()
    if txt.endswith('.0'):
        txt = txt[:-2]
    return txt

def processar_planilha_logtudo(caminho_arquivo_entrada):
    if not caminho_arquivo_entrada:
        logger.error("Nenhum arquivo de entrada fornecido. Processo cancelado.")
        return None
        
    logger.info(f"Iniciando o processamento do arquivo: {caminho_arquivo_entrada}")
    
    # Gerar nome do arquivo de saída baseado no de entrada
    diretorio = os.path.dirname(caminho_arquivo_entrada)
    nome_arquivo = os.path.basename(caminho_arquivo_entrada)
    caminho_arquivo_saida = os.path.join(diretorio, f"Processado_{nome_arquivo}")

    # Mapa de variações de nomes de colunas usando Regex
    mapa_colunas = {
        'ID': [r'\bid\b', r'\bsenha\b', r'.*id\s*ravex.*', r'.*senha\s*ravex.*'],
        'Tipo de custo': [r'.*tipo.*custo.*', r'.*tipo.*adc.*'],
        'Nota fiscal': [r'.*nota\s*fiscal.*', r'\bnf\b', r'.*n\.?f\.?.*'],
        'Transporte': [r'.*transporte.*']
    }

    try:
        # Carregar todas as abas do arquivo Excel
        todas_as_abas = pd.read_excel(caminho_arquivo_entrada, sheet_name=None, header=None)
        
        # 1. Identificar a aba alvo ("Logtudo" ou "Base") e a aba ZLE ignorando case
        nome_aba_alvo = None
        nome_aba_zle = None
        for nome_aba in todas_as_abas.keys():
            if re.search(r'logtudo|base', str(nome_aba), re.IGNORECASE):
                nome_aba_alvo = nome_aba
            elif re.search(r'zle', str(nome_aba), re.IGNORECASE):
                nome_aba_zle = nome_aba
                
        if not nome_aba_alvo:
            logger.error("Nenhuma aba contendo 'Logtudo' ou 'Base' foi encontrada.")
            return None

        logger.success(f"Aba alvo encontrada: '{nome_aba_alvo}'")
        if nome_aba_zle:
            logger.success(f"Aba ZLE encontrada: '{nome_aba_zle}'")
            
        df_bruto = todas_as_abas[nome_aba_alvo]

        # 2. Localizar a linha de cabeçalho nas primeiras 10 linhas
        indice_cabecalho = -1
        mapeamento_indices = {'ID': -1, 'Tipo de custo': -1, 'Nota fiscal': -1, 'Transporte': -1}
        
        max_linhas_busca = min(10, len(df_bruto))
        
        for i in range(max_linhas_busca):
            linha = df_bruto.iloc[i].tolist()
            matches = 0
            indices_temporarios = {'ID': -1, 'Tipo de custo': -1, 'Nota fiscal': -1, 'Transporte': -1}
            
            for col_idx, valor_celula in enumerate(linha):
                if pd.isna(valor_celula):
                    continue
                
                valor_str = str(valor_celula).strip()
                
                # Verifica a qual chave do nosso mapa este valor pertence usando regex ignorando case
                encontrou = False
                for chave_padrao, padroes_regex in mapa_colunas.items():
                    for padrao in padroes_regex:
                        if re.search(padrao, valor_str, re.IGNORECASE):
                            indices_temporarios[chave_padrao] = col_idx
                            matches += 1
                            encontrou = True
                            break # Achou uma regex que bate, para de testar outras regex para esta coluna
                    if encontrou:
                        break # Achou a chave padrão, passa para a próxima célula
            
            # Se encontrou pelo menos 2 colunas mapeadas, consideramos que é o cabeçalho
            if matches >= 2:
                indice_cabecalho = i
                mapeamento_indices = indices_temporarios
                logger.success(f"Cabeçalho encontrado na linha {i + 1} do Excel (Índice {i}).")
                break
                
        if indice_cabecalho == -1:
            logger.error("Não foi possível identificar o cabeçalho nas primeiras linhas.")
            return None

        # 3. Extrair os dados usando os índices encontrados
        logger.info("Extraindo dados das colunas mapeadas...")
        
        # Recarregar o DataFrame da aba alvo usando a linha correta como cabeçalho
        df_dados = pd.read_excel(caminho_arquivo_entrada, sheet_name=nome_aba_alvo, header=indice_cabecalho)
        
        # Criar um novo DataFrame apenas com as colunas que conseguimos mapear
        colunas_para_extrair = {}
        for chave_padrao, indice_coluna in mapeamento_indices.items():
            if indice_coluna != -1:
                nome_coluna_no_df = df_dados.columns[indice_coluna]
                colunas_para_extrair[nome_coluna_no_df] = chave_padrao
        
        df_extraido = df_dados[list(colunas_para_extrair.keys())].copy()
        df_extraido.rename(columns=colunas_para_extrair, inplace=True)
        df_extraido.dropna(how='all', inplace=True)
        
        logger.success(f"{len(df_extraido)} linhas de dados extraídas.")

        # 3.5. Cruzar dados com a aba ZLE
        if nome_aba_zle and 'Transporte' in df_extraido.columns:
            logger.info(f"Cruzando dados com a aba '{nome_aba_zle}'...")
            
            # Lê a aba ZLE (assumindo cabeçalho na linha 0)
            df_zle = pd.read_excel(caminho_arquivo_entrada, sheet_name=nome_aba_zle, header=0)
            
            # Encontrar as colunas exatas ignorando maiúsculas/minúsculas usando regex
            col_transp_zle = next((c for c in df_zle.columns if re.search(r'nº transporte', str(c), re.IGNORECASE)), None)
            col_frete = next((c for c in df_zle.columns if re.search(r'valor frete', str(c), re.IGNORECASE)), None)
            col_centro = next((c for c in df_zle.columns if str(c).strip().lower() == 'centro'), None)
            col_codigo_imposto = next((c for c in df_zle.columns if re.search(r'código.*imposto', str(c), re.IGNORECASE)), None)
            
            if col_transp_zle and col_frete and col_centro:
                df_extraido['Chave_Temp'] = df_extraido['Transporte'].apply(limpar_chave)
                df_zle['Chave_Temp'] = df_zle[col_transp_zle].apply(limpar_chave)
                
                colunas_para_merge = ['Chave_Temp', col_frete, col_centro]
                if col_codigo_imposto:
                    colunas_para_merge.append(col_codigo_imposto)
                
                df_zle_subset = df_zle[colunas_para_merge].drop_duplicates(subset=['Chave_Temp'])
                
                df_extraido = pd.merge(df_extraido, df_zle_subset, on='Chave_Temp', how='left')
                
                df_extraido.rename(columns={col_frete: 'Valor Frete', col_centro: 'Centro'}, inplace=True)
                if col_codigo_imposto:
                    df_extraido.rename(columns={col_codigo_imposto: 'Código de imposto'}, inplace=True)
                df_extraido.drop('Chave_Temp', axis=1, inplace=True)
                colunas_adicionadas = ['Valor Frete', 'Centro']
                if col_codigo_imposto:
                    colunas_adicionadas.append('Código de imposto')
                logger.success(f"Colunas {', '.join(colunas_adicionadas)} adicionadas com sucesso.")
            else:
                logger.error("Colunas 'Nº transporte', 'Valor Frete' ou 'Centro' não encontradas na ZLE.")
        else:
            logger.info("Aba ZLE ou coluna 'Transporte' ausente. Pulando cruzamento.")

        # 4. Salvar o novo arquivo Excel
        logger.info(f"Gerando arquivo final: {caminho_arquivo_saida}")
        with pd.ExcelWriter(caminho_arquivo_saida, engine='openpyxl') as writer:
            # Salva aba base cortando nome se muito grande pro Excel (máx 31 chars)
            nome_base_sheet = f"Base ({nome_aba_alvo[:20]})"
            todas_as_abas[nome_aba_alvo].to_excel(writer, sheet_name=nome_base_sheet, index=False, header=False)
            logger.info(f"Aba original '{nome_aba_alvo}' salva como '{nome_base_sheet}'.")
            
            # Salvar a nova aba com os dados extraídos
            df_extraido.to_excel(writer, sheet_name='Dados Extraídos', index=False)
            logger.info("Aba 'Dados Extraídos' gerada.")
            
            # Preservar as outras abas (ZLE e Valores) se existirem
            for nome_aba, df_aba in todas_as_abas.items():
                if nome_aba == nome_aba_alvo:
                    continue
                    
                if re.search(r'zle|valores', str(nome_aba), re.IGNORECASE):
                    df_aba.to_excel(writer, sheet_name=nome_aba[:31], index=False, header=False)
                    logger.info(f"Aba preservada: '{nome_aba}'.")

        logger.success("Processo concluído com sucesso!")
        return caminho_arquivo_saida

    except Exception as e:
        logger.error(f"Ocorreu um erro durante a execução: {e}")
        return None
