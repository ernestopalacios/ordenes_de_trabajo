from pathlib import Path
import json
from datetime import datetime

# Import your existing modules
from .constants import BoxesValues, Current
from .constants import Current, Chars
from .gestionOT import toDateEcuador, getDiaSemana

# PDF Conversion Library
import pymupdf
from   pymupdf import Rect
import pandas as pd
import numpy as np

import logging
from pprint import pprint


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def to_log_entry( level, message, detail ):
  """
     Devuelve un objeto en formato diccionario para ser insertado en el 
     array de Logs.
  """  
  if isinstance(detail, str):
    detalles = detail
  else:
    detalles = "No se pudo capturar la Excepcion, lo mas probable campos vacios"
  
  entry = {
    "t": datetime.now(),
    "level"  : level,
    "message": message,
    "detail" : detalles
  }

  return entry
  

def procesarOt( link_to_pdf ):
  """ 
  Esta será la función central para procesamiento en paralelo,
  sin clases ni objetos ni dependecias externas
  todo en un solo lugar, siempre devuelve un diccionario, puede
  ser válido o no. Los mensajes de Excepción se guardan en el Log
  dentro del mismo diccionario, un solo objeto.

  :param str inputPDF_path: Path to the PDF File to be processed
  """

  DEFAULT_EMPTY_CHAR = Chars.DEFAULT_EMPTY_CHAR.value
  VERSION = Current.VERSION.value

  ot = {}
  ot["version"] = VERSION
  ot["link"]    = link_to_pdf
  ot["exito"]   = False
  ot["log"]     = []

  # = 1. No es String

  if not isinstance(link_to_pdf, str):
    ot["log"].append(
      to_log_entry( "FATAL", "No es un directorio valido","El enlace no es de tipo String"))
    return ot
  
  # = 2. Validamos el String que sea un directorio valido
  try:
    
    pdf_path = Path(link_to_pdf)

    if not pdf_path.exists():
      ot["log"].append(
        to_log_entry( "FATAL", "No es un directorio valido",f"El enlace no es de un directorio valido:{link_to_pdf} "))
      return ot
  except:
    ot["log"].append( 
      to_log_entry( "FATAL", "No es un directorio valido",f"Fallo al obtener Path: {link_to_pdf}"))
    return ot
  
  # = 3. Verificamos que sea un archivo PDF de tipo Orden de Trabajo
  try:

    with pymupdf.open( pdf_path ) as pdf:

      hojas = pdf.page_count
      paginaUno = pdf.load_page(0)

      if ( hojas > 1 and hojas < 5 ):       
        
        check = paginaUno.get_textbox( Rect( BoxesValues.FECHA_INICIO_TESTIMADO.value) )
        if  "TIEMPO ESTIMADO DE DURACIÓN (HORAS):" in check:
          ot["exito"] = True
          ot["log"].append(
            to_log_entry("INFO", "CREACION DE LA OT, se encuentra un archivo PDF de al menos tres hojas ", f"Ubicacion: {link_to_pdf}"))
          ot["createdAt"] = datetime.now()

      else:
        ot["log"].append(
          to_log_entry("FATAL","No es un archivo PDF valido",f"La cantidad de hojas no es valida: {hojas} ")
        )
        return ot 
  except:
    ot["log"].append(
      to_log_entry( "FATAL", "No es un archivo PDF", f"No se reconoce como archivo PDF valido: {link_to_pdf}"))
    return ot
  
  # = 4. Obtenemos los campos necesarios
  if ot["exito"] == True:
        
    with pymupdf.open( pdf_path ) as pdf:
      paginaUno = pdf.load_page(0)

    # - ACTIVIDADES -
      try:
        actividades = []
        for x in range( 1, pdf.page_count ):
          paginaDos = pdf.load_page(x)
          tables = paginaDos.find_tables( clip=Rect( BoxesValues.ACTIVIDADES.value), strategy='lines_strict') # type: ignore
          
          # Check if any tables were found before trying to access them
          if not tables.tables:
            ot["log"].append(  
            to_log_entry("ERROR", "No se pudo extraer la tabla de Actividades.", f"La funcion 'find_tables()' no encontro tablas en la pagina: {paginaDos.number+1}")
          )
              
          df = tables.tables[0].to_pandas()
          df.columns = ['Item','Actividad','Evento','Ali','Alimentador','Tipo','InicioEvento','FinEvento']

          # More robust way to filter header rows
          df['Item'] = df['Item'].astype(str)
          is_valid_item = df['Item'].str.contains(r'\d', na=False)
          df = df[is_valid_item].copy()

          # Clean up data
          df['InicioEvento'] = df['InicioEvento'].str.replace('\n', ' ', regex=False)
          df['FinEvento']   = df['FinEvento'].str.replace('\n', ' ', regex=False)
          df = df.replace('', pd.NA).dropna(how='all')
          
          actividades.append(df.to_dict('records'))

      
        if len(actividades[0]) == 0:
          ot["exito"] = False
          ot["log"].append(  
            to_log_entry("FATAL","No se pudieron encontrar actividades",f"No hay actividades en la hoja: {paginaDos.number+1}"))
          return ot
        else:
          # Cargo las actividades al objeto
          ot["actividades"] = actividades[0]
          


      except Exception:
        ot["log"].append(  
          to_log_entry("ERROR", "No se pudo extraer la tabla de Actividades.", f"Desde la funcion getActividades() en la hoja {paginaDos.number+1}")
        )
  return ot