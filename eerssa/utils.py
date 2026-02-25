# 2. Funcion para eliminar el componente de Time Zone
#    éste es introducido cuando en actividades no se consigue una 'fecha_moda' 
#    y es necesario utilizar la 'fecha' de hoja_uno.   

def elimina_timezone( fecha ):
  try:
    fecha_inicio = fecha.replace('T', ' ').split()
    fecha_inicio = fecha_inicio[0]+' '+fecha_inicio[-1]
    return fecha_inicio
  except:
    return fecha


def soloFecha_SinTimezone( fecha ):
  try:
    fecha_inicio = fecha.replace('T', ' ').split()
    fecha_inicio = fecha_inicio[0]
    return fecha_inicio
  except:
    return fecha


def ColocarTimezone( fecha ):
  try:
    return fecha+'T00:00:00-05:00'
  except:
    return fecha

def calcular_minutos_transcurridos( start_times, end_times ):
  """
  This function works because subtracting two pandas Series of datetimes
  is a vectorized operation.
  """
  try:
    # Ensure columns are in datetime format first
    start_times = pd.to_datetime(start_times)
    end_times = pd.to_datetime(end_times)

    time_difference = end_times - start_times
    # Return the difference in minutes
    return (time_difference.dt.total_seconds() / 60).astype(int)
  except Exception as e:
    print(f" EXCEPTION:\n{e}")