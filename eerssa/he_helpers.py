from datetime import datetime, date, time
import pandas as pd
import re
import ast
import numpy as np


# ── Cuadrilla que labora en tiempo Nocturno ───────────────────────────────────

CUADRILLA_AP_4 = "Zamora Z1 (Cuadrilla. AP Nro. 4)"


# ── String / Timezone helpers ──────────────────────────────────────────────────

def elimina_timezone(fecha: str) -> str:
    """Elimina el componente TimeZone de una fecha. 

    Args:
        fecha (str): Fecha en formato ISO 'YYYY-MM-DDTHH:MM:SS±HH:MM'.

    Returns:
        str: Fecha en formato 'YYYY-MM-DD HH:MM:SS'. Si falla, retorna el valor original.
    """
    try:
        fecha_inicio = fecha.replace('T', ' ').split()
        return fecha_inicio[0] + ' ' + fecha_inicio[-1]
    except:
        return fecha


def ColocarTimezone(fecha: str) -> str:
    """Agrega el componente TimeZone '-05:00' a una fecha.

    Args:
        fecha (str): Fecha en formato 'YYYY-MM-DD'.

    Returns:
        str: Fecha en formato 'YYYY-MM-DDT00:00:00-05:00'. Si falla, retorna el valor original.
    """
    try:
        return fecha + 'T00:00:00-05:00'
    except:
        return fecha


def toDateObject(date_str: str) -> date:
    """Convierte una fecha en formato 'YYYY-MM-DD' a un objeto date de Python.

    Útil para luego filtrar filas en un DataFrame por fecha:
        df[df['Date'] > toDateObject('2026-01-01')]

    Args:
        date_str (str): Fecha en formato 'YYYY-MM-DD'. Ej: '2026-02-01'.

    Returns:
        date: Objeto date de Python.
    """
    return datetime.strptime(date_str, '%Y-%m-%d').date()


def toTimeObject(date_str: str) -> date:
    """Convierte una fecha en formato 'YYYY-MM-DD HH:MM:SS' a un objeto date de Python.

    Útil para luego filtrar filas en un DataFrame por fecha:
        df[df['InicioEvento'] > toTimeObject('2026-01-01 08:23:00')]

    Args:
        date_str (str): Fecha en formato 'YYYY-MM-DD HH:MM:SS'. Ej: '2026-02-01 08:23:00'.

    Returns:
        date: Objeto date de Python.
    """
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')


# ── DataFrame helpers ──────────────────────────────────────────────────────────

def calcular_minutos_transcurridos(
    start_times: pd.Series,
    end_times: pd.Series
) -> pd.Series:
    """Calcula los minutos transcurridos entre dos columnas de fechas.

    Args:
        start_times (pd.Series): Serie con las fechas/horas de inicio.
        end_times (pd.Series): Serie con las fechas/horas de fin.

    Returns:
        pd.Series: Serie de enteros con los minutos transcurridos.
    """
    try:
        start_times = pd.to_datetime(start_times)
        end_times = pd.to_datetime(end_times)
        time_difference = end_times - start_times
        return ( time_difference.dt.total_seconds() / 60 ).astype(int)
    except Exception as e:
        print(f" EXCEPTION:\n{e}")


def natural_key(s):
    """Rompe una cadena de palabras en partes numéricas y no numéricas.

    Args:
        s (String): Cadena a romper.

    Returns:
        Array: Lista de palabras y digitos.
    """
    """Split string into text and numeric parts for natural ordering."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(s))]


# ── HoraExtra helpers ──────────────────────────────────────────────────────────

def limpiar_items(lista_items):
    # 1. Convert all elements to strings (handles ints/floats)
    # Using sorted(set()) if you want unique, ordered numbers
    # Using just (str(i) for i in lista_items) if you want to keep duplicates
    str_items = [str(i) for i in lista_items]
    return str(str_items)


def limpiar_lista_eventos(lista_eventos):
    cleaned_list = []
    for texto in lista_eventos:
        # Replace newlines/hashtags and collapse multiple spaces
        t = texto.replace("\n", " ").replace("#", " ")
        t = " ".join(t.split())
        if t:  # Only add if the string isn't empty after cleaning
            cleaned_list.append(t)
    # Join the cleaned strings into one block of text
    return " ".join(cleaned_list)


def limpiar_cuentas(cuentas):
    exclude = {"transporte", "lunch", "informativa"}
    # Remove duplicates and excluded words
    result_list = list(set(cuentas) - exclude)
    # If empty, use "?", otherwise join with a space
    if not result_list:
        return "?"
    return ", ".join(result_list)


def cuenta_to_dict(valor):
    if pd.isna(valor) or valor == "":
        return []
    elementos = str(valor).split(", ")
    resultado = []
    for item in elementos:
        if ":" in item:
            # Split "REDES:30" -> key: "REDES", value: 30
            key, val = item.rsplit(":", 1)
            resultado.append({"cuenta": key.strip(), "peso": float(val) / 100})
        else:
            # No ":" found, assume 100% (1.0)
            resultado.append({"cuenta": item.strip(), "peso": 1.0})
    return resultado


def dict_to_cuenta(lista):
    if not lista or (isinstance(lista, float) and pd.isna(lista)):
        return ""
    elementos = []
    for item in lista:
        cuenta = item["cuenta"].strip()
        peso = item["peso"]
        if peso == 1.0:
            # No ":" needed, just the account name
            elementos.append(cuenta)
        else:
            # Convert back: 0.30 -> 30, format as "CUENTA:30"
            valor = int(round(peso * 100))
            elementos.append(f"{cuenta}:{valor}")
    return ", ".join(elementos)


# ── Ajustar Horarios de Inicio y Fin HE ──────────────────────────────────────────────────────────

def ajustar_horario_inicio(row):
    inicio_rango = time(8, 1, 0)
    inicio_noche = time(19, 0, 0)
    fin_rango = time(16, 59, 0)
    nuevo_horario = time(17, 0, 0)

    if row['Tipo'] == 'NORMAL' and inicio_rango <= row['InicioEvento'] <= fin_rango:
        return nuevo_horario
    if row['Tipo'] == 'CAMBIO_HORARIO' and inicio_noche > row['InicioEvento']:
        return inicio_noche
    return row['InicioEvento']


def ajustar_horario_fin(row):
    inicio_rango = time(8, 1, 0)
    fin_rango = time(16, 59, 0)
    fin_noche = time(22, 0, 0)
    nuevo_horario = time(8, 0, 0)

    if row['Tipo'] == 'NORMAL' and inicio_rango <= row['FinEvento'] <= fin_rango:
        return nuevo_horario
    if row['Tipo'] == 'CAMBIO_HORARIO' and fin_noche < row['FinEvento']:
        return fin_noche
    return row['FinEvento']


"""
transform_horas_extra.py
------------------------
Aplica transformaciones a cada DataFrame dentro del diccionario
'horasExtra_validado' y produce 'horasExtra_final' con las columnas:
    Fecha, InicioEvento, FinEvento, Normal, Descanso, Madrugada, Evento

