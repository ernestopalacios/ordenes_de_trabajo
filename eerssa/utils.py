from datetime import datetime, date, time
import pandas as pd
import argparse
import re
import os

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
        result.at[row_idx, 'Evento'] = db_indexed.loc[key, 'Evento']#.iloc[0]
        result.at[row_idx, 'Cuenta'] = db_indexed.loc[key, 'Cuenta']#.iloc[0]
    
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
