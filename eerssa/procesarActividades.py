import pandas as pd
from unidecode import unidecode
import pickle
from   os.path import basename
from datetime import datetime
import eerssa.utils
import re
import logging
from pprint import pprint

from .constants import Chars

DEFAULT_EMPTY_CHAR = Chars.DEFAULT_EMPTY_CHAR.value
CUADRILLA_AP_4 = "Zamora Z1 (Cuadrilla. AP Nro. 4)"

#TODO:  Verificar el procesamiento de actividades en YQ ot


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Obtener listas de dias festivos y jornadas nocturnas
dict_festivos = None
try:
  dict_festivos = eerssa.utils.get_festivos()
except:
  logger.error( f"\n[ FESTIVOS ] Error: al intentar Obtener los dias festivos desde utils.py\n")

def he_festivo(row):
  """Aplica Horas Extra a los días Festivos en DATAFRAME ACTIVIDAD"""
  try:
    fecha = eerssa.utils.soloFecha_SinTimezone(row['Fecha'])
    fecha = pd.to_datetime(fecha).date()
    cuadrilla = row['Cuadrilla']
    he_actual = row['HorasExtra']
    #logger.info(f"\n  >>>> Debuger: Hora Extra Actual es: {he_actual}")

    if dict_festivos == None:
      return he_actual

    if(fecha,cuadrilla) in dict_festivos['ESPECIFICOS']:
      #logger.info(f"\n  >>>> Debuger: Se aplica la hora Extra: 'Si' a la fecha: {fecha} para la cuadrilla: {cuadrilla}")
      return 'Si'
    elif fecha in dict_festivos['TODOS']:
      #logger.info(f"\n  >>>> Debuger: Se aplica la hora Extra: 'Si' a la fecha: {fecha}")
      return 'Si'
    else:
      #logger.info(f"\n  >>>> Debuger: No se aplica la hora Extra a la fecha: {fecha}")
      return he_actual

  except:
    logger.error( f"\n[ MATRIZ ] Error: al intentar asignar la etiqueta de Horas extra: FECHA ES: {row['Fecha']}\n")


"""
Convertimos el Dataframe multidimensional a un formato de Matriz (2D) Filas-Columnas,
durante la transformación se ejecutan correcciones más frecuentes, fechas, horas,
con la intención de que la matriz sea lo más correcta posible.

Los cambios realizados serán registrados en la sección de LOG.txt.

Se transforma el texto expandiendo las abreviaciones y errores comunes de escritura.

A partir de esta matriz se generará los Informes y se podra Exportar/Importar a Excel
para la revisión manual y actualización de OT.
"""



def limpiar_texto_actividad( actividad ):
  palabras = {
          "#"             : "nro",
          "Est"           : "estructura",
          "Est."          : "estructura",
          "Estr"          : "estructura",
          "est"           : "estructura",
          "estr"          : "estructura",
          "estr#"         : "estructura",
          "est."          : "estructura",
          "estructuras"   : "estructura",
          "poste"         : "estructura",
          "ingnitor"      : "ignitor",
          "w na"          : "wna",
          "70 w"          : "70w",
          "100 w"         : "100w",
          "150 w"         : "150w",
          "70 wna"        : "70wna",
          "70w na"        : "70wna",
          "70 w na"       : "70wna",
          "100 wna"       : "100wna",
          "100w na"       : "100wna",
          "100 w na"      : "100wna",
          "150 wna"       : "150wna",
          "150w na"       : "150wna",
          "150 w na"      : "150wna",
          "tiraf"         : "tirafusible",
          "med."          : "medidor",
          "med"           : "medidor",
          "med#"           : "medidor",
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
      "511.03.001"       : "SUBESTACION",
      "511.03.003"       : "SUBTRANSMISION",
      "511.04.001"       : "REDES",
      "511.04.002"       : "ALUMBRADO",
      "511.05.001"       : "ACOMETIDAS",
      "511.05.002"       : "MEDIDORES",
      "521.01.001"       : "Servicio_Ocasional",
      "511.06.002"       : "PLANILLAS",
      "OT-01-2022-GECOM" : "Nuevo_Servicio",
      "OT-07-2022-GECOM" : "Restituciones"
    }

    respuesta = replace_words( respuesta, conversiones )

  except:

    respuesta = "revisar"

  return ( respuesta )


