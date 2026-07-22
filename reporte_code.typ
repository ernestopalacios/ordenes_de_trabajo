#import "eerssa/templateReporte.typ": *

#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "
TERMINADO",
    abstract: "
      Zamora (Agencia) 

      sábado, 12 de febrero del 2022 

      MACAS CURIPOMA RAMIRO HOMERO 

      id_ot: 81013",
  )

= Novedades encontradas

#informativo("Informativo - 2026-07-22 09:19:43")[
  CREACION DE LA OT, se encuentra un archivo PDF valido
  $
    "Archivo PDF es reconocido como Orden de Trabajo"
  $
]

#error("ERROR - 2026-07-22 09:19:43")[
  No coinciden las fechas en la HOJA UNO
  $
    "Fecha de la OT: 2022-02-11T00:00:00-05:00 Fecha Mitad:
2022-02-12T00:00:00-05:00 Fecha String: sábado, 12 de febrero del
2022"
  $
]

#informativo("Informativo - 2026-07-22 09:19:43")[
  Desde \>\> Obtener fechaModa. No se encontro fecha en las
actividades
  $
    "Se utiliza como fechaModa la fecha de Inicio en la Hoja 1"
  $
]