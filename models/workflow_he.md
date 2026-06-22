
# Workflow de Horas Extra en Marimo

Voy a describir el flujo de datos que deseo para esta parte del proyecto. Empezamos por el Log de Eventos, que describen las actividades individuales y quienes las realizan, toma en cuenta que se encuentran en un Pandas Dataframe, las columnas relevantes son estas:

Importante, cada orden de trabajo individual describe las actividades en un único día, en ningun caso una orden de trabajo sobrepasa las 24 horas del día.

`id_ot` [ int64 ] Identificador único de cada orden de trabajo, la cual contiene varios eventos
`item`  [ int64 ] Numero entero que describe el número de evento dentro de cada orden de trabajo (ot)
`Cuenta` [ String ] Etiqueta del evento, cada evento tiene solamente una única etiqueta
`Evento` [ String ] Descripcion del evento, texto en el que el trabajador describe la actividad.
`Cuadrilla` [ String ] Nombre del grupo de trabajo de los colaboradores
`Dia` [ String ] Nombre del día de la semana
`Fecha` [ Date ] Objeto de python que contiene solamente la fecha sin componente de horas
`InicioEvento` [ Time ] Objeto de python que contiene solamente tiempos sin considerar la fecha
`FinEvento` [ Time ] Objeto de python que contiene solamente tiempos sin considerar la fecha
`Duracion` [ int64 ] Numero entero que describe la cantidad de minutos entre Inicio y Fin Evento
`HoraExtra` [ String ] Cadena de texto que describe si el evento es o no Hora Extra: 'Si', 'No'
`Iniciales` [String] Cadena de texto que describe las iniciales, separadas por comas de las personas que intervienen en el evento. 

La constante es `id_ot`, se puede cambiar la fecha, los horarios de inicio Fin, las iniciales de colaboradores, pero siempre será con la misma `id_ot` 

A partir de estos eventos, se los agrupa en base a las horas extra continuas, te mostrare las partes relevantes del código.

```python
  
# Aggregate

result = he.groupby('group').agg(

Cuadrilla = ('Cuadrilla', 'first'),

Colaboradores = ('Iniciales', 'first'),

Dia = ('Dia', 'first'),

Fecha = ('Date', 'first'),

InicioEvento = ('InicioEvento', 'min'),

FinEvento = ('FinEvento', 'max'),

Duracion = ('Duracion', 'sum'),

Evento = ('Evento', list),

Cuenta = ('Cuenta', list),

id_ot = ('id_ot', 'first'),

Items = ('Item', list),

Num_Filas = ('Evento', 'count'),

Archivo = ('Archivo', 'first'),

).reset_index(drop=True)


pass

return result
```

Existen otros procesos de limpieza que finalmente entregan el Dataframe llamado consolidado

Este Dataframe 'consolidado' debe ser presentado al usuario para que lo revise y modifique de ser necesario. En este punto es posible y común detectar errores en el registro de eventos, y que se modifiquen los eventos individuales, aguas arriba, si esto sucede no deseo que se pierdan los avances y modificaciones ya avanzados en aquellas partes de 'consolidado' que no cambian.

Por ello el flujo de trabajo es:
1. Genero un archivo consolidado desde las ordenes de trabajo
2. Descargo desde DuckDB y de existir coincidencias sobreescribo la información únicamente de 'Evento' y 'Cuenta' estos dos valores son los que modifica el usuario en este paso del Consolidado.
3. A partir del consolidado una vez descargadas las coincidencias, presento al usuario en un archivo Excel el dataframe consolidado para que se continue la revisión y la edición de los eventos. 
4. Con los cambios realizados reemplazo/actualizo en DuckDB los valores de Consolidado.
5. Hago una nueva presentación al usuario ya no el consolidado, sino los datos individuales para los ajustes finos de tiempo individuales nuevamente en Excel. 
6. Se lee estos cambios, se actualiza en la tabla individual
7. Finalmente cuando todo esta revisado y corregido se presenta el informe final individual.