def calcular_minutos_transcurridos( fecha_inicio, fecha_fin ):
  """
  Convierte dos Strings de tiempo y calcula los minutos transcurridos.
  La Zona Horaria es necesaria cuando se sube a MongoDB para ser procesada correctamente
  por su motor de busqueda

  Args:
    datetime_str1: The first datetime string (e.g., "2025-07-23T00:00:00-05:00 16:35:00").
    datetime_str2: The second datetime string (e.g., "2025-07-23T00:00:00-05:00 17:00:00").

  Returns:
    La cantidad de tiempo transcurrido en minutos _as_integer, o None si hay un error.
  """
  try:
    # Formato esperado para el calulo
    datetime_format = "%Y-%m-%d %H:%M:%S"

    # Se elimina el componente de Zona Horaria
    fecha_inicio = fecha_inicio.replace('T', ' ').split()
    fecha_inicio = fecha_inicio[0]+' '+fecha_inicio[-1]

    fecha_fin = fecha_fin.replace('T', ' ').split()
    fecha_fin = fecha_fin[0]+' '+fecha_fin[-1]

    # Convert the strings to datetime objects
    datetime_obj1 = datetime.strptime(fecha_inicio, datetime_format)
    datetime_obj2 = datetime.strptime(fecha_fin, datetime_format)

    # Calculate the difference between the two datetime objects
    time_difference = datetime_obj2 - datetime_obj1

    # Calculate the elapsed time in minutes
    elapsed_minutes = int(time_difference.total_seconds() / 60)

    return elapsed_minutes

  except:
    logger.error( f"\n[ MATRIZ ] Error: al intentar calcular el tiempo transcurrido para una actividad texto de inicio {fecha_inicio} texto de fin {fecha_fin}\n")
    return -1



# ==================================
#     ORGANIZAR ACTIVIDADES
# ==================================

