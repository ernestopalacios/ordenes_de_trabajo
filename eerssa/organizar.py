import os
import gspread
import shutil
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# CODIGO GENERADO POR GEMINI 2.5 PARA OBTENER EL LISTADO DEL PERSONAL, SU ORDEN CARGO Y CUADRILLA

# --- Configuration ---
# Define the scope for the APIs you're using
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

# Path to your downloaded JSON credentials file
creds_file = 'secrets/gdrive_credentials.json' # Or the full path if it's elsewhere

# Name of the Google Sheet you want to access
google_sheet_name = 'DB_calificar_ot'

# Name of the specific worksheet within the Sheet (optional, defaults to the first sheet)
# If you want a specific sheet, uncomment and set the name below
worksheet_name = 'Iniciales'

# --- End Configuration ---


def get_gsheet_df( ):
  try:
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
    client = gspread.authorize(creds)
    logger.info("Authentication successful!")
    
  except Exception as e:
    logger.info(f"Authentication failed: {e}")
    # Handle error appropriately, maybe stop execution
    return "Fail"
  
  try:
    # Open the Google Sheet by its name
    sheet = client.open(google_sheet_name)
    
    logger.info(f"|->> Successfully opened Google Sheet: '{google_sheet_name}'")

    # Select the worksheet
    worksheet = sheet.worksheet(worksheet_name)
    logger.info(f"|->> Selected worksheet by name: '{worksheet.title}'")

  except gspread.SpreadsheetNotFound:
    logger.info(f"[ X ]  Error: Spreadsheet '{google_sheet_name}' not found.")
    logger.info("Make sure the name is correct and the sheet is shared with the service account email.")
    return "Fail"
  except gspread.WorksheetNotFound:
    logger.info(f"[ X ]  Error: Worksheet '{worksheet_name}' not found in the spreadsheet.")
    return "Fail"
  except Exception as e:
    logger.info(f"[ X ]  An error occurred while accessing the sheet/worksheet: {e}")
    return "Fail"

  try:
    # Get all values from the worksheet
    data = worksheet.get_all_values() # Reads data as a list of lists

    # Convert the list of lists into a Pandas DataFrame
    # Assumes the first row contains the headers
    if data:
      headers = data[0]
      df = pd.DataFrame(data[1:], columns=headers)
      logger.info("\n|->> Data successfully imported into DataFrame")
      
      # Elimina las filas vacias
      df.loc[df["NOMBRE"] == '',"NOMBRE" ] = pd.NA
      df = df.dropna()
    else:
      logger.info("[ X ]  Error: The selected worksheet appears to be empty.")
      df = pd.DataFrame() # Create an empty DataFrame

  except Exception as e:
    logger.info(f"[ X ]  An error occurred while reading data or creating the DataFrame: {e}")
    return "Fail"

  return df



def get_num_responsable( nombre:str, df ):
  if isinstance( df, pd.DataFrame ):
    if 'NOMBRE' in df.columns and 'ORDEN_RESPONSABLE' in df.columns:
      series = df.query( f"NOMBRE == '{nombre}'" )["ORDEN_RESPONSABLE"]
      if not series.empty:
        return series.iloc[0]
      else:
        return '0'
  else:
    return 'x'
  


def get_num_cuadrilla( cuadrilla_ot:str, df):

  if not isinstance( df, pd.DataFrame ):
    return 'XX'

  if 'CUADRILLA_OT' in df.columns and 'ORDEN_CUADRILLA' in df.columns:
    series = df.query( f"CUADRILLA_OT == '{cuadrilla_ot}'" )["ORDEN_CUADRILLA"]

    if not series.empty:
      return series.iloc[0]
    else:
      return 'no'
  else:
    return 'no_df'