En cualquier punto de este proceso debe ser posible volver y ajustar el archivo de Eventos individuales Original, y que vuelva a correr por todo el proceso. Modifico Deltalake a travez de Mairmo -> Excel -> Deltalake

## COMO IDENTIFICAR COINCIDENCIAS:

Para el paso (2) para saber si hay una coincidencia entre DuckDB y el Dataframe Consolidado, es necesario comparar mediante `id_ot` y la lista de `Items`, que vienen del proceso de agrupacion.

Si modifico la lista de items en la agrupación, no habrá coincidencia con los eventos almacenados en DuckDB y debo volver a editar estos eventos

MUY IMPORTANTE:
Si modifico la lista de iniciales se deben borrar de la persona que he eliminado. Este es un paso crucial para evitar errores del sistema. Es posible y ocurre a menudo que se modifiquen estas iniciales. Aquí también es importante aclarar, que hasta el momento, considero que todos han participado en una fila continua de Consolidado: la linea `Colaboradores = ('Iniciales', 'first'),` asigna la lista del primer evento a todos los siguientes, esto no siempre es verdad y en este punto del desarrollo dejo al revisor la responsabilidad de detectar esta condición.

Principalmente necesito de un revisor para resumir y consolidar los eventos y asignar las proporciones correctas a las Cuentas. 

## QUE NECESITO

Debemos concentrarnos en las consideraciones de diseño de los pasos 2. y 4. el resto de pasos los desarrollaremos luego. En otra LLM ya se ha diseñado la interacción entre Pandas Dataframe y DuckDB para mantener sincronizados los avances y cambios en la edición de 'Evento' y 'Cuenta'. 

Considera la base de Datos en DuckDB:

```sql
-- Master table: one row per group activity
CREATE TABLE IF NOT EXISTS actividades (
    id_actividad    INTEGER PRIMARY KEY DEFAULT nextval('seq_actividad'),
    id_ot           INTEGER,
    Fecha           DATE,
    Cuadrilla       VARCHAR,
    Colaboradores   VARCHAR[],            -- full group: ['RS', 'JCR', 'VZH']
    InicioEvento    TIME,                 -- group default start time
    FinEvento       TIME,                 -- group default end time
    Evento          VARCHAR,              -- activity description (shared)
    Cuenta          MAP(VARCHAR, INTEGER), -- account allocation: {'REDES': 50, 'ALUMBRADO': 50}
    Items           VARCHAR[],
    Num_Filas       INTEGER,
    Archivo         VARCHAR,
    Tipo            VARCHAR,
    Dia             VARCHAR,
    items_key       VARCHAR,        --como columna derivada para matching determinístico y un `UNIQUE` constraint:
);

-- Detail table: one row per person per activity
CREATE TABLE IF NOT EXISTS participaciones (
    id_actividad    INTEGER REFERENCES actividades(id_actividad),
    Responsable     VARCHAR,              -- single person initials: 'RS'
    InicioEvento    TIME,                 -- individual override (NULL = use group time)
    FinEvento       TIME,                 -- individual override (NULL = use group time)
    tiempo_ajustado BOOLEAN DEFAULT FALSE, -- TRUE = manually tweaked, protect from bulk overwrite
    PRIMARY KEY (id_actividad, Responsable)
);

-- 2. Unique constraint on the natural key
CREATE UNIQUE INDEX idx_actividad_natural ON actividades(id_ot, items_key);

-- items_key = sorted items joined by comma: "1,2,4"
-- Computed in Python before INSERT/UPDATE, NOT a generated column
-- (DuckDB generated columns can't be indexed)
```

Esta otra LLM genero las funciones en `he_helpers.py` desde la Linea 583 DuckDB Sync Utilities.

