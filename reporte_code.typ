#import "eerssa/templateReporte.typ": *

#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "TERMINADO",
    abstract: "Zamora Z1 (Cuadrilla. AP Nro. 4) 
 miércoles, 23 de julio del 2025 
 MORALES RIVERA LUIS ALBERTO 
 id_ot : 157727",
  )

= Novedades encontradas

#informativo("Informativo - 2025-07-23 23:11:31")[
  CREACIÓN DE LA OT, se encuentra un archivo PDF de al menos tres hojas 
  $
    "Ninguno"
  $
]

#informativo("Informativo - 2025-07-23 23:11:32")[
  Desde >> Obtener fechaModa. No se encontro fecha en las actividades
  $
    "Se utiliza como fechaModa la fecha de Inicio en la Hoja 1"
  $
]

#revisar("Revisar - 2025-07-23 23:11:32")[
  Se detectaron fechas inconsistentes
  $
    "En actividades, revisar las fechas de inicio actividad"
  $
]

#revisar("Revisar - 2025-07-23 23:11:32")[
  Se detectaron fechas inconsistentes
  $
    "En actividades, revisar las fechas de fin de actividad"
  $
]