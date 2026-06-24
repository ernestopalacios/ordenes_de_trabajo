# Milestone Checkpoint — Horas Extra Pipeline

**Fecha:** 24 de junio de 2026
**Estado:** Etapa de sincronización y reporte completada con éxito.

---

## 1. Cambios implementados

### Nuevos módulos

| Archivo | Propósito |
|---------|-----------|
| `eerssa/he_helpers.py` | Funciones HE: consolidación, export Excel, sincronización DuckDB, informe final |
| `eerssa/excel_styles.py` | Estilos y reglas de formato condicional para Excel (openpyxl) |

### Módulo modificado

| Archivo | Cambio |
|---------|--------|
| `eerssa/utils.py` | Reducido a 3 funciones usadas por 01/02/03: `load_r2_credentials`, `get_festivos`, `soloFecha_SinTimezone`. Todo lo demás migrado a `he_helpers.py`. |

### Notebook principal

| Archivo | Estado |
|---------|--------|
| `05_HE_Delta_R2.py` | Flujo completo implementado (Marimo) |

### Documentación

| Archivo | Propósito |
|---------|-----------|
| `AGENTS.md` | Instrucciones para futuras sesiones de OpenCode |
| `models/workflow_he.md` | Diseño del flujo Horas Extra (referencia) |
| `models/Consolidado_Excel.md` | Diseño de exportación/importación Excel (referencia) |
| `models/Informe_final.md` | Diseño del informe final (referencia) |
| `docs/milestone_checkpoint.md` | Este archivo |

---

## 2. Estado actual de la arquitectura

### Flujo completo

```
Delta Lake (R2)
      │
      ▼
  55_HE_Delta_R2.py (Marimo)
      │
      ├─ Paso 1: Cargar df desde Delta Lake
      ├─ Paso 2: consolidar_horas_extra(df) → consolidado
      ├─ Paso 2 (reactivo): enriquecer_desde_duckdb() → consolidado_enriquecido
      ├─ Paso 3a (gated): Exportar consolidado_enriquecido a Excel
      ├─ Paso 3b (gated): Importar Excel editado → consolidado_editado
      ├─ Paso 4 (gated): sincronizar_a_duckdb() → actividades + participaciones
      └─ Paso 6 (gated): generar_informe_he() → Excel con una hoja por persona
```

### Tablas DuckDB (MotherDuck)

```sql
actividades (id_actividad PK, id_ot, Fecha, Cuadrilla, Colaboradores VARCHAR[],
             InicioEvento TIME, FinEvento TIME, Duracion INTEGER, Evento VARCHAR,
             Cuenta MAP(VARCHAR,INTEGER), Items VARCHAR[], items_key VARCHAR,
             Num_Filas INTEGER, Archivo VARCHAR, Tipo VARCHAR, Dia VARCHAR)

participaciones (id_actividad, Responsable, PRIMARY KEY,
                 InicioEvento TIME, FinEvento TIME, tiempo_ajustado BOOLEAN DEFAULT FALSE)
                 -- SIN foreign key constraint (app logic lo mantiene)
```

### Módulos existentes (sin cambios)

- `01_producer.py` — Dask + watchdog → Kafka
- `02_consumer.py` — Kafka → MongoDB → Kafka
- `03_concat_ot.py` — Kafka → Delta Lake (R2)
- `eerssa/utils.py` — `load_r2_credentials`, `get_festivos`, `soloFecha_SinTimezone`
- `eerssa/procesarActividades.py`, `eerssa/matrizActividades.py` — usan utils.py

---

## 3. Decisiones críticas y dependencias

### Decisiones de diseño

- **Separación utils.py / he_helpers.py**: `utils.py` solo para la pipeline 01/02/03. `he_helpers.py` exclusivo del notebook Marimo. Desacoplamiento completo.
- **Sin FK constraint en participaciones**: DuckDB/MotherDuck no soporta UPDATE en tabla padre con FK activas. La integridad referencial se mantiene por lógica de aplicación (borrado de huérfanos en dos loops).
- **Flujo único de edición**: El usuario siempre pasa por Excel para editar Evento y Cuenta. La sincronización solo acepta `consolidado_editado` (no el enriquecido directamente).
- **Formato Cuenta**: Round-trip `[dict] → string → dict → MAP(VARCHAR,INTEGER)` mediante `cuenta_consolidado_to_str`, `cuenta_str_to_map`, `map_to_cuenta_str`.
- **items_key**: Columna derivada en Python, almacenada en DuckDB para matching determinístico (`id_ot + items_key`). Índice único `idx_actividad_natural`.

