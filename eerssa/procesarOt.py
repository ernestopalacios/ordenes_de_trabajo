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

import traceback
import logging
from pprint import pprint


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def to_log_entry( level, message, detail ):
  """
     Devuelve un objeto en formato diccionario para ser insertado en el 
     array de Logs.
  """
  if isinstance(detail, Exception):
    # Format the exception with its traceback for detailed logging
    detalles = "".join(traceback.format_exception(type(detail), detail, detail.__traceback__))
  elif not isinstance(detail, str):
    # Fallback for other non-string types, convert them safely
    detalles = str(detail)
  else: # it's a string
    detalles = detail
  
  entry = {
    "t": datetime.now().isoformat(),
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
  ot['log']     = []

  # = 1. No es String

  if not isinstance(link_to_pdf, str):
    ot['log'].append(
      to_log_entry( "FATAL", "No es un directorio valido","El enlace no es de tipo String"))
    return ot
  
  # = 2. Validamos el String que sea un directorio valido
  try:
    
    pdf_path = Path(link_to_pdf)
    if not pdf_path.exists():
      ot['log'].append(
        to_log_entry( "FATAL", "No es un directorio valido",f"El enlace no es de un directorio valido:{link_to_pdf} "))
      return ot
  except Exception as e:
    ot['log'].append( 
      to_log_entry( "FATAL", f"Ocurrio un error al interpretar como Path el String: {link_to_pdf}", e))
    return ot
  
  # = 3. Verificamos que sea un archivo PDF de tipo Orden de Trabajo
  try:
    with pymupdf.open(pdf_path) as pdf:
      hojas = pdf.page_count
      if not (1 < hojas < 5):
        ot['log'].append(
          to_log_entry("FATAL", "No es un archivo PDF valido", f"La cantidad de hojas no es valida: {hojas}"))
        return ot

      paginaUno = pdf.load_page(0)
      # Verifica un marcador de texto en la pagina UNO para validar que es un archivo Orden de Trabajo.
      check_text = paginaUno.get_textbox( Rect(BoxesValues.FECHA_INICIO_TESTIMADO.value ))
      if "TIEMPO ESTIMADO DE DURACIÓN (HORAS):" in check_text:
        ot["exito"] = True
        ot['log'].append(
          to_log_entry("INFO", "CREACION DE LA OT, se encuentra un archivo PDF valido", f"Ubicacion: {link_to_pdf}"))
        ot["createdAt"] = datetime.now().isoformat()
  except Exception as e:
    ot['log'].append(to_log_entry("FATAL", "No se pudo abrir o procesar el archivo PDF", e))
    return ot
  
  # = 4. Obtenemos los campos necesarios
  if ot["exito"] == True:
        
    with pymupdf.open( pdf_path ) as pdf:
      paginaUno = pdf.load_page(0)
      paginaDos = pdf.load_page(1)

    # - identificacion de ot ID_OT
      texto = DEFAULT_EMPTY_CHAR
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.ID_OT.value) )
        id_ot = texto.split('\n')[1].replace(',',"")
        id_ot = int(id_ot)
        ot["id_ot"] = id_ot

      except Exception as e:
        ot['exito'] = False   # SI NO HAY 'id_ot' NO SE PUEDE CONTINUAR
        ot['log'].append(
          to_log_entry('FATAL',f"No se pudo extraer el ID de la Orden de Trabajo en el texto: {texto}", e)) 
        
        return ot  # <=== No es Ot Valida. 
        
    # - Terminado
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.ESTADO_OT.value) )
        terminado = texto.strip()
        ot["terminado"] = terminado

        if terminado != "TERMINADO":
          ot['exito'] = False
          ot['log'].append(
            to_log_entry('FATAL',"La Orden de trabajo no se encuentra en estado TERMINADO",f"Texto es: {terminado}"))
          
      except Exception as e:
        ot['exito'] = False
        ot['log'].append(
          to_log_entry('FATAL',"No se pudo extraer el ESTADO de la Orden de Trabajo", e)) 

    # - Cuadrilla
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.CUADRILLA_NOMBRE.value) )
        cuadrilla = texto.strip()
        ot["cuadrilla"] = cuadrilla

        if len(cuadrilla) < 4:
          ot['cuadrilla'] = DEFAULT_EMPTY_CHAR
          ot['exito'] = False
          ot['log'].append(
            to_log_entry('FATAL',"No se pudo extraer la CUADRILLA de la Orden de Trabajo",f"Texto es: {cuadrilla}"))

      except Exception as e:
        ot['cuadrilla'] = DEFAULT_EMPTY_CHAR
        ot['exito'] = False
        ot['log'].append(
          to_log_entry('FATAL',"No se pudo extraer la CUADRILLA de la Orden de Trabajo", e)) 
    
    # - Responsable
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.RESPONSABLE.value) )
        df_personal = texto.strip().split('\n')
        responsable = [df_personal[0],df_personal[1]]
        ot['responsable'] = responsable
      except Exception as e:
        ot['responsable'] = DEFAULT_EMPTY_CHAR
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer el RESPONSABLE de la Orden de Trabajo", e)) 
    

    # - Colaboradores
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.COLABORADORES_NOMBRES.value) )
        df_personal = texto.strip().split('\n')
        df_personal = [ item for item in df_personal if item != '' ]

        data = paginaUno.get_textbox( Rect( BoxesValues.COLABORADORES_CARGOS.value) )
        df_cargos = data.strip().split('\n')
        df_cargos = [ item for item in df_cargos if item != '' ]

        totalColaboradores = len(df_personal)

        colaboradores = []

        for i in range(totalColaboradores):
          colaboradores.append([df_personal[i],df_cargos[i]])

        respuesta = {}
        respuesta['total'] = totalColaboradores
        respuesta['nombres'] = colaboradores

        if ot['responsable'] in respuesta['nombres']:
          respuesta['total'] -= 1
          respuesta['nombres'] = [x for x in respuesta['nombres'] if x != ot['responsable']]

        ot['colaboradores'] = respuesta
      except Exception as e:
        lista_colaboradores = {}
        lista_colaboradores['total'] = 0
        lista_colaboradores['nombres'] = []
        ot['colaboradores'] = lista_colaboradores
        ot['log'].append(
          to_log_entry('REVISAR',"No se pudo extraer los COLABORADORES de la Orden de Trabajo", e)) 
    

    # - FECHA DE INICIO HOJA UNO.Arriba
      try:
        fechaInicio = paginaUno.get_textbox( Rect( BoxesValues.FECHA_INICIAL_UNO.value) )
        fechaInicio = fechaInicio.strip()
        diaSemana = getDiaSemana( fechaInicio )
        fechaInicio = toDateEcuador( fechaInicio )

        ot['diaSemana'] = diaSemana
        ot['fecha'] = fechaInicio

      except Exception as e:
        ot['diaSemana'] = DEFAULT_EMPTY_CHAR
        ot['fecha'] = DEFAULT_EMPTY_CHAR
        ot['exito'] = False
        ot['log'].append(
          to_log_entry('FATAL',"No se pudo extraer la FECHA la Orden de Trabajo", e)) 
    
    #
    # TODO  fecha Inicio HOja Uno mitad.  n_fallas, n_errores, n_revisar, n_info
    #



    # - FechaFinal2
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.FECHA_FINAL.value) )
        fechaFinal = texto.strip()
        ot["fechaFinal"] = fechaFinal
        if len(fechaFinal) < 4:
          ot['fechaFinal'] = DEFAULT_EMPTY_CHAR
          ot['log'].append(
            to_log_entry('ERROR','No ha competado la fecha final',f"Texto es: {texto}"))
      except Exception as e:
        ot['fechaFinal'] = DEFAULT_EMPTY_CHAR
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer la FECHA FINAL de la Orden de Trabajo", e)) 
    
    
    # - Numeracion

      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.NUMERO_OT.value) )
        numeracion = texto.replace('NM:',"").replace(',',"").strip()
        ot["numeracion"] = int(numeracion)
      except Exception as e:
        ot['numeracion'] = 0
        ot['log'].append(
          to_log_entry('REVISAR',f"No se pudo extraer el NUMERO de la Orden de Trabajo, texto: {texto}", e))
    
    # - Gerencia
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.GERENCIA.value) )
        gerencia = texto.strip()
        ot["gerencia"] = gerencia
      except Exception as e:
        ot['gerencia'] = DEFAULT_EMPTY_CHAR
        ot['log'].append(
          to_log_entry('ERROR',f"No se pudo extraer la GERENCIA de la Orden de Trabajo, texto: {texto}", e)) 
    
    # - Sitio
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.SITIO.value) )
        sitio = texto.strip().replace('\n'," ")
        ot["sitio"] = sitio
      except Exception as e:
        ot["sitio"] = DEFAULT_EMPTY_CHAR
        ot['log'].append(
          to_log_entry('ERROR',f"No se pudo extraer el SITIO de la Orden de Trabajo, texto: {texto}", e)) 
    
    # - Descripcion
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.DESCRIPCION.value) )
        descripcion = texto.strip().replace('\n'," ") 
        ot["descripcion"] = descripcion
      except Exception as e:
        ot["descripcion"] = DEFAULT_EMPTY_CHAR
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer la DESCRIPCION de la Orden de Trabajo", e)) 
    
    # - Precauciones
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.PRECAUCIONES.value) )
        precauciones = texto.replace('PRECAUCIONES:',"").strip()
        ot["precauciones"] = precauciones
      except Exception as e:
        ot['log'].append(
          to_log_entry('REVISAR',"No se pudo extraer las PRECAUCIONES de la Orden de Trabajo", e)) 
    
    # - Carencias
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.CARENCIAS.value) )
        carencias = texto.replace('CARENCIAS:',"").strip()
        ot["carencias"] = carencias

        if len(carencias) > 4:
          ot['log'].append(
          to_log_entry('REVISAR','Se reportan CARENCIAS','Revisar si estan reportadas CARENCIAS'))
      except Exception as e:
        ot['carencias'] = DEFAULT_EMPTY_CHAR
        ot['log'].append(
          to_log_entry('REVISAR',"No se pudo extraer las CARENCIAS de la Orden de Trabajo", e)) 
    
    # - Observaciones
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.OBSERVACIONES.value) )
        observaciones = texto.strip().replace('\n'," ")
        ot["observaciones"] = observaciones
      except Exception as e:
        ot['observaciones'] = DEFAULT_EMPTY_CHAR
        ot['log'].append(
          to_log_entry('REVISAR',"No se pudo extraer las OBSERVACIONES de la Orden de Trabajo", e)) 
    
    # - Accidentes
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.ACCIDENTES.value) )
        accidentes = texto.strip()
        ot["accidentes"] = accidentes
        if accidentes != "NO":
          ot['log'].append(
          to_log_entry('REVISAR','Se reportan accidentes','Revisar si estan reportados accidentes'))
      except Exception as e:
        ot['accidentes'] = DEFAULT_EMPTY_CHAR
        ot['log'].append(
          to_log_entry('REVISAR',"No se pudo extraer los ACCIDENTES de la Orden de Trabajo", e)) 
    

    # - TIPOS DE TRABAJO - 
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.TIPOS_TRABAJO.value) )
        df_tipos_trabajo = texto.split('\n')
        ot["trabajo"] = df_tipos_trabajo
        if len(df_tipos_trabajo) < 1:
          ot['log'].append(
          to_log_entry('ERROR',"No se encontaron TIPOS DE TRABAJO", f"texto: {texto}" ))
      except Exception as e:
        ot['trabajo'] = []
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer los TIPOS DE TRABAJO", e))

    # - RIESGOS DE TRABAJO - 
      try:
        df_riesgos = paginaUno.get_textbox( Rect( BoxesValues.RIESGOS_EPPS.value) )
        df_riesgos = df_riesgos.replace('RIESGOS EXISTENTES:\nCONSECUENCIAS PROBABLES:\nELEMENTOS DE PREVENCIÓN A UTILIZAR\n','')
        df_riesgos = df_riesgos.split('\n')
        
        ot["riesgos"] = df_riesgos
      except Exception as e:
        ot['riesgos'] = []
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer los RIESGOS DE TRABAJO", e))

    # - MEDIDAS DE SEGURIDAD -
      try:
        df_seguridad = paginaUno.get_textbox( Rect( BoxesValues.MEDIDAS_SEGURIDAD.value) )
        df_seguridad = df_seguridad.replace('MEDIDAS\nESTADO\nEQUIPOS DE PROTECCIÓN\nESTADO\n','')
        df_seguridad = df_seguridad.split('\n')
        
        ot["seguridad"] = df_seguridad
      except Exception as e:
        ot['seguridad'] = []
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer las MEDIDAS DE SEGURIDAD", e))

    # - PRECAUCIONES -
      try:
        df_precauciones = paginaUno.get_textbox( Rect( BoxesValues.PRECAUCIONES.value) )
        df_precauciones = df_precauciones.replace('PRECAUCIONES:', "").replace('\n', ' ').strip()
        
        ot["precauciones"] = df_precauciones
      except Exception as e:
        ot['precauciones'] = DEFAULT_EMPTY_CHAR
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer las PRECAUCIONES", e))

    """
    # - ACTIVIDADES -
      try:
        actividades = []
        # Loop through pages that can contain activities (page 2 onwards)
        for i in range(1, pdf.page_count):
          page = pdf.load_page(i)
          tables = page.find_tables(clip=Rect(BoxesValues.ACTIVIDADES.value), strategy='lines_strict') # type: ignore
          
          # Check if any tables were found before trying to access them
          if not tables.tables:
            ot['log'].append(  
              to_log_entry("INFO", "No se encontraron tablas de actividades.", f"En la pagina: {page.number + 1}")
            )
            continue # Skip to the next page
              
          df = tables.tables[0].to_pandas()
          df.columns = ['Item','Actividad','Evento','Ali','Alimentador','Tipo','InicioEvento','FinEvento']

          # More robust way to filter header rows
          df['Item'] = df['Item'].astype(str).str.strip()
          is_valid_item = df['Item'].str.match(r'^\d+$', na=False)
          df = df[is_valid_item].copy()

          # Clean up data
          df['InicioEvento'] = df['InicioEvento'].str.replace('\n', ' ', regex=False)
          df['FinEvento']   = df['FinEvento'].str.replace('\n', ' ', regex=False)
          df['Actividad'] = df['Actividad'].str.replace('\n', ' ', regex=False)
          df = df.replace('', pd.NA).dropna(how='all')
          df = df.fillna(DEFAULT_EMPTY_CHAR)

          actividades.extend(df.to_dict('records'))

        if not actividades:
          ot["exito"] = False
          ot['log'].append(  
            to_log_entry("FATAL", "No se pudieron encontrar actividades", "No se encontraron actividades en ninguna de las hojas del documento.")
          )
          return ot

        ot["actividades"] = actividades

      except Exception as e:
        ot['log'].append(  
          to_log_entry("ERROR", f"No se pudo extraer la tabla de Actividades en la hoja {paginaDos.number+1}", e)
        )

    """
  return ot