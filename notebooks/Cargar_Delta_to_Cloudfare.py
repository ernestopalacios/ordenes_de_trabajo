import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Migración Deltalake: local ➡️ R2 Cloudfare

    ###Fecha: 17-06-2026.
    ###Autor: Ernesto Palacios

    Script para la migración de datos desde Delta Lake Local hacia CloudFare R2

    ## Version inicial de la Migración: dt.version() ☘️ `5909`
    """)
    return


@app.cell
def _():
    import marimo as mo
    import os
    import pandas as pd
    from deltalake import DeltaTable, write_deltalake

    import sys
    from pathlib import Path

    # El notebook está en notebooks/, el proyecto en el directorio padre
    PROJECT_ROOT = Path.cwd().parent  # sube un nivel desde notebooks/
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from eerssa.utils import load_r2_credentials


    return (
        DeltaTable,
        PROJECT_ROOT,
        load_r2_credentials,
        mo,
        pd,
        write_deltalake,
    )


@app.cell
def _(PROJECT_ROOT, load_r2_credentials):
    # ── Carga de Credenciales ────────────────────────────────────────────
    LOCAL_DELTA_PATH = "/home/vlad/delta_V30"
    CREDS_PATH = PROJECT_ROOT / "secrets" / "r2_credentials.json"
    creds = load_r2_credentials(str(CREDS_PATH))
    # ── Configuración de rutas ────────────────────────────────────────────
    LOCAL_DELTA_PATH = "/home/vlad/delta_V30"
    R2_BUCKET = "delta-v30"
    R2_ACCOUNT_ID = creds["account_id"]
    R2_ACCESS_KEY = creds["access_key"]
    R2_SECRET_KEY = creds["secret_key"]
    R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    # ── Configuración de storage options para R2 ────────────────────────────
    storage_options = {
        "AWS_ENDPOINT_URL": R2_ENDPOINT,
        "AWS_ACCESS_KEY_ID": R2_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": R2_SECRET_KEY,
        "AWS_REGION": "auto",
        "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
    }

    print("✅ Configuración cargada.")
    print(f"   Ruta local : {LOCAL_DELTA_PATH}")
    print(f"   R2 bucket  : {R2_BUCKET}")
    print(f"   R2 endpoint: {R2_ENDPOINT}")
    return LOCAL_DELTA_PATH, R2_BUCKET, storage_options


@app.cell
def _(DeltaTable, LOCAL_DELTA_PATH):
    # ============================================================================
    # SECCIÓN 2: Cargar la tabla Delta local e inspeccionar
    # ============================================================================
    dt = DeltaTable(LOCAL_DELTA_PATH)

    # ── Ver esquema ────────────────────────────────────────────────────────────
    print("📋 Esquema de la tabla local:")
    print(dt.schema())

    # ── Cargar a Pandas ─────────────────────────────────────────────────────────
    df = dt.to_pandas()
    print(f"\n📊 Registros cargados: {len(df):,}")
    print(f"   Columnas: {list(df.columns)}")
    print(f"\n🔍 Tipos de datos:")
    print(df.dtypes)
    print(f"\n👀 Primeras 5 filas:")
    return (df,)


@app.cell
def _(df, display, pd):
    # ============================================================================
    # SECCIÓN 3: Explorar la columna "Fecha" y sus valores únicos
    # ============================================================================
    print(f"🔍 Tipo actual de 'Fecha': {df['Fecha'].dtype}")
    print(f"\n📅 Muestra de valores en 'Fecha':")
    print(df['Fecha'].dropna().head(10).to_list())

    # ── Ver si hay nulos ──────────────────────────────────────────────────────────
    nulos_fecha = df['Fecha'].isna().sum()
    print(f"\n⚠️  Valores nulos en 'Fecha': {nulos_fecha}")

    # ── Intentar parsear como datetime ────────────────────────────────────────────
    # El formato parece ser ISO 8601 con timezone: "2022-02-11T00:00:00-05:00"
    df['Fecha_dt'] = pd.to_datetime(df['Fecha'], errors='coerce')
    fallos = df['Fecha_dt'].isna().sum() - nulos_fecha
    print(f"\n❌ Filas que no se pudieron parsear: {fallos}")

    if fallos > 0:
        print("\n🔎 Filas problemáticas:")
        display(df[df['Fecha'].notna() & df['Fecha_dt'].isna()][['Fecha']].head())

    print(f"\n📅 Rango de fechas: {df['Fecha_dt'].min()} → {df['Fecha_dt'].max()}")
    return


@app.cell
def _(df):
    # =============================================================================
    # SECCIÓN 4: Crear columna "Year" y columna "Iniciales"
    # =============================================================================
    # ── Extraer año de Fecha_dt ───────────────────────────────────────────────────
    df['Year'] = df['Fecha_dt'].dt.year

    # Convertir a entero (los años de partición deben ser int, no float)
    df['Year'] = df['Year'].astype('Int64')  # Int64 permite nulos

    # ── Añadir columna "Iniciales" con valor por defecto "." ──────────────────────
    df['Iniciales'] = '.'

    # ── Verificar ─────────────────────────────────────────────────────────────────
    print("📊 Años encontrados y su distribución:")
    print(df['Year'].value_counts().sort_index())
    print(f"\n📋 Columnas ahora: {list(df.columns)}")
    print(f"\n👀 Muestra con nuevas columnas:")
    df[['Fecha', 'Year', 'Iniciales']].head(10)
    return


@app.cell
def _(df, pd):
    # =============================================================================
    # SECCIÓN 5: Limpiar el DataFrame — quitar columnas auxiliares y ajustar tipos
    # =============================================================================
    # ── Quitar la columna auxiliar Fecha_dt (ya tenemos Year) ─────────────────────
    df_clean = df.drop(columns=['Fecha_dt'])

    # ── Asegurar tipos correctos ──────────────────────────────────────────────────
    # Columnas numéricas (según especificación)
    columnas_numericas = ['Item', 'Duracion', 'Colaboradores', 'id_ot', 'Year']
    for col in columnas_numericas:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    # ── Verificar resultado final ─────────────────────────────────────────────────
    print("📋 Tipos finales:")
    print(df_clean.dtypes)
    print(f"\n📊 Total registros a migrar: {len(df_clean):,}")
    print(f"📅 Años a particionar: {sorted(df_clean['Year'].dropna().unique())}")
    df_clean.head(3)
    return (df_clean,)


@app.cell
def _(R2_BUCKET, df_clean, storage_options, write_deltalake):
    # =============================================================================
    # SECCIÓN 6: Escribir a R2 Cloudflare con partición por "Year"
    # =============================================================================
    R2_TABLE_PATH = f"s3://{R2_BUCKET}/delta_v30"

    print(f"🚀 Escribiendo a: {R2_TABLE_PATH}")
    print(f"   Partición por: Year")
    print(f"   Registros    : {len(df_clean):,}")

    # ── Escribir con partición ────────────────────────────────────────────────────
    write_deltalake(
        R2_TABLE_PATH,
        df_clean,
        mode="overwrite",               # Primera carga: overwrite
        partition_by=["Year"],
        storage_options=storage_options,
    )

    print("\n✅ Migración completada exitosamente.")
    return (R2_TABLE_PATH,)


@app.cell
def _(DeltaTable, R2_TABLE_PATH, storage_options):
    # =============================================================================
    # SECCIÓN 7: Verificar — leer desde R2 y validar
    # =============================================================================
    print("🔍 Verificando la tabla en R2...\n")

    # ── Leer desde R2 ─────────────────────────────────────────────────────────────
    dt_r2 = DeltaTable(R2_TABLE_PATH, storage_options=storage_options)

    print("📋 Esquema en R2:")
    print(dt_r2.schema())
    print(f"\n📊 Registros en R2: {dt_r2.to_pandas().shape[0]:,}")

    # ── Ver particiones ───────────────────────────────────────────────────────────
    print(f"\n📁 Particiones creadas:")
    partitions = dt_r2.metadata().partition_columns
    print(f"   Columnas de partición: {partitions}")

    # ── Leer una muestra ──────────────────────────────────────────────────────────
    df_r2 = dt_r2.to_pandas()
    print(f"\n👀 Muestra desde R2:")
    df_r2.head(5)
    return (df_r2,)


@app.cell
def _(df_clean, df_r2):
    # =============================================================================
    # SECCIÓN 8: Comparación final — local vs R2
    # =============================================================================
    df_local = df_clean.copy()

    print("📊 Comparación Local vs R2:")
    print(f"   Registros locales : {len(df_local):,}")
    print(f"   Registros en R2   : {len(df_r2):,}")

    # ── Comparar columnas ─────────────────────────────────────────────────────────
    cols_local = set(df_local.columns)
    cols_r2 = set(df_r2.columns)
    print(f"\n   Columnas solo en local : {cols_local - cols_r2}")
    print(f"   Columnas solo en R2    : {cols_r2 - cols_local}")

    # ── Comparar distribución de años ─────────────────────────────────────────────
    print(f"\n📅 Años en local: {sorted(df_local['Year'].dropna().unique())}")
    print(f"📅 Años en R2   : {sorted(df_r2['Year'].dropna().unique())}")

    print("\n✅ Verificación completada.")
    return


if __name__ == "__main__":
    app.run()
