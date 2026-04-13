#import "eerssa/templateReporte.typ": *

#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "
TERMINADO",
    abstract: "
      Gualaquiza Z1 (Cuadrilla. Nro. 3) 

      martes, 07 de abril del 2026 

      LOJAN PAZ CARLOS DIEGO 

      id_ot: 174313",
  )

= Novedades encontradas

#informativo("Informativo - 2026-04-13 09:41:00")[
  CREACION DE LA OT, se encuentra un archivo PDF valido
  $
    "Archivo PDF es reconocido como Orden de Trabajo"
  $
]

#error("ERROR - 2026-04-13 09:41:00")[
  No ha competado la fecha final
  $
    "Texto es:"
  $
]

#error("ERROR - 2026-04-13 09:41:01")[
  No ha descrito el TIEMPO ESTIMADO en la Hoja Uno
  $
    "Dia de la semana: martes"
  $
]