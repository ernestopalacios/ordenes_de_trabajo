## Lets generate the final report

There is one step we are going to address later, for now, I need to produce the final report based of 'plantilla_informe_he.xls' In order to generate this final report consider the following code:

Dataframe `base` We need to re-calculate it,  directly from DuckDB, taking into account the second table `participaciones` (we'll deal later with edits in this table). It needs to have the same schema as `consolidado_editado` The functions should go into `he_helpers.py`

Remember to change variable `wb` to local `_wb`, the printf should be callouts:

```python
# Dividir para cada persona
from eerssa import organizar as gdrive # download sheet from Google Drive

# Convertir strings separados por comas de vuelta a listas nativas de Python
for col in ['Colaboradores']:
    base_div = base.copy() 
    base_div[col] = base_div[col].apply(lambda x: str(x).split(", ") if pd.notnull(x) else [])

# 1. Extract all unique labels (initials) from base lists
unique_Colaboradoress = base_div['Colaboradores'].explode().dropna().unique()

# 3. Initialize a dictionary to map names to DataFrames
horasExtra_todos = {}

# Multiplier map for each Tipo
TIPO_MULTIPLIER = {
    "NORMAL":          1.5,
    "MAD":             2.0,
    "FESTIVO":         2.0,
    "DESCANSO":        2.0,
    "CANTONIZACION":   2.0,
    "CAMBIO_HORARIO":  0.25,
}

# Funcion que Pivotea los horarios
def pivot_time_events(filtered_df):
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

        # Aggregate Tipo values in order into a list
        base_row['Lista_tipos'] = group['Tipo'].tolist()
        base_row['Lista_Eventos'] = group['Evento'].tolist()
        base_row['Lista_Eventos'] = ' '.join(group['Evento'].astype(str).tolist())
        result_rows.append(base_row)
        
    result = pd.DataFrame(result_rows)

    cols = result.columns.tolist()
    inicio_pos = cols.index('InicioEvento')
    new_cols = ['Extra_1', 'Fin_1', 'Extra_2', 'Fin_2', 'Extra_3', 'Fin_3']
    cols_clean = [c for c in cols if c not in new_cols + ['InicioEvento', 'FinEvento', '_occurrence']]
    final_cols = cols_clean[:inicio_pos] + new_cols + cols_clean[inicio_pos:]

    return result[final_cols].reset_index(drop=True)


def build_sobretiempos_formula(lista_tipos, row_i, fila_offset=6):
    """
    Builds an Excel SUM formula for overtime based on Lista_tipos.
    Each tipo maps to a multiplier. Pairs are (C,D), (E,F), (G,H).
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

# Funcion que rellena las fechas
def complete_date_range(df_pivot, reporte_inicia, reporte_finaliza):
    """
    Completa el DataFrame con todas las fechas entre reporte_inicia y reporte_finaliza.
    Las fechas sin datos se rellenan con NaN excepto la columna 'Fecha'.
    """
    all_dates = pd.DataFrame({
        'Fecha': pd.date_range(reporte_inicia, reporte_finaliza)
    })

    df_pivot['Fecha'] = pd.to_datetime(df_pivot['Fecha'])
    result = all_dates.merge(df_pivot, on='Fecha', how='left')

    return result

# 4. Loop through each unique person
for person in unique_Colaboradoress:

    # 5. Filter base DataFrame to keep only rows where the person is in the list
    filtered_df = base_div[
        base_div['Colaboradores'].apply(lambda x: person in x if isinstance(x, list) else False)
    ].copy()

    # 6. Reset index so rows are numbered from 0
    filtered_df = filtered_df.sort_values(by=['Fecha', 'InicioEvento'])
    filtered_df = filtered_df.reset_index(drop=True)

    # 7. PIVOTEAR los horarios
    filtered_df = pivot_time_events(filtered_df)

    # 8. Rellenar las fechas vacias
    filtered_df = complete_date_range(filtered_df, reporte_inicia, reporte_finaliza)

    # 9. Recalculate formulas based on FINAL row positions
    fila_inicial_xl = 6

    filtered_df['Duracion'] = [
        f'=SUM(D{i + fila_inicial_xl}-C{i + fila_inicial_xl}, F{i + fila_inicial_xl}-E{i + fila_inicial_xl}, H{i + fila_inicial_xl}-G{i + fila_inicial_xl})'
        for i in range(len(filtered_df))
    ]

    filtered_df['Sobretiempos'] = [
        build_sobretiempos_formula(lista_tipos, i, fila_inicial_xl)
        if isinstance(lista_tipos, list) else ''
        for i, lista_tipos in enumerate(filtered_df['Lista_tipos'], start=0)
    ]

    # 10. Store the filtered DataFrame
    horasExtra_todos[person] = filtered_df[
        [
            "Dia",
            "Fecha",
            "Extra_1",
            "Fin_1",
            "Extra_2",
            "Fin_2",
            "Extra_3",
            "Fin_3",
            "Duracion",
            #"Evento",
            "Lista_Eventos",
            "Sobretiempos",
        ]
    ]

print(list(horasExtra_todos.keys()))


df_datos_cuadrilla = gdrive.get_gsheet_df()


# ── Paths ──────────────────────────────────────────────────────────────────────
TEMPLATE_PATH = "models/plantilla_informe_he.xlsx"
OUTPUT_PATH = "reporte/00_Informe_HE_todos.xlsx"
TEMPLATE_SHEET = "HORAS_EXTRA"
START_ROW = 6
START_COL = 2  # Column B

# ── Copy template to output ────────────────────────────────────────────────────
shutil.copy2(TEMPLATE_PATH, OUTPUT_PATH)

# ── Load workbook copy ─────────────────────────────────────────────────────────
wb = load_workbook(OUTPUT_PATH)
template_ws = wb[TEMPLATE_SHEET]

# ── Create one sheet per dataframe in the dictionary ───────────────────────────
for key, df_pivot in horasExtra_todos.items():
    # Copy template sheet
    new_ws = wb.copy_worksheet(template_ws)
    new_ws.title = str(key)
    
    # ── Consultar datos de la cuadrilla ────────────────────────────────────────
    match = df_datos_cuadrilla[df_datos_cuadrilla['INICIALES'] == key]
    
    if not match.empty:
        nombre_completo = match['NOMBRE'].iloc[0]
        nombre_cuadrilla = match['CUADRILLA_CORTO'].iloc[0]
        
        new_ws['H2'] = nombre_completo
        new_ws['H3'] = nombre_cuadrilla
    else:
        new_ws['H2'] = "No registrado"
        new_ws['H3'] = "No registrado"

    # Omit first dataframe column
    df_to_export = df_pivot.iloc[:, 1:]

    # ── Find "Evento" column position (if it exists) ──────────────────────────
    eventos_col_idx = None
    if 'Lista_Eventos' in df_to_export.columns:
        eventos_col_idx = df_to_export.columns.get_loc('Lista_Eventos')

    # Write data starting at row 6, column B
    for row_idx, row_data in enumerate(df_to_export.itertuples(index=False), start=START_ROW):
        for col_idx, value in enumerate(row_data, start=START_COL):
            new_ws.cell(row=row_idx, column=col_idx, value=value)

        # ── Adjust row height based on "Evento" character length ──────────────
        if eventos_col_idx is not None:
            eventos_value = row_data[eventos_col_idx]
            char_len = len(str(eventos_value)) if pd.notna(eventos_value) else 0

            if char_len >= 430:
                new_ws.row_dimensions[row_idx].height = 60
            elif char_len >= 286:
                new_ws.row_dimensions[row_idx].height = 40
            elif char_len >= 151:
                new_ws.row_dimensions[row_idx].height = 27
                
            # else: < 151 → no modification

    apply_he_informe(new_ws)

wb.save(OUTPUT_PATH)
print(f"Workbook saved to: {OUTPUT_PATH}")
```