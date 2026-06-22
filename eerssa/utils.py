import json
from pathlib import Path
import pandas as pd


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
    path_festivos = 'models/plantilla_consolidado_he.xlsx'
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
        usecols='D',      # Only columns D
        header=0            # First row as column names
    ).squeeze("columns") # Turns the 1-column DataFrame into a Series
    
    festivos['Fecha'] = pd.to_datetime(festivos['Fecha']).dt.date
    dict_todos = festivos[festivos['Aplica'] == 'TODOS'].set_index('Fecha')['Etiqueta'].to_dict()
    dict_especificos = festivos[festivos['Aplica'] != 'TODOS'].set_index(['Fecha', 'Aplica'])['Etiqueta'].to_dict()
    set_noche = set(pd.to_datetime(noche.dropna()).dt.date)

    return { 'TODOS':dict_todos, 'ESPECIFICOS':dict_especificos, 'NOCHE':set_noche}


# ── String / Timezone helpers ──────────────────────────────────────────────────

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