A PARTIR DE ESTE PUNTO: copiare su output literal para que lo revises, analices, y planifiques la implementación. Verifica si las funciones estan ya en `he_helpers.py`

IMPORTANTE: La interacción con la base de datos la realizaré personalmente ingresando los comandos en consola. Debes validar que los pasos son correctos. 

### Casos borde que el diseño resuelve

|Escenario|Qué pasa|
|---|---|
|**Primera ejecución** (DuckDB vacío)|Paso 2: 0 matches, todo auto-generado. Paso 4: todo INSERT.|
|**Re-ejecución sin cambios upstream**|Paso 2: todas coinciden, preserva edits. Paso 4: todo UPDATE, 0 diffs.|
|**Se corrige un evento upstream, misma agrupación**|Items no cambia → match → DuckDB Evento/Cuenta se preservan (ya editados).|
|**Se agrega/quita evento upstream, agrupación cambia**|Items cambia → sin match → nuevo auto-generado. El viejo queda huérfano → DELETE.|
|**Se quita una persona de Iniciales**|Paso 4 detecta diff → DELETE participación + sus ajustes de tiempo.|
|**Se agrega una persona**|Paso 4 detecta diff → INSERT participación (sin ajuste).|
|**Lunch-split: misma id_ot, dos filas**|`items_key` diferente (`"1,2"` vs `"3,4"`) → dos registros independientes. ✓|

### Lo que NO cubre este diseño (para resolver después)

1. **Paso 5-6**: Exportar/importar ajustes individuales de tiempo — lo haremos cuando completemos los pasos 2 y 4.
    
2. **Auditoría**: No hay historial de quién cambió qué. Podemos agregar `fecha_modificacion TIMESTAMP DEFAULT current_timestamp` si lo necesitas.
    
3. **Conflictos simultáneos**: Si dos personas editan el mismo consolidado, gana el último. Para tu caso de uso (un solo revisor) es suficiente.

---------

Voy a darte el código completo, primero las funciones utilitarias y luego las celdas Marimo en orden.

### 1. Funciones para `eerssa/utils.py`

