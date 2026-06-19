from datetime import datetime, date, time
import pandas as pd
import argparse
import re
import os
import json
from pathlib import Path

# ── Cuadrilla que labora en tiempo Nocturno ───────────────────────────────────

CUADRILLA_AP_4 = "Zamora Z1 (Cuadrilla. AP Nro. 4)"

# ── Cargar Credenciales R2 Cloudfare ───────────────────────────────────

REQUIRED_KEYS = {"account_id", "api_token", "access_key", "secret_key","duckdb_he_token"}



def load_r2_credentials(json_path: str) -> dict:
    """
    Carga las credenciales de R2 desde un archivo JSON.

    Parámetros
    ----------
    json_path : str
        Ruta al archivo JSON con las credenciales.

    Retorna
    -------
    dict
        Diccionario con las claves: account_id, api_token, access_key, secret_key.

    Lanza
    -----
    FileNotFoundError si el archivo no existe.
    json.JSONDecodeError si el archivo no es JSON válido.
    ValueError si faltan claves requeridas o hay valores vacíos.
    """
    path = Path(json_path)

    # ── 1. Verificar que el archivo existe ────────────────────────────────────
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path.resolve()}")

    # ── 2. Leer y parsear JSON ───────────────────────────────────────────────
    try:
        with open(path, "r", encoding="utf-8") as f:
            creds = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"El archivo no contiene JSON válido: {e.msg}", e.doc, e.pos
        )

    # ── 3. Verificar que sea un diccionario ───────────────────────────────────
    if not isinstance(creds, dict):
        raise ValueError("El archivo JSON debe contener un objeto (diccionario).")

    # ── 4. Verificar claves requeridas ────────────────────────────────────────
    missing = REQUIRED_KEYS - set(creds.keys())
    if missing:
        raise ValueError(
            f"Faltan las siguientes claves en el archivo: {sorted(missing)}"
        )

    # ── 5. Verificar que ningún valor esté vacío ──────────────────────────────
    empty = [k for k in REQUIRED_KEYS if not creds.get(k)]
    if empty:
        raise ValueError(
            f"Las siguientes claves tienen valores vacíos: {sorted(empty)}"
        )

    return creds



# ── Festivos / Obtener Festivos ────────────────────────────────────────────────
def get_festivos():
    path_festivos = 'models/hora_extra_template.xlsx'
    # visualizar dias festivos
    festivos = pd.read_excel(
        path_festivos,
        sheet_name='Revisar_primero',
        usecols='A:C',      # Only columns A and B
        header=0            # First row as column names
    )


    # visualizar cambios de horario en Cuadrilla Alumbrado
    noche = pd.read_excel(
        path_festivos,
        sheet_name='Revisar_primero',
        usecols='D',      # Only columns A and B
        header=0            # First row as column names
    ).squeeze("columns") # Turns the 1-column DataFrame into a Series
    
    festivos['Fecha'] = pd.to_datetime(festivos['Fecha']).dt.date
    dict_todos = festivos[festivos['Aplica'] == 'TODOS'].set_index('Fecha')['Etiqueta'].to_dict()
    dict_especificos = festivos[festivos['Aplica'] != 'TODOS'].set_index(['Fecha', 'Aplica'])['Etiqueta'].to_dict()
    set_noche = set(pd.to_datetime(noche.dropna()).dt.date)

    return { 'TODOS':dict_todos, 'ESPECIFICOS':dict_especificos, 'NOCHE':set_noche}
 


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

def soloFecha_SinTimezone(fecha: str) -> str:
    """Elimina el componente TimeZone y retorna solo la fecha.

    Args:
        fecha (str): Fecha en formato ISO 'YYYY-MM-DDTHH:MM:SS±HH:MM'.

    Returns:
        str: Fecha en formato 'YYYY-MM-DD'. Si falla, retorna el valor original.
    """
    try:
        fecha_inicio = fecha.replace('T', ' ').split()
        return fecha_inicio[0]
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
    
    # 2. Join with ", "
    #resultado = ", ".join(str_items)
    
    # 3. Handle empty lists for Excel clarity
    return str(str_items)

def limpiar_lista_eventos(lista_eventos):
    cleaned_list = []
    for texto in lista_eventos:
        # Replace newlines/hashtags and collapse multiple spaces
        t = texto.replace("\n", " ").replace("#", " ")
        t = " ".join(t.split())
        
        if t: # Only add if the string isn't empty after cleaning
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
    # Definimos los límites de tiempo
    inicio_rango = time(8, 1, 0)
    inicio_noche = time(19, 0, 0)
    
    fin_rango = time(16, 59, 0)
    
    nuevo_horario = time(17, 0, 0)

    
    # Verificamos las condiciones
    if row['Tipo'] == 'NORMAL' and inicio_rango <= row['InicioEvento'] <= fin_rango:
        return nuevo_horario
    
    if row['Tipo'] == 'CAMBIO_HORARIO' and inicio_noche > row['InicioEvento']:
        return inicio_noche
    
    
    return row['InicioEvento']

