import pandas as pd
import uuid

from   os.path import basename

import nltk
from nltk.probability import FreqDist
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn import metrics


import re

"""Convertimos el Dataframe multidimensional a un formato de Matriz (2D) Filas-Columnas, 
durante la transformación se ejecutan correcciones más frecuentes, fechas, horas, 
con la intención de que la matriz sea lo más correcta posible. 

Los cambios realizados serán registrados en la sección de LOG.txt.

Se transforma el texto expandiendo las abreviaciones y errores comunes de escritura.

A partir de esta matriz se generará los Informes y se podra Exportar/Importar a Excel 
para la revisión manual y actualización de OT.
"""


#nltk.download('stopwords')
#nltk.download('punkt')
#stopword_es = nltk.corpus.stopwords.words('spanish')


# ORGANIZAR ACTIVIDADES

def organizarActividades( obj_ot ):


  ot_df = obj_ot.data
  actividades = pd.DataFrame( obj_ot.data['actividades'] )
  
  if len(actividades) == 0:
    return actividades

  actividades = actividades[actividades.Evento.notnull()]
  actividades = actividades.reset_index()

  #····························································
  #        Validar y Corregir Fecha y Hora.
  #····························································


  try:

    fInicio = actividades[['Item','InicioEvento','FinEvento']].dropna()
    fInicio['solofechaI'] = fInicio['InicioEvento'].apply( lambda x: re.findall( '\d{4}-\d{2}-\d{2}', x)[0])
    
    fechaModa = fInicio.solofechaI.mode().values[0] # fecha 'moda' en el arreglo

  except:
    # En aquellas OT solo informativas, que no tienen puesto una fecha en las
    # actividades, primero intentamos tomar la fecha de inicio, sino, la fecha final
    # sino una fecha de referencia.
    if( ot_df['fecha'] != "·" ):
      fechaModa = ot_df['fecha'].strftime('%Y-%m-%d %H:%M:%S').split(' ')[0]
      obj_ot.Log2Ot("INFO", "No se encontro fecha en las actividades", "Se utiliza la fecha de Inicio en la Hoja 1")
    elif( ot_df['fechaFinal'] != "·" ):
      obj_ot.Log2Ot("INFO", "No se encontro fecha en la Hoja 1", "Se utiliza la fecha final en la Hoja 2")
      fechaModa = ot_df['fechaFinal'].split()[0] 
    else:
      fechaModa = '16/09/1988' # no es posible obtener una fecha.
      obj_ot.Log2Ot("FATAL", "No se encontro fecha en la ot", "No se ha podido determinar ninguna fecha en la OT")


  #····························································
  #        Etiquetar eventos 'LABORA'
  #·························································"""

  # Sub datafram with only rows where Actividad is null
  etiq_labora = actividades.query( 'Actividad.isnull()', engine = 'python' )

  try:

    #  |SE LAB___  // mayusculas o minusculas
    etiq_SE_LABORA = etiq_labora.Evento.str.contains('^se lab', case = False, regex = True )
    index_labora = etiq_SE_LABORA[etiq_SE_LABORA].index.values

    for fila in index_labora:
      actividades.at[fila,'Actividad'] = 'LABORA'
      actividades.at[fila,'InicioEvento'] = fechaModa + " 00:00:01"
      actividades.at[fila,'FinEvento'] = fechaModa + " 00:00:02"


    #  |Labora_  // mayusculas o minusculas
    etiq_LABORA = etiq_labora.Evento.str.contains('^labora ', case = False, regex = True )
    index_labora = etiq_LABORA[etiq_LABORA].index.values

    for fila in index_labora:
      actividades.at[fila,'Actividad'] = 'LABORA'
      actividades.at[fila,'InicioEvento'] = fechaModa + " 00:00:01"
      actividades.at[fila,'FinEvento'] = fechaModa + " 00:00:02"

  except:
    index_labora = None
    obj_ot.Log2Ot("REVISAR", "No se encontro SE LABORA", "No se encontro evento que al principio indique: SE LABORA")



  #····························································
  #          Etiquetar eventos 'INFO'
  #·························································"""

  indexIni = 0

  # ¿Es el primer Item Informativo. ej DIA FESTIVO?.
  if( pd.isna(actividades['InicioEvento'][0]) 
          and   pd.isna(actividades['FinEvento'][0]) ):

    actividades.at[indexIni,'Actividad'] = 'INFO'
    actividades.at[indexIni,'InicioEvento'] = fechaModa + " 00:00:01"
    actividades.at[indexIni,'FinEvento'] = fechaModa + " 00:00:02"

    #"""····························································
    #        Organización de Fechas y Hora 'YQ'
    #
    #   En el caso de existir "huecos" en las actividades, se las
    #   rellena con la siguiente válida, sea Inicial o Final, no
    #   importa, se toma la siguiente válida y se la llena
    #····························································"""


  #   | -- | o  |  =>   |  o  |  o  |
  #   caso especial, primera fila sin Hora Inicial. Se duplica y dt = 0
  if( pd.isna(actividades['InicioEvento'][0]) 
          and not pd.isna(actividades['FinEvento'][0])  ):
      actividades.at['InicioEvento'][0] = actividades.at['FinEvento'][0]
      obj_ot.Log2Ot("REVISAR", "Falta llenar una hora", "Falta llenar la hora final de la Primera Actividad")

  #   |  o | o  |  =>   |  o  |  o  |
  #   | -- | o  |  =>   |  o  |  o  |

  ulitmaFechaCorrecta = None
  filaDondeFalta = None
  fechaQueFalta = None

  for fila in actividades.index:

    # | o | o |   Ambas fechas correctas
    if( not pd.isna(actividades['InicioEvento'][fila]) 
        and not pd.isna(actividades['FinEvento'][fila]) ):

      ulitmaFechaCorrecta = actividades['FinEvento'][fila]

      if( filaDondeFalta != None  ): # Hay un hueco por llenar

        if( fechaQueFalta == 'InicioEvento' ):
          actividades.at[filaDondeFalta,'InicioEvento'] = actividades['FinEvento'][fila]
        elif( fechaQueFalta == 'FinEvento' ):
          actividades.at[filaDondeFalta,'FinEvento'] = actividades['InicioEvento'][fila]

        filaDondeFalta = None
        fechaQueFalta = None

    # | - | o |
    if( pd.isna(actividades['InicioEvento'][fila]) 
        and not pd.isna(actividades['FinEvento'][fila]) ):

      ulitmaFechaCorrecta = actividades['FinEvento'][fila]

      if( filaDondeFalta == None ): # No hay huecos previos, reportar este como Hueco
        filaDondeFalta = fila
        fechaQueFalta = 'InicioEvento'
      else:                       # Mover la fechaFinal a la que falta

        actividades.at[filaDondeFalta,fechaQueFalta]= actividades['FinEvento'][fila]

        actividades.at[fila,'FinEvento'] = float('NaN')
        filaDondeFalta = None
        fechaQueFalta = None

    # | o | - |
    if( pd.isna(actividades['InicioEvento'][fila]) 
        and pd.isna(actividades['FinEvento'][fila]) ):

      ulitmaFechaCorrecta = actividades['InicioEvento'][fila]

      if( filaDondeFalta == None ): # No hay huecos previos, reportar este como Hueco
        filaDondeFalta = fila
        fechaQueFalta = 'FinEvento'
      else:                       # Mover la fechaInicial a la que falta

        actividades.at[filaDondeFalta,fechaQueFalta] = actividades['InicioEvento'][fila]
        actividades.at[fila,'InicioEvento'] = float('NaN')
        filaDondeFalta = None
        fechaQueFalta = None


  #"""····························································
  #    Consolidar Items adicionales en uno solo
  #·······························································"""
  backup = actividades

  try:

    for iteraciones in range( actividades['InicioEvento'].isna().sum() ):
      fila = 1
      totalIdx = len(actividades.index)

      while fila < totalIdx:
        if pd.isna(actividades.at[actividades.index[fila],'InicioEvento']):  # AND or OR ?
          data = actividades.at[ actividades.index[fila-1],'Evento' ]
          actividades.at[ actividades.index[fila-1],'Evento' ] = data + '\r' + actividades.at[ actividades.index[fila],'Evento' ]
          actividades = actividades.drop(actividades.index[fila])
          fila = totalIdx
        
        fila = fila + 1

        """ Lo programo de esta manera ya que al hacer el Drop no se actualizan los indices
          si uso un lazo FOR. Al hacerlo de esta manera cada vez leo los indices tomando
          en cuenta aquellos que ya elimine. y funciona.
        """

    actividades.Item = actividades.Item.astype(int)

  except:

    actividades = backup
    obj_ot.Log2Ot("ERROR", "No se consolidaron actividades", "Ocurrio un error al consolidar las actividades")

  return actividades



