def get_iniciales( nombre:str, df = "vacio" ):
  
  df_ok = False # assume there is no dataframe
  
  if isinstance( df, pd.DataFrame) and 'NOMBRE' in df.columns and 'INICIALES' in df.columns:    
    df_ok = True
    series = df.query(f"NOMBRE == '{nombre}'" )["INICIALES"]
     
    if not series.empty:
      return series.iloc[0] # RETURN initial on list
  
  lista_nombre = nombre.split(' ')
  
  # Verify it has at least three names_items
  if len(lista_nombre) < 3:
    return "revisar_nombre"
  else:
    respuesta = lista_nombre[2][0]+lista_nombre[0][0]
  
  if df_ok == False:
    return respuesta # RETURN calculated initial
  else:
    # Are the calulated initials already taken
    check_initials = df.query( f"INICIALES == '{respuesta}'" )["NOMBRE"]

    if check_initials.empty:
      return respuesta # RETURN calculated initial
    else: # Needs another letter
      respuesta = respuesta + lista_nombre[1][0]
      # the posibility of this three letter initial to collide is very small
      # and in the samen work group even less. This is good enough
      return respuesta 



def from_name_get_cuadrilla( nombre:str, df ):

  if not isinstance( df, pd.DataFrame ):
    return 'no'

  if 'NOMBRE' in df.columns and 'CUADRILLA_OT' in df.columns:
    series = df.query(f"NOMBRE == '{nombre}'" )["CUADRILLA_OT"]
    if not series.empty:
      return series.iloc[0]
    else:
      return "no"
  else:
    return "no"
  


def get_nombre_corto_cuadrilla( cuadrilla:str, df = "vacio" ):

  if isinstance(df, pd.DataFrame) and 'CUADRILLA_OT' in df.columns and 'CUADRILLA_CORTO' in df.columns:
    series = df.query(f"CUADRILLA_OT == '{cuadrilla}'" )["CUADRILLA_CORTO"]

    if not series.empty:
      return series.iloc[0] # RETURN the short name from the list.
  
  try:
    grupo,tipo = cuadrilla.split(" Z")
    if tipo.__contains__("Cuadrilla"):
      tipo = "Cuadrilla "
    elif tipo.__contains__("Agencia"):
      tipo = "Agencia "
    else:
      return cuadrilla # Special name can't have short name
    
    return tipo+grupo # Calulated name
  except:
    return cuadrilla  # Can't calculate the short name


def get_nombre_archivo( obj, df = "vacio" ):
  try:

    if obj.valido == False:
      return os.path.basename(obj.link)

    num_cudarilla = get_num_cuadrilla( obj.data["cuadrilla"], df )
    num_responsable = get_num_responsable( obj.data["responsable"][0], df )
    iniciales = get_iniciales( obj.data["responsable"][0], df )
    cuadrilla_corto = get_nombre_corto_cuadrilla( obj.data["cuadrilla"], df )

    try:
      fecha_ot = obj.data["fecha"].split('T')[0]
    except:
      fecha_ot = obj.data["fecha"]
    
    return f"OT [{num_cudarilla}] {cuadrilla_corto} {fecha_ot} ({num_responsable}) {iniciales}.pdf"
  
  except Exception as e:
    logger.info(f"[ X ]  No fue posible renombrar la OT Error: {e}")
    obj.Log2Ot("ERROR", "No fue posible renombrar la OT", "No se pudo extraer la información de la Orden de Trabajo para ser renombrada")
    return os.path.basename(obj.link)
  

# Esta es la función que será utilizada en el archivo principal

def renombrar_ot( current_file_path, nombre_nuevo ):

  carpeta_procesados = os.path.join(
    os.path.dirname(current_file_path), 
    "ot_procesados"
  )

  if not os.path.exists(carpeta_procesados):
    os.makedirs(carpeta_procesados)

  new_file_path = os.path.join( carpeta_procesados, nombre_nuevo)

  try:
    # shutil.move will overwrite an existing file at the destination.
    # If new_file_path is an existing directory, current_file_path will be moved into it.
    # To ensure it replaces a file if it exists with the same name,
    # and doesn't move into a directory if new_file_path accidentally points to one:
    if os.path.isdir(new_file_path):
      logger.info(f"Error: Destination '{new_file_path}' is a directory. Cannot overwrite with a file.")
      return "Failed"

    shutil.move(current_file_path, new_file_path)
    logger.debug(f"[OK] Archivo: '{os.path.basename(current_file_path)}' reubicado a: '{new_file_path}' correctamente.")
    return new_file_path
  
  except FileNotFoundError:
    logger.info(f"Error: The file '{current_file_path}' was not found.")
    return "Failed"
  
  except shutil.Error as e:
    logger.info(f"Error moving/renaming file: {e}")
    return "Failed"