import typst
import pypst
import textwrap
import pandas as pd

import sys
import os

def sanitize_for_typst(text: str) -> str:
    """
    Escapes special characters in a string for safe inclusion in a Typst document.
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Characters to escape with a backslash in Typst
    special_chars = {
        "\\": "\\\\",
        "#": "\\#",
        "*": "\\*",
        "_": "\\_",
        "$": "\\$",
        "~": "\\~",
        "`": "\\`",
        "[": "\\[",
        "]": "\\]",
        "{": "\\{",
        "}": "\\}",
        "\"": "\\\"",
        '"': '\\"',
        "'": "\\'",
        "|": "\\|",
        "<": "\\<",
        ">": "\\>",
    }
    
    for char, escaped_char in special_chars.items():
        text = text.replace(char, escaped_char)
        
    return text


def generate_comment( doc, log_item ):
  level_msg = log_item["level"]
  time_msg = log_item["t"].replace('T',' ').split('.')[0]
  
  if level_msg == 'FATAL':
    color = f"#problema(\"FATAL - {time_msg}\")"
  elif level_msg == 'ERROR':
    color = f"#error(\"ERROR - {time_msg}\")"
  elif level_msg == 'REVISAR':
    color = f"#revisar(\"Revisar - {time_msg}\")"
  else:
    color = f"#informativo(\"Informativo - {time_msg}\")"

  message = sanitize_for_typst(log_item["message"])
  detail = sanitize_for_typst(log_item["detail"])

  wrapped_message = textwrap.fill(message, width=80)
  wrapped_detail = textwrap.fill(detail, width=80)

  doc.add(
    f"""{color}[
  {wrapped_message}
  $
    \"{wrapped_detail}"
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
      return "nada_por_reportar"


  doc = pypst.Document()
  doc.add_import("eerssa/templateReporte.typ", ['*']) # Import all Modules


  doc.add(f"""#show: dvdtyp.with(
    title: "Reporte de Orden de Trabajo",
    subtitle: [ ],
    author: "{sanitize_for_typst(estado)}",
    abstract: [
      {sanitize_for_typst(cuadrilla)} \
      {sanitize_for_typst(fecha)} \
      {sanitize_for_typst(responsable)} \
      id_ot: {sanitize_for_typst(id_ot)} ],
  )""")

  doc.add("= Novedades encontradas")

  for log_item in ot.log:
    doc = generate_comment( doc, log_item )
    
  return doc
  