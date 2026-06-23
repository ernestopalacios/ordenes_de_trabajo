# Export to Excel - Consolidado

In order to review the consolidado Dataframe on Excel we need to export it, after it has synced with DuckDB.

For this I have a "models/plantilla_consolidado_he.xlsx" file, on top of this plantilla file there are some aditional formatting done, as describe in this code:


```python
from openpyxl.styles import Font, PatternFill, Border, Side
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.formatting.rule import Rule

  
# ============================================================
# STYLE DEFINITIONS
# ============================================================

# 1. Red background, dark red text (Light Red Fill with Dark Red Text)
style_FinEvento = DifferentialStyle(
font=Font(color="9C0006"),
fill=PatternFill(bgColor="FFC7CE")
)
  
# 2. Yellow background, dark yellow text
style_sabado = DifferentialStyle(
font=Font(color="000000"),
fill=PatternFill(bgColor="FFEB9C")
)
  
# 2. Yellow background, dark yellow text
style_domingo = DifferentialStyle(
font=Font(color="000000"),
fill=PatternFill(bgColor="EEE31D")
)
  
  
# 3. Green background, dark green text
style_green = DifferentialStyle(
font=Font(color="006100"),
fill=PatternFill(bgColor="C6EFCE")
)
  
# 4. Dark red background, white text
style_red_error = DifferentialStyle(
font=Font(color="FFFFFF"),
fill=PatternFill(bgColor="C00000")
)
  
# 5. Red text, no fill
style_red_text = DifferentialStyle(
font=Font(color="000000"),
fill=PatternFill(bgColor="FF9D9D")
)
  
# 6. Bold black text, no fill
style_bold = DifferentialStyle(
font=Font(bold=True)
)
  
# 7. Blue background, white text
style_blue = DifferentialStyle(
font=Font(color="FFFFFF"),
fill=PatternFill(bgColor="4472C4")
)
  
  
# 7. Blue background, white text
style_mad = DifferentialStyle(
font=Font(color="000000"),
fill=PatternFill(bgColor="97B4E8")
)
  
  
# 8. White text, purple background
style_festivo = DifferentialStyle(
font=Font(color="FFFFFF"),
fill=PatternFill(bgColor="7030A0")
)
  
  
style_purple = DifferentialStyle(
font=Font(color="FFFFFF"),
fill=PatternFill(bgColor="FF8D8DB3")
)
  
  
  
# 9. White text, gray background
style_gray = DifferentialStyle(
font=Font(color="FFFFFF"),
fill=PatternFill(bgColor="808080")
)
  
# 10. Thick black bottom border
style_bottom_border = DifferentialStyle(
border=Border(
bottom=Side(style="thick", color="000000")
)
)
  
# ============================================================
# REGLAS DE FORMATO CONDICIONAL CORREGIDAS
# ============================================================
  
rules_informe_he = [
# 1. Regla fines de semana y Festivos (Púrpura)
# Usamos WEEKDAY($B6, 2) > 5 para detectar Sábados (6) y Domingos (7)
# Usamos SEARCH para que no importe si dice "Festivo" o "FESTIVO"
{
"formula": '=OR(WEEKDAY($B6, 2) > 5, ISNUMBER(SEARCH("FESTIVO", $J6)))',
"style": style_purple,
"range": "A6:J36",
},
  
# 2. Regla solo para festivos (Negrita)
{
"formula": '=ISNUMBER(SEARCH("FESTIVO", $J6))',
"style": style_bold,
"range": "A6:I36"
}
]
  
  
rules = [
# Rule 1 - Red bg: =CONTAR.SI(Revisar_primero!$B$2:$B$14, $D1)>0
{
"formula": '=COUNTIF(Revisar_primero!$B$2:$B$14,$D1)>0',
"style": style_festivo,
"range": "A1:N5000",
},
# Rule 2 - Yellow bg: =Y( O($A1="Zamora Z1 (Cuadrilla. Nro. 6)", $A1="Zamora Z1 (Cuadrilla. AP Nro. 4)", $A1="Zamora (Agencia)", $A1="Jefatura Zonal Zamora"), CONTAR.SI(Revisar_primero!$B$15:$B$18, $D1)>0 )
{
"formula": '=AND(OR($A1="Zamora Z1 (Cuadrilla. Nro. 6)",$A1="Zamora Z1 (Cuadrilla. AP Nro. 4)",$A1="Zamora (Agencia)",$A1="Jefatura Zonal Zamora"),COUNTIF(Revisar_primero!$B$15:$B$18,$D1)>0)',
"style": style_festivo,
"range": "A1:N5000",
},
# Rule 3 - Yellow bg: =Y( $A1="Yacuambi Z1 (Cuadrilla. Nro. 8)", CONTAR.SI(Revisar_primero!$B$19:$B$19, $D1)>0 )
{
"formula": '=AND($A1="Yacuambi Z1 (Cuadrilla. Nro. 8)",COUNTIF(Revisar_primero!$B$19:$B$19,$D1)>0)',
"style": style_festivo,
"range": "A1:N5000",
},
# Rule 4 - Yellow bg: =Y( O($A1="Yantzaza Z1 (Cuadrilla. Nro. 5)", $A1="Lineas Energizadas (Cuadrilla Nro.6)", $A1="Yantzaza (Agencia)"), CONTAR.SI(Revisar_primero!$B$20:$B$22, $D1)>0 )
{
"formula": '=AND(OR($A1="Yantzaza Z1 (Cuadrilla. Nro. 5)",$A1="Lineas Energizadas (Cuadrilla Nro.6)",$A1="Yantzaza (Agencia)"),COUNTIF(Revisar_primero!$B$20:$B$22,$D1)>0)',
"style": style_festivo,
"range": "A1:N5000",
},
# Rule 5 - Yellow bg: =Y( $A1="Paquisha Z1 (Cuadrilla. Nro. 10)", CONTAR.SI(Revisar_primero!$B$23:$B$23, $D1)>0 )
{
"formula": '=AND($A1="Paquisha Z1 (Cuadrilla. Nro. 10)",COUNTIF(Revisar_primero!$B$23:$B$23,$D1)>0)',
"style": style_festivo,
"range": "A1:N5000",
},
# Rule 6 - Yellow bg: =Y( $A1="Guayzimi Z1 (Cuadrilla. Nro. 7)", CONTAR.SI(Revisar_primero!$B$24:$B$24, $D1)>0 )
{
"formula": '=AND($A1="Guayzimi Z1 (Cuadrilla. Nro. 7)",COUNTIF(Revisar_primero!$B$24:$B$24,$D1)>0)',
"style": style_festivo,
"range": "A1:N5000",
},
# Rule 7 - Yellow bg: =Y( O($A1="El Pangui Z1 (Cuadrilla. Nro. 4)", $A1="El Pangui (Agencia)"), CONTAR.SI(Revisar_primero!$B$25:$B$26, $D1)>0 )
{
"formula": '=AND(OR($A1="El Pangui Z1 (Cuadrilla. Nro. 4)",$A1="El Pangui (Agencia)"),COUNTIF(Revisar_primero!$B$25:$B$26,$D1)>0)',
"style": style_festivo,
"range": "A1:N5000",
},
# Rule 8 - Yellow bg: =Y( O($A1="Gualaquiza Z1 (Cuadrilla. Nro. 3)", $A1="Gualaquiza (Agencia)"), CONTAR.SI(Revisar_primero!$B$27:$B$28, $D1)>0 )
{
"formula": '=AND(OR($A1="Gualaquiza Z1 (Cuadrilla. Nro. 3)",$A1="Gualaquiza (Agencia)"),COUNTIF(Revisar_primero!$B$27:$B$28,$D1)>0)',
"style": style_festivo,
"range": "A1:N5000",
},
# Rule 10 - Bold: =$C1="sábado"
{
"formula": '=$C1="sábado"',
"style": style_sabado,
"range": "A1:N5000",
},
# Rule 11 - Dark red bg: =$C1="domingo"
{
"formula": '=$C1="domingo"',
"style": style_domingo,
"range": "A1:N5000",
},
# Rule 14 - Blue bg: =Y($A1="Zamora Z1 (Cuadrilla. AP Nro. 4)", CONTAR.SI(Revisar_primero!$D$2:$D$114, $D1)>0)
{
"formula": '=AND($A1="Zamora Z1 (Cuadrilla. AP Nro. 4)",COUNTIF(Revisar_primero!$D$2:$D$114,$D1)>0)',
"style": style_blue,
"range": "A1:N5000",
},
# Rule 9 - Green bg: =$A1<>$A2
{
"formula": "=$A1<>$A2",
"style": style_bottom_border,
"range": "A1:N5000",
},
# Rule 12 - Red text: =$E1<>"" * (HORA($E1)<6 * (HORA($F1) + MINUTO($F1)/100) > 8)
{
"formula": '=AND($E1<>"",(HOUR($E1)<6),((HOUR($F1)+MINUTE($F1)/100)>6))',
"style": style_red_error,
"range": "A1:N5000",
},
# Rule 13 - Gray bg: =$F1<$E1
{
"formula": "=$F1<$E1",
"style": style_red_error,
"range": "A1:N5000",
},
# Rule 15 - Purple bg: =$E1<>"" Y (HORA($E1)<6)
{
"formula": '=AND($E1<>"",HOUR($E1)<6)',
"style": style_mad,
"range": "A1:N5000",
},
# Rule 16 - Bottom border: =Y(HORA($E1)<8, (HORA($F1)+MINUTO($F1)/100)>8)
{
"formula": "=AND(HOUR($E1)<8,(HOUR($F1)+MINUTE($F1)/100)>8)",
"style": style_red_text,
"range": "F1:F5000",
},
# Rule 17 - Bottom border: =Y(HORA($E1)>17, HORA($F1)>17)
{
"formula": "=AND(HOUR($E1)<17,HOUR($F1)>17)",
"style": style_red_text,
"range": "E1:E5000",
},
]
  
# FUNCTION TO APPLY RULES TO WORKSHEET
# ============================================================
  
def apply_conditional_formatting(ws):
"""Apply all conditional formatting rules to a worksheet."""
for r in rules:
rule = Rule(
type="expression",
formula=[r["formula"]],
dxf=r["style"],
stopIfTrue=False,
)
ws.conditional_formatting.add(r["range"], rule)
  
  
def apply_he_informe(ws):
"""Apply all conditional formatting rules to a worksheet."""
for r in rules_informe_he:
rule = Rule(
type="expression",
formula=[r["formula"]],
dxf=r["style"],
stopIfTrue=False,
)
ws.conditional_formatting.add(r["range"], rule)
``` 