Reglas de clasificación (columna 'Tipo'):
    Normal    → NORMAL
    Descanso  → DESCANSO | FESTIVO | CANTONIZACION
    Madrugada → MAD

La fórmula Excel almacenada es "=(C{i}-B{i})" donde {i} es la fila
real en Excel (fila 2 = primera fila de datos, considerando header).

Uso como módulo:
    from he_helpers import build_horas_extra_final
    horasExtra_final = build_horas_extra_final(horasExtra_validado)

Uso como script independiente (carga un CSV de prueba):
    python he_helpers.py --csv MA.csv --key MA
"""

# Tipos que van a cada columna
TIPOS_NORMAL    = {"NORMAL"}
TIPOS_DESCANSO  = {"DESCANSO", "FESTIVO", "CANTONIZACION"}
TIPOS_MADRUGADA = {"MAD"}

# Columnas del resultado final
COLUMNAS_FINALES = ["Fecha", "InicioEvento", "FinEvento",
                    "Normal", "Descanso", "Madrugada", "Evento"]


def agregar_columnas_formulas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recibe un DataFrame con columna 'Tipo' y agrega Normal, Descanso, Madrugada.
    La fila Excel empieza en 2 (fila 1 = encabezado).
    """
    df = df.copy().reset_index(drop=True)
    df["Normal"]    = ""
    df["Descanso"]  = ""
    df["Madrugada"] = ""

    for idx in df.index:
        excel_row = idx + 2
        tipo = str(df.at[idx, "Tipo"]).strip().upper()

        formula = f"=(C{excel_row}-B{excel_row})"

        if tipo in TIPOS_NORMAL:
            df.at[idx, "Normal"] = formula
        elif tipo in TIPOS_DESCANSO:
            df.at[idx, "Descanso"] = formula
        elif tipo in TIPOS_MADRUGADA:
            df.at[idx, "Madrugada"] = formula

    return df


def build_horas_extra_final(horasExtra_validado: dict) -> dict:
    """
    Transforma cada DataFrame del diccionario y devuelve 'horasExtra_final'
    con solo las columnas requeridas.
    """
    horasExtra_final = {}

    for key, df in horasExtra_validado.items():
        df_transformado = agregar_columnas_formulas(df)
        horasExtra_final[key] = df_transformado[COLUMNAS_FINALES].copy()

    return horasExtra_final


# CREAR EXCEL DE ACTIVIDADES

