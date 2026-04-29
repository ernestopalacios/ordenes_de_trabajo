#import "eerssa/templateReporte.typ": *

#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "
TERMINADO",
    abstract: "
      Gualaquiza Z1 (Cuadrilla. Nro. 3) 

      miércoles, 31 de diciembre del 1969 

      CARTUCHE SILVA GERARDO PATRICIO 

      id_ot: 175698",
  )

= Novedades encontradas

#informativo("Informativo - 2026-04-29 12:55:29")[
  CREACION DE LA OT, se encuentra un archivo PDF valido
  $
    "Archivo PDF es reconocido como Orden de Trabajo"
  $
]

#error("ERROR - 2026-04-29 12:55:29")[
  No coinciden las fechas en la HOJA UNO
  $
    "Fecha de la OT: 2026-04-25T00:00:00-05:00 Fecha Mitad:
1969-12-31T00:00:00-05:00 Fecha String: miércoles, 31 de diciembre
del 1969"
  $
]

#error("ERROR - 2026-04-29 12:55:30")[
  No ha descrito el TIEMPO ESTIMADO en la Hoja Uno
  $
    "Dia de la semana: sábado"
  $
]