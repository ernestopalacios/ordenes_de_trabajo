import typst
import pypst
import pandas as pd

import sys
import os


def generate_comment( doc, log_item ):
  level_msg = log_item["level"]
  time_msg = log_item["t"].replace('T',' ').split('.')[0]
  detail = log_item["detail"]
  message = log_item["message"]
  
  if level_msg == 'FATAL':
    color = f"#problem(\"FATAL - {time_msg}\")"
  elif level_msg == 'ERROR':
    color = f"#error(\"ERROR - {time_msg}\")"
  elif level_msg == 'REVISAR':
    color = f"#revisar(\"Revisar - {time_msg}\")"
  else:
    color = f"#informativo(\"Informativo - {time_msg}\")"

  doc.add(
    f"""{color}[
  {message}
  $
    \"{detail}"
  $
]""")

  return doc


def create_typst_doc( ot ):
  try:
    estado = ot.data["estado"]
  except:
    estado = "SIN ESTADO"
  try:
    cuadrilla = ot.data["cuadrilla"]
  except:
    cuadrilla = "SIN CUADRILLA"
  try:
    fecha = ot.data["fechaInicio"]
  except:
    fecha = "Sin Fecha"
  try:
    responsable = ot.data["responsable"][0]
  except:
    responsable = "Sin Responsable"

  doc = pypst.Document()
  doc.add_import("eerssa/templateReporte.typ", ['*']) # Import all Modules


  doc.add(f"""#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "{estado}",
    abstract: "{cuadrilla} \n {fecha} \n {responsable}",
  )""")

  doc.add("= Novedades encontradas")

  for log_item in ot.log:
    doc = generate_comment( doc, log_item )
    
  return doc
  