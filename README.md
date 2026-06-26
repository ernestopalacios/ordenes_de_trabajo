# Órdenes de Trabajo — EERSSA

Proyecto personal de uso diario. Procesa y analiza órdenes de trabajo de mantenimiento eléctrico, genera informes de horas extra y consolida datos en Delta Lake (Cloudflare R2) y DuckDB (MotherDuck).

## Arquitectura

```
PDFs → 01_producer (Dask + watchdog) → Kafka (json_ot_v30)
       → 02_consumer → MongoDB (ot_v30) → Kafka (to_delta)
       → 03_concat_ot (ventana 15s) → Delta Lake (R2) ← 05_HE_Delta_R2 (Marimo)
```

### Servicios asumidos corriendo

- **Kafka + Zookeeper**: `localhost:29092`, topics `json_ot_v30`, `to_delta`
- **MongoDB**: colecciones `ot_v30`, `ot_reload`
- **Delta Lake**: `s3://delta-v30/delta_v30` en Cloudflare R2
- **DuckDB (MotherDuck)**: `md:horas_extra`
- **Google Sheets**: `DB_calificar_ot` (hoja `Iniciales`) — datos de cuadrillas y personal

### Componentes

| Componente | Propósito |
|---|---|
| `01_producer.py` | Dask + watchdog → Kafka |
| `02_consumer.py` | Kafka → MongoDB → Kafka |
| `03_concat_ot.py` | Kafka → Delta Lake (R2) |
| `05_HE_Delta_R2.py` | Notebook Marimo: carga Delta Lake, consolida HE, sincroniza DuckDB, genera informe final |
| `eerssa/utils.py` | Funciones compartidas: `load_r2_credentials`, `get_festivos`, `soloFecha_SinTimezone` |
| `eerssa/he_helpers.py` | Lógica HE/Excel/DuckDB exclusiva del notebook |
| `eerssa/organizar.py` | Datos de personal desde Google Sheets (cuadrillas, nombres, orden) |
| `eerssa/excel_styles.py` | Estilos y formato condicional para Excel (openpyxl) |

## Configuración

- **Gestor de paquetes**: `uv`. Ejecutar `uv sync` para instalar.
- **Python**: 3.10 (`.python-version`).
- **Secretos** (nunca commitear): `eerssa/secret.py` (MongoDB URI), `secrets/r2_credentials.json` (R2 keys + duckdb_he_token).
- **Kafka**: `docker-compose up` (Kafka + Zookeeper en `localhost:29092`).

## Flujo de trabajo — Notebook

```bash
marimo edit 05_HE_Delta_R2.py
```

1. **Delta Lake**: cargar datos, exportar actividades a Excel, editar, guardar cambios
2. **DuckDB Consolidado**: consolidar horas extra, enriquecer desde DuckDB, exportar/importar Excel de consolidado, sincronizar
3. **Ajustes + Informe**: validar GDrive, seleccionar cuadrilla/persona, revisar y ajustar tiempos individuales, generar informe final

## Mejoras Planificadas

- **Reubicar columnas en PDFs**: mover `Alimentador`, `Tipo`, `Primario`, `Desconexion`, `SIG` antes de la columna `Materiales`. Afecta desde el Producer.
- **Actividades `se_labora`**: las actividades etiquetadas como `'se_labora'` deben marcarse como `HorasExtra="Si"` para ser incluidas en el filtrado → consolidado.
- **Protección de columnas en plantillas Excel**: bloquear columnas como `id_ot` (color gris, solo lectura) y agregar validación de tipos de datos en celdas específicas.
- **Corregir espacios en cuentas**: error desde Producer → Consumer → Concat que causa espacios al inicio en valores de cuentas (ej: `" REDES"`, `"MEDIDORES "`).

## Largo Plazo

- **Dependency Injection**: refactorizar microservicios (01/02/03) para usar inyección de dependencias.
- **Clases**: migrar funciones sueltas en `utils.py` y `he_helpers.py` a clases con responsabilidades definidas.
- **Librería Excel propia**: biblioteca personalizada para manejo de plantillas, estilos, colores y formato condicional con OpenPyXL.