### Dependencias externas (asumidas corriendo)

| Servicio | Detalle |
|----------|---------|
| Kafka + Zookeeper | `localhost:29092`, topics: `json_ot_v30`, `to_delta` |
| MongoDB | Colecciones: `ot_v30`, `ot_reload` |
| Delta Lake | `s3://delta-v30/delta_v30` en Cloudflare R2 |
| DuckDB (MotherDuck) | `md:horas_extra` |
| Google Sheets | Datos de cuadrilla vía `eerssa.organizar.get_gsheet_df()` |

### Secretos (nunca commitear)

- `eerssa/secret.py` — MongoDB URI
- `secrets/r2_credentials.json` — R2 keys + `duckdb_he_token`

### SQL ejecutado manualmente

```sql
-- Tablas
CREATE SEQUENCE IF NOT EXISTS seq_actividad START 1;
CREATE TABLE actividades ( ... );
CREATE TABLE participaciones ( ... );  -- sin FK

-- Columnas e índices añadidos
ALTER TABLE actividades ADD COLUMN IF NOT EXISTS items_key VARCHAR;
ALTER TABLE actividades ADD COLUMN IF NOT EXISTS Duracion INTEGER;
CREATE UNIQUE INDEX IF NOT EXISTS idx_actividad_natural ON actividades(id_ot, items_key);
```

---

## 4. Próximos pasos (TODO)

### Alta prioridad

- [ ] **Paso 5: Ajustes individuales de tiempo**: Exportar/importar tiempos por persona desde `participaciones` (InicioEvento, FinEvento individuales). Hoy el informe final usa `COALESCE(p.InicioEvento, a.InicioEvento)`.
- [ ] **Validar que `tiempo_ajustado` se preserve**: Al hacer diff de Colaboradores en `sincronizar_a_duckdb`, los ajustes de tiempo de una persona eliminada y re-agregada se pierden. Necesita lógica de preservación.

### Media prioridad

- [ ] **Manejo de NaN/None**: Varias funciones en `he_helpers.py` asumen valores no-nulos. Agregar guards proactivos (especialmente en `cuenta_str_to_map`, `parse_items_consolidado`, `parse_colaboradores`).
- [ ] **Limpiar funciones muertas**: `parse_cuenta_consolidado` ya no se usa (reemplazada por `cuenta_str_to_map`). `build_horas_extra_final` y helpers asociados son del flujo antiguo de 04_DataLake.
- [ ] **Feedback visual en sync**: El callout de sincronización muestra totales pero no detalla qué filas fueron UPDATE/INSERT/DELETE. Agregar desglose.

### Baja prioridad

- [ ] **Columna `Duracion` en consolidado**: Al ajustar horarios (`ajustar_horario_inicio/fin`) no se recalcula Duracion. Puede mostrar valores inconsistentes en Excel.
- [ ] **Auditoría**: Agregar `fecha_modificacion` a `actividades` y `participaciones` para trazabilidad.
- [ ] **Refactor de `eerssa/excel_styles.py`**: Las reglas de formato condicional tienen referencias hardcodeadas a `Revisar_primero!$B$2:$B$14`, etc. Podrían parametrizarse.
- [ ] **Tests automatizados**: No hay framework de testing. Las funciones de `he_helpers.py` son candidatas para tests unitarios (especialmente las de conversión de Cuenta e Items).

### Notas para la próxima sesión

- Kafka, 01/02/03 deben estar corriendo antes de abrir el notebook.
- El notebook se lanza con: `marimo edit 05_HE_Delta_R2.py`
- Si se modifica `eerssa/utils.py`, reiniciar 03_concat_ot (kernel de Marimo auto-recarga `he_helpers.py`).
- MotherDuck no soporta transacciones multi-statement con FK checks — mantener el diseño sin FK.