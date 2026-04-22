#import "eerssa/templateReporte.typ": *

#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "
ECURSO",
    abstract: "
      Zamora Z1 (Cuadrilla. AP Nro. 4) 

      miércoles, 22 de abril del 2026 

      MORALES RIVERA LUIS ALBERTO 

      id_ot: 175258",
  )

= Novedades encontradas

#informativo("Informativo - 2026-04-22 10:39:25")[
  CREACION DE LA OT, se encuentra un archivo PDF valido
  $
    "Archivo PDF es reconocido como Orden de Trabajo"
  $
]

#problema("FATAL - 2026-04-22 10:39:25")[
  La Orden de trabajo no se encuentra en estado TERMINADO
  $
    "Texto es: ECURSO"
  $
]

#error("ERROR - 2026-04-22 10:39:25")[
  No coinciden las fechas en la HOJA UNO
  $
    "Fecha de la OT: 2026-04-24T00:00:00-05:00 Fecha Mitad:
2026-04-22T00:00:00-05:00 Fecha String: miércoles, 22 de abril del
2026"
  $
]

#error("ERROR - 2026-04-22 10:39:25")[
  No ha competado la fecha final
  $
    "Texto es:"
  $
]

#problema("FATAL - 2026-04-22 10:39:25")[
  No se pudieron encontrar actividades
  $
    "No se han llenado las Actividades en la OT: /home/vlad/Documentos/_g
estion_ot/sc_pdf_20260422090506_519_pdfreport_ordenesTrabajoVisualiz
ar.pdf"
  $
]