def organizarActividades( obj_ot ):


  ot_df = obj_ot.data

  actividades = pd.DataFrame( obj_ot.data['actividades'] )

  if len(actividades) == 0:
    return actividades

  # Volver a convertir de DEFAULT_EMPTY_CHAR a NaN
  actividades.replace( DEFAULT_EMPTY_CHAR, pd.NA, inplace=True )
  actividades = actividades[actividades.Evento.notnull()]
  actividades = actividades.reset_index()

  # Clean whitespace from event time columns at the beginning
  if 'InicioEvento' in actividades.columns:
      actividades['InicioEvento'] = actividades['InicioEvento'].str.strip()
  if 'FinEvento' in actividades.columns:
      actividades['FinEvento'] = actividades['FinEvento'].str.strip()

  #····························································
  #        Validar y Corregir Fecha y Hora.
  #····························································


  try:

    fInicio = actividades[['Item','InicioEvento','FinEvento']].dropna().copy()

    # Use .loc to create the new 'solofechaI' column safely
    fInicio.loc[:, 'solofechaI'] = fInicio['InicioEvento'].apply(
        lambda x: re.findall(r'\d{4}-\d{2}-\d{2}', str(x))[0] if re.findall(r'\d{4}-\d{2}-\d{2}', str(x)) else None
    )

    fechaModa = fInicio.solofechaI.mode().values[0] # fecha 'moda' en el arreglo la fecha mas común usada en actividades


    try: #puede darse el caso de una OT sin fecha inicial en la Hoja 1.
      fecha_hoja1 = ot_df['fecha'].split('T')[0]  # Convertir de Python Time Object a String


      if fechaModa != fecha_hoja1:
        obj_ot.Log2Ot("ERROR", "No coinciden las fechas", "La fecha en Hoja 1 no es la misma que en Actividades")
    except:
      fecha_hoja1 = fechaModa


  except:
    # En aquellas OT solo informativas, que no tienen puesto una fecha en las
    # actividades, primero intentamos tomar la fecha de inicio, sino, la fecha final
    # sino una fecha de referencia.
    if( ot_df['fecha'] != DEFAULT_EMPTY_CHAR ):
      fechaModa = ot_df['fecha'].split(' ')[0]
      fechaModa = eerssa.utils.soloFecha_SinTimezone(fechaModa)
      obj_ot.Log2Ot("INFO", "Desde >> Obtener fechaModa. No se encontro fecha en las actividades", "Se utiliza como fechaModa la fecha de Inicio en la Hoja 1")

    elif( ot_df['fechaFinal'] != DEFAULT_EMPTY_CHAR ):
      obj_ot.Log2Ot("REVISAR", "Desde >> Obtener fechaModa. No se encontro fecha en la Hoja 1", "Se utiliza como fechaModa la fecha final en la Hoja 2")
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

    #  |Laboran  // mayusculas o minusculas
    etiq_LABORA = etiq_labora.Evento.str.contains('^laboran', case = False, regex = True )
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
  backup = actividades.copy()

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

        # Lo programo de esta manera ya que al hacer el Drop no se actualizan los indices
        #  si uso un lazo FOR. Al hacerlo de esta manera cada vez leo los indices tomando
        #  en cuenta aquellos que ya elimine. y funciona.


    actividades.Item = actividades.Item.astype(int)
    actividades.insert( 3, 'Cuenta'     ,  DEFAULT_EMPTY_CHAR )

  except:

    actividades = backup.copy()
    obj_ot.Log2Ot("ERROR", "No pudo consolidar la matriz de Actividades", "Ocurrio un error al consolidar las actividades. Desde >> iteraciones while fila < totalIdx")


  #"""····························································
  #    CORREGIR FECHAS ERRONEAS EN LAS ACTIVIDADES DE UNA OT
  #·······························································"""
  backup = actividades.copy()
  try:
    actividades['corregir_fechaInicio'] = actividades[ 'InicioEvento' ].apply(lambda x: x.split()[0] == fechaModa )
    actividades['corregir_fechaFin'] = actividades[ 'FinEvento' ].apply(lambda x: x.split()[0] == fechaModa )
    actividades.loc[ actividades['corregir_fechaInicio'] == False, 'InicioEvento' ] = actividades.loc[actividades['corregir_fechaInicio'] == False, 'InicioEvento'].apply(lambda x: " ".join([ fechaModa, x.split()[1] ]) if isinstance(x, str) and len(x.split()) > 1 else x )
    actividades.loc[ actividades['corregir_fechaFin'] == False, 'FinEvento' ] = actividades.loc[actividades['corregir_fechaFin'] == False, 'FinEvento'].apply(lambda x: " ".join([ fechaModa, x.split()[1] ]) if isinstance(x, str) and len(x.split()) > 1 else x )

    if ( not actividades['corregir_fechaInicio'].all() ) : # at leas one error
      obj_ot.Log2Ot("REVISAR", "Se detectaron fechas inconsistentes", "En actividades, revisar las fechas de inicio actividad")

    if ( not actividades['corregir_fechaFin'].all() ) : # at leas one error
      obj_ot.Log2Ot("REVISAR", "Se detectaron fechas inconsistentes", "En actividades, revisar las fechas de fin de actividad")

  except:
    actividades = backup.copy()
    obj_ot.Log2Ot("ERROR", "No pudo corregir las fechas erroneas", "Ocurrio un error al corregir fechas mal digitadas. Desde >> corregir_fechaInicio/Fin")

  return actividades

















def convert_to_time(time_string):
    """
    Converts a time string in the format "HH:MM:SS" to a Python time object.

    Args:
        time_string: The time string to convert.

    Returns:
        A Python time object, or None if the string is invalid.
    """
    try:
        only_time = time_string.split()[1]
        time_obj = datetime.strptime(only_time, "%H:%M:%S").time()
        return time_obj
    except:
        return None



# CONVERTIR OT A MATRIZ DE ACTIVIDADES