```python
# ── Normalización de Items → clave canónica ──────────────────────────  
  
import ast  
  
  
def items_to_key(items_val) -> str:  
    """  
    Normaliza cualquier representación de Items en una clave canónica.  
      
    Maneja:  
      - Lista Python:       ['1', '2', '4']  
      - String de lista:    "['1', '2', '4']"  
      - Separado por comas: "1, 2"  
      - Entero/string solo: 4 o "4"  
      
    Retorna: "1,2,4" (ordenado numéricamente, sin espacios)  
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
  
  
# ── Conversiones de Cuenta ───────────────────────────────────────────  
  
def cuenta_consolidado_to_str(cuenta_val) -> str:  
    """  
    Convierte el formato del consolidado (lista de dicts con peso)  
    al formato legible para Excel.  
      
    [{'cuenta':'REDES','peso':1.0}, {'cuenta':'MEDIDORES','peso':1.0}]  
    → "REDES:50, MEDIDORES:50"  
      
    [{'cuenta':'MEDIDORES','peso':1.0}]  
    → "MEDIDORES:100"  
    """  
    if not cuenta_val or str(cuenta_val) == 'nan':  
        return ""  
      
    try:  
        items = ast.literal_eval(str(cuenta_val)) if isinstance(cuenta_val, str) else cuenta_val  
    except (ValueError, SyntaxError):  
        return str(cuenta_val)  
      
    if not isinstance(items, list):  
        return str(items)  
      
    # Si es lista de strings simples: ['REDES', 'MEDIDORES']  
    if items and isinstance(items[0], str):  
        total = len(items)  
        pct = round(100 / total)  
        return ", ".join(f"{c}:{pct}" for c in items)  
      
    # Lista de dicts: [{'cuenta': 'X', 'peso': 1.0}, ...]  
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
    Convierte string legible a MAP(VARCHAR, INTEGER) para DuckDB.  
      
    "REDES:50, MEDIDORES:50" → {'REDES': 50, 'MEDIDORES': 50}  
    "MEDIDORES"              → {'MEDIDORES': 100}  
    """  
    if not s or str(s) == 'nan':  
        return {}  
    s = str(s).strip()  
      
    # Intentar formato dict literal  
    if s.startswith('{'):  
        try:  
            return ast.literal_eval(s)  
        except (ValueError, SyntaxError):  
            pass  
      
    # Intentar formato lista de dicts (viene del consolidado crudo)  
    if s.startswith('['):  
        try:  
            items = ast.literal_eval(s)  
            if isinstance(items, list) and items:  
                if isinstance(items[0], dict):  
                    total = sum(d.get('peso', 0) for d in items)  
                    if total == 0:  
                        return {}  
                    return {d['cuenta']: round(d['peso'] / total * 100) for d in items}  
                # Lista de strings  
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
    Convierte MAP de DuckDB a string legible.  
      
    {'REDES': 50, 'MEDIDORES': 50} → "REDES:50, MEDIDORES:50"  
    """  
    if not m:  
        return ""  
    if isinstance(m, str):  
        return m  
    return ", ".join(f"{k}:{v}" for k, v in m.items())  
  
  
# ── Parsing de Colaboradores ─────────────────────────────────────────  
  
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
  
  
def parse_items(items_val):  
    """Normaliza Items a lista de strings."""  
    if isinstance(items_val, list):  
        return [str(x).strip() for x in items_val]  
    if items_val is None or (isinstance(items_val, float) and str(items_val) == 'nan'):  
        return []  
    s = str(items_val).strip()  
    try:  
        parsed = ast.literal_eval(s)  
        if isinstance(parsed, list):  
            return [str(x).strip() for x in parsed]  
    except (ValueError, SyntaxError):  
        pass  
    return [x.strip().strip("'\"") for x in s.split(',') if x.strip()]  
  
  
def _to_time_str(val) -> str:  
    """Normaliza a 'HH:MM:SS' para DuckDB TIME."""  
    if val is None or (isinstance(val, float) and str(val) == 'nan'):  
        return None  
    if hasattr(val, 'strftime'):  
        return val.strftime('%H:%M:%S')  
    s = str(val).strip()  
    if ' ' in s:  
        s = s.split(' ')[-1]  
    return s[:8]  
  
  
# ── PASO 2: Enriquecer consolidado desde DuckDB ─────────────────────  
  
def enriquecer_desde_duckdb(con, consolidado, fecha_inicio, fecha_fin):  
    """  
    Para cada fila en consolidado, busca coincidencia en DuckDB por (id_ot, items_key).  
    Si existe: sobreescribe Evento y Cuenta con los valores editados de DuckDB.  
    Si no existe: mantiene los valores auto-generados.  
      
    Retorna  
    -------  
    pd.DataFrame — consolidado con Evento/Cuenta enriquecidos  
    int          — cantidad de coincidencias encontradas  
    """  
    result = consolidado.copy()  
  
    # Computar items_key en consolidado  
    result['items_key'] = result['Items'].apply(items_to_key)  
  
    # Traer actividades existentes en el rango  
    duck_df = con.execute("""  
        SELECT id_ot, items_key, Evento, Cuenta  
        FROM actividades  
        WHERE Fecha BETWEEN $1 AND $2  
    """, [str(fecha_inicio), str(fecha_fin)]).df()  
  
    if duck_df.empty:  
        # Convertir Cuenta al formato string legible  
        result['Cuenta'] = result['Cuenta'].apply(cuenta_consolidado_to_str)  
        result.drop(columns='items_key', inplace=True)  
        return result, 0  
  
    # Lookup: (id_ot, items_key) → {Evento, Cuenta}  
    duck_lookup = {}  
    for _, row in duck_df.iterrows():  
        key = (int(row['id_ot']), row['items_key'])  
        duck_lookup[key] = {  
            'Evento': row['Evento'],  
            'Cuenta': row['Cuenta'],  # dict desde MAP  
        }  
  
    n_matches = 0  
    for idx, row in result.iterrows():  
        key = (int(row['id_ot']), row['items_key'])  
        if key in duck_lookup:  
            result.at[idx, 'Evento'] = duck_lookup[key]['Evento']  
            result.at[idx, 'Cuenta'] = map_to_cuenta_str(duck_lookup[key]['Cuenta'])  
            n_matches += 1  
        else:  
            # Sin coincidencia → convertir formato auto-generado  
            result.at[idx, 'Cuenta'] = cuenta_consolidado_to_str(row['Cuenta'])  
  
    result.drop(columns='items_key', inplace=True)  
    return result, n_matches  
  
  
# ── PASO 4: Sincronizar consolidado editado → DuckDB ────────────────  
  
def sincronizar_a_duckdb(con, consolidado_editado, fecha_inicio, fecha_fin):  
    """  
    Upsert del consolidado editado hacia DuckDB.  
      
    - UPDATE filas existentes (match por id_ot + items_key)  
      - Diff de Colaboradores → add/remove participaciones  
      - Preserva tiempo_ajustado en participaciones que sobreviven  
    - INSERT filas nuevas + sus participaciones  
    - DELETE huérfanos en el rango (ya no están en consolidado)  
      - Cascada a participaciones  
      
    Retorna  
    -------  
    dict: {updated, inserted, deleted, part_added, part_removed}  
    """  
    stats = {  
        'updated': 0, 'inserted': 0, 'deleted': 0,  
        'part_added': 0, 'part_removed': 0,  
    }  
  
    df = consolidado_editado.copy()  
    df['items_key'] = df['Items'].apply(items_to_key)  
  
    # Existentes en DuckDB dentro del rango  
    existing = con.execute("""  
        SELECT id_actividad, id_ot, items_key, Colaboradores  
        FROM actividades  
        WHERE Fecha BETWEEN $1 AND $2  
    """, [str(fecha_inicio), str(fecha_fin)]).df()  
  
    existing_lookup = {}  
    for _, row in existing.iterrows():  
        key = (int(row['id_ot']), row['items_key'])  
        existing_lookup[key] = {  
            'id_actividad': int(row['id_actividad']),  
            'Colaboradores': set(row['Colaboradores'] or []),  
        }  
  
    touched_ids = set()  
  
    for _, row in df.iterrows():  
        key = (int(row['id_ot']), row['items_key'])  
        new_colabs = parse_colaboradores(row['Colaboradores'])  
        new_colabs_set = set(new_colabs)  
        cuenta = cuenta_str_to_map(row['Cuenta'])  
        fecha = str(row['Fecha'])[:10]  
        inicio = _to_time_str(row['InicioEvento'])  
        fin = _to_time_str(row['FinEvento'])  
        items_list = parse_items(row['Items'])  
  
        if key in existing_lookup:  
            # ── UPDATE ──  
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
                inicio, fin, row.get('Tipo', ''), row['Cuadrilla'],  
                row['Dia'], int(row['Num_Filas']), row['Archivo'],  
                int(row.get('Duracion', 0)), id_act,  
            ])  
            stats['updated'] += 1  
  
            # ── DIFF Colaboradores ──  
            old_colabs = info['Colaboradores']  
  
            # Eliminar personas que ya no están  
            for persona in (old_colabs - new_colabs_set):  
                con.execute("""  
                    DELETE FROM participaciones  
                    WHERE id_actividad = $1 AND Responsable = $2  
                """, [id_act, persona])  
                stats['part_removed'] += 1  
  
            # Agregar personas nuevas  
            for persona in (new_colabs_set - old_colabs):  
                con.execute("""  
                    INSERT INTO participaciones (id_actividad, Responsable)  
                    VALUES ($1, $2)  
                """, [id_act, persona])  
                stats['part_added'] += 1  
  
        else:  
            # ── INSERT nueva actividad ──  
            result = con.execute("""  
                INSERT INTO actividades  
                    (id_ot, Fecha, Cuadrilla, Colaboradores,  
                     InicioEvento, FinEvento, Duracion,  
                     Evento, Cuenta, Items, items_key,  
                     Num_Filas, Archivo, Tipo, Dia)  
                VALUES ($1, $2::DATE, $3, $4,  
                        $5::TIME, $6::TIME, $7,  
                        $8, $9, $10, $11,  
                        $12, $13, $14, $15)  
                RETURNING id_actividad  
            """, [  
                int(row['id_ot']), fecha, row['Cuadrilla'], new_colabs,  
                inicio, fin, int(row.get('Duracion', 0)),  
                row['Evento'], cuenta, items_list, row['items_key'],  
                int(row['Num_Filas']), row['Archivo'],  
                row.get('Tipo', ''), row['Dia'],  
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
  
    # ── DELETE huérfanos ──  
    all_existing_ids = {info['id_actividad'] for info in existing_lookup.values()}  
    orphan_ids = all_existing_ids - touched_ids  
  
    for oid in orphan_ids:  
        con.execute("DELETE FROM participaciones WHERE id_actividad = $1", [oid])  
        con.execute("DELETE FROM actividades WHERE id_actividad = $1", [oid])  
    stats['deleted'] = len(orphan_ids)  
  
    return stats  
```
---