def exportar_actividades_excel(
    df: "pd.DataFrame",
    plantilla_path: str,
    output_path: str,
    *,
    sheet_index: int = 1,
) -> int:
    """
    Export a DataFrame of actividades into an Excel template with data validations.

    Parameters
    ----------
    df : pd.DataFrame
        The filtered/conditioned DataFrame to export.
    plantilla_path : str
        Path to the Excel template (.xlsx) to copy from.
    output_path : str
        Path where the populated Excel file will be saved.
    sheet_index : int
        Index of the worksheet to populate (default: 1).

    Returns
    -------
    int
        Number of rows written.
    """
    import shutil
    from openpyxl import load_workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.worksheet.datavalidation import DataValidation
    from natsort import index_natsorted

    from eerssa.utils import soloFecha_SinTimezone

    shutil.copyfile(plantilla_path, output_path)

    excel = df.copy()

    reubica_cols = list(excel.columns)
    reubica_cols.insert(3, reubica_cols.pop())
    excel = excel[reubica_cols]

    excel['Fecha'] = excel['Fecha'].apply(lambda x: soloFecha_SinTimezone(x))
    excel['Duracion'] = excel['Duracion'] / (60 * 24)
    excel.loc[excel['Cuenta'] == 'se_labora', 'HorasExtra'] = 'No'
    excel = excel.iloc[index_natsorted(zip(excel['Archivo'], excel['Item']))]

    wb = load_workbook(output_path)
    sheet = wb.worksheets[sheet_index]

    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column):
        for cell in row:
            cell.value = None

    for r_idx, row in enumerate(dataframe_to_rows(excel, index=False, header=False), 2):
        for c_idx, value in enumerate(row, 1):
            sheet.cell(row=r_idx, column=c_idx, value=value)

    max_row = sheet.max_row

    _validations = [
        ('=LISTAS!B$3:B$30', True,  ['B']),
        ('=LISTAS!E$3:E$30', True,  ['J']),
        ('=LISTAS!G$3:G$30', True,  ['E']),
        ('=LISTAS!I$3:I$100', True, ['F']),
        ('"Si,No"',          False, ['G','H','I','T']),
    ]

    for formula, allow_blank, columns in _validations:
        dv = DataValidation(
            type="list",
            formula1=formula,
            allow_blank=allow_blank,
            showErrorMessage=not allow_blank,
        )
        for col in columns:
            dv.add(f'{col}2:{col}{max_row}')
        sheet.add_data_validation(dv)

    wb.save(output_path)
    return len(excel)


# ── Consolidación de Horas Extra ────────────────────────────────────────

def agrupar_eventos(df):
    """
    Groups consecutive events by id_ot + time continuity into
    consolidated overtime activities.

    Parameters
    ----------
    df : pd.DataFrame
        Raw event data (already filtered to HorasExtra == 'Si').
    
    Returns
    -------
    pd.DataFrame
        Consolidated activities, one row per continuous work block.
    """

    from eerssa.utils import soloFecha_SinTimezone

    he = df.copy()
    he['Fecha'] = he['Fecha'].apply(lambda x: soloFecha_SinTimezone( x ))
    he['Date']  = he['Fecha'].apply(lambda x: toDateObject( x ))

    he = he[[
        'Cuadrilla', 'Iniciales', 'Dia', 'Date', 'Item',
        'InicioEvento', 'FinEvento', 'Duracion', 'Evento', 'Cuenta',
        'id_ot', 'Archivo',
    ]]

    he['InicioEvento'] = pd.to_datetime(he['InicioEvento'])
    he['FinEvento']    = pd.to_datetime(he['FinEvento'])
    he['Inicio_min']   = he['InicioEvento'].dt.floor('min')
    he['Fin_min']      = he['FinEvento'].dt.floor('min')

    he = he.sort_values(['id_ot', 'InicioEvento']).reset_index(drop=True)

    new_group = (
        (he['id_ot'] != he['id_ot'].shift()) |
        (he['Inicio_min'] != he['Fin_min'].shift())
    )
    he['group'] = new_group.cumsum()

    result = he.groupby('group').agg(
        Cuadrilla     = ('Cuadrilla', 'first'),
        Colaboradores = ('Iniciales', 'first'),
        Dia           = ('Dia', 'first'),
        Fecha         = ('Date', 'first'),
        InicioEvento  = ('InicioEvento', 'min'),
        FinEvento     = ('FinEvento', 'max'),
        Duracion      = ('Duracion', 'sum'),
        Evento        = ('Evento', list),
        Cuenta        = ('Cuenta', list),
        id_ot         = ('id_ot', 'first'),
        Items         = ('Item', list),
        Num_Filas     = ('Evento', 'count'),
        Archivo       = ('Archivo', 'first'),
    ).reset_index(drop=True)

    result = result.query('Duracion != 0.0') \
                   .sort_values(['Archivo', 'InicioEvento']) \
                   .reset_index(drop=True)

    result['Evento'] = result['Evento'].apply(limpiar_lista_eventos)
    result['Cuenta'] = result['Cuenta'].apply(limpiar_cuentas)
    result['Cuenta'] = result['Cuenta'].apply(cuenta_to_dict)
    result['Items']  = result['Items'].apply(limpiar_items)

    result['InicioEvento'] = result['InicioEvento'].dt.time
    result['FinEvento']    = result['FinEvento'].dt.time

    return result


def cargar_reglas_tipo(xls_path):
    """
    Load holiday calendar and night-shift dates from the template Excel.

    Returns
    -------
    dict with keys: 'dict_todos', 'dict_especificos', 'set_noche'
    """
    festivos = pd.read_excel(xls_path, sheet_name='Revisar_primero',
                             usecols='A:C', header=0)
    festivos['Fecha'] = pd.to_datetime(festivos['Fecha']).dt.date

    dict_todos = (festivos[festivos['Aplica'] == 'TODOS']
                  .set_index('Fecha')['Etiqueta'].to_dict())
    dict_especificos = (festivos[festivos['Aplica'] != 'TODOS']
                        .set_index(['Fecha', 'Aplica'])['Etiqueta'].to_dict())

    noche = pd.read_excel(xls_path, sheet_name='Revisar_primero',
                          usecols='D', header=0).squeeze('columns')
    set_noche = set(pd.to_datetime(noche.dropna()).dt.date)

    return {
        'dict_todos': dict_todos,
        'dict_especificos': dict_especificos,
        'set_noche': set_noche,
    }


