from .constants import BoxesValues
from .constants import Current

VERSION = Current.VERSION.value

import os

from operator import index
from datetime import datetime
from pytz import timezone

# Dask
from dask.distributed import LocalCluster
client = LocalCluster().get_client()

import pickle
import json

import pandas as pd
pd.set_option("future.no_silent_downcasting", True)
import numpy as np

import pymupdf
from   pprint import pprint
from   pymupdf import Rect

from icecream import ic
ic.configureOutput( prefix = '\not_pdf| ', includeContext=True)


# Areas where the information is to be extracted using PyMuPDF
# boxes hoja 1 : primera cara

bx_id_ot                  = Rect( BoxesValues.ID_OT.value )
bx_numero_ot              = Rect( BoxesValues.NUMERO_OT.value )
bx_gerencia               = Rect( BoxesValues.GERENCIA.value )
bx_sitio                  = Rect( BoxesValues.SITIO.value )
bx_fechaInicial_1         = Rect( BoxesValues.FECHA_INICIAL_UNO.value )

bx_responsable            = Rect( BoxesValues.RESPONSABLE.value )
bx_nombresColaboradores   = Rect( BoxesValues.COLABORADORES_NOMBRES.value)
bx_cargosColaboradores    = Rect( BoxesValues.COLABORADORES_CARGOS.value)

bx_vehiculoHoja1          = Rect( BoxesValues.DATOS_VEHICULO_HOJA_1.value )
bx_tipos_trabajo          = Rect( BoxesValues.TIPOS_TRABAJO.value )
bx_descripcion            = Rect( BoxesValues.DESCRIPCION.value)
bx_fechaInicio_Testimado  = Rect( BoxesValues.FECHA_INICIO_TESTIMADO.value)
bx_riesgos_epps           = Rect( BoxesValues.RIESGOS_EPPS.value)
bx_medidas_seg            = Rect( BoxesValues.MEDIDAS_SEGURIDAD.value)
bx_precauciones           = Rect( BoxesValues.PRECAUCIONES.value)
bx_carencias              = Rect( BoxesValues.CARENCIAS.value)
bx_firmas                 = Rect( BoxesValues.FIRMAS.value)


# boxes hoja 2: reverso

bx_cuadrilla              = Rect( BoxesValues.CUADRILLA_NOMBRE.value )
bx_vehiculo               = Rect( BoxesValues.VEHICULO.value )
bx_kilometraje            = Rect( BoxesValues.KILOMETRAJE.value )
bx_actividades            = Rect( BoxesValues.ACTIVIDADES.value )
bx_observaciones          = Rect( BoxesValues.OBSERVACIONES.value )
bx_terminado              = Rect( BoxesValues.ESTADO_OT.value)
bx_fechaFin               = Rect( BoxesValues.FECHA_FINAL.value)
bx_accidentes             = Rect( BoxesValues.ACCIDENTES.value)


def DrawBoxesOt( inputPDF_path ):
  """ 
  Draw the fields with information to be extracted.

  :param str inputPDF_path: Path to the PDF File to be drawn uppon
  :return: The path to the created file, same directory as input or FALSE
  """
  try:
    doc = pymupdf.open( inputPDF_path )

    page_one = doc[0].new_shape()

    page_one.draw_rect( bx_id_ot          )
    page_one.draw_rect( bx_numero_ot      )
    page_one.draw_rect( bx_gerencia       )
    page_one.draw_rect( bx_sitio          )
    page_one.draw_rect( bx_fechaInicial_1 )
    page_one.draw_rect( bx_responsable       )
    page_one.draw_rect( bx_nombresColaboradores )
    page_one.draw_rect( bx_cargosColaboradores )
    page_one.draw_rect( bx_vehiculoHoja1  )
    page_one.draw_rect( bx_tipos_trabajo  )
    page_one.draw_rect( bx_descripcion )
    page_one.draw_rect( bx_fechaInicio_Testimado )
    page_one.draw_rect( bx_riesgos_epps )
    page_one.draw_rect( bx_medidas_seg )
    page_one.draw_rect( bx_precauciones )
    page_one.draw_rect( bx_carencias )
    page_one.draw_rect( bx_firmas )

    page_two = doc[1].new_shape()

    page_two.draw_rect( bx_cuadrilla )
    page_two.draw_rect( bx_vehiculo  )
    page_two.draw_rect( bx_kilometraje )
    page_two.draw_rect( bx_actividades )
    page_two.draw_rect( bx_observaciones )
    page_two.draw_rect( bx_terminado )
    page_two.draw_rect( bx_fechaFin )
    page_two.draw_rect( bx_accidentes )

    page_one.finish( color=(1, 0, 0), fill=None )
    page_two.finish( color=(1, 0, 0), fill=None )
    page_one.commit()
    page_two.commit()

    result = os.path.dirname(inputPDF_path)+ "/CAMPOS_version_"+ VERSION + ".pdf"

    doc.save(result)

    return result
  
  except:

    return False


