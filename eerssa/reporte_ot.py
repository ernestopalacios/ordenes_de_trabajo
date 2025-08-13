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
    color = f"#problema(\"FATAL - {time_msg}\")"
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
    id_ot = ot.data["id_ot"]
  except:
    id_ot = "SIN ID"
  try:
    estado = ot.data["estado"]
  except:
    estado = "SIN ESTADO"
  try:
    cuadrilla = ot.data["cuadrilla"]
  except:
    cuadrilla = "SIN CUADRILLA"
  try:
    fecha = ot.data["fechaString"]
  except:
    fecha = "Sin Fecha"
  try:
    responsable = ot.data["responsable"][0]
  except:
    responsable = "Sin Responsable"

  # No generar Reporte para OT finalizadas en caso de no haber novedades.
  if len(ot.log) == 1 and ot.log[0]["level"] == "INFO" and estado == "TERMINADO":
      return "todo_ok"


  doc = pypst.Document()
  doc.add_import("eerssa/templateReporte.typ", ['*']) # Import all Modules


  doc.add(f"""#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "{estado}",
    abstract: "{cuadrilla} \n {fecha} \n {responsable} \n id_ot : {id_ot}",
  )""")

  doc.add("= Novedades encontradas")

  for log_item in ot.log:
    doc = generate_comment( doc, log_item )
    
  return doc
  