### 2. Cambio de esquema DuckDB (ejecutar una vez)

```sql

-- Agregar columna items_key y Duracion si no existen  
ALTER TABLE actividades ADD COLUMN IF NOT EXISTS items_key VARCHAR;  
ALTER TABLE actividades ADD COLUMN IF NOT EXISTS Duracion INTEGER;  
  
-- Índice único sobre la clave natural  
CREATE UNIQUE INDEX IF NOT EXISTS idx_actividad_natural  
    ON actividades(id_ot, items_key);  
```
---

### 3. Celdas Marimo

```python
# ═══════════════════════════════════════════════════════════════════════  
# CELDA: Paso 2 — Enriquecer consolidado desde DuckDB  
# ═══════════════════════════════════════════════════════════════════════  
# Reactiva: se ejecuta automáticamente cuando 'consolidado' cambia.  
# Es lectura pura, no modifica DuckDB.  
  
@app.cell(hide_code=True)  
def paso_2_enriquecer(con, consolidado, date_picker, eerssa, mo):  
    _inicio, _fin = date_picker.value  
  
    consolidado_enriquecido, n_coincidencias = eerssa.utils.enriquecer_desde_duckdb(  
        con, consolidado, _inicio, _fin  
    )  
  
    _total = len(consolidado_enriquecido)  
    _nuevos = _total - n_coincidencias  
  
    mo.callout(  
        mo.md(  
            f"**Paso 2 — Enriquecimiento desde DuckDB**<br>"  
            f"📊 Total: `{_total}` filas · "  
            f"🔗 Coincidencias: `{n_coincidencias}` (ediciones preservadas) · "  
            f"🆕 Nuevos: `{_nuevos}` (auto-generados)"  
        ),  
        kind="info" if n_coincidencias > 0 else "neutral",  
    )  
  
    return (consolidado_enriquecido,)  
```
```python
# ═══════════════════════════════════════════════════════════════════════  
# CELDA: Vista previa del consolidado enriquecido  
# ═══════════════════════════════════════════════════════════════════════  
  
@app.cell(hide_code=True)  
def preview_consolidado(consolidado_enriquecido, mo):  
    mo.md("### Vista previa del Consolidado")  
  
    # Mostrar columnas relevantes para revisión rápida  
    _cols_preview = [  
        'id_ot', 'Fecha', 'Cuadrilla', 'Colaboradores',  
        'InicioEvento', 'FinEvento', 'Duracion',  
        'Cuenta', 'Items', 'Tipo',  
    ]  
    _cols = [c for c in _cols_preview if c in consolidado_enriquecido.columns]  
  
    mo.ui.table(  
        consolidado_enriquecido[_cols],  
        selection=None,  
        label=f"{len(consolidado_enriquecido)} actividades consolidadas",  
    )  
    return  
```
```python
# ═══════════════════════════════════════════════════════════════════════  
# CELDA: Paso 3 — Exportar consolidado a Excel (GATED)  
# ═══════════════════════════════════════════════════════════════════════  
  
@app.cell(hide_code=True)  
def paso_3_controles(mo):  
    btn_exportar_consol = mo.ui.run_button(  
        label="📤 Exportar Consolidado a Excel"  
    )  
    mo.md(  
        f"### Paso 3 — Exportar para revisión\n"  
        f"Exporte el consolidado enriquecido a Excel para editar "  
        f"**Evento** y **Cuenta**.\n\n{btn_exportar_consol}"  
    )  
    return (btn_exportar_consol,)  
  
  
@app.cell(hide_code=True)  
def paso_3_exportar(  
    btn_exportar_consol, consolidado_enriquecido, eerssa, mo, os, datetime  
):  
    mo.stop(  
        not btn_exportar_consol.value,  
        mo.callout(mo.md("⏸️ Presione el botón para exportar."), kind="warn"),  
    )  
  
    _today = datetime.today().strftime('%Y%m%d')  
    consolidado_xlsx = os.path.join('reporte', f"consolidado_he_{_today}.xlsx")  
  
    # Exportar — adapta esto a tu función existente o usa pandas directo  
    consolidado_enriquecido.to_excel(consolidado_xlsx, index=False, sheet_name="CONSOLIDADO")  
  
    mo.callout(  
        mo.md(  
            f"✅ **Excel exportado:** `{consolidado_xlsx}`<br>"  
            f"Edite las columnas **Evento** y **Cuenta** en Excel.<br>"  
            f"Formato de Cuenta: `REDES:50, MEDIDORES:50`"  
        ),  
        kind="success",  
    )  
    return (consolidado_xlsx,)  
```
```python
# ═══════════════════════════════════════════════════════════════════════  
# CELDA: Paso 3b — Leer Excel editado (GATED)  
# ═══════════════════════════════════════════════════════════════════════  
  
@app.cell(hide_code=True)  
def paso_3b_controles(mo):  
    btn_leer_consol = mo.ui.run_button(label="👓 Cargar cambios desde Excel")  
    mo.md(  
        f"### Paso 3b — Cargar Excel editado\n"  
        f"Una vez terminada la revisión en Excel:\n\n{btn_leer_consol}"  
    )  
    return (btn_leer_consol,)  
  
  
@app.cell(hide_code=True)  
def paso_3b_leer(btn_leer_consol, consolidado_xlsx, mo, pd):  
    mo.stop(  
        not btn_leer_consol.value,  
        mo.callout(mo.md("⏸️ Presione el botón para cargar el Excel editado."), kind="warn"),  
    )  
  
    consolidado_editado = pd.read_excel(consolidado_xlsx, sheet_name="CONSOLIDADO")  
  
    # Asegurar tipos  
    consolidado_editado['id_ot'] = consolidado_editado['id_ot'].astype(int)  
    consolidado_editado['Fecha'] = pd.to_datetime(consolidado_editado['Fecha']).dt.date  
  
    mo.callout(  
        mo.md(f"✅ **Excel cargado:** `{len(consolidado_editado)}` filas"),  
        kind="success",  
    )  
  
    # Preview de columnas editables  
    _preview_cols = ['id_ot', 'Colaboradores', 'Evento', 'Cuenta', 'Items', 'Tipo']  
    _cols = [c for c in _preview_cols if c in consolidado_editado.columns]  
    mo.ui.table(consolidado_editado[_cols], selection=None)  
  
    return (consolidado_editado,)  
```
```python
# ═══════════════════════════════════════════════════════════════════════  
# CELDA: Paso 4 — Sincronizar a DuckDB (GATED — DANGER)  
# ═══════════════════════════════════════════════════════════════════════  
  
@app.cell(hide_code=True)  
def paso_4_controles(mo):  
    btn_sync_duck = mo.ui.run_button(  
        label="🦆 Sincronizar a DuckDB", kind="danger"  
    )  
    mo.md(  
        f"### Paso 4 — Actualizar DuckDB\n"  
        f"⚠️ Esta operación actualiza, inserta y elimina registros en DuckDB.\n\n"  
        f"{btn_sync_duck}"  
    )  
    return (btn_sync_duck,)  
  
  
@app.cell(hide_code=True)  
def paso_4_sync(btn_sync_duck, con, consolidado_editado, date_picker, eerssa, mo):  
    mo.stop(  
        not btn_sync_duck.value,  
        mo.callout(mo.md("⏸️ Revise los datos antes de sincronizar."), kind="warn"),  
    )  
  
    _inicio, _fin = date_picker.value  
  
    stats = eerssa.utils.sincronizar_a_duckdb(  
        con, consolidado_editado, _inicio, _fin  
    )  
  
    _parts = []  
    if stats['updated']:  
        _parts.append(f"🔄 Actualizadas: `{stats['updated']}`")  
    if stats['inserted']:  
        _parts.append(f"🆕 Insertadas: `{stats['inserted']}`")  
    if stats['deleted']:  
        _parts.append(f"🗑️ Eliminadas: `{stats['deleted']}`")  
    if stats['part_added']:  
        _parts.append(f"👤+ Participaciones añadidas: `{stats['part_added']}`")  
    if stats['part_removed']:  
        _parts.append(f"👤− Participaciones eliminadas: `{stats['part_removed']}`")  
  
    mo.callout(  
        mo.md(  
            f"**✅ DuckDB sincronizado**<br>"  
            + "<​br>".join(_parts)  
        ),  
        kind="success",  
    )  
    return  
```
---