# Primera tabla,

def getId_Ot( hoja ):
  try:
    texto = hoja.get_text( clip = bx_id_ot )
    id_ot = texto
    id_ot = id_ot.split('\n')[1].replace(',',"")
    id_ot = int(id_ot)
  except:

    ic({"archivo: ": hoja, "variable: ":texto})
    id_ot = "·"
  return id_ot

# Function to getNumeracion

def getNumeracion( hoja ):
  try:
    texto = hoja.get_text( clip = bx_numero_ot )
    numeracion = texto
    numeracion = numeracion.replace('NM:', "").replace(',', "").strip()
    numeracion = int(numeracion)
  except:
    ic({"archivo: ": hoja, "variable: ":texto})
    numeracion = 0
  return numeracion

# Function to getGerencia

def getGerencia( hoja ):
  try:
    texto = hoja.get_text( clip = bx_gerencia ).strip()
    gerencia = texto
  except:
    ic({"archivo: ": hoja, "variable: ":texto})
    gerencia = "·"
  return gerencia

# Function to getSitio using get_text()

def getSitio( hoja ):
  try:
    sitio = hoja.get_text( clip = bx_sitio ).strip()
  except:
    ic({"archivo: ": hoja, "variable: ":sitio})
    sitio = "·"
  return sitio

# Funtion to getFechaInicio usint get_text()

def getFechaInicio( hoja ):
  try:
    fechaInicio = hoja.get_text( clip = bx_fechaInicial_1 ).strip()
  except:
    ic({"archivo: ": hoja, "variable: ":fechaInicio})
    fechaInicio = "·"
  return fechaInicio

# Funcion que transforma una fecha de String largo a toDateString compatible
# Si no es posible la transformacion, devuelve la misma cadena sin alterar

def toDateEcuador( fecha ):
    try:
        meses_a_numero = {
            'enero' : '01',
            'febrero' : '02',
            'marzo' : '03',
            'abril' : '04',
            'mayo' : '05',
            'junio' : '06',
            'julio' : '07',
            'agosto' : '08',
            'septiembre' : '09',
            'octubre' : '10',
            'noviembre' : '11',
            'diciembre' : '12'
        }

        fechaString = fecha.lower()

        fechaString = (
            fechaString
            .split(',')[1]
            .strip()
            .replace('del ', '')
            .replace('de ', '')
            )

        for mes, numero in meses_a_numero.items():
            fechaString = fechaString.replace(mes, numero)

        respuesta = fechaString.split(' ')
        respuesta = '/'.join(respuesta)
        date_object = datetime.strptime(respuesta, '%d/%m/%Y')
        ecuador = timezone("America/Guayaquil")
        local_datetime = ecuador.localize(date_object)


    except:
        ic({"archivo: ": fecha, "variable: ": fechaString})
        local_datetime = fecha

    return local_datetime

# Function getDiaSemana: try and split by ',' return the first part except return '·'

def getDiaSemana( fechaInicio ):
  try:
    diaSemana = fechaInicio.split(',')[0]
  except:
    ic({"archivo: ": fechaInicio, "variable: ":diaSemana})
    diaSemana = "·"
  return diaSemana