# CONVERTIR OT A MATRIZ DE ACTIVIDADES

def ConvertirOT_a_ActividadesCSV( obj_ot ):

  """ Convierte una fila del Dataframe que contiene las OTs y
    devuelve un nuevo dataframe exponienda cada una de las
    actividades de acuerdo al formato descrito.
  """

  ot_df = obj_ot.data 

  if ot_df['exito'] != True:
    return False

  if ot_df['actividades'] == "·":
    return False

  # campos generales a cada una de las Actividad
  cuadrilla     = ot_df['cuadrilla']
  primario      = 'No'    # Se obtendrá del SIG (Sistema de Info Geograf)
  horasExtra    = 'No'    # Actividad fuera de horario normal
  desconexion   = 'No'    # ML
  id_ot         = ot_df['id_ot']
  responsable   = ot_df['responsable'][0]
  colaboradores = ot_df['colaboradores']['total']
  vehiculo      = ot_df['vehiculo']['numero']
  sitio         = ot_df['sitio']
  dia           = ot_df['diaSemana']  # solo el nombre del dia de labores: lunes, martes, ...
  fecha         = ot_df['fecha'].strftime('%Y-%m-%d %H:%M:%S')  # Convertir a Python Time Object
  archivo       = ot_df['link']   # solo el nombre de archivo PDF

  # obtiene el día de la semana: lunes, martes, ....
  try:
    fecha = fecha.split(',')[0]
  except:
    fecha = "·"
  
  # Obtiene nombre del archivo a PDF
  try:
    archivo = basename(archivo)
  except:
    archivo = "·"

  # Obtener las Actividades
  actividades = organizarActividades( obj_ot )
  if len(actividades) == 0:
    obj_ot.Log2Ot("FATAL", "No se encontraron actividades", "Fallo al intentar obtener la matriz de actividades")
    return


  """
    Se añaden las Columnas con los valores comunes a cada fila de Actividad

    VALIDAR UNA MEJOR FORMA DE HACER ESTO EN PANDAS PARA EVITAR ERRORES CUANDO
    SE EJECUTA EN UN GRAN CANTIDAD DE OTS

  """

  actividades['uuid'] = actividades.apply(lambda x: uuid.uuid4(), axis=1)
  actividades.insert( 1, 'Cuenta'        , "·" )
  actividades.insert( 2, 'Confianza'     , 0.0 )
  actividades.insert( 3, 'Cuadrilla'     , cuadrilla  )
  actividades.insert( 4, 'Primario'      , primario   )
  actividades.insert( 5, 'SIG'           , "No"   )
  actividades.insert( 6, 'HorasExtra'    , horasExtra )
  actividades.insert( 8, 'Desconexion'   , desconexion)
  actividades.insert( 9, 'id_ot'         , id_ot      )
  actividades.insert( 1, 'Responsable'   , responsable)
  actividades.insert( 2, 'Colaboradores' , colaboradores )
  actividades.insert( 3, 'Vehiculo'      , vehiculo   )
  actividades.insert( 4, 'Sitio'         , sitio      )
  actividades.insert( 5, 'Dia'           , dia        )
  actividades.insert( 6, 'Fecha'         , fecha      )
  actividades.insert( 7, 'Archivo'       , archivo    )

  """
    Se reorganizan las columanas
  """

  actividades = actividades[['uuid','Item','Confianza','Cuenta',
                              'Evento','Alimentador','Primario',
                              'Tipo','Actividad','Cuadrilla',
                              'InicioEvento','FinEvento','Dia','Fecha',
                              'HorasExtra','Desconexion','SIG',
                              'Responsable','Colaboradores',
                              'Vehiculo','Sitio',
                              'id_ot','Archivo'
                              ]]


  # cambiar los valores para mejorar la lectura y visualización
  actividades = actividades.fillna("·")

  return( actividades )