def clasificar_tipo(row, dict_todos, dict_especificos, set_noche):
    """Classify a single row's overtime type."""
    fecha     = row['Fecha'] if not hasattr(row['Fecha'], 'date') else row['Fecha'].date()
    cuadrilla = row['Cuadrilla']
    dia       = row['Dia']
    inicio    = row['InicioEvento']

    if cuadrilla == CUADRILLA_AP_4 and fecha in set_noche:
        return 'CAMBIO_HORARIO'
    if fecha in dict_todos:
        return 'FESTIVO'
    if (fecha, cuadrilla) in dict_especificos:
        return 'CANTONIZACION'
    if dia in ('sábado', 'domingo'):
        return 'DESCANSO'
    if inicio.hour < 6:
        return 'MAD'
    return 'NORMAL'


def etiquetar_tipo(result, reglas):
    """
    Apply clasificar_tipo to every row using pre-loaded rules.

    Parameters
    ----------
    result : pd.DataFrame
        Output of agrupar_eventos().
    reglas : dict
        Output of cargar_reglas_tipo().

    Returns
    -------
    pd.DataFrame with 'Tipo' column added.
    """
    result = result.copy()
    result['Tipo'] = result.apply(
        clasificar_tipo, axis=1,
        dict_todos=reglas['dict_todos'],
        dict_especificos=reglas['dict_especificos'],
        set_noche=reglas['set_noche'],
    )
    return result


def dividir_almuerzo(result):
    """
    Split holiday/weekend activities that span lunch (>4h crossing 12:00–15:00)
    into two rows with a 13:00–14:00 lunch break.

    Returns
    -------
    pd.DataFrame with split rows.
    """
    mask = (
        result['Tipo'].isin(['DESCANSO', 'FESTIVO', 'CANTONIZACION']) &
        (result['FinEvento'] > time(15, 0, 0)) &
        (result['InicioEvento'] < time(12, 0, 0)) &
        (
            (pd.to_datetime(result['FinEvento'].astype(str))
             - pd.to_datetime(result['InicioEvento'].astype(str)))
            .dt.total_seconds() > 4 * 3600
        )
    )

    no_split = result[~mask].copy()
    to_split = result[mask].copy()

    part1 = to_split.copy()
    part1['FinEvento'] = time(13, 0, 0)
    part1['Items'] =  "['1', '2']"

    part2 = to_split.copy()
    part2['InicioEvento'] = time(14, 0, 0)
    part2['Items'] = "['3', '4']"

    return (pd.concat([no_split, part1, part2], ignore_index=True)
              .sort_values(['Archivo', 'InicioEvento'])
              .reset_index(drop=True))


def formulas_duracion_excel(result):
    """Add Excel duration formulas. Call only before Excel export."""
    result = result.copy()
    result['Duracion'] = [f'=F{i}-E{i}' for i in range(2, len(result) + 2)]
    return result


def consolidar_horas_extra(df, reglas):
    """
    Full pipeline: filter → group → label → adjust times → split lunch.

    This is the main entry point.

    Parameters
    ----------
    df : pd.DataFrame
        Raw event data with 'HorasExtra' column.
    reglas : dict
        Output of cargar_reglas_tipo().

    Returns
    -------
    pd.DataFrame
        Consolidated, classified, lunch-split overtime records.
    """
    he = df[df['HorasExtra'] == 'Si'].copy()
    result = agrupar_eventos(he)
    result = etiquetar_tipo(result, reglas)
    result['InicioEvento'] = result.apply(ajustar_horario_inicio, axis=1)
    result['FinEvento']    = result.apply(ajustar_horario_fin, axis=1)
    result['Evento'] = result.apply(
        lambda row: f"OT # {row['id_ot']}. {row['Evento']}", axis=1
    )
    result = dividir_almuerzo(result)
    return result


# ── DuckDB Sync Utilities ──────────────────────────────────────────────


# ==================================================================================
#
#      DUCK DB horas extra database 
#
# ==================================================================================

# ── Parsing: consolidado DataFrame → DuckDB-ready values ─────────────

def parse_cuenta_consolidado(cuenta_str):
    """
    Parse the list-of-dicts format from consolidado DataFrame
    into a normalized percentage dict for DuckDB MAP(VARCHAR, INTEGER).

    '[{"cuenta":"REDES","peso":1.0},{"cuenta":"MEDIDORES","peso":1.0}]'
    → {"REDES": 50, "MEDIDORES": 50}
    """
    if not cuenta_str or str(cuenta_str) == 'nan':
        return {}
    try:
        items = ast.literal_eval(str(cuenta_str))
        total = sum(d['peso'] for d in items)
        if total == 0:
            return {}
        return {d['cuenta']: round(d['peso'] / total * 100) for d in items}
    except Exception:
        return {}


# ── Cuenta Format Conversions ──────────────────────────────────────────

def cuenta_consolidado_to_str(cuenta_val) -> str:
    """
    Convert consolidado Cuenta format (list of dicts with weight)
    to legible Excel string.

    [{'cuenta':'REDES','peso':1.0}, {'cuenta':'MEDIDORES','peso':1.0}]
    → "REDES:50, MEDIDORES:50"
    """
    if not cuenta_val or str(cuenta_val) == 'nan':
        return ""
    try:
        items = ast.literal_eval(str(cuenta_val)) if isinstance(cuenta_val, str) else cuenta_val
    except (ValueError, SyntaxError):
        return str(cuenta_val)
    if not isinstance(items, list):
        return str(items)
    if items and isinstance(items[0], str):
        total = len(items)
        pct = round(100 / total)
        return ", ".join(f"{c}:{pct}" for c in items)
    total_peso = sum(d.get('peso', 0) for d in items)
    if total_peso == 0:
        return ""
    parts = []
    for d in items:
        pct = round(d['peso'] / total_peso * 100)
        parts.append(f"{d['cuenta']}:{pct}")
    return ", ".join(parts)