# Function to getResponsable

def getResponsable( hoja ):
    try:
        texto = hoja.get_text( clip = bx_responsable)
        df_personal = texto
        df_personal = df_personal.strip().split('\n')
        responsable = [df_personal[0],df_personal[1]]
    except:
        ic({"archivo: ": hoja, "variable: ":texto})
        responsable = "·"
    return responsable


def getColaboradores( hoja ):
    try:
        texto = hoja.get_text( clip = bx_nombresColaboradores )
        df_personal = texto
        df_personal = df_personal.strip().split('\n')
        df_personal = [ item for item in df_personal if item != '' ]

        data = hoja.get_text( clip = bx_cargosColaboradores )
        df_cargos = data
        df_cargos = df_cargos.strip().split('\n')
        df_cargos = [ item for item in df_cargos if item != '' ]

        totalColaboradores = len(df_personal)

        colaboradores = []
        for i in range(totalColaboradores):
            colaboradores.append([df_personal[i],df_cargos[i]])
    except:
        ic({"archivo: ": hoja, "Nombres: ":texto, "Cargo: ":data})
        totalColaboradores = 0
        colaboradores = []

    respuesta = {}
    respuesta['total'] = totalColaboradores
    respuesta['nombres'] = colaboradores
    return respuesta


# Function getVehiculo using to_pandas()

def getVehiculo( hoja ):
  try:
    texto = hoja.get_text( clip = bx_vehiculoHoja1 ).strip().split('\n')
    df_vehiculo = texto

    if df_vehiculo[3] == 'Placa:':  # Hay un vehículo

      data_vehiculo={}
      data_vehiculo['numero'] = df_vehiculo[2]
      data_vehiculo['placa'] = df_vehiculo[4]
      data_vehiculo['marca'] = df_vehiculo[6]
      data_vehiculo['rentado'] = df_vehiculo[8]
      data_vehiculo['propietario'] = df_vehiculo[10]

      if len(df_vehiculo) == 13:
        data_vehiculo['chofer'] = df_vehiculo[12]
      else:
        data_vehiculo['chofer'] = "·"

    else:
      data_vehiculo={}
      data_vehiculo['numero'] = "·"
      data_vehiculo['placa'] = "·"
      data_vehiculo['marca'] = "·"
      data_vehiculo['rentado'] = "·"
      data_vehiculo['propietario'] = "·"
      data_vehiculo['chofer'] = "·"

  except:
    ic({"archivo: ": hoja, "variable: ":texto})
    data_vehiculo = "·"

  return data_vehiculo

# Function getTiposTrabajo using to_pandas()

def getTiposTrabajo( hoja ):
  try:
    df_tipos_trabajo = hoja.find_tables( clip = bx_tipos_trabajo )
    df_tipos_trabajo = df_tipos_trabajo.tables[0].to_pandas()
    df_tipos_trabajo = df_tipos_trabajo.to_numpy().flatten()
    df_tipos_trabajo = [ item for item in df_tipos_trabajo if item != '' ]
  except:
    ic(hoja)
    df_tipos_trabajo = "·"
  return df_tipos_trabajo

# Function getDescripcion using get_text()

def getDescripcion( hoja ):
  try:
    descripcion = hoja.get_text( clip = bx_descripcion ).strip()
  except:
    ic({"archivo: ": hoja, "variable: ":descripcion})
    descripcion = "·"
  return descripcion

# Function getFechaInicio2 with bx_fechaInicio_Testimado

def getFechaInicio2( hoja ):

  find_word_index = lambda word_list, target_word: word_list.index(target_word) if target_word in word_list else -1

  try:
    texto = hoja.get_text( clip = bx_fechaInicio_Testimado ).strip().split('\n')
    fechaInicio2 = texto
    index = find_word_index(fechaInicio2, 'TIEMPO ESTIMADO DE DURACIÓN (HORAS):')

    if index != -1:
      fechaInicio2 = fechaInicio2[index - 1]
    else:
      ic(fechaInicio2)
      fechaInicio2 = "·"
  except:
    ic({"archivo: ": hoja, "variable: ":texto})
    fechaInicio2 = "·"
  return fechaInicio2

