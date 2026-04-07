#import "eerssa/templateReporte.typ": *

#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "
TERMINADO",
    abstract: "
      Zamora Z1 (Cuadrilla. Nro. 6) 

      sábado, 28 de marzo del 2026 

      SILVA ARMIJOS ROMEL EDUARDO 

      id_ot: 174146",
  )

= Novedades encontradas

#informativo("Informativo - 2026-04-07 08:18:14")[
  CREACION DE LA OT, se encuentra un archivo PDF valido
  $
    "Archivo PDF es reconocido como Orden de Trabajo"
  $
]

#error("ERROR - 2026-04-07 08:18:14")[
  No coinciden las fechas en la HOJA UNO
  $
    "Fecha de la OT: 2026-03-29T00:00:00-05:00 Fecha Mitad:
2026-03-28T00:00:00-05:00 Fecha String: sábado, 28 de marzo del 2026"
  $
]