def cuenta_str_to_map(s) -> dict:
    """
    Convert legible string to MAP(VARCHAR, INTEGER) for DuckDB.

    "REDES:50, MEDIDORES:50" → {'REDES': 50, 'MEDIDORES': 50}
    "MEDIDORES"              → {'MEDIDORES': 100}
    """
    if not s or str(s) == 'nan':
        return {}
    s = str(s).strip()
    if s.startswith('{'):
        try:
            return ast.literal_eval(s)
        except (ValueError, SyntaxError):
            pass
    if s.startswith('['):
        try:
            items = ast.literal_eval(s)
            if isinstance(items, list) and items:
                if isinstance(items[0], dict):
                    total = sum(d.get('peso', 0) for d in items)
                    if total == 0:
                        return {}
                    return {d['cuenta']: round(d['peso'] / total * 100) for d in items}
                pct = round(100 / len(items))
                return {c: pct for c in items}
        except (ValueError, SyntaxError):
            pass
    result = {}
    for part in s.split(','):
        part = part.strip()
        if ':' in part:
            k, v = part.rsplit(':', 1)
            try:
                result[k.strip()] = int(v.strip())
            except ValueError:
                result[k.strip()] = 0
        elif part:
            result[part] = 100
    return result


def map_to_cuenta_str(m) -> str:
    """
    Convert DuckDB MAP to legible string.

    {'REDES': 50, 'MEDIDORES': 50} → "REDES:50, MEDIDORES:50"
    """
    if not m:
        return ""
    if isinstance(m, str):
        return m
    return ", ".join(f"{k}:{v}" for k, v in m.items())


def parse_items_consolidado(items_val):
    """Parse Items from consolidado (handles both "['1','2']" and "1, 2")."""
    if not items_val or str(items_val) == 'nan':
        return []
    s = str(items_val).strip()
    try:
        result = ast.literal_eval(s)
        if isinstance(result, list):
            return [str(x).strip() for x in result]
    except Exception:
        pass
    return [x.strip().strip("'\"") for x in s.split(',') if x.strip()]


def parse_colaboradores(colab_val):
    """
    'AO, LP' → ['AO', 'LP']
    ['AO', 'LP'] → ['AO', 'LP']  (passthrough)
    """
    if isinstance(colab_val, list):
        return colab_val
    if not colab_val or str(colab_val) == 'nan':
        return []
    return [x.strip() for x in str(colab_val).split(',') if x.strip()]


def _to_time_str(val):
    """Normalize to 'HH:MM:SS' string for DuckDB TIME."""
    if val is None or (isinstance(val, float) and str(val) == 'nan'):
        return None
    if hasattr(val, 'strftime'):
        return val.strftime('%H:%M:%S')
    s = str(val).strip()
    if ' ' in s:
        s = s.split(' ')[-1]
    return s[:8]


def items_to_key(items_val) -> str:
    """
    Normalize any Items representation into a canonical sort key.
    
    Handles:
      - Python list:        ['1', '2', '4']
      - List-as-string:     "['1', '2', '4']"
      - Comma-separated:    "1, 2"
      - Single int/string:  4 or "4"
    
    Returns: "1,2,4" (numerically sorted, no spaces)
    """
    if items_val is None or (isinstance(items_val, float) and str(items_val) == 'nan'):
        return ""
    
    if isinstance(items_val, list):
        raw = items_val
    else:
        s = str(items_val).strip()
        try:
            parsed = ast.literal_eval(s)
            raw = parsed if isinstance(parsed, list) else [parsed]
        except (ValueError, SyntaxError):
            raw = [x.strip().strip("'\"") for x in s.split(',') if x.strip()]
    
    nums = []
    for x in raw:
        try:
            nums.append(int(str(x).strip().strip("'\"")))
        except ValueError:
            nums.append(str(x).strip())
    
    nums.sort(key=lambda x: (isinstance(x, str), x))
    return ",".join(str(n) for n in nums)


# ── Download from DuckDB HE ───────────────────────────────────