# from operator import index
# Function getTestimado with bx_fechaInicio_Testimado

def getTiempoEstimado( hoja ):

  find_word_index = lambda word_list, target_word: word_list.index(target_word) if target_word in word_list else -1

  try:
    texto = hoja.get_text( clip = bx_fechaInicio_Testimado ).strip().split('\n')
    Testimado = texto
    index = find_word_index(Testimado, 'TIEMPO ESTIMADO DE DURACIÓN (HORAS):')

    if index != -1:
      Testimado = Testimado[index + 1]
    else:
      ic(Testimado)
      Testimado = "·"
  except:
    ic({"archivo: ": hoja, "variable: ":texto})
    Testimado = "·"
  return Testimado


# Function to getRiesgos to_pandas()

def getRiesgos( hoja ):
    riesgos_dict = {}
    try:
        df_riesgos = hoja.find_tables( clip = bx_riesgos_epps )
        df_riesgos = df_riesgos.tables[0].to_pandas().replace('', np.nan).dropna(how = 'all')
        for _, row in df_riesgos.iterrows():
            key = row['RIESGOS EXISTENTES:']
            value = [row[col] for col in df_riesgos.columns if col != 'RIESGOS EXISTENTES:']
            riesgos_dict[key] = value
    except:
        ic(hoja)
        riesgos_dict = "·"
    return riesgos_dict

# Function getMedidasSeguridad return pandas dataframe

def getMedidasSeguridad( hoja ):
    try:
        df_medidas_seg = hoja.find_tables( clip = bx_medidas_seg )
        df_medidas_seg = df_medidas_seg.tables[0].to_pandas()
        df_medidas_seg = df_medidas_seg[['0-MEDIDAS','1-ESTADO']].replace('', np.nan).dropna(how = 'all')
        df_medidas_seg = dict(zip(df_medidas_seg['0-MEDIDAS'],df_medidas_seg['1-ESTADO']))

    except:
        ic(hoja)
        df_medidas_seg = "·"
    return df_medidas_seg

# Function getEPPs to_pandas

def getEPPs( hoja ):
    try:
        df_epps = hoja.find_tables( clip = bx_medidas_seg )
        df_epps = df_epps.tables[0].to_pandas()
        df_epps = df_epps[['2-EQUIPOS DE PROTECCIÓN','3-ESTADO']].replace('', np.nan).dropna(how = 'all')
        df_epps = dict(zip(df_epps['2-EQUIPOS DE PROTECCIÓN'],df_epps['3-ESTADO']))

    except:
        ic(hoja)
        df_epps = "·"
    return df_epps

# Funcion getPrecauciones using get_text()

def getPrecauciones( hoja ):
    try:
        precauciones = hoja.get_text( clip = bx_precauciones ).strip()
        precauciones = precauciones.replace('PRECAUCIONES:', "").strip()
    except:
        ic({"archivo: ": hoja, "variable: ":precauciones})
        precauciones = "·"
    return precauciones

# Function getCarencias using get_text()

def getCarencias( hoja ):
    try:
        carencias = hoja.get_text( clip = bx_carencias ).strip()
        carencias = carencias.replace('CARENCIAS:', "").strip()
    except:
        ic({"archivo: ": hoja, "variable: ":carencias})
        carencias = "·"
    return carencias

# Function getFechaFinal using to_pandas

def getFechaInicioHoja1( hoja ):
    try:
        df_fecha_final = hoja.find_tables( clip = bx_firmas )
        df_fecha_final = df_fecha_final.tables[0].to_pandas()
        df_fecha_final = df_fecha_final.iloc[1,0].strip().split(':')
        df_fecha_final = df_fecha_final[1].strip()
    except:
        ic(hoja)
        df_fecha_final = "·"
    return df_fecha_final

# FUnction getFirmas to_pandas()