And for the future Marimo cell conside this code to be migrated and adapted:

```python
# Genera el archivo de Excel "base_he_2026XXX" desde el Dataset `result`

# Copia el Template
shutil.copyfile(t_xls_consol_path, base_he_path)
print(f"Se ha copiado Excel para HE en {base_he_path}")

# Load the copied workbook
wb = load_workbook(base_he_path)

# Access the second sheet (0-based index; change if needed)
sheet = wb.worksheets[1]  # Or wb['result'] if named

# ===== Manejo de CUENTAS 

consolidado['Cuenta'] = consolidado['Cuenta'].apply( lambda x: eerssa.utils.dict_to_cuenta(x) )

# Insert DataFrame starting from row 2 (skip headers in DF)
for r_idx, row in enumerate(dataframe_to_rows(result, index=False, header=False), 2):
    for c_idx, value in enumerate(row, 1):
        sheet.cell(row=r_idx, column=c_idx, value=value)

apply_conditional_formatting( sheet )

# Save the modified workbook
wb.save(output_he)
print(f"✅ Se ha generado el archivo de EXCEL en -> {output_he}")
```

Once the file has been modified and saved on Excel i got this code for you to consider:

```python 

wb = load_workbook(output_he, data_only=False)
ws = wb["result"]
data = ws.values
cols = next(data)  
base = pd.DataFrame(data, columns=cols)
base = base.dropna(subset=['Cuadrilla'])

#base['Items'] = base['Items'].apply(lambda x: str(sorted(x)) if isinstance(x, list) else str(x))

# Convierte los valores de texto plano a diccionario
base['Cuenta'] = base['Cuenta'].apply(eerssa.utils.cuenta_to_dict)
base['id_ot']  = base['id_ot'].apply( lambda x: int(x) )

# Estandarizar Fechas y Horas a objetos nativos
base['Fecha'] = pd.to_datetime(base['Fecha']).dt.date
base['InicioEvento'] = pd.to_datetime(base['InicioEvento'], format='%H:%M:%S').dt.time
base['FinEvento'] = pd.to_datetime(base['FinEvento'], format='%H:%M:%S').dt.time
```

This base dataframe, will then be uploaded/updated to DuckDB as we can currently do. 

Keep in mind the dictionary transformations for Cuenta and Evento, verify this comply with current DuckDB schema. There may be already functions on he_helpers.py to be used. 

This style definitions should go to a separate file, I need to implement this functionality into Marimo.