def enriquecer_desde_duckdb(con, consolidado, fecha_inicio, fecha_fin):
    """
    Step 2: For each row in consolidado, check DuckDB for match on (id_ot, items_key).
    If match found: overwrite Evento and Cuenta with DuckDB values (preserving user edits).
    If no match: keep auto-generated values.
    
    Parameters
    ----------
    con : duckdb.DuckDBPyConnection
    consolidado : pd.DataFrame
        Fresh output of consolidar_horas_extra()
    fecha_inicio, fecha_fin : date
    
    Returns
    -------
    pd.DataFrame — consolidado with Evento/Cuenta enriched from DuckDB
    int          — count of matches found
    """
    result = consolidado.copy()
    
    result['items_key'] = result['Items'].apply(items_to_key)
    
    duck_df = con.execute("""
        SELECT id_ot, items_key, Evento, Cuenta
        FROM actividades
        WHERE Fecha BETWEEN $1 AND $2
    """, [str(fecha_inicio), str(fecha_fin)]).df()
    
    if duck_df.empty:
        result['Cuenta'] = result['Cuenta'].apply(cuenta_consolidado_to_str)
        result.drop(columns='items_key', inplace=True)
        return result, 0
    
    duck_lookup = {}
    for _, row in duck_df.iterrows():
        key = (int(row['id_ot']), row['items_key'])
        duck_lookup[key] = {
            'Evento': row['Evento'],
            'Cuenta': row['Cuenta'],
        }
    
    n_matches = 0
    for idx, row in result.iterrows():
        key = (int(row['id_ot']), row['items_key'])
        if key in duck_lookup:
            result.at[idx, 'Evento'] = duck_lookup[key]['Evento']
            result.at[idx, 'Cuenta'] = map_to_cuenta_str(duck_lookup[key]['Cuenta'])
            n_matches += 1
        else:
            result.at[idx, 'Cuenta'] = cuenta_consolidado_to_str(row['Cuenta'])
    
    result.drop(columns='items_key', inplace=True)
    return result, n_matches


# ── UPLOAD to DuckDB ───────────────────────────────────

def sincronizar_a_duckdb(con, consolidado_editado, fecha_inicio, fecha_fin):
    """
    Step 4: Upsert edited consolidado back to DuckDB.
    
    - UPDATE existing rows (match on id_ot + items_key)
      - Diff Colaboradores → add/remove participaciones
      - Preserves tiempo_ajustado on surviving participaciones
    - INSERT new rows + their participaciones  
    - DELETE orphaned actividades in date range (no longer in consolidado)
      - Cascades to participaciones
    
    Returns
    -------
    dict with counts: {updated, inserted, deleted, part_added, part_removed}
    """
    stats = {'updated': 0, 'inserted': 0, 'deleted': 0,
             'part_added': 0, 'part_removed': 0}
    
    consolidado_editado = consolidado_editado.copy()
    consolidado_editado['items_key'] = consolidado_editado['Items'].apply(items_to_key)
    
    existing = con.execute("""
        SELECT id_actividad, id_ot, items_key, Colaboradores
        FROM actividades
        WHERE Fecha BETWEEN $1 AND $2
    """, [str(fecha_inicio), str(fecha_fin)]).df()
    
    existing_lookup = {}
    for _, row in existing.iterrows():
        key = (int(row['id_ot']), row['items_key'])
        
        # Safely extract the array
        colabs_raw = row['Colaboradores']
        
        # If it's a valid list or NumPy array, make it a set. Otherwise, empty set.
        if isinstance(colabs_raw, (list, np.ndarray)):
            colabs_set = set(colabs_raw)
        else:
            colabs_set = set()
            
        existing_lookup[key] = {
            'id_actividad': int(row['id_actividad']),
            'Colaboradores': colabs_set,
        }   
    
    touched_ids = set()
    
    for _, row in consolidado_editado.iterrows():
        key = (int(row['id_ot']), row['items_key'])
        new_colabs = parse_colaboradores(row['Colaboradores'])
        new_colabs_set = set(new_colabs)
        cuenta = cuenta_str_to_map(row['Cuenta'])
        fecha = str(row['Fecha'])[:10]
        inicio = _to_time_str(row['InicioEvento'])
        fin = _to_time_str(row['FinEvento'])
        items_list = parse_items_consolidado(row['Items'])
        
        if key in existing_lookup:
            info = existing_lookup[key]
            id_act = info['id_actividad']
            touched_ids.add(id_act)
            
            con.execute("""
                UPDATE actividades SET
                    Evento        = $1,
                    Cuenta        = $2,
                    Colaboradores = $3,
                    InicioEvento  = $4::TIME,
                    FinEvento     = $5::TIME,
                    Tipo          = $6,
                    Cuadrilla     = $7,
                    Dia           = $8,
                    Num_Filas     = $9,
                    Archivo       = $10,
                    Duracion      = $11
                WHERE id_actividad = $12
            """, [
                row['Evento'], cuenta, new_colabs,
                inicio, fin, row['Tipo'], row['Cuadrilla'],
                row['Dia'], int(row['Num_Filas']), row['Archivo'],
                int(row.get('Duracion', 0)), id_act,
            ])
            stats['updated'] += 1
            
            old_colabs = info['Colaboradores']
            
            removed = old_colabs - new_colabs_set
            if removed:
                for persona in removed:
                    con.execute("""
                        DELETE FROM participaciones
                        WHERE id_actividad = $1 AND Responsable = $2
                    """, [id_act, persona])
                    stats['part_removed'] += 1
            
            added = new_colabs_set - old_colabs
            if added:
                for persona in added:
                    con.execute("""
                        INSERT INTO participaciones (id_actividad, Responsable)
                        VALUES ($1, $2)
                    """, [id_act, persona])
                    stats['part_added'] += 1
        
        else:
            result = con.execute("""
                INSERT INTO actividades
                    (id_ot, Fecha, Cuadrilla, Colaboradores, InicioEvento, FinEvento, Duracion,
                     Evento, Cuenta, Items, items_key, Num_Filas, Archivo, Tipo, Dia)
                VALUES ($1, $2::DATE, $3, $4, $5::TIME, $6::TIME, $7,
                        $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING id_actividad
            """, [
                int(row['id_ot']), fecha, row['Cuadrilla'], new_colabs,
                inicio, fin, int(row.get('Duracion', 0)),
                row['Evento'], cuenta, items_list, row['items_key'],
                int(row['Num_Filas']), row['Archivo'], row['Tipo'], row['Dia'],
            ])
            
            id_act = result.fetchone()[0]
            touched_ids.add(id_act)
            stats['inserted'] += 1
            
            for persona in new_colabs:
                con.execute("""
                    INSERT INTO participaciones (id_actividad, Responsable)
                    VALUES ($1, $2)
                """, [id_act, persona])
                stats['part_added'] += 1
    
    all_existing_ids = {info['id_actividad'] for info in existing_lookup.values()}
    orphan_ids = all_existing_ids - touched_ids
    
    for oid in orphan_ids:
        con.execute("DELETE FROM participaciones WHERE id_actividad = $1", [oid])
        con.execute("DELETE FROM actividades WHERE id_actividad = $1", [oid])

    stats['deleted'] = len(orphan_ids)

    return stats