def getFirmas( hoja ):
    try:
        df_firmas = hoja.find_tables( clip = bx_firmas )
        df_firmas = df_firmas.tables[0].to_pandas()
        df_firmas = df_firmas.iloc[0,:].to_list()
        df_firmas = [ item for item in df_firmas if item != '' ]
        df_firmas = df_firmas[1:]
    except:
        ic(hoja)
        df_firmas = "·"
    return df_firmas

###  HOJA ACTIVIDADES

# Function getCuadrilla using get_text()

def getCuadrilla( hoja ):
    try:
        cuadrilla = hoja.get_text( clip = bx_cuadrilla ).strip()
    except:
        ic({"archivo: ": hoja, "variable: ":cuadrilla})
        cuadrilla = "·"
    return cuadrilla

# Function getKilometraje using find_tables()

def getKilometraje( hoja ):
    try:
        df_kilometraje = hoja.find_tables( clip = bx_kilometraje )
        df_kilometraje = df_kilometraje.tables[0].header.names
        kmInicio = int(df_kilometraje[2].replace(',',""))
        kmFinal = int(df_kilometraje[4].replace(',',""))
        kmRecorrido = int(df_kilometraje[6].replace(',',""))
    except:
        ic(hoja)
        kmInicio = "·"
        kmFinal = "·"
        kmRecorrido = "·"
    return kmInicio, kmFinal, kmRecorrido

# Function getActividades to_pandas()

def getActividades( hoja ):
    try:
        df_actividades = hoja.find_tables( clip = bx_actividades, strategy = 'lines_strict' )
        df_actividades = df_actividades.tables[0].to_pandas()
        df_actividades.columns = ['Item','Actividad','Descipcion','Ali','Alimentador','Tipo','FechaInicial','FechaFinal']

        while len(df_actividades.iloc[0,0]) > 2:
            df_actividades = df_actividades.drop(0)
            df_actividades = df_actividades.reset_index(drop=True)

        df_actividades['FechaInicial'] = df_actividades['FechaInicial'].str.replace('\n', ' ')
        df_actividades['FechaFinal']   = df_actividades['FechaFinal'].str.replace('\n', ' ')
        df_actividades = df_actividades.replace('', np.nan).dropna(how='all')
        df_actividades = df_actividades.replace(np.nan, "·" )
        df_actividades = df_actividades.to_dict('records')
    except:
        ic(hoja)
        df_actividades = "·"
    return df_actividades


# Function to getObservaciones using get_text()

def getObservaciones( hoja ):
    try:
        observaciones = hoja.get_text( clip = bx_observaciones ).strip()
    except:
        ic({"archivo: ": hoja, "variable: ":observaciones})
        observaciones = "·"
    return observaciones


# Function getTerminado using get_text()

def getTerminado( hoja ):
    try:
        terminado = hoja.get_text( clip = bx_terminado ).strip()
    except:
        ic({"archivo: ": hoja, "variable: ":terminado})
        terminado = "·"
    return terminado


# Function getFechaFinal using get_text()

def getFechaFinal2( hoja ):
    try:
        fechaFinal2 = hoja.get_text( clip = bx_fechaFin ).strip()
    except:
        ic({"archivo: ": hoja, "variable: ":fechaFinal2})
        fechaFinal2 = "·"
    return fechaFinal2

# Functio getAccidentes uson get_text()

def getAccidentes( hoja ):
    try:
        accidentes = hoja.get_text( clip = bx_accidentes ).strip()
    except:
        ic({"archivo: ": hoja, "variable: ":accidentes})
        accidentes = "·"
    return accidentes


####  CONVERT TO JSON


