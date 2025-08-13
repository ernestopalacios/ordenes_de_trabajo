#import "eerssa/templateReporte.typ": *

#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "TERMINADO",
    abstract: "Zamora Z1 (Cuadrilla. AP Nro. 4) 
 Sin Fecha 
 CABRERA CABRERA MIGUEL ISAURO 
 id_ot : 158512",
  )

= Novedades encontradas

#informativo("Informativo - 2025-08-13 09:16:46")[
  CREACION DE LA OT, se encuentra un archivo PDF valido
  $
    "Ubicacion:
/home/vlad/Documents/temp_borrar/aTest/sc_pdf_20250813091627_209_pdfreport_ordenesTrabajoVisualizar.pdf"
  $
]

#error("ERROR - 2025-08-13 09:16:47")[
  No coinciden las fechas
  $
    "La fecha en Hoja 1 no es la misma que en Actividades"
  $
]

#revisar("Revisar - 2025-08-13 09:16:48")[
  Se detectaron fechas inconsistentes
  $
    "En actividades, revisar las fechas de inicio actividad"
  $
]

#revisar("Revisar - 2025-08-13 09:16:48")[
  Se detectaron fechas inconsistentes
  $
    "En actividades, revisar las fechas de fin de actividad"
  $
]