def ajustar_horario_fin(row):
    # Definimos los límites de tiempo
    inicio_rango = time(8, 1, 0)
    
    fin_rango = time(16, 59, 0)
    fin_noche = time(22, 0, 0)

    nuevo_horario = time(8, 0, 0)
    
    # Verificamos las condiciones
    # Nota: Asegúrate de que 'InicioEvento' ya sea un objeto datetime.time
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
    from transform_horas_extra import build_horas_extra_final
    horasExtra_final = build_horas_extra_final(horasExtra_validado)

Uso como script independiente (carga un CSV de prueba):
    python transform_horas_extra.py --csv MA.csv --key MA
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
        # Fila Excel: posición en el df (0-based) + 2 (header ocupa fila 1)
        excel_row = idx + 2
        tipo = str(df.at[idx, "Tipo"]).strip().upper()

        formula = f"=(C{excel_row}-B{excel_row})"

        if tipo in TIPOS_NORMAL:
            df.at[idx, "Normal"] = formula
        elif tipo in TIPOS_DESCANSO:
            df.at[idx, "Descanso"] = formula
        elif tipo in TIPOS_MADRUGADA:
            df.at[idx, "Madrugada"] = formula
        # Tipos no reconocidos quedan con celdas vacías

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



# ---------------------------------------------------------------------------
# PICKLE DATADABASE
# ---------------------------------------------------------------------------

#import pandas as pd
#import os

def download_he_db(result: pd.DataFrame, db_he_path: str) -> pd.DataFrame:
    """
    Downloads data from pickle DB into result DataFrame.
    For matching rows (id_ot + Num_Filas), copies 'Evento' and 'Cuenta' 
    columns from pickle into result.
    """
    if not os.path.exists(db_he_path):
        print(f">>> [download] DB not found at {db_he_path}, returning result unchanged.")
        return result

    db = pd.read_pickle(db_he_path)

    # Build a lookup index from the DB: (id_ot, Num_Filas) -> (Evento, Cuenta)
    db_indexed = db.set_index(['id_ot', 'Items'])[['Evento', 'Cuenta']]

    # Create a MultiIndex from result to find matches
    result_keys = list(zip(result['id_ot'], result['Items']))
    db_keys = set(db_indexed.index)

    matched = [(i, key) for i, key in enumerate(result_keys) if key in db_keys]

    if not matched:
        print(">>> [download] No matching rows found.")
        return result

    for row_idx, key in matched:
        result.at[row_idx, 'Evento'] = db_indexed.loc[key, 'Evento'].iloc[0]
        result.at[row_idx, 'Cuenta'] = db_indexed.loc[key, 'Cuenta'].iloc[0]
    
    print(f">>> [download] Copied values into {len(matched)} matching rows.")
    return result


def upload_he_db(result: pd.DataFrame, db_he_path: str) -> None:
    """
    Uploads data from result DataFrame into the pickle DB.
    - Matching rows (id_ot + Items): overwrites entire row in DB.
    - New rows (no match): appends to DB.
    Saves the updated DB back to db_he_path.
    """
    
    COLS = ['Cuadrilla', 'Responsable', 'Dia', 'Fecha', 'InicioEvento', 'FinEvento',
            'Duracion', 'Evento', 'Cuenta', 'id_ot', 'Items', 'Num_Filas',
            'Archivo', 'Tipo']

    if not os.path.exists(db_he_path):
        print(f">>> [upload] DB not found, creating new DB at {db_he_path}.")
        result[COLS].to_pickle(db_he_path)
        return

    db = pd.read_pickle(db_he_path)

    existing_keys = set(db.set_index(['id_ot', 'Items']).index)

    updated = 0
    appended = 0
    rows_to_add = []

    for _, row in result.iterrows():
        key = (row['id_ot'], row['Items'])
        if key in existing_keys:
            mask = (db['id_ot'] == key[0]) & (db['Items'] == key[1])
            db = db[~mask]  # drop old row
            updated += 1
        else:
            appended += 1
        rows_to_add.append(row)  # always add the new version

    db = pd.concat([db, pd.DataFrame(rows_to_add)], ignore_index=True)
    db = db[COLS].sort_values(['id_ot', 'Items']).reset_index(drop=True)
    db.to_pickle(db_he_path)
    print(f">>> [upload] Updated: {updated} rows | Appended: {appended} rows | "
          f">>> DB total: {len(db)} rows.")
    




