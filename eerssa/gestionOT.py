from .constants import BoxesValues
from .constants import Current
from datetime import datetime
from pytz import timezone
from pprint import pprint

import os
import traceback

import pymupdf
from   pymupdf import Rect

import pandas as pd
pd.set_option("future.no_silent_downcasting", True)
import numpy as np

# Default character when a text field is missing, 
# I chose this character because np.nan is ugly
DEFAULT_EMPTY_CHAR = "·"

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
    return local_datetime

  except Exception as e:
      return e
      

def getDiaSemana( fechaInicio ):
  try:
    return fechaInicio.split(',')[0]
  except Exception as e:
    return e
    

# this function defines if the directory is a PDF and from a valid producer:
# as of v0.10.2 there is support for FPFD 1.7 and pdf24
def isOT( pdf_path ):
  
  pdf = None

  try: 
    with pymupdf.open( pdf_path ) as pdf:

      if pdf.metadata['producer'] not in ['FPDF 1.7','PDF24']:
        return pdf.metadata['producer']
      
      if ( pdf.page_count < 4 ):       
        return True
      else:
        return pdf.page_count # Log error, too many pages.
  
  except Exception as e:
    return e  # Log error, not a valid "Orden de Trabajo PDF"


# CLASS DEFINITION

class GestionOt:
  
  VERSION = Current.VERSION.value


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


  # init method or constructor
  def __init__(self, link_to_pdf):
    self.link       = link_to_pdf
    self.version    = self.VERSION 
    self.createdAt  = None
    self.modifiedAt = []
    self.id_ot      = 0
    self.log        = []
    self.n_fallas   = 0
    self.n_errores  = 0
    self.n_revisar  = 0
    self.n_info     = 0
    self.data       = {}    # JSON for MongoDB
    self.matriz     = None  # Matriz de Actividades Pandas Dataframe

    analisis_pdf    = isOT(link_to_pdf)

    if analisis_pdf == True:
      self.valido = True
      return

    if isinstance(analisis_pdf, str):
      producer_entry = {
                  "t": datetime.now().isoformat(),
                  "level"  : "FATAL",
                  "message": "El archivo PDF se encuentra en un formato no reconocido",
                  "detail" : f"Formato PDF: {analisis_pdf}"
      }
      self.log.append( producer_entry )
      self.n_fallas = 1
      self.valido = False
      return

    if isinstance(analisis_pdf, int):
      pages_entry = {
                  "t": datetime.now().isoformat(),
                  "level"  : "FATAL",
                  "message": "El archivo PDF tiene un numero no soportado de hojas",
                  "detail" : f"Hojas PDF: {analisis_pdf}"
      }
      self.log.append( pages_entry )
      self.n_fallas = 1
      self.valido = False
      return

    if isinstance( analisis_pdf, Exception ):
        falla_entry = {
                  "t": datetime.now().isoformat(),
                  "level"  : "FATAL",
                  "message": "El archivo indicado no es una Orden de Trabajo",
                  "detail" : link_to_pdf
        }
        self.log.append(falla_entry)
        self.n_fallas = 1
        return

  def DrawBoxesOt( self ):
    """ 
    Draw the fields with information to be extracted.

    :param str inputPDF_path: Path to the PDF File to be drawn uppon
    :return: The path to the created file, same directory as input or FALSE
    """
    try:
      doc = pymupdf.open( self.link )

      page_one = doc[0].new_shape()

      page_one.draw_rect( self.bx_id_ot          )
      page_one.draw_rect( self.bx_numero_ot      )
      page_one.draw_rect( self.bx_gerencia       )
      page_one.draw_rect( self.bx_sitio          )
      page_one.draw_rect( self.bx_fechaInicial_1 )
      page_one.draw_rect( self.bx_responsable       )
      page_one.draw_rect( self.bx_nombresColaboradores )
      page_one.draw_rect( self.bx_cargosColaboradores )
      page_one.draw_rect( self.bx_vehiculoHoja1  )
      page_one.draw_rect( self.bx_tipos_trabajo  )
      page_one.draw_rect( self.bx_descripcion )
      page_one.draw_rect( self.bx_fechaInicio_Testimado )
      page_one.draw_rect( self.bx_riesgos_epps )
      page_one.draw_rect( self.bx_medidas_seg )
      page_one.draw_rect( self.bx_precauciones )
      page_one.draw_rect( self.bx_carencias )
      page_one.draw_rect( self.bx_firmas )

      page_two = doc[1].new_shape()

      page_two.draw_rect( self.bx_cuadrilla )
      page_two.draw_rect( self.bx_vehiculo  )
      page_two.draw_rect( self.bx_kilometraje )
      page_two.draw_rect( self.bx_actividades )
      page_two.draw_rect( self.bx_observaciones )
      page_two.draw_rect( self.bx_terminado )
      page_two.draw_rect( self.bx_fechaFin )
      page_two.draw_rect( self.bx_accidentes )

      page_one.finish( color=(1, 0, 0), fill=None )
      page_two.finish( color=(1, 0, 0), fill=None )
      page_one.commit()
      page_two.commit()

      result = os.path.dirname(self.link)+ "/CAMPOS_version_"+ self.VERSION + ".pdf"

      doc.save(result)

      return result
    
    except:
      return False

  def Log2Ot( self, level, message, detail ):
    entry = {
      "t": datetime.now().isoformat(),
      "level"  : level,
      "message": message,
      "detail" : detail
    }
    self.log.append(entry)

    match level:
      case "FATAL":
        self.n_fallas += 1      
      case "ERROR":
        self.n_errores += 1
      case "REVISAR":
        self.n_revisar += 1
      case "INFO":
        self.n_info += 1
      case _:
        pass

  def load_ot( self ):
    try:
      with pymupdf.open( self.link ) as pdf:

        # Is it a Valid OT ?
        if self.valido == False:

          # Cannot create on an invalid OT
          self.Log2Ot("INFO", "No es posible la creacion de la OT", "No se puede crear una OT que no es valida")
          self.createdAt = datetime.now().isoformat(),
          return         # EXIT no more processing needed
        
        else: 
          # Log the creation of the OT
          self.Log2Ot("INFO", "Creacion de la OT", "Ninguno")
          self.createdAt = datetime.now().isoformat(),

        # 1. id_ot
        id_ot = self.getId_Ot( pdf[0], self.bx_id_ot )         
        
        if isinstance(id_ot, Exception):
          self.Log2Ot( "ERROR", "El archivo no tiene un ID automatico del sistema Intranet", traceback.format_exc( id_ot ) )
          return
        
        self.id_ot = id_ot
        
        self.data["version"] = self.version
        self.data["link"] = self.link
        self.data["id_ot"] = id_ot
        self.data["exito"] = self.valido
        
        # 2. cuadrilla
        cuadrilla = self.getCuadrilla( pdf[1], self.bx_cuadrilla )
        if isinstance( cuadrilla, Exception):
          self.Log2Ot( "REVISAR", "No se ha podido encontrar el nombre de CUADRILLA", traceback.format_exc( cuadrilla ) )
          self.data.update( {"cuadrilla" : DEFAULT_EMPTY_CHAR} )
        else:
          self.data.update( {"cuadrilla" : cuadrilla} )

        # 3. responsable
        responsable = self.getResponsable( pdf[0], self.bx_responsable )
        if isinstance( responsable, Exception ):
          self.Log2Ot( "ERROR", "No se ha podido encontrar el nombre del RESPONSABLE", traceback.format_exc( responsable ) )
          self.data.update( {"responsable" : DEFAULT_EMPTY_CHAR} )
        else:
          self.data.update( {"responsable" : responsable} )

        # 4. colaboradores TODO: verificar comportamiento
        lista_colaboradores = self.getColaboradores( pdf[0], self.bx_nombresColaboradores, self.bx_cargosColaboradores )
        if isinstance( lista_colaboradores, Exception ):
          self.Log2Ot( "REVISAR", "No se ha podido encontrar COLABORADORES", traceback.format_exc( lista_colaboradores ) )
          
          lista_colaboradores = {}
          lista_colaboradores['total'] = 0
          lista_colaboradores['nombres'] = []
          self.data.update( {"colaboradores" : lista_colaboradores} )
          
        else:
          if responsable in lista_colaboradores["nombres"]:
            lista_colaboradores["total"] -= 1
            lista_colaboradores["nombres"] = [x for x in lista_colaboradores["nombres"] if x != responsable] 
          self.data.update( {"colaboradores" : lista_colaboradores} )

        # 5. fecha de Inicio - Hoja 1
        fecha = self.getFechaInicio( pdf[0], self.bx_fechaInicial_1 )
        if isinstance( fecha, Exception):
          self.Log2Ot( "ERROR", "No se ha encontrado Fecha Inicial en la Hoja 1", traceback.format_exc( fecha ) )
          self.data.update({"diaSemana" : DEFAULT_EMPTY_CHAR, "fecha" : DEFAULT_EMPTY_CHAR })
        else:
          diaSemana = getDiaSemana( fecha )
          if isinstance( diaSemana, Exception ):
            self.Log2Ot( "ERROR", "No se ha podido convertir la Fecha a DIA SEMANA", traceback.format_exc( diaSemana ) )
            self.data.update({"diaSemana" : DEFAULT_EMPTY_CHAR })
          else:
            self.data.update({"diaSemana" : diaSemana })
          fechaObject = toDateEcuador( fecha )
          if isinstance( fechaObject, Exception ):
            self.Log2Ot( "ERROR", "No se ha podido convertir la Fecha a DATE-TIME", traceback.format_exc( fechaObject ) )
            self.data.update({"fecha" : DEFAULT_EMPTY_CHAR })
          else:
            self.data.update({"fecha" : fechaObject })
        
        # 6. fecha de Inicio - String
        fechaStr = self.getFechaInicioHoja1( pdf[0], self.bx_firmas )
        if isinstance( fechaStr, Exception ):
          self.Log2Ot( "ERROR", "No se ha encontrado FECHA LARGA en la Hoja1, seccion FIRMAS", traceback.format_exc(fechaStr) )
          self.data.update({"fechaInicio":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"fechaInicio":fechaStr})

        # 7. Fecha Final - String
        fechaFinal = self.getFechaFinal2( pdf[1], self.bx_fechaFin )
        if isinstance(fechaFinal, Exception):
          self.Log2Ot("REVISAR", "No se ha encontrado FECHA FINAL en la Hoja2", traceback.format_exc(fechaStr))
        else:
          self.data.update({"fechaFinal":fechaFinal})

        # 8. Sitio
        sitio = self.getSitio( pdf[0], self.bx_sitio )
        if isinstance( sitio, Exception ):
          self.Log2Ot( "REVISAR", "No se ha encontrado SITIO en la Hoja1", traceback.format_exc(sitio) )
          self.data.update({"sitio":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"sitio":sitio})
        
        # 9. Descripcion
        descripcion = self.getDescripcion( pdf[0], self.bx_descripcion )
        if isinstance( descripcion, Exception ):
          self.Log2Ot( "REVISAR", "No se ha encontrado DESCRIPCION en la Hoja 1", traceback.format_exc(descripcion) )
          self.data.update({"descripcion":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"descripcion":descripcion})

        # 10. Tiempo Estimado
        tEstimado = self.getTiempoEstimado( pdf[0], self.bx_fechaInicio_Testimado )
        if isinstance( tEstimado, Exception ):
          self.Log2Ot( "REVISAR", "No se ha encontrado NUMERO DE HORAS estimadas en la Hoja 1", traceback.format_exc(tEstimado))
          self.data.update({"tEstimado":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"tEstimado":tEstimado})


        # 11. Vehiculo
        vehiculo = self.getVehiculo( pdf[0], self.bx_vehiculoHoja1 )
        if isinstance( vehiculo,Exception ):
          self.Log2Ot( "REVISAR", "No se ha encontrado DATOS VEHICULO en la Hoja 1", traceback.format_exc(vehiculo) )
          self.data.update({"vehiculo":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"vehiculo":vehiculo})

        # 12. Kilometrajes
        try:
          kmInicial, kmFinal, kmRecorrido = self.getKilometraje( pdf[1], self.bx_kilometraje )
          self.data.update({"kmInicial": kmInicial, "kmFinal":kmFinal, "kmRecorrido":kmRecorrido})
        except Exception as noKm:
          self.Log2Ot( "REVISAR", "No se ha podido obtener datos de KILOMETRAJE en la Hoja 2", traceback.format_exc(noKm))
          self.data.update({"kmInicial": DEFAULT_EMPTY_CHAR, "kmFinal":DEFAULT_EMPTY_CHAR, "kmRecorrido":DEFAULT_EMPTY_CHAR})
        
        # 13. Tipos de Trabajo
        trabajo = self.getTiposTrabajo( pdf[0], self.bx_tipos_trabajo )
        if isinstance( trabajo, Exception ):
          self.Log2Ot( "ERROR", "No se ha podido obtener TIPOS DE TRABAJO de la Hoja 1", traceback.format_exc( trabajo ) )
          self.data.update({"trabajo":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"trabajo":trabajo})

        # 14. Riesgos del trabajo
        riesgos = self.getRiesgos( pdf[0], self.bx_riesgos_epps )
        if isinstance( riesgos, Exception ):
          self.Log2Ot( "ERROR", "No se ha podido obtener RIGESGOS DE TRABAJO de la Hoja 1", traceback.format_exc( riesgos ) )
          self.data.update({"riesgos":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"riesgos":riesgos})

        # 15. Medidas de Seguridad
        seguridad = self.getMedidasSeguridad( pdf[0], self.bx_medidas_seg )
        if isinstance( seguridad, Exception ):
          self.Log2Ot( "ERROR", "No se ha podido obtener MEDIDAS DE SEGURIDAD de la Hoja 1", traceback.format_exc( seguridad ))
          self.data.update({"seguridad":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"seguridad":seguridad})

        # 16. EPPs

        epps = self.getEPPs( pdf[0], self.bx_medidas_seg )
        if isinstance( epps, Exception ):
          self.Log2Ot( "ERROR", "No se ha podido obtener EPPS de la Hoja 1", traceback.format_exc( epps ))
          self.data.update({"epps":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"epps":epps})

        # 17. Precauciones
        precauciones = self.getPrecauciones( pdf[0], self.bx_precauciones )
        if isinstance( precauciones, Exception ):
          self.Log2Ot( "REVISAR", "No se ha encontrado texto de PRECACIONES en la Hoja 1", traceback.format_exc( precauciones ))
          self.data.update( {"precauciones": DEFAULT_EMPTY_CHAR })
        else:
          self.data.update( {"precauciones": precauciones })

        # 18. Carencias
        carencias = self.getCarencias( pdf[0], self.bx_carencias )
        if isinstance( carencias, Exception ):
          self.Log2Ot( "REVISAR", "No se ha encontrado texto de CARENCIAS en la Hoja 1", traceback.format_exc( carencias ) )
          self.data.update({"carencias":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"carencias":carencias})

        # 19. Accidente
        accidente = self.getAccidentes( pdf[1], self.bx_accidentes)
        if isinstance( accidente, Exception ):
          self.Log2Ot( "REVISAR", "No se ha encontrado texto de ACCIDENTE en la Hoja 2", traceback.format_exc(accidente))
          self.data.update({"accidente":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"accidente":accidente})

        # 20. Observaciones
        observaciones = self.getObservaciones( pdf[1], self.bx_observaciones )
        if isinstance( observaciones, Exception ):
          self.Log2Ot( "REVISAR", "No se ha encontrado texto de OBSERVACIONES en la Hoja 1", traceback.format_exc(observaciones))
          self.data.update({"observaciones":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"observaciones":observaciones})

        #21. Numeracion Manual
        numeracion = self.getNumeracion( pdf[0], self.bx_numero_ot)
        if isinstance( numeracion, Exception ):
          self.Log2Ot("REVISAR", "No se ha encontrado NUMERACION en la Hoja 1", traceback.format_exc(numeracion))
          self.data.update({"numeracion":DEFAULT_EMPTY_CHAR} )
        else:
          self.data.update({"numeracion":numeracion} )
        
        #22. Gerencia
        gerencia = self.getGerencia( pdf[0], self.bx_gerencia )
        if isinstance( gerencia, Exception ):
          self.Log2Ot("ERROR", "No se ha encontrado GERENCIA en la Hoja 1", traceback.format_exc(gerencia))
          self.data.update({"gerencia":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"gerencia":gerencia})

        # 23. Estado
        estado = self.getTerminado( pdf[1], self.bx_terminado )
        if isinstance( estado, Exception ) :
          self.Log2Ot("ERROR", "No se ha encontrado el ESTADO en la Hoja 2", traceback.format_exc(estado))
          self.data.update({"estado":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"estado":estado})

        # 24. Firmas
        firmas = self.getFirmas( pdf[0], self.bx_firmas )
        if isinstance( firmas, Exception ):
          self.Log2Ot("ERROR", "No se ha encontrado FIRMAS en la Hoja 1", traceback.format_exc(firmas))
          self.data.update({"firmas":DEFAULT_EMPTY_CHAR})
        else:
          self.data.update({"firmas":firmas})

        # 25. ACTIVIDADES
        actividades = self.getActividades( pdf[1], self.bx_actividades )
        if isinstance( actividades, Exception ):
          self.Log2Ot("FATAL", "No se ha podido extraer ACTIVIDADES en la Hoja 2", traceback.format_exc(actividades))
          self.data.update({"actividades":DEFAULT_EMPTY_CHAR})
        
        elif len(actividades)== 0:
          self.Log2Ot("FATAL", "No se ha podido extraer ACTIVIDADES en la Hoja 2", 'No se ha llenado las actividades')
          self.data.update({"actividades":DEFAULT_EMPTY_CHAR})
          
        else:
          if pdf.page_count > 1:
            for x in range(2, pdf.page_count):
              extra_actividades = self.getActividades( pdf[x], self.bx_actividades )
              if isinstance( extra_actividades, Exception ):
                pass
              elif len(extra_actividades) == 0:
                pass # Do not add empty arrays, empte second page
              else:
                actividades.extend(extra_actividades)
          
        self.data.update({"actividades":actividades})

        # NUMERO DE LOGS CREADOS
        self.data.update({
          "n_fallas"  : self.n_fallas,
          "n_errores" : self.n_errores,
          "n_revisar" : self.n_revisar,
          "n_info"    : self.n_info
        })

        return self
        
    except Exception as e:
      self.Log2Ot( "FATAL", "Error desde la funcion load_Ot()", traceback.format_exception(e) )
      return self
    
    # END OF load_ot()

  def getId_Ot( self, hoja, box ):
    try:
      texto = hoja.get_text( clip = box )
      id_ot = texto
      id_ot = id_ot.split('\n')[1].replace(',',"")
      id_ot = int(id_ot)
      return id_ot
    
    except Exception as e:
      return e
    
  def getNumeracion( self, hoja, box ):
    try:
      texto = hoja.get_text( clip = box )
      numeracion = texto
      numeracion = numeracion.replace('NM:', "").replace(',', "").strip()
      return int(numeracion)

    except Exception as e:
      return e
    
  def getGerencia( self, hoja, box ):
    try:
      return hoja.get_text( clip = box ).strip()
    except Exception as e:
      return e
      

  def getSitio( self, hoja, box ):
    try:
      return hoja.get_text( clip = box ).strip()
    except Exception as e:
      return e
      

  def getFechaInicio( self, hoja, box ):
    try:
      return hoja.get_text( clip = box ).strip()
    except Exception as e:
      return e      


  def getResponsable( self, hoja, box ):
    try:
      texto = hoja.get_text( clip = box)
      df_personal = texto
      df_personal = df_personal.strip().split('\n')
      responsable = [df_personal[0],df_personal[1]]
      return responsable
    except Exception as e:
      return e
      

  def getColaboradores( self, hoja, box_colab, box_cargos ):
    try:
      texto = hoja.get_text( clip = box_colab )
      df_personal = texto
      df_personal = df_personal.strip().split('\n')
      df_personal = [ item for item in df_personal if item != '' ]

      data = hoja.get_text( clip = box_cargos )
      df_cargos = data
      df_cargos = df_cargos.strip().split('\n')
      df_cargos = [ item for item in df_cargos if item != '' ]

      totalColaboradores = len(df_personal)

      colaboradores = []

      for i in range(totalColaboradores):
        colaboradores.append([df_personal[i],df_cargos[i]])

      respuesta = {}
      respuesta['total'] = totalColaboradores
      respuesta['nombres'] = colaboradores
      
      return respuesta

    except Exception as e:
      return e


  def getVehiculo( self, hoja, box ):
    try:
      texto = hoja.get_text( clip = box ).strip().split('\n')
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

      return data_vehiculo

    except Exception as e:
      return e
      

  def getTiposTrabajo( self, hoja, box ):
    try:
      df_tipos_trabajo = hoja.find_tables( clip = box )
      df_tipos_trabajo = df_tipos_trabajo.tables[0].to_pandas()
      df_tipos_trabajo = df_tipos_trabajo.to_numpy().flatten()
      df_tipos_trabajo = [ item for item in df_tipos_trabajo if item != '' ]
      return df_tipos_trabajo

    except Exception as e:
      return e
      

  def getDescripcion( self, hoja, box ):
    try:
      return hoja.get_text( clip = box ).strip()
    except Exception as e:
      return e
      

  def getFechaInicio2( self, hoja, box ):

    find_word_index = lambda word_list, target_word: word_list.index(target_word) if target_word in word_list else -1

    try:
      texto = hoja.get_text( clip = box ).strip().split('\n')
      fechaInicio2 = texto
      index = find_word_index(fechaInicio2, 'TIEMPO ESTIMADO DE DURACIÓN (HORAS):')

      if index != -1:
        fechaInicio2 = fechaInicio2[index - 1]
      else:
        fechaInicio2 = "·"
      return fechaInicio2

    except Exception as e:
      return e
      

  def getTiempoEstimado( self, hoja, box ):

    find_word_index = lambda word_list, target_word: word_list.index(target_word) if target_word in word_list else -1

    try:
      texto = hoja.get_text( clip = box ).strip().split('\n')
      Testimado = texto
      index = find_word_index(Testimado, 'TIEMPO ESTIMADO DE DURACIÓN (HORAS):')

      if index != -1:
        Testimado = Testimado[index + 1]
      else:
        Testimado = "·"
      return Testimado

    except Exception as e:
      return e
      

  def getRiesgos(self, hoja, box ):
    riesgos_dict = {}
    try:
      df_riesgos = hoja.find_tables( clip = box )
      df_riesgos = df_riesgos.tables[0].to_pandas().replace('', np.nan).dropna(how = 'all')
      for _, row in df_riesgos.iterrows():
        key = row['RIESGOS EXISTENTES:']
        value = [row[col] for col in df_riesgos.columns if col != 'RIESGOS EXISTENTES:']
        riesgos_dict[key] = value

      return riesgos_dict
    except Exception as e:
      return e
          

  def getMedidasSeguridad( self, hoja, box ):
    try:
      df_medidas_seg = hoja.find_tables( clip = box )
      df_medidas_seg = df_medidas_seg.tables[0].to_pandas()
      df_medidas_seg = df_medidas_seg[['0-MEDIDAS','1-ESTADO']].replace('', np.nan).dropna(how = 'all')
      df_medidas_seg = dict(zip(df_medidas_seg['0-MEDIDAS'],df_medidas_seg['1-ESTADO']))

      return df_medidas_seg

    except Exception as e:
      return e
        

  def getEPPs( self, hoja, box ):
    try:
      df_epps = hoja.find_tables( clip = box )
      df_epps = df_epps.tables[0].to_pandas()
      df_epps = df_epps[['2-EQUIPOS DE PROTECCIÓN','3-ESTADO']].replace('', np.nan).dropna(how = 'all')
      df_epps = dict(zip(df_epps['2-EQUIPOS DE PROTECCIÓN'],df_epps['3-ESTADO']))
      return df_epps

    except Exception as e:
      return e
        

  def getPrecauciones( self, hoja, box ):
    try:
      precauciones = hoja.get_text( clip = box ).strip()
      precauciones = precauciones.replace('PRECAUCIONES:', "").strip()
      return precauciones
    
    except Exception as e:
      return e
    

  def getCarencias( self, hoja, box ):
    try:
      carencias = hoja.get_text( clip = box ).strip()
      carencias = carencias.replace('CARENCIAS:', "").strip()
      return carencias

    except Exception as e:
      return e
      

  def getFechaInicioHoja1( self, hoja, box ):
    try:
      df_fecha_final = hoja.find_tables( clip = box )
      df_fecha_final = df_fecha_final.tables[0].to_pandas()
      df_fecha_final = df_fecha_final.iloc[1,0].strip().split(':')
      df_fecha_final = df_fecha_final[1].strip()
      return df_fecha_final

    except Exception as e:
      return e


  def getFirmas( self, hoja, box ):
    try:
      df_firmas = hoja.find_tables( clip = box )
      df_firmas = df_firmas.tables[0].to_pandas()
      df_firmas = df_firmas.iloc[0,:].to_list()
      df_firmas = [ item for item in df_firmas if item != '' ]
      df_firmas = df_firmas[1:]
      return df_firmas

    except Exception as e:
      return e
      

  def getCuadrilla( self, hoja, box ):
    try:
        return hoja.get_text( clip = box ).strip()
    except Exception as e:
      return e
          

  def getKilometraje( self, hoja, box ):
    try:
        df_kilometraje = hoja.find_tables( clip = box )
        df_kilometraje = df_kilometraje.tables[0].header.names
        
        kmInicio = int(df_kilometraje[2].replace(',',""))
        kmFinal = int(df_kilometraje[4].replace(',',""))
        kmRecorrido = int(df_kilometraje[6].replace(',',""))
        
        return kmInicio, kmFinal, kmRecorrido

    except Exception as e:
      return e
        

  def getActividades( self, hoja, box ):
    try:
      df_actividades = hoja.find_tables( clip = box, strategy = 'lines_strict' )
      df_actividades = df_actividades.tables[0].to_pandas()
      df_actividades.columns = ['Item','Actividad','Evento','Ali','Alimentador','Tipo','InicioEvento','FinEvento']

      while len(df_actividades.iloc[0,0]) > 2:
        df_actividades = df_actividades.drop(0)
        df_actividades = df_actividades.reset_index(drop=True)

      df_actividades['InicioEvento'] = df_actividades['InicioEvento'].str.replace('\n', ' ')
      df_actividades['FinEvento']   = df_actividades['FinEvento'].str.replace('\n', ' ')
      df_actividades = df_actividades.replace('', pd.NA).dropna(how='all')
      df_actividades = df_actividades.to_dict('records')
      return df_actividades

    except Exception as e:
      return e
      

  def getObservaciones( self, hoja, box ):
    try:
      observaciones = hoja.get_text( clip = box ).strip()
      return observaciones

    except Exception as e:
      return e


  def getTerminado( self, hoja, box ):
    try:
        return hoja.get_text( clip = box ).strip()
    except Exception as e:
      return e
    

  def getFechaFinal2( self, hoja, box ):
    try:
      return hoja.get_text( clip = box ).strip()
    except Exception as e:
      return e
      

  def getAccidentes( self, hoja, box ):
    try:
      return hoja.get_text( clip = box ).strip()
    except Exception as e:
      return e
    