### Flujo completo en el notebook

|Celda|Tipo|Depende de|
|---|---|---|
|`consolidado`|Reactiva|`df`, proceso de agrupación|
|**paso_2_enriquecer**|Reactiva|`consolidado`, `con`, `date_picker`|
|**preview_consolidado**|Reactiva|`consolidado_enriquecido`|
|**paso_3_exportar**|🔘 Gated|`consolidado_enriquecido`|
|**paso_3b_leer**|🔘 Gated|`consolidado_xlsx`|
|**paso_4_sync**|🔴 Gated+Danger|`consolidado_editado`, `con`|

### Notas de integración

- **Paso 2 es reactivo a propósito** — si cambias los eventos upstream y `consolidado` se regenera, automáticamente busca tus ediciones previas en DuckDB y las preserva. Cero pérdida de trabajo.
    
- **El `items_key`** se calcula en Python y se almacena en DuckDB. No es un generated column porque DuckDB no puede indexar esos.
    
- **El diff de Colaboradores** en el Paso 4 borra la participación completa (incluyendo ajustes de tiempo) cuando quitas a alguien. Esto es intencional — si la persona no estuvo, sus ajustes no aplican.
    
- **El formato de Cuenta en Excel** es `REDES:50, MEDIDORES:50`. Si alguien escribe solo `REDES`, `cuenta_str_to_map` lo interpreta como `{'REDES': 100}`.
    
- Falta agregar `Duracion` al `ALTER TABLE` si no la tienes — ya está incluida en el SQL de arriba.