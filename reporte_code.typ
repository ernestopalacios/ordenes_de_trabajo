#import "eerssa/templateReporte.typ": *

#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "
TERMINADO",
    abstract: "
      Guayzimi Z1 (Cuadrilla. Nro. 7) 

      lunes, 23 de marzo del 2026 

      CACAY LUZURIAGA ASDRUBAL HUMBERTO 

      id_ot: 173379",
  )

= Novedades encontradas

#informativo("Informativo - 2026-04-01 08:54:32")[
  CREACION DE LA OT, se encuentra un archivo PDF valido
  $
    "Archivo PDF es reconocido como Orden de Trabajo"
  $
]

#error("ERROR - 2026-04-01 08:54:32")[
  No coinciden las fechas en la HOJA UNO
  $
    "Fecha de la OT: 2026-03-24T00:00:00-05:00 Fecha Mitad:
2026-03-23T00:00:00-05:00 Fecha String: lunes, 23 de marzo del 2026"
  $
]