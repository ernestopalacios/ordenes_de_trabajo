#import "eerssa/templateReporte.typ": *

#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "
TERMINADO",
    abstract: "
      Gualaquiza (Agencia) 

      miércoles, 29 de julio del 2026 

      BUELE UYAGUARI CESAR CRISTIAN 

      id_ot: 181742",
  )

= Novedades encontradas

#informativo("Informativo - 2026-07-31 10:46:14")[
  CREACION DE LA OT, se encuentra un archivo PDF valido
  $
    "Archivo PDF es reconocido como Orden de Trabajo"
  $
]

#error("ERROR - 2026-07-31 10:46:14")[
  No coinciden las fechas en la HOJA UNO
  $
    "Fecha de la OT: 2026-07-30T00:00:00-05:00 Fecha Mitad:
2026-07-29T00:00:00-05:00 Fecha String: miércoles, 29 de julio del
2026"
  $
]