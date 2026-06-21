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


def parse_items_consolidado(items_val):
    """Parse Items from consolidado (handles both "['1','2']" and "1, 2")."""
    if not items_val or str(items_val) == 'nan':
        return []
    s = str(items_val).strip()
    # Try ast.literal_eval for "['1', '2']" format
    try:
        result = ast.literal_eval(s)
        if isinstance(result, list):
            return [str(x).strip() for x in result]
    except Exception:
        pass
    # Fallback: comma-separated "1, 2"
    return [x.strip().strip("'\"") for x in s.split(',') if x.strip()]


def parse_colaboradores(colab_str):
    """Parse 'AO, LP' → ['AO', 'LP']."""
    if not colab_str or str(colab_str) == 'nan':
        return []
    return [x.strip() for x in str(colab_str).split(',') if x.strip()]


def _to_time_str(val):
    """Normalize to 'HH:MM:SS' string for DuckDB TIME."""
    if hasattr(val, 'strftime'):
        return val.strftime('%H:%M:%S')
    s = str(val).strip()
    if ' ' in s:
        s = s.split(' ')[-1]
    return s[:8]