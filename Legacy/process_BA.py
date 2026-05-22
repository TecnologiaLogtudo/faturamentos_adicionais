import pandas as pd
import numpy as np
import os
from openpyxl import load_workbook

def get_visible_sheets(file_path):
    """Retorna uma lista de nomes de abas que não estão ocultas."""
    wb = load_workbook(file_path, read_only=True)
    visible_sheets = [sheet.title for sheet in wb.worksheets if sheet.sheet_state == 'visible']
    wb.close()
    return visible_sheets

def clean_numeric(val):
    """Limpa e converte valores para float, tratando vírgula como decimal."""
    if pd.isna(val) or str(val).strip() == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = str(val).strip()
        # Se houver vírgula e ponto, o ponto é milhar e a vírgula é decimal
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        # Se houver apenas vírgula, é decimal
        elif ',' in s:
            s = s.replace(',', '.')
        # Se houver apenas ponto, precisamos decidir se é milhar ou decimal. 
        # Geralmente em Excel brasileiro, ponto sozinho em string de valor é decimal se for algo como "10.50"
        # Mas se for "1.000", é milhar. Vamos assumir padrão brasileiro de exportação:
        # Se houver 3 dígitos após o ponto, pode ser milhar.
        return float(s)
    except:
        return 0.0

def is_sum_row(header_row, data_rows, potential_sum_row):
    """Verifica se a linha atual contém a soma dos valores das linhas de dados."""
    if not data_rows: return False
    
    temp_df = pd.DataFrame([header_row] + data_rows)
    temp_df.columns = [str(c).strip() for c in temp_df.iloc[0]]
    
    col_v_sem = next((c for c in temp_df.columns if "valor" in c.lower() and "sem" in c.lower() and "imposto" in c.lower()), None)
    col_v_com = next((c for c in temp_df.columns if "valor" in c.lower() and ("c/" in c.lower() or "com" in c.lower()) and "imposto" in c.lower()), None)
    
    if not col_v_sem and not col_v_com: return False
    
    actual_data = temp_df.iloc[1:].copy()
    
    for col in [col_v_sem, col_v_com]:
        if col:
            sum_val = actual_data[col].apply(clean_numeric).sum()
            try:
                col_idx = list(temp_df.columns).index(col)
                row_val = clean_numeric(potential_sum_row.iloc[col_idx])
                if abs(sum_val - row_val) < 0.1 and sum_val > 0:
                    return True
            except: continue
    return False

