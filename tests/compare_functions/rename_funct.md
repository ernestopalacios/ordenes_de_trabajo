## Propuesta para re-nombrar funciones de UTILS.PY con mejor descripcion.

`import eerssa.utils as f_utils`

elimina_timezone()      => fechaHora_elimina_timezone()  Mantiene fecha y hora, elimina timezone
soloFecha_SinTimeZone() => fecha_elimina_timezone()      Elimina Timezone y hora, devuelve solo fecha
ColocarTimezone()       => fecha_coloca_timezone()       a partir de una fecha agrega el componente de timezone fijo de Ecuador 
toDateObject()          => fecha_toDateObj()             a partir de una Fecha retorna un objeto Date sin el componente del Tiempo
toTimeObject()          => fechaHora_toDateTimeObj()     convierte FechaHora a DateTimeObject

-------------

limpiar_items()         => toStringArray()    Convierte elementos de un alista a Strings. 


