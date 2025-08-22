from pathlib import Path
from datetime import datetime
from pytz import timezone

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
  ot['n_fatales'] = 0
  ot['n_errores'] = 0
  ot['n_revisar'] = 0

  

  # = 1. No es String

  if not isinstance(link_to_pdf, str):
    ot['n_fatales'] = 1
    ot['log'].append(
      to_log_entry( "FATAL", "No es un directorio valido","El enlace no es de tipo String"))
    return ot
  
  # = 2. Validamos el String que sea un directorio valido
  try:
    
    pdf_path = Path(link_to_pdf)
    if not pdf_path.exists():
      ot['n_fatales'] = 1
      ot['log'].append(
        to_log_entry( "FATAL", "No es un directorio valido",f"El enlace no es de un directorio valido:\n{link_to_pdf} "))
      return ot
  except Exception as e:
    ot['n_fatales'] = 1
    ot['log'].append( 
      to_log_entry( "FATAL", f"Ocurrio un error al interpretar como Path el String:\n {link_to_pdf}", e))
    return ot
  
  # = 3. Verificamos que sea un archivo PDF de tipo Orden de Trabajo
  try:
    with pymupdf.open(pdf_path) as pdf:
      hojas = pdf.page_count
      if not (1 < hojas < 5):
        ot['n_fatales'] = 1
        ot['log'].append(
          to_log_entry("FATAL", f"No es un archivo PDF valido:\n{link_to_pdf}", f"La cantidad de hojas no es valida: {hojas}"))
        return ot

      paginaUno = pdf.load_page(0)
      # Verifica un marcador de texto en la pagina UNO para validar que es un archivo Orden de Trabajo.
      check_text = paginaUno.get_textbox( Rect(BoxesValues.FECHA_INICIO_TESTIMADO.value ))
      if "TIEMPO ESTIMADO DE DURACIÓN (HORAS):" in check_text:
        ot["exito"] = True
        ot['log'].append(
          to_log_entry("INFO", "CREACION DE LA OT, se encuentra un archivo PDF valido", f"Archivo PDF de reconocido como Orden de Trabajo"))
        ot["createdAt"] = datetime.now().isoformat()
  except Exception as e:
    ot['n_fatales'] = 1
    ot['log'].append(to_log_entry("FATAL", f"No se pudo abrir o procesar el archivo PDF:\n {link_to_pdf}", f"[ERROR] en la ot: {ot['link']}\n\n {e}"))
    return ot
  
  # = 4. Obtenemos los campos necesarios
  if ot["exito"] == True:
        
    with pymupdf.open( pdf_path ) as pdf:
      paginaUno = pdf.load_page(0)
      paginaDos = pdf.load_page(1)

        
    # - Terminado
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.ESTADO_OT.value) )
        terminado = texto.strip()
        ot["estado"] = terminado

        if terminado != "TERMINADO":
          ot['n_fatales'] = 1
          ot['log'].append(
            to_log_entry('FATAL',"La Orden de trabajo no se encuentra en estado TERMINADO",f"Texto es: {terminado}"))
          
      except Exception as e:
        ot['exito'] = False
        ot['n_fatales'] = 1
        ot['log'].append(
          to_log_entry('FATAL',"No se pudo extraer el ESTADO de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 



    # - identificacion de ot ID_OT
      texto = DEFAULT_EMPTY_CHAR
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.ID_OT.value) )
        id_ot = texto.split('\n')[1].replace(',',"")
        id_ot = int(id_ot)
        ot["id_ot"] = id_ot

      except Exception as e:
        ot['exito'] = False   # SI NO HAY 'id_ot' NO SE PUEDE CONTINUAR
        ot['n_fatales'] += 1
        ot['log'].append(
          to_log_entry('FATAL',f"No se pudo extraer el ID de la Orden de Trabajo en el texto: {texto}", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
        
        return ot  # <=== No es Ot Valida. 
      
    # - Cuadrilla
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.CUADRILLA_NOMBRE.value) )
        cuadrilla = texto.strip()
        ot["cuadrilla"] = cuadrilla

        if len(cuadrilla) < 4:
          ot['cuadrilla'] = DEFAULT_EMPTY_CHAR
          ot['exito'] = False
          ot['n_fatales'] += 1
          ot['log'].append(
            to_log_entry('FATAL',"No se pudo extraer la CUADRILLA de la Orden de Trabajo",f"Texto es: {cuadrilla}"))

      except Exception as e:
        ot['cuadrilla'] = DEFAULT_EMPTY_CHAR
        ot['exito'] = False
        ot['n_fatales'] += 1
        ot['log'].append(
          to_log_entry('FATAL',"No se pudo extraer la CUADRILLA de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    
    # - Responsable
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.RESPONSABLE.value) )
        df_personal = texto.strip().split('\n')

        if len(df_personal) == 0:
          ot['n_fatales'] += 1
          ot['exito'] = False
          ot['log'].append(
            to_log_entry( 'FATAL',
                         "No se pudo extraer el RESPONSABLE de la Orden de Trabajo", 
                         "No se envia la OT al Servidor")) 

        else:
          responsable = [df_personal[0],df_personal[1]]
          ot['responsable'] = responsable

      except Exception as e:
        ot['responsable'] = DEFAULT_EMPTY_CHAR
        ot['exito'] = False
        ot['n_fatales'] += 1
        ot['log'].append(
          to_log_entry('FATAL',"No se pudo extraer el RESPONSABLE de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    

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
        ot['n_revisar'] += 1
        ot['log'].append(
          to_log_entry('REVISAR',"No se pudo extraer los COLABORADORES de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    

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
        ot['n_fatales'] += 1
        ot['exito'] = False
        ot['log'].append(
          to_log_entry('FATAL',"No se pudo extraer la FECHA la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
        
    # - Fecha String HOJA UNO mitad de la hoja

      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.FECHA_STRING.value) )
        fechaString = texto.strip()
        
        if len(fechaString) < 4:
          ot['n_errores'] += 1
          ot['fechaString'] = DEFAULT_EMPTY_CHAR
          ot['log'].append(
            to_log_entry('ERROR',f"No ha competado la FECHA STRING. Texto es: {fechaString}",f"Fehca de la OT: {ot['fecha']}"))
        
        ot["fechaString"] = fechaString

        if ot['fecha'] != toDateEcuador(fechaString):
          ot['n_errores'] += 1
          ot['log'].append(
            to_log_entry("ERROR","No coinciden las fechas en la HOJA UNO",f"Fecha de la OT: {ot['fecha']}\nFecha Mitad: {toDateEcuador(fechaString)}\nFecha String: {fechaString}")
          )
        
      except Exception as e:
        ot['fechaString'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer la FECHA STRING de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 

    # - FechaFinal2
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.FECHA_FINAL.value) )
        fechaFinal = texto.strip()
        ot["fechaFinal"] = fechaFinal
        if len(fechaFinal) < 4:
          ot['fechaFinal'] = DEFAULT_EMPTY_CHAR
          ot['n_errores'] += 1
          ot['log'].append(
            to_log_entry('ERROR','No ha competado la fecha final',f"Texto es: {fechaFinal}"))
      
      except Exception as e:
        ot['fechaFinal'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer la FECHA FINAL de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
        
    # - Vehiculo
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.VEHICULO.value) )
        vehiculo = texto.strip()
        ot["vehiculo"] = vehiculo
      except Exception as e:
        ot['vehiculo'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer el VEHICULO de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 

        
    # - KMI
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.KMI.value) )
        kmi = texto.strip().replace(',' ,  '' )
        ot["kmInicial"] = int(kmi)
      except Exception as e:
        ot['kmInicial'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer el KMI de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
        
    # - KMF
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.KMF.value) )
        kmf = texto.strip().replace(',' ,  '' )
        ot["kmFinal"] = int(kmf)
      except Exception as e:
        ot['kmFinal'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer el KMF de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
        
    # - KMT 
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.KMT.value) )
        kmt = texto.strip().replace(',' ,  '' )
        ot["kmTotal"] = int(kmt)
      except Exception as e:
        ot['kmTotal'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer el KMT de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 





    # - ACTIVIDADES -
      try:
        itemX1 = 28
        itemY1 = 92

        itemX2 = 41
        itemY2 = 117.85

        deltaY = 28.32

        deltaXactiv1 = 15
        anchoActiv = 36

        deltaEvento = 53
        anchoEvento = 298

        deltaLMT = 340
        anchoLMT = 397

        deltaTipo = 440
        anchoTipo = 490

        deltaInicio = 491
        anchoFecha = 37

        deltaFin = 529.5
        
        actividades = []

        # Loop through pages that can contain activities (page 2 onwards)
        for i in range(1, pdf.page_count):
          page = pdf.load_page(i)
          
          for i in range(21):
            # ITEM
            fila = {}

            fila['Item'] = page.get_textbox( 
              Rect(itemX1, itemY1+(i*deltaY), itemX2, itemY2+(i*deltaY)))
            
            if fila['Item'] == "":
              fila['Item'] = DEFAULT_EMPTY_CHAR
            
            # Activ
            fila['Actividad'] = page.get_textbox( 
              Rect(
                itemX1 + deltaXactiv1, 
                itemY1+(i*deltaY), 
                itemX2 + anchoActiv, 
                itemY2+(i*deltaY) ))
            
            if fila['Actividad'] == "":
              fila['Actividad'] = DEFAULT_EMPTY_CHAR

            #Evento
            fila['Evento'] = page.get_textbox( 
              Rect(
                itemX1 + deltaEvento, 
                itemY1+(i*deltaY), 
                itemX2 + anchoEvento, 
                itemY2+(i*deltaY) ))
            if fila['Evento'] == "":
              continue
            
            #Alimentador
            fila['Alimentador'] = page.get_textbox( 
              Rect(
                itemX1 + deltaLMT, 
                itemY1+(i*deltaY), 
                itemX2 + anchoLMT, 
                itemY2+(i*deltaY) ))
            if fila['Alimentador'] == "":
              fila['Alimentador'] = DEFAULT_EMPTY_CHAR
            
            # Tipo
            fila['Tipo'] = page.get_textbox( 
              Rect(
                deltaTipo, 
                itemY1+(i*deltaY), 
                anchoTipo, 
                itemY2+(i*deltaY) ))
            if fila['Tipo'] == "":
              fila['Tipo'] = DEFAULT_EMPTY_CHAR
            
            # Inicio
            fila['InicioEvento'] = page.get_textbox( 
              Rect(
                deltaInicio, 
                itemY1+(i*deltaY), 
                deltaInicio+anchoFecha, 
                itemY2+(i*deltaY) )).replace('\n', ' ').strip()
            if fila['InicioEvento'] == "":
              fila['InicioEvento'] = DEFAULT_EMPTY_CHAR
            
            # Fin
            fila['FinEvento'] = page.get_textbox( 
              Rect(
                deltaFin, 
                itemY1+(i*deltaY), 
                deltaFin+anchoFecha, 
                itemY2+(i*deltaY) )).replace('\n', ' ').strip()
            if fila['FinEvento'] == "":
              fila['FinEvento'] = DEFAULT_EMPTY_CHAR
          
            actividades.append(fila)


        if len(actividades) == 0:
          ot["exito"] = False
          ot["actividades"] = []
          ot['n_fatales'] += 1
          ot['log'].append(  
            to_log_entry("FATAL", "No se pudieron encontrar actividades", f"No se han llenado las Actividades en la OT: {ot['link']}")
          )
          return ot

        ot["actividades"] = actividades

      except Exception as e:
        ot["exito"] = False
        ot["actividades"] = []
        ot['n_fatales'] += 1
        ot['log'].append(  
          to_log_entry("FATAL", f"No se pudo extraer la tabla de Actividades", f"[ERROR] en la ot: {ot['link']}\n\n {e}"))





    # - Placa
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.PLACA.value) )
        placa = texto.strip()
        ot["placa"] = placa
      except Exception as e:
        ot['placa'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer la PLACA de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    
    # - Chofer
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.CHOFER.value) )
        chofer = texto.strip()
        ot["chofer"] = chofer
      except Exception as e:
        ot['chofer'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer el CHOFER de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}"))
    
    # - Rentado
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.RENTADO.value) )
        rentado = texto.strip()
        ot["rentado"] = rentado
      except Exception as e:  
        ot['rentado'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer el RENTADO de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    
    # - Tiempo Estimado
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.DURACION.value) )
        duracion = texto.strip()
        ot["tEstimado"] = duracion
        if len(duracion) == 0:
          ot['tEstimado'] = DEFAULT_EMPTY_CHAR
          ot['n_errores'] += 1
          ot['log'].append(
            to_log_entry('ERROR',f"No ha descrito el TIEMPO ESTIMADO en la Hoja Uno", f"Dia de la semana: {ot['diaSemana']}")) 
      
      except Exception as e:
        ot['tEstimado'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer la DURACION de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
        
      
    # - Gerencia
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.GERENCIA.value) )
        gerencia = texto.strip()
        ot["gerencia"] = gerencia
        if len(gerencia) == 0:
          ot['gerencia'] = DEFAULT_EMPTY_CHAR
          ot['n_errores'] += 1
          ot['log'].append(
            to_log_entry('ERROR',f"Falta seleccionar la GERENCIA de la Orden de Trabajo", f"La Cuadrilla es: {ot['cuadrilla']}")) 
      except Exception as e:
        ot['gerencia'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',f"No se pudo extraer la GERENCIA de la Orden de Trabajo, texto: {texto}", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    
    # - Sitio
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.SITIO.value) )
        sitio = texto.strip().replace('\n'," ")
        ot["sitio"] = sitio
        if len(sitio) == 0:
          ot['sitio'] = DEFAULT_EMPTY_CHAR
          ot['n_errores'] += 1
          ot['log'].append(
            to_log_entry('ERROR',f"Falta describir el SITIO de la Orden de Trabajo", f"Se encuentra vacio")) 
          
      except Exception as e:
        ot["sitio"] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',f"No se pudo extraer el SITIO de la Orden de Trabajo, texto: {texto}", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    


    # - Descripcion
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.DESCRIPCION.value) )
        descripcion = texto.strip().replace('\n'," ") 
        ot["descripcion"] = descripcion
        if len(descripcion) == 0:
          ot['n_errores'] += 1
          ot['descripcion'] = DEFAULT_EMPTY_CHAR
          ot['log'].append(
            to_log_entry('ERROR',"Falta describir la DESCRIPCION de la Orden de Trabajo", f"Se encuentra vacio")) 

      except Exception as e:
        ot["descripcion"] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer la DESCRIPCION de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    
    # - Precauciones
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.PRECAUCIONES.value) )
        precauciones = texto.replace('PRECAUCIONES:',"").strip()
        ot["precauciones"] = precauciones
      except Exception as e:
        ot['precauciones'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer las PRECAUCIONES de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    
    # - Carencias
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.CARENCIAS.value) )
        carencias = texto.replace('CARENCIAS:',"").strip()
        ot["carencias"] = carencias

        if len(carencias) > 4:
          ot['n_revisar'] += 1
          ot['log'].append(
          to_log_entry('REVISAR','Se reportan CARENCIAS',f'{carencias}'))
      except Exception as e:
        ot['carencias'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer las CARENCIAS de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    
    # - Observaciones
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.OBSERVACIONES.value) )
        observaciones = texto.strip().replace('\n'," ")
        ot["observaciones"] = observaciones
      except Exception as e:
        ot['observaciones'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer las OBSERVACIONES de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 
    
    # - Accidentes
      try:
        texto = paginaDos.get_textbox( Rect( BoxesValues.ACCIDENTES.value) )
        accidentes = texto.strip()
        ot["accidentes"] = accidentes
        if accidentes != "NO":
          ot['log'].append(
          to_log_entry('REVISAR','Se reportan accidentes','Confirmar si estan reportados accidentes'))
      except Exception as e:
        ot['accidentes'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer los ACCIDENTES de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 

    # - TIPOS DE TRABAJO - 
      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.TIPOS_TRABAJO.value) )
        df_tipos_trabajo = texto.split('\n')
        ot["trabajo"] = df_tipos_trabajo
        if len(df_tipos_trabajo) < 1:
          ot['n_errores'] += 1
          ot['log'].append(
          to_log_entry('ERROR',"No se encontaron TIPOS DE TRABAJO", f"texto: {texto}" ))
      except Exception as e:
        ot['trabajo'] = []
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer los TIPOS DE TRABAJO", f"[ERROR] en la ot: {ot['link']}\n\n {e}"))

    # - RIESGOS DE TRABAJO - 
      try:
        df_riesgos = paginaUno.get_textbox( Rect( BoxesValues.RIESGOS_EPPS.value) )
        df_riesgos = df_riesgos.replace('RIESGOS EXISTENTES:\nCONSECUENCIAS PROBABLES:\nELEMENTOS DE PREVENCIÓN A UTILIZAR\n','')
        df_riesgos = df_riesgos.split('\n')
        
        if len(df_riesgos) < 1:
          ot['riesgos'] = []
          ot['n_errores'] += 1
          ot['log'].append(
            to_log_entry('ERROR',"No se encontraron RIESGOS DE TRABAJO", f"texto: {df_riesgos}" ))
        else:
          ot["riesgos"] = df_riesgos
      
      except Exception as e:
        ot['riesgos'] = []
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer los RIESGOS DE TRABAJO", f"[ERROR] en la ot: {ot['link']}\n\n {e}"))

    # - MEDIDAS DE SEGURIDAD -
      try:
        df_seguridad = paginaUno.get_textbox( Rect( BoxesValues.MEDIDAS_SEGURIDAD.value) )
        df_seguridad = df_seguridad.replace('MEDIDAS\nESTADO\nEQUIPOS DE PROTECCIÓN\nESTADO\n','')
        df_seguridad = df_seguridad.split('\n')

        if len(df_seguridad) < 1:
          ot['seguridad'] = []
          ot['n_errores'] += 1
          ot['log'].append(
            to_log_entry('ERROR',"No se encontraron MEDIDAS DE SEGURIDAD", f"texto: {df_seguridad}" ))
        else:
          ot["seguridad"] = df_seguridad
      except Exception as e:
        ot['seguridad'] = []
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer las MEDIDAS DE SEGURIDAD", f"[ERROR] en la ot: {ot['link']}\n\n {e}"))

    # - PRECAUCIONES -
      try:
        df_precauciones = paginaUno.get_textbox( Rect( BoxesValues.PRECAUCIONES.value) )
        df_precauciones = df_precauciones.replace('PRECAUCIONES:', "").replace('\n', ' ').strip()
        
        ot["precauciones"] = df_precauciones
      except Exception as e:
        ot['precauciones'] = DEFAULT_EMPTY_CHAR
        ot['n_errores'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer las PRECAUCIONES", f"[ERROR] en la ot: {ot['link']}\n\n {e}"))
    
    # - Numeracion

      try:
        texto = paginaUno.get_textbox( Rect( BoxesValues.NUMERO_OT.value) )
        numeracion = texto.replace('NM:',"").replace(',',"").strip()
        ot["numeracion"] = int(numeracion)
      except Exception as e:
        ot['numeracion'] = 0
        ot['n_revisar'] += 1
        ot['log'].append(
          to_log_entry('REVISAR',f"No se pudo extraer el NUMERO de la Orden de Trabajo, texto: {texto}", f"[ERROR] en la ot: {ot['link']}\n\n {e}"))
    
    # - Firmas
      try:
        firmasX1 = 85
        firmasAncho = 159
        firmasDelta = 160

        firmasY1 = 740
        firmasAlto = 23.4

        firmas_list = []
        for i in range(3):
          firmas_list.append(
            paginaUno.get_textbox( 
              Rect( firmasX1 + (i*firmasDelta),
                    firmasY1,
                    firmasX1 + (i*firmasDelta) + firmasAncho,
                    firmasY1+firmasAlto  )))
        if len(firmas_list) < 3:
          ot['n_errores'] += 1
          ot['log'].append(
            to_log_entry("ERROR","Faltan Firmas Revisar","No se encontraron todas las firmas")
          )
        ot["firmas"] = firmas_list
      except Exception as e:
        ot['firmas'] = DEFAULT_EMPTY_CHAR
        ot['n_error'] += 1
        ot['log'].append(
          to_log_entry('ERROR',"No se pudo extraer las FIRMAS de la Orden de Trabajo", f"[ERROR] en la ot: {ot['link']}\n\n {e}")) 

  return ot