def sync_deltalake_to_duckdb(con, consolidado, fecha_inicio, fecha_fin):
    """
    Full sync pipeline: enrich from DuckDB → synchronize back to DuckDB.

    Parameters
    ----------
    con : duckdb.DuckDBPyConnection
    consolidado : pd.DataFrame
        Output of consolidar_horas_extra()
    fecha_inicio, fecha_fin : date

    Returns
    -------
    tuple (n_act, n_part)
        n_act  : total actividades affected (updated + inserted + deleted)
        n_part : total participaciones affected (added + removed)
    """
    stats = sincronizar_a_duckdb(con, consolidado, fecha_inicio, fecha_fin)
    n_act = stats['updated'] + stats['inserted'] + stats['deleted']
    n_part = stats['part_added'] + stats['part_removed']

    
    return n_act, n_part


# ── Informe Final HE ──────────────────────────────────────────────

# Multiplier map for each Tipo
TIPO_MULTIPLIER = {
    "NORMAL":          1.5,
    "MAD":             2.0,
    "FESTIVO":         2.0,
    "DESCANSO":        2.0,
    "CANTONIZACION":   2.0,
    "CAMBIO_HORARIO":  0.25,
}


def fetch_base_desde_duckdb(con, fecha_inicio, fecha_fin):
    """
    Fetch base data from DuckDB joined with participaciones.
    One row per person per actividad.

    Returns DataFrame with same schema as consolidado_editado.
    """
    query = """
        SELECT
            a.Cuadrilla,
            p.Responsable AS Colaboradores,
            a.Dia,
            a.Fecha,
            COALESCE(p.InicioEvento, a.InicioEvento) AS InicioEvento,
            COALESCE(p.FinEvento, a.FinEvento) AS FinEvento,
            a.Duracion,
            a.Evento,
            a.Cuenta,
            a.id_ot,
            a.Items,
            a.Num_Filas,
            a.Archivo,
            a.Tipo,
            a.items_key
        FROM actividades a
        JOIN participaciones p ON a.id_actividad = p.id_actividad
        WHERE a.Fecha BETWEEN $1 AND $2
        ORDER BY a.Fecha, a.InicioEvento
    """
    base = con.execute(query, [str(fecha_inicio), str(fecha_fin)]).df()
    base['Fecha'] = pd.to_datetime(base['Fecha']).dt.date
    return base


def pivot_time_events(filtered_df):
    """
    Pivot time events so each day has up to 3 block columns.
    Produces Extra_1/Fin_1, Extra_2/Fin_2, Extra_3/Fin_3.
    """
    df_pivot = filtered_df.copy()
    df_pivot['_occurrence'] = df_pivot.groupby('Fecha').cumcount()
    df_pivot = df_pivot[df_pivot['_occurrence'] < 3].copy()

    for i in range(1, 4):
        df_pivot[f'Extra_{i}'] = np.nan
        df_pivot[f'Fin_{i}'] = np.nan

    result_rows = []
    for fecha, group in df_pivot.groupby('Fecha', sort=False):
        group = group.sort_values('InicioEvento').reset_index(drop=True)
        base_row = group.iloc[0].copy()
        for i, (_, row) in enumerate(group.iterrows()):
            if i < 3:
                base_row[f'Extra_{i+1}'] = row['InicioEvento']
                base_row[f'Fin_{i+1}'] = row['FinEvento']

        base_row['Lista_tipos'] = group['Tipo'].tolist()
        base_row['Lista_Eventos'] = ' '.join(group['Evento'].astype(str).tolist())
        result_rows.append(base_row)

    result = pd.DataFrame(result_rows)

    cols = result.columns.tolist()
    inicio_pos = cols.index('InicioEvento')
    new_cols = ['Extra_1', 'Fin_1', 'Extra_2', 'Fin_2', 'Extra_3', 'Fin_3']
    cols_clean = [c for c in cols if c not in new_cols + ['InicioEvento', 'FinEvento', '_occurrence']]
    final_cols = cols_clean[:inicio_pos] + new_cols + cols_clean[inicio_pos:]

    return result[final_cols].reset_index(drop=True)


def complete_date_range(df_pivot, reporte_inicia, reporte_finaliza):
    """Fill missing dates with NaN between reporte_inicia and reporte_finaliza."""
    all_dates = pd.DataFrame({
        'Fecha': pd.date_range(reporte_inicia, reporte_finaliza)
    })
    df_pivot['Fecha'] = pd.to_datetime(df_pivot['Fecha'])
    result = all_dates.merge(df_pivot, on='Fecha', how='left')
    return result