# ---------------------------------------------------------------------------
# Ejecución como script independiente
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transforma horasExtra_validado -> horasExtra_final")
    parser.add_argument("--csv",    required=True, help="Ruta al CSV de entrada")
    parser.add_argument("--key",    default="df",  help="Clave a usar en el diccionario")
    parser.add_argument("--output", default=None,  help="Ruta CSV de salida (opcional)")
    args = parser.parse_args()

    df_cargado = pd.read_csv(args.csv)
    horasExtra_validado = {args.key: df_cargado}

    horasExtra_final = build_horas_extra_final(horasExtra_validado)

    resultado = horasExtra_final[args.key]
    print(f"\n>>> horasExtra_final['{args.key}'] — {len(resultado)} filas\n")
    print(resultado.to_string())

    if args.output:
        resultado.to_csv(args.output, index=False)
        print(f"\nGuardado en: {args.output}")


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

    # 1. Copy template → output
    shutil.copyfile(plantilla_path, output_path)

    # 2. Condition the DataFrame
    excel = df.copy()

    # Move last column to position 3
    reubica_cols = list(excel.columns)
    reubica_cols.insert(3, reubica_cols.pop())
    excel = excel[reubica_cols]

    # Data transformations
    excel['Fecha'] = excel['Fecha'].apply(lambda x: soloFecha_SinTimezone(x))
    excel['Duracion'] = excel['Duracion'] / (60 * 24)
    excel.loc[excel['Cuenta'] == 'se_labora', 'HorasExtra'] = 'No'
    excel = excel.iloc[index_natsorted(zip(excel['Archivo'], excel['Item']))]

    # 3. Write to workbook
    wb = load_workbook(output_path)
    sheet = wb.worksheets[sheet_index]

    # Clear existing data (preserve headers and formatting)
    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column):
        for cell in row:
            cell.value = None

    # Insert DataFrame rows
    for r_idx, row in enumerate(dataframe_to_rows(excel, index=False, header=False), 2):
        for c_idx, value in enumerate(row, 1):
            sheet.cell(row=r_idx, column=c_idx, value=value)

    # 4. Data validations
    max_row = sheet.max_row

    _validations = [
        ('=LISTAS!B$3:B$30', True,  ['B']),          # Cuenta
        ('=LISTAS!E$3:E$30', True,  ['J']),          # Tipo
        ('=LISTAS!G$3:G$30', True,  ['E']),          # Actividad
        ('=LISTAS!I$3:I$100', True, ['F']),          # Alimentador
        ('"Si,No"',          False, ['G','H','I','T']),  # Binario
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

    he = df.copy()
    he['Fecha'] = he['Fecha'].apply(lambda x: soloFecha_SinTimezone( x ))
    he['Date']  = he['Fecha'].apply(lambda x: toDateObject( x ))

    he = he[[
        'Cuadrilla', 'Iniciales', 'Dia', 'Date', 'Item',
        'InicioEvento', 'FinEvento', 'Duracion', 'Evento', 'Cuenta',
        'id_ot', 'Archivo',
    ]]

    # Parse + truncate to minute
    he['InicioEvento'] = pd.to_datetime(he['InicioEvento'])
    he['FinEvento']    = pd.to_datetime(he['FinEvento'])
    he['Inicio_min']   = he['InicioEvento'].dt.floor('min')
    he['Fin_min']      = he['FinEvento'].dt.floor('min')

    # Sort and detect breaks
    he = he.sort_values(['id_ot', 'InicioEvento']).reset_index(drop=True)

    new_group = (
        (he['id_ot'] != he['id_ot'].shift()) |
        (he['Inicio_min'] != he['Fin_min'].shift())
    )
    he['group'] = new_group.cumsum()

    # Aggregate
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

    # Clean aggregated lists (using existing utils functions)
    result['Evento'] = result['Evento'].apply(limpiar_lista_eventos)
    result['Cuenta'] = result['Cuenta'].apply(limpiar_cuentas)
    result['Cuenta'] = result['Cuenta'].apply(cuenta_to_dict)
    result['Items']  = result['Items'].apply(limpiar_items)

    # Extract time objects
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
    # 1. Filter
    he = df[df['HorasExtra'] == 'Si'].copy()

    # 2. Group
    result = agrupar_eventos(he)

    # 3. Classify
    result = etiquetar_tipo(result, reglas)

    # 4. Adjust start/end times (existing utils functions)
    result['InicioEvento'] = result.apply(ajustar_horario_inicio, axis=1)
    result['FinEvento']    = result.apply(ajustar_horario_fin, axis=1)

    # 5. Prepend OT number to event text
    result['Evento'] = result.apply(
        lambda row: f"OT # {row['id_ot']}. {row['Evento']}", axis=1
    )

    # 6. Split lunch on holidays
    result = dividir_almuerzo(result)

    return result


# ── DuckDB Sync Utilities ──────────────────────────────────────────────

def parse_cuenta(cuenta_str) -> dict:
    """Parse 'REDES:50, MEDIDORES:50' → {'REDES': 50, 'MEDIDORES': 50}.
       Single values like 'REDES' become {'REDES': 100}."""
    if not cuenta_str or (hasattr(cuenta_str, '__class__') and str(cuenta_str) == 'nan'):
        return {}
    result = {}
    for part in str(cuenta_str).split(','):
        part = part.strip()
        if ':' in part:
            key, val = part.split(':', 1)
            result[key.strip()] = int(val.strip())
        elif part:
            result[part.strip()] = 100
    return result


def parse_colaboradores(responsable_str) -> list:
    """Parse 'RS, JCR, VZH' → ['RS', 'JCR', 'VZH']."""
    if not responsable_str or (hasattr(responsable_str, '__class__') and str(responsable_str) == 'nan'):
        return []
    return [x.strip() for x in str(responsable_str).split(',') if x.strip()]


def parse_items(items_val) -> list:
    """Parse Items to a clean list. Handles "['11','12']" and "1, 2" formats."""
    if not items_val or (hasattr(items_val, '__class__') and str(items_val) == 'nan'):
        return []
    s = str(items_val).strip().strip('[]')
    return [x.strip().strip("'\"") for x in s.split(',') if x.strip()]


def _fecha_to_date(fecha_val):
    """Extract a clean date string from Delta Lake Fecha (ISO with TZ)."""
    s = str(fecha_val)[:10]  # '2026-06-01T00:00:00-05:00' → '2026-06-01'
    return s


def _time_str(time_val):
    """Normalize time values to 'HH:MM:SS' string for DuckDB TIME column."""
    if hasattr(time_val, 'strftime'):
        return time_val.strftime('%H:%M:%S')
    s = str(time_val).strip()
    # Handle '2026-01-01 17:40:00' format from Excel roundtrip
    if ' ' in s:
        s = s.split(' ')[-1]
    return s[:8]  # 'HH:MM:SS'


def sync_deltalake_to_duckdb(con, df, fecha_inicio, fecha_fin):
    """
    Sync a Delta Lake DataFrame into DuckDB actividades + participaciones.

    Strategy: delete existing records in the date range, then re-insert.
    This keeps DuckDB in sync with whatever Delta Lake has.

    Parameters
    ----------
    con : duckdb.DuckDBPyConnection
        Active MotherDuck/DuckDB connection.
    df : pd.DataFrame
        The Delta Lake DataFrame (same date range).
    fecha_inicio : date
        Start date of the sync range.
    fecha_fin : date
        End date of the sync range.

    Returns
    -------
    tuple (int, int)
        (n_actividades, n_participaciones) inserted.
    """
    f_inicio = str(fecha_inicio)
    f_fin = str(fecha_fin)

    # 1. Delete existing data in range (participaciones first — FK)
    con.execute("""
        DELETE FROM participaciones
        WHERE id_actividad IN (
            SELECT id_actividad FROM actividades
            WHERE Fecha BETWEEN $1 AND $2
        )
    """, [f_inicio, f_fin])

    con.execute(
        "DELETE FROM actividades WHERE Fecha BETWEEN $1 AND $2",
        [f_inicio, f_fin],
    )

    # 2. Insert row by row (need RETURNING for participaciones FK)
    n_act = 0
    n_part = 0

    for _, row in df.iterrows():
        colaboradores = parse_colaboradores(row.get('Iniciales'))
        cuenta = parse_cuenta(row.get('Cuenta'))
        items = parse_items(row.get('Items'))
        fecha = _fecha_to_date(row['Fecha'])
        inicio = _time_str(row['InicioEvento'])
        fin = _time_str(row['FinEvento'])

        result = con.execute("""
            INSERT INTO actividades
                (id_ot, Fecha, Cuadrilla, Colaboradores, InicioEvento, FinEvento,
                 Evento, Cuenta, Items, Num_Filas, Archivo, Tipo, Dia)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
            RETURNING id_actividad
        """, [
            int(row['id_ot']), fecha, row['Cuadrilla'], colaboradores,
            inicio, fin, row['Evento'], cuenta, items,
            int(row['Num_Filas']), row['Archivo'], row['Tipo'], row['Dia'],
        ])

        id_actividad = result.fetchone()[0]
        n_act += 1

        # 3. One participación per collaborator (default times = NULL → use group)
        for persona in colaboradores:
            con.execute("""
                INSERT INTO participaciones (id_actividad, Responsable)
                VALUES ($1, $2)
            """, [id_actividad, persona])
            n_part += 1

    return n_act, n_part