def process_accumulated(header_row, data_rows, sum_row, all_data, sheet_name="?", block_idx=0):
    """Consolida os dados de um bloco em uma única linha de saída."""
    temp_df = pd.DataFrame([header_row] + data_rows)
    temp_df.columns = [str(c).strip() for c in temp_df.iloc[0]]
    
    col_id = next((c for c in temp_df.columns if "id" in c.lower() or "código" in c.lower() or "codigo" in c.lower()), None)
    col_nf = next((c for c in temp_df.columns if "nota fiscal" in c.lower() or "nf" == c.lower().strip()), None)
    col_v_sem = next((c for c in temp_df.columns if "valor" in c.lower() and "sem" in c.lower() and "imposto" in c.lower()), None)
    col_v_com = next((c for c in temp_df.columns if "valor" in c.lower() and ("c/" in c.lower() or "com" in c.lower()) and "imposto" in c.lower()), None)
    col_transp = next(
        (c for c in temp_df.columns if "transporte" in c.lower() and "transportadora" not in c.lower() and "unidade" not in c.lower()),
        None,
    )
    if not col_transp:
        col_transp = next(
            (c for c in temp_df.columns if "transportadora" in c.lower() and "unidade" not in c.lower()),
            None,
        )
    col_tipo_custo = next((c for c in temp_df.columns if "tipo" in c.lower() and "custo" in c.lower()), None)

    if not col_id: return

    actual_data = temp_df.iloc[1:].copy()
    has_isento = False
    if col_v_com:
        try:
            has_isento = any(actual_data[col_v_com].astype(str).str.strip().str.lower() == "isento")
        except Exception:
            has_isento = False
    
    codigo_imposto = "I1"
    if has_isento:
        codigo_imposto = "CH"
        col_tipo_doc = next((c for c in temp_df.columns if "tipo de documento" in c.lower() or "tipo documento" in c.lower()), None)
        
        doc_values = []
        if col_tipo_doc:
            doc_values = actual_data[col_tipo_doc].astype(str).str.strip().str.upper()
        elif len(actual_data.columns) > 9:
            doc_values = actual_data.iloc[:, 9].astype(str).str.strip().str.upper()
            
        if any(v == "CTE" for v in doc_values):
            codigo_imposto = "I1"
        elif any(v == "NF" for v in doc_values):
            codigo_imposto = "IT"
            
    # Sempre prioriza a coluna "Valor sem imposto" (com fallback de segurança)
    valor_col = col_v_sem if col_v_sem else col_v_com

    # Regras de prioridade para Valor TT CTe:
    # 1) Se houver linha de somatório/total, usa o valor dessa linha.
    #    - Pode vir via sum_row detectada no parser
    #    - Ou via linha com ID vazio e valor numérico na coluna de valor
    # 2) Sem total: se houver mais de uma linha de detalhe, soma os valores
    # 3) Sem total e com apenas uma linha de detalhe: usa o último valor válido
    val_tt = 0.0
    if valor_col:
        try:
            detail_values = []
            total_values = []

            id_series = actual_data[col_id]
            value_series = actual_data[valor_col]

            for id_val, raw_val in zip(id_series.values, value_series.values):
                num_val = clean_numeric(raw_val)
                if num_val == 0:
                    continue

                id_str = "" if pd.isna(id_val) else str(id_val).strip().lower()
                id_vazio = id_str in ["", "nan", "none"]

                if id_vazio:
                    total_values.append(num_val)
                else:
                    detail_values.append(num_val)

            # Regra 1.a: total detectado fora do bloco de dados (sum_row)
            if sum_row is not None:
                try:
                    col_idx = list(temp_df.columns).index(valor_col)
                    sum_row_val = clean_numeric(sum_row.iloc[col_idx])
                    if sum_row_val != 0:
                        val_tt = sum_row_val
                except Exception:
                    pass

            # Regra 1.b: total detectado dentro do bloco (ID vazio)
            if val_tt == 0 and total_values:
                val_tt = total_values[-1]

            # Regra 2: somar detalhes se houver mais de um
            if val_tt == 0 and len(detail_values) > 1:
                val_tt = sum(detail_values)

            # Regra 3: último valor válido de detalhe
            if val_tt == 0 and len(detail_values) == 1:
                val_tt = detail_values[-1]
        except Exception:
            val_tt = 0.0

    # Garantir 2 casas decimais no Valor TT CTe
    try:
        val_tt = round(float(val_tt), 2)
    except Exception:
        val_tt = 0.0

    last_row = actual_data.iloc[-1]

    def _last_non_empty(series):
        """Retorna o último valor não vazio/NaN de uma coluna."""
        if series is None:
            return ""
        try:
            values = list(series.values)
        except Exception:
            values = list(series)
        for v in reversed(values):
            if pd.isna(v):
                continue
            s = str(v).strip()
            if not s or s.lower() in ["nan", "none"]:
                continue
            if s.endswith(".0"):
                s = s[:-2]
            return s
        return ""

    def _all_non_empty(series):
        """Retorna todos os valores não vazios/NaN unidos por vírgula (mantém bloco inteiro)."""
        if series is None:
            return ""
        try:
            values = list(series.values)
        except Exception:
            values = list(series)
        valid_vals = []
        for v in values:
            if pd.isna(v): continue
            s = str(v).strip()
            if not s or s.lower() in ["nan", "none"]: continue
            if s.endswith(".0"): s = s[:-2]
            if s not in valid_vals:
                valid_vals.append(s)
        return ", ".join(valid_vals)

    nf_val = _all_non_empty(actual_data[col_nf]) if col_nf else ""
    ravex_val = _all_non_empty(actual_data[col_id]) if col_id else ""
    transp_val = _all_non_empty(actual_data[col_transp]) if col_transp else ""
    tipo_val = _last_non_empty(actual_data[col_tipo_custo]) if col_tipo_custo else ""

    all_data.append({
        "Nota Fiscal": nf_val,
        "Valor TT CTe": val_tt,
        "Senha Ravex": ravex_val,
        "Nº CTE": "",
        "Transporte adicional": transp_val,
        "Tipo ADC": tipo_val,
        "código de imposto": codigo_imposto
    })