def ConvertirOT_a_ActividadesCSV( obj_ot ):

  """
    Convierte una fila del Dataframe que contiene las OTs y
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
    if ot_df['actividades'] == DEFAULT_EMPTY_CHAR:
      return None
  except Exception as e:
    print(f"Desde ConvertirOT_a_ActividadesCSV. No tiene actividades el archivo: {obj_ot.link}")
    obj_ot.Log2Ot("ERROR","Desde ConvertirOT_a_ActividadesCSV. No tiene actividades el archivo: {obj_ot.link}","Error de excepcion" )
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
  vehiculo      = ot_df['vehiculo']
  sitio         = ot_df['sitio']
  dia           = ot_df['diaSemana']  # solo el nombre del dia de labores: lunes, martes, ...
  materiales    = DEFAULT_EMPTY_CHAR
  archivo       = ot_df['link']   # solo el nombre de archivo PDF

  # obtiene el día de la semana: lunes, martes, ....
  try:
    fecha = ot_df['fecha']
    fecha = fecha.split()[0]
  except:
    fecha = DEFAULT_EMPTY_CHAR


  # Obtiene nombre del archivo a PDF
  try:
    archivo = basename(archivo)
  except:
    archivo = DEFAULT_EMPTY_CHAR


  # Obtener las Actividades
  actividades = organizarActividades( obj_ot )
  if len(actividades) == 0:
    obj_ot.Log2Ot("FATAL", "No se encontraron actividades", "Fallo al intentar obtener la matriz de actividades")
    return

  if isinstance(actividades, list):
    actividades = pd.DataFrame(actividades)


  # Calcular los minutos transcurridos en cada actividad.
  actividades['Duracion'] = actividades.apply( lambda x: calcular_minutos_transcurridos( x['InicioEvento'], x['FinEvento'] ), axis=1 )



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
  actividades.loc[ actividades['Tipo'] == "ALIMENTACI", 'Tipo' ] = "LUNCH"


  actividades.loc[(actividades['Alimentador'].isnull()) & (actividades['Cuenta'] == DEFAULT_EMPTY_CHAR ), 'Cuenta'] = "informativa"
  actividades.loc[ :,'Evento'] = actividades[ 'Evento' ].apply( lambda x:limpiar_texto_actividad(x) )
  actividades.loc[ actividades['Cuenta'] == DEFAULT_EMPTY_CHAR , 'Cuenta' ] = actividades.loc[actividades['Cuenta'] == DEFAULT_EMPTY_CHAR , 'Evento'].apply(lambda x:get_estimated_cuenta(x) )

  # ==========================================
  #           IDENTIFICACIÓN DE HORAS EXTRA
  # ==========================================



  actividades['inicio'] = actividades['InicioEvento'].apply( lambda x: convert_to_time(x) )
  actividades ['fin'] = actividades['FinEvento'].apply( lambda x: convert_to_time(x) )

  corte_he_inicio = convert_to_time("h 07:55:00")
  corte_he_fin    = convert_to_time("h 17:45:00")


  # Fin de semana
  if dia == "sábado" or dia == "domingo":
    actividades.insert( 6, 'HorasExtra'    , 'Si' )
  else:
    actividades.insert( 6, 'HorasExtra'    , 'No' )
    actividades.loc[ actividades['inicio'] < corte_he_inicio, 'HorasExtra' ] = 'Si'
    actividades.loc[ actividades['fin'] > corte_he_fin, 'HorasExtra' ] = 'Si'



  """
    Se añaden las Columnas con los valores comunes a cada fila de Actividad

    VALIDAR UNA MEJOR FORMA DE HACER ESTO EN PANDAS PARA EVITAR ERRORES CUANDO
    SE EJECUTA EN UN GRAN CANTIDAD DE OTS

  """

  datos_comunes = {
    'Cuadrilla' : cuadrilla,
    'Primario'  : primario,
    'SIG' : "No",
    'Desconexion' : desconexion,
    'id_ot' : id_ot,
    'Responsable' : responsable,
    'Colaboradores' : colaboradores,
    'Vehiculo' : vehiculo,
    'Sitio' : sitio,
    'Dia' : dia,
    'Fecha' : fecha,
    'Materiales' : materiales,
    'Archivo' : archivo
  }

  for col, value in datos_comunes.items():
    actividades[col] = value


  # Dias Festivos: coloca 'Si' en los días festivos y cantonales
  actividades['HorasExtra'] = actividades.apply( he_festivo, axis=1 )



  """
    Se reorganizan las columanas
  """

  actividades = actividades[
    ['Item',        'Cuenta',
     'Evento',      'Actividad',
     'Alimentador', 'Primario',    'Desconexion', 'SIG',
     'Tipo',        'Materiales',   'Cuadrilla',
     'Dia',  'Fecha', 'InicioEvento', 'FinEvento', 'Duracion',
     'Responsable', 'Colaboradores',
     'HorasExtra',
     'Vehiculo',    'Sitio',
     'id_ot',       'Archivo'
     ]]


  # Guardo la respuesta en el objeto
  actividades = actividades.fillna(DEFAULT_EMPTY_CHAR)
  obj_ot.matriz = actividades.copy()
  # Lo regreso al programa principal
  return( actividades )
