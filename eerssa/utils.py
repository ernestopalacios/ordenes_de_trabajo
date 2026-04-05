from datetime import datetime, date
import pandas as pd
import re


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
        return (time_difference.dt.total_seconds() / 60).astype(int)
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
    resultado = ", ".join(str_items)
    
    # 3. Handle empty lists for Excel clarity
    return resultado if resultado else "0"

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