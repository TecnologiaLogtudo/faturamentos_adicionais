import pandas as pd
import warnings
import os
import re
from app.utils.logger import Logger

# Ignorar avisos do openpyxl sobre estilos padrão do Excel
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# Instancia o logger no padrão do projeto
logger = Logger()

def limpar_texto(texto):
    """Limpa o texto para facilitar a comparação (minúsculas, sem espaços extras)."""
    if pd.isna(texto):
        return ""
    return str(texto).strip().lower()

def limpar_chave(valor):
    """Garante que números de transporte como 12345.0 virem '12345' para não errar o cruzamento."""
    if pd.isna(valor):
        return ""
    txt = str(valor).strip()
    if txt.endswith('.0'):
        txt = txt[:-2]
    return txt

def processar_planilha_logtudo_agrupada(caminho_arquivo_entrada, caminho_arquivo_saida=None):
    if not caminho_arquivo_entrada:
        logger.error("Nenhum arquivo de entrada fornecido. Processo cancelado.")
        return None
        
    logger.info(f"Iniciando o processamento e agrupamento do arquivo: {caminho_arquivo_entrada}")
    
    if not caminho_arquivo_saida:
        diretorio = os.path.dirname(caminho_arquivo_entrada)
        nome_arquivo = os.path.basename(caminho_arquivo_entrada)
        caminho_arquivo_saida = os.path.join(diretorio, f"Processado_Agrupado_{nome_arquivo}")

    mapa_colunas = {
        'ID': ['id', 'senha', 'senha ravex', 'id ravex'],
        'Tipo de custo': ['tipo de custo', 'tipo adc', 'tipo do custo'],
        'Nota fiscal': ['nota fiscal', 'nf'],
        'Transporte': ['transporte', 'transporte adc', 'transporte adc criado', 'transporte criado']
    }

    try:
        todas_as_abas = pd.read_excel(caminho_arquivo_entrada, sheet_name=None, header=None)
        
        # 1. Identificar a aba alvo ("Logtudo" ou "Base")
        nome_aba_base = None
        nome_aba_zle = None
        
        for nome_aba in todas_as_abas.keys():
            nome_limpo = str(nome_aba).lower()
            if 'logtudo' in nome_limpo or 'base' in nome_limpo:
                nome_aba_base = nome_aba
            elif 'zle' in nome_limpo:
                nome_aba_zle = nome_aba
                
        if not nome_aba_base:
            logger.error("Nenhuma aba contendo 'Logtudo' ou 'Base' foi encontrada.")
            return None

        logger.success(f"Aba Base identificada: '{nome_aba_base}'")
        df_bruto = todas_as_abas[nome_aba_base]

        # 2. Localizar cabeçalho da Base
        indice_cabecalho = -1
        mapeamento_indices = {'ID': -1, 'Tipo de custo': -1, 'Nota fiscal': -1, 'Transporte': -1}
        
        for i in range(min(10, len(df_bruto))):
            linha = df_bruto.iloc[i].tolist()
            matches = 0
            indices_temporarios = {'ID': -1, 'Tipo de custo': -1, 'Nota fiscal': -1, 'Transporte': -1}
            
            for col_idx, valor_celula in enumerate(linha):
                valor_limpo = limpar_texto(valor_celula)
                for chave_padrao, variacoes in mapa_colunas.items():
                    if valor_limpo in variacoes:
                        indices_temporarios[chave_padrao] = col_idx
                        matches += 1
                        break
            
            if matches >= 2:
                indice_cabecalho = i
                mapeamento_indices = indices_temporarios
                logger.success(f"Cabeçalho encontrado na linha {i + 1} do Excel.")
                break
                
        if indice_cabecalho == -1:
            logger.error("Não foi possível identificar o cabeçalho na aba Base.")
            return None

        # 3. Extrair os dados da Base
        logger.info("Extraindo dados da Base...")
        df_dados = pd.read_excel(caminho_arquivo_entrada, sheet_name=nome_aba_base, header=indice_cabecalho)
        
        colunas_para_extrair = {df_dados.columns[idx]: chave for chave, idx in mapeamento_indices.items() if idx != -1}
        df_extraido = df_dados[list(colunas_para_extrair.keys())].copy()
        df_extraido.rename(columns=colunas_para_extrair, inplace=True)
        df_extraido.dropna(how='all', inplace=True)
        
        # 4. BUSCAR VALORES DA ABA ZLE
        if nome_aba_zle and 'Transporte' in df_extraido.columns:
            logger.info(f"Cruzando dados com a aba '{nome_aba_zle}'...")
            df_zle = pd.read_excel(caminho_arquivo_entrada, sheet_name=nome_aba_zle, header=0)
            
            col_transp_zle = next((c for c in df_zle.columns if re.search(r'nº transporte', str(c), re.IGNORECASE)), None)
            col_frete = next((c for c in df_zle.columns if re.search(r'valor frete', str(c), re.IGNORECASE)), None)
            col_centro = next((c for c in df_zle.columns if str(c).lower().strip() == 'centro'), None)
            
            if col_transp_zle and col_frete and col_centro:
                df_extraido['Chave_Temp'] = df_extraido['Transporte'].apply(limpar_chave)
                df_zle['Chave_Temp'] = df_zle[col_transp_zle].apply(limpar_chave)
                df_zle_subset = df_zle[['Chave_Temp', col_frete, col_centro]].drop_duplicates(subset=['Chave_Temp'])
                
                df_extraido = pd.merge(df_extraido, df_zle_subset, on='Chave_Temp', how='left')
                df_extraido.rename(columns={col_frete: 'Valor Frete', col_centro: 'Centro'}, inplace=True)
                df_extraido.drop('Chave_Temp', axis=1, inplace=True)
                logger.success("Colunas 'Valor Frete' e 'Centro' adicionadas com sucesso.")
            else:
                logger.warning("Colunas necessárias não encontradas na ZLE.")
        
        # Garantir que as colunas existam mesmo se a ZLE falhou
        if 'Centro' not in df_extraido.columns: df_extraido['Centro'] = 'Sem Centro'
        if 'Valor Frete' not in df_extraido.columns: df_extraido['Valor Frete'] = 0

        # ---------------------------------------------------------
        # 5. NOVA FUNCIONALIDADE: TRATAMENTO E AGRUPAMENTO
        # ---------------------------------------------------------
        logger.info("Tratando nomes das colunas e agrupando tabelas...")
        
        # Renomear colunas
        df_extraido.rename(columns={
            'ID': 'Senha Ravex',
            'Transporte': 'Nº Transporte',
            'Centro': 'Tipo Cte'
        }, inplace=True)
        
        # Criar a nova coluna CTe gerado vazia
        df_extraido['CTe gerado'] = ""
        
        # Garantir que Valor Frete é numérico para conseguir somar depois
        def _limpar_valor_frete(val):
            if pd.isna(val) or str(val).strip() == "":
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).strip()
            if ',' in s and '.' in s:
                s = s.replace('.', '').replace(',', '.')
            elif ',' in s:
                s = s.replace(',', '.')
            try:
                return float(s)
            except ValueError:
                return 0.0

        df_extraido['Valor Frete'] = df_extraido['Valor Frete'].apply(_limpar_valor_frete)
        
        # Reordenar colunas para ficar visualmente bonito
        ordem_colunas = ['Senha Ravex', 'Tipo de custo', 'Nota fiscal', 'Nº Transporte', 'Valor Frete', 'Tipo Cte', 'CTe gerado']
        df_extraido = df_extraido[[c for c in ordem_colunas if c in df_extraido.columns]]

        lista_relatorio = []
        
        # Lista para armazenar os dados de cada tabela (para uso futuro)
        tabelas_data = []
        
        # Pega todos os tipos de Cte únicos (removendo vazios e normalizando)
        df_extraido['Tipo Cte'] = df_extraido['Tipo Cte'].fillna('NÃO IDENTIFICADO')
        tipos_unicos = df_extraido['Tipo Cte'].unique()

        for tipo in tipos_unicos:
            # Filtra os dados deste "Tipo Cte" específico
            df_tipo = df_extraido[df_extraido['Tipo Cte'] == tipo].copy()
            
            if df_tipo.empty:
                continue
                
            # Obter os últimos valores e a soma solicitados
            ultima_senha = df_tipo['Senha Ravex'].iloc[-1]
            ultima_nf = df_tipo['Nota fiscal'].iloc[-1]
            ultimo_transporte = df_tipo['Nº Transporte'].iloc[-1]
            ultimo_tipo_custo = df_tipo['Tipo de custo'].iloc[-1]  # Último tipo de custo
            soma_frete = df_tipo['Valor Frete'].sum()
                
            # Coletar os arrays de dados para cada tabela
            tabelas_data.append({
                'tipo_custo': ultimo_tipo_custo,  # Último tipo de custo
                'senha_ravex': df_tipo['Senha Ravex'].tolist(),
                'nota_fiscal': df_tipo['Nota fiscal'].tolist(),
                'transporte': df_tipo['Nº Transporte'].tolist(),
                'valor_cte': soma_frete  # Adicionar valor total
            })
            
            # Montar a linha de resumo (Dicionário com as colunas)
            linha_resumo = pd.DataFrame([{
                'Senha Ravex': ultima_senha,
                'Tipo de custo': 'RESUMO ->', 
                'Nota fiscal': ultima_nf,
                'Nº Transporte': ultimo_transporte,
                'Valor Frete': soma_frete,
                'Tipo Cte': '',
                'CTe gerado': ''
            }])
            
            # Linha em branco para separar as tabelas
            linha_branca = pd.DataFrame([{col: '' for col in df_extraido.columns}])
            
            # Empilhar: Tabela do tipo -> Resumo -> Linha Branca
            lista_relatorio.append(df_tipo)
            lista_relatorio.append(linha_resumo)
            lista_relatorio.append(linha_branca)

        # Junta tudo de volta em um único DataFrame formatado
        if lista_relatorio:
            df_final = pd.concat(lista_relatorio, ignore_index=True)
            logger.success("Tratamento e agrupamento concluídos.")
        else:
            logger.warning("Nenhum dado válido para agrupar.")
            df_final = df_extraido

        # ---------------------------------------------------------

        # 6. Salvar o novo arquivo Excel
        logger.info(f"Gerando arquivo final: {caminho_arquivo_saida}")
        with pd.ExcelWriter(caminho_arquivo_saida, engine='openpyxl') as writer:
            # Salva aba base cortando nome se muito grande pro Excel (máx 31 chars)
            nome_base_sheet = f"Base ({str(nome_aba_base)[:20]})"
            todas_as_abas[nome_aba_base].to_excel(writer, sheet_name=nome_base_sheet, index=False, header=False)
            
            # Salvar a nova aba tratada e agrupada
            df_final.to_excel(writer, sheet_name='Dados Extraídos', index=False)
            
            for nome_aba, df_aba in todas_as_abas.items():
                if nome_aba == nome_aba_base:
                    continue
                nome_limpo = str(nome_aba).lower()
                if 'zle' in nome_limpo or 'valores' in nome_limpo:
                    df_aba.to_excel(writer, sheet_name=str(nome_aba)[:31], index=False, header=False)

        logger.success("Processo concluído com sucesso!")
        return caminho_arquivo_saida, tabelas_data

    except Exception as e:
        logger.error(f"Ocorreu um erro durante a execução: {e}")
        return None