def process_sheet(file_path, output_path=None):
    visible_sheets = get_visible_sheets(file_path)
    xl = pd.ExcelFile(file_path)
    all_data = []
    block_idx = 0

    for sheet_name in visible_sheets:
        df = xl.parse(sheet_name, header=None)
        current_header = None
        current_data_rows = []
        
        for idx, row in df.iterrows():
            row_vals_str = [str(v).strip() for v in row.values]
            row_vals_lower = [s.lower() for s in row_vals_str]
            
            # Detecção de cabeçalho mais flexível (aceita variações como "NF", "Transporte", "Código")
            has_nf = any("nota fiscal" in v or "nf" == v for v in row_vals_lower)
            has_transp = any("transportadora" in v or "transporte" in v for v in row_vals_lower)
            has_id = any("id" == v or "código" in v or "codigo" in v for v in row_vals_lower)
            
            is_header = (has_nf and (has_transp or has_id)) or ("id" in row_vals_lower and "transportadora" in row_vals_lower and "nota fiscal" in row_vals_lower)
            
            # Detecção de dados mais robusta
            is_total = any("total" in v or "soma" in v for v in row_vals_lower)
            has_content = any(len(v) > 0 and v.lower() not in ['nan', 'none'] for v in row_vals_str)
            
            # Se já temos um cabeçalho, qualquer linha com conteúdo (e sem "Total") é dado
            if current_header is not None:
                is_data = has_content and not is_header and not is_total
            else:
                # Se ainda não achamos o cabeçalho, mantemos rigor para evitar lixo inicial
                is_data = any(val.isdigit() and len(val) > 2 for val in row_vals_str) and not is_header
            
            if is_header:
                if current_header is not None and current_data_rows:
                    process_accumulated(current_header, current_data_rows, None, all_data, sheet_name, block_idx)
                block_idx += 1
                current_header = row
                current_data_rows = []
            elif is_data:
                if current_header is not None:
                    current_data_rows.append(row)
            else:
                if current_header is not None and current_data_rows:
                    if is_sum_row(current_header, current_data_rows, row):
                        process_accumulated(current_header, current_data_rows, row, all_data, sheet_name, block_idx)
                        block_idx += 1
                        current_header = None
                        current_data_rows = []
                    elif all(s == "" or s == "nan" or s == "none" for s in row_vals_lower):
                        process_accumulated(current_header, current_data_rows, None, all_data, sheet_name, block_idx)
                        block_idx += 1
                        current_header = None
                        current_data_rows = []

        if current_header is not None and current_data_rows:
            process_accumulated(current_header, current_data_rows, None, all_data, sheet_name, block_idx)

    # Fallback: Se o processamento não gerou dados (0 linhas), usa a planilha original
    # Isso evita o erro de arquivo vazio e permite que o usuário prossiga
    if not all_data and visible_sheets:
        try:
            df_fallback = xl.parse(visible_sheets[0])
            if output_path:
                df_fallback.to_excel(output_path, index=False)
            return df_fallback
        except:
            pass

    result_df = pd.DataFrame(all_data)
    if output_path:
        result_df.to_excel(output_path, index=False)
    return result_df

if __name__ == "__main__":
    input_file = "/home/ubuntu/upload/Logtudo01.xlsx"
    output_file = "/home/ubuntu/Planilha_Tratada_Final.xlsx"
    process_sheet(input_file, output_file)
    print(f"Processamento concluído. Arquivo salvo em: {output_file}")
