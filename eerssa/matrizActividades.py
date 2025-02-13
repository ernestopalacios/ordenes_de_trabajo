import pandas as pd
import uuid
from unidecode import unidecode
import pickle
from   os.path import basename
from datetime import datetime

#import nltk
#from nltk.probability import FreqDist
#from sklearn.feature_extraction.text import CountVectorizer
#from sklearn.naive_bayes import MultinomialNB
#from sklearn import metrics

import traceback
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



def limpiar_texto_actividad( actividad ):
  palabras = {
          "#"             : "nro",
          "Est"           : "estructura",
          "Est."          : "estructura",
          "Estr"          : "estructura",
          "est"           : "estructura",
          "est."          : "estructura",
          "est."          : "estructura",
          "estructuras"   : "estructura",
          "poste"         : "estructura",
          "tiraf"         : "tirafusible",
          "med."          : "medidor",
          "med"           : "medidor",
          "med"           : "medidor",
          "CC"            : "Centro de Control",
          "C.C"           : "Centro de Control",
          "C.C."          : "Centro de Control",
          "C C"           : "Centro de Control",
          "trafo"         : "transformador",
          "tranfo"        : "transformador",
          "breiker"       : "breaker",
          "  "            : " ",
  }

  keys = (re.escape(k) for k in palabras.keys())
  pattern = re.compile(r'\b(' + '|'.join(keys) + r')\b')

  resultado = pattern.sub(lambda x: palabras[x.group()], actividad )

  return resultado

def replace_words(text, replacements_dict):
  for word, replacement in replacements_dict.items():
      text = re.sub(r'\b{}\b'.format(word), replacement, text) 
  return text

def get_estimated_cuenta( actividad ):

  try:
    # Operaciones
    txt = unidecode(actividad)  # Quitar tildes y caracteres especiales
    txt = txt.lower()           # todo a minusculas
    txt = re.sub( r'[^\w\s]',' ', txt ) # Eliminar puntuacion

    ### Mover el modelo a las constantes
    clasificador_actividad_v1 = './models/NB_clasif_activ_2024_03.pkl'
    nb_clf = pickle.load(open(clasificador_actividad_v1, 'rb'))

    vect_filename = './models/NB_vectorizer.pkl'
    vectorizer = pickle.load(open(vect_filename, 'rb'))

    prediction = str( nb_clf.predict( vectorizer.transform( [txt] ))[0] )
    confidence = float( nb_clf.predict_proba( vectorizer.transform( [txt] )).max() )

    if confidence > 0.59:
      respuesta = prediction
    else:
      respuesta = "?"

    conversiones = {
      "511.03.001"       : "Subestaciones",        
      "511.03.003"       : "Subtransmision",        
      "511.04.001"       : "Redes",             
      "511.04.002"       : "Alumbrado",             
      "511.05.001"       : "Acometidas",            
      "511.05.002"       : "Medidores",             
      "521.01.001"       : "Servicios_Ocasionales", 
      "511.06.002"       : "Planillas",             
      "OT-01-2022-GECOM" : "Nuevos_Servicios",      
      "OT-07-2022-GECOM" : "Restituciones"         
    }

    respuesta = replace_words( respuesta, conversiones )

  except:

    respuesta = "revisar"

  return ( respuesta )


# ==================================
#     ORGANIZAR ACTIVIDADES
# ==================================

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
    actividades.insert( 3, 'Cuenta'     ,  "·" )

  except:

    actividades = backup
    obj_ot.Log2Ot("ERROR", "No pudo consolidar la matriz de Actividades", "Ocurrio un error al consolidar las actividades")

  return actividades



























# CONVERTIR OT A MATRIZ DE ACTIVIDADES

def ConvertirOT_a_ActividadesCSV( obj_ot ):

  """ Convierte una fila del Dataframe que contiene las OTs y
    devuelve un nuevo dataframe exponienda cada una de las
    actividades de acuerdo al formato descrito.
  """

  # En caso de que no sea un objeto valido, no hagas nada más
  # obj_ot.matriz = None   <--- continua
  if obj_ot.valido == False:
    return None

  ot_df = obj_ot.data 


  # Si no fue posible extraer las actividades en un paso previo
  # no se hace nada más
  try:
    if ot_df['actividades'] == "·":
      return None
  except Exception as e:
    print(f"Desde ConvertirActividades. No tiene actividades el archivo: {obj_ot.link}")
    return None
      

  # Extraigo desde el objeto la información generica en todos los eventos
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

  # ==========================================
  #           CALIFICACION DE CUENTAS
  # ==========================================

  actividades.loc[ actividades['Tipo'] == "TRANSPORTE", 'Cuenta' ]  = "transporte"
  actividades.loc[ actividades['Tipo'] == "ALIMENTACI", 'Cuenta' ]  = "lunch"
  actividades.loc[ actividades['Actividad'] == "LABORA", 'Cuenta' ] = "se_labora"

  actividades.loc[ actividades['Tipo'] == "CORRECTIAS", 'Tipo' ] = "CORRECTIVO"
  actividades.loc[ actividades['Tipo'] == "PREDICTIAS", 'Tipo' ] = "PREDICTIVO"
  actividades.loc[ actividades['Tipo'] == "PREVENTIAS", 'Tipo' ] = "PREVENTIVO"
  actividades.loc[ actividades['Tipo'] == "ACTIVCOAS", 'Tipo'  ] = "RUTINARIA"
  actividades.loc[ actividades['Tipo'] == "EXPANSIAS", 'Tipo'  ] = "EXPANSION"

  
  actividades.loc[(actividades['Alimentador'].isnull()) & (actividades['Cuenta'] == "·" ), 'Cuenta'] = "informativa"
  actividades.loc[ :,'Evento'] = actividades[ 'Evento' ].apply( lambda x:limpiar_texto_actividad(x) )
  actividades.loc[ actividades['Cuenta'] == "·" , 'Cuenta' ] = actividades.loc[actividades['Cuenta'] == "·" , 'Evento'].apply(lambda x:get_estimated_cuenta(x) )
  


  """
    Se añaden las Columnas con los valores comunes a cada fila de Actividad

    VALIDAR UNA MEJOR FORMA DE HACER ESTO EN PANDAS PARA EVITAR ERRORES CUANDO
    SE EJECUTA EN UN GRAN CANTIDAD DE OTS

  """

  actividades['uuid'] = actividades.apply(lambda x: uuid.uuid4(), axis=1)
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

  actividades = actividades[
    ['uuid',        'Item',        'Cuenta',
     'Evento',      'Alimentador', 'Primario',
     'Tipo',        'Actividad',   'Cuadrilla',
     'InicioEvento','FinEvento',   'Dia','Fecha',
     'HorasExtra',  'Desconexion',  'SIG',
     'Responsable', 'Colaboradores',
     'Vehiculo',    'Sitio',
     'id_ot',       'Archivo'
     ]]


  # Guardo la respuesta en el objeto
  obj_ot.matriz =  actividades.fillna("·")
  
  # Lo regreso al programa principal "for debuggin purposes"
  return( actividades )