def build_sobretiempos_formula(lista_tipos, row_i, fila_offset=6):
    """
    Build Excel SUM formula for overtime based on Lista_tipos.
    Pairs are (C,D), (E,F), (G,H). Multiplier from TIPO_MULTIPLIER.
    """
    col_pairs = [('C', 'D'), ('E', 'F'), ('G', 'H')]
    xl_row = row_i + fila_offset

    terms = []
    for idx, tipo in enumerate(lista_tipos):
        if idx >= 3:
            break
        tipo = str(tipo).strip()
        multiplier = TIPO_MULTIPLIER.get(tipo, 1.5)
        start_col, end_col = col_pairs[idx]
        terms.append(f"({end_col}{xl_row}-{start_col}{xl_row})*{multiplier}*24")

    if not terms:
        return ''
    return f'=SUM({",".join(terms)})'


def generar_informe_he(con, fecha_inicio, fecha_fin, template_path, output_path):
    """
    Generate the final HE report Excel workbook.
    One sheet per person, using plantilla_informe_he.xlsx as template.

    Returns list of person initials that were processed.
    """
    import shutil
    from openpyxl import load_workbook
    import eerssa.organizar as gdrive
    from eerssa.excel_styles import apply_he_informe

    # 1. Fetch base from DuckDB
    base = fetch_base_desde_duckdb(con, fecha_inicio, fecha_fin)

    if base.empty:
        return []

    # 2. Split Colaboradores into lists
    base_div = base.copy()
    for col in ['Colaboradores']:
        base_div[col] = base_div[col].apply(
            lambda x: str(x).split(", ") if pd.notnull(x) else []
        )

    unique_colaboradores = base_div['Colaboradores'].explode().dropna().unique()

    # 3. Build per-person DataFrames
    horasExtra_todos = {}
    for person in unique_colaboradores:
        filtered_df = base_div[
            base_div['Colaboradores'].apply(
                lambda x: person in x if isinstance(x, list) else False
            )
        ].copy()

        filtered_df = filtered_df.sort_values(by=['Fecha', 'InicioEvento'])
        filtered_df = filtered_df.reset_index(drop=True)

        filtered_df = pivot_time_events(filtered_df)
        filtered_df = complete_date_range(filtered_df, fecha_inicio, fecha_fin)

        fila_inicial_xl = 6
        filtered_df['Duracion'] = [
            f'=SUM(D{i+fila_inicial_xl}-C{i+fila_inicial_xl},'
            f'F{i+fila_inicial_xl}-E{i+fila_inicial_xl},'
            f'H{i+fila_inicial_xl}-G{i+fila_inicial_xl})'
            for i in range(len(filtered_df))
        ]
        filtered_df['Sobretiempos'] = [
            build_sobretiempos_formula(lista_tipos, i, fila_inicial_xl)
            if isinstance(lista_tipos, list) else ''
            for i, lista_tipos in enumerate(filtered_df['Lista_tipos'], start=0)
        ]

        horasExtra_todos[person] = filtered_df[[
            "Dia", "Fecha", "Extra_1", "Fin_1", "Extra_2", "Fin_2",
            "Extra_3", "Fin_3", "Duracion", "Lista_Eventos", "Sobretiempos",
        ]]

    # 4. Get cuadrilla data from Google Sheets
    df_datos_cuadrilla = gdrive.get_gsheet_df()

    # 5. Generate Excel workbook
    TEMPLATE_SHEET = "HORAS_EXTRA"
    START_ROW = 6
    START_COL = 2

    shutil.copy2(template_path, output_path)
    _wb = load_workbook(output_path)
    template_ws = _wb[TEMPLATE_SHEET]

    for key, df_pivot in horasExtra_todos.items():
        _ws = _wb.copy_worksheet(template_ws)
        _ws.title = str(key)

        match = df_datos_cuadrilla[df_datos_cuadrilla['INICIALES'] == key]
        if not match.empty:
            _ws['H2'] = match['NOMBRE'].iloc[0]
            _ws['H3'] = match['CUADRILLA_CORTO'].iloc[0]
        else:
            _ws['H2'] = "No registrado"
            _ws['H3'] = "No registrado"

        df_to_export = df_pivot.iloc[:, 1:]  # skip Dia column

        eventos_col_idx = None
        if 'Lista_Eventos' in df_to_export.columns:
            eventos_col_idx = df_to_export.columns.get_loc('Lista_Eventos')

        for row_idx, row_data in enumerate(df_to_export.itertuples(index=False), start=START_ROW):
            for col_idx, value in enumerate(row_data, start=START_COL):
                _ws.cell(row=row_idx, column=col_idx, value=value)

            if eventos_col_idx is not None:
                eventos_value = row_data[eventos_col_idx]
                char_len = len(str(eventos_value)) if pd.notna(eventos_value) else 0
                if char_len >= 430:
                    _ws.row_dimensions[row_idx].height = 60
                elif char_len >= 286:
                    _ws.row_dimensions[row_idx].height = 40
                elif char_len >= 151:
                    _ws.row_dimensions[row_idx].height = 27

        apply_he_informe(_ws)

    _wb.save(output_path)
    return list(horasExtra_todos.keys())