def toJSON_ot( pdf_path:str ):

    pdf = None
    OT_dict = {"VERSION" : VERSION}
    OT_dict = OT_dict | { "link" : pdf_path }

    try:
        with pymupdf.open( pdf_path ) as pdf:

            # Validación del PDF como una Orden de trabajo EERSSA
            if pdf.metadata['producer'] not in ['FPDF 1.7']:
                OT_dict = OT_dict | {"id_ot": np.nan}
                OT_dict = OT_dict | {"exito": False}
                return OT_dict

            # Extracción de los datos usando las funciones get

            OT_dict = OT_dict | { "id_ot"          : getId_Ot( pdf[0] )}
            OT_dict = OT_dict | { "cuadrilla"      : getCuadrilla( pdf[1] )}

            responsable_nombre = getResponsable( pdf[0] )
            OT_dict = OT_dict | { "responsable"    : responsable_nombre }
            
            lista_colaboradores = getColaboradores( pdf[0] )

            # Elimina el responsable del listado de colaboradores en caso de que tambien se incluya
            if responsable_nombre in lista_colaboradores["nombres"]:
                lista_colaboradores["total"] -= 1
                lista_colaboradores["nombres"] = [x for x in lista_colaboradores["nombres"] if x != responsable_nombre] 
            
            OT_dict = OT_dict | { "colaboradores"  : lista_colaboradores }

            fecha = getFechaInicio( pdf[0] )
            OT_dict = OT_dict | { "diaSemana"      : getDiaSemana( fecha )}
            OT_dict = OT_dict | { "fecha"          : toDateEcuador( fecha ) }
            OT_dict = OT_dict | { "fechaInicio"    : getFechaInicioHoja1( pdf[0] )} # Convertir a DateTimeObject compatible with BSON
            OT_dict = OT_dict | { "fechaFinal"     : getFechaFinal2( pdf[1] )}

            OT_dict = OT_dict | { "sitio"          : getSitio( pdf[0] )}
            OT_dict = OT_dict | { "descripcion"    : getDescripcion( pdf[0] )}
            OT_dict = OT_dict | { "tEstimado"      : getTiempoEstimado( pdf[0] )}
            OT_dict = OT_dict | { "vehiculo"       : getVehiculo( pdf[0] )}

            kmInicial, kmFinal, kmRecorrido = getKilometraje( pdf[1] )
            OT_dict = OT_dict | { "kmInicial"      : kmInicial}
            OT_dict = OT_dict | { "kmFinal"        : kmFinal}
            OT_dict = OT_dict | { "kmRecorrido"    : kmRecorrido}

            OT_dict = OT_dict | { "trabajo"        : getTiposTrabajo( pdf[0] )}
            OT_dict = OT_dict | { "riesgos"        : getRiesgos( pdf[0] )}
            OT_dict = OT_dict | { "seguridad"      : getMedidasSeguridad( pdf[0] )}
            OT_dict = OT_dict | { "epps"           : getEPPs( pdf[0] )}
            OT_dict = OT_dict | { "precauciones"   : getPrecauciones( pdf[0] )}
            OT_dict = OT_dict | { "carencias"      : getCarencias( pdf[0] )}
            OT_dict = OT_dict | { "accidente"      : getAccidentes( pdf[1] )}
            OT_dict = OT_dict | { "observaciones"  : getObservaciones( pdf[1] )}
            OT_dict = OT_dict | { "numeracion"     : getNumeracion( pdf[0] )}
            OT_dict = OT_dict | { "gerencia"       : getGerencia( pdf[0] )}
            OT_dict = OT_dict | { "estado"         : getTerminado( pdf[1] )}
            OT_dict = OT_dict | { "firmas"         : getFirmas( pdf[0] )}
            OT_dict = OT_dict | { "actividades"    : getActividades( pdf[1])}

            if pdf.page_count > 2: # Funciona para OTs con mas de dos hojas
                for x in range(2, pdf.page_count):
                    OT_dict["actividades"].append( getActividades( pdf[x] ) )

            OT_dict = OT_dict | { "exito"          : True }

    except:
        ic(pdf_path)
        OT_dict = OT_dict | { "exito": False }

    return OT_dict


def convertPDFList( list_pdfs ):

  try:
    results = []
    for file in list_pdfs:
      result = client.submit(toJSON_ot, file)
      results.append(result)

    ic.disable()  
    results = client.gather(results)
    ic.enable()
    return results
    
  
  except:
    ic.enable()
    return False 

