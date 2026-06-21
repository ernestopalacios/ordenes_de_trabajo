
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

