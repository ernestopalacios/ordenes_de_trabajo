import dask.bag as db
from dask.distributed import Client
from pathlib import Path
import json
from datetime import datetime

# Import your existing modules
from .constants import BoxesValues, Current


def procesarOt( link_to_pdf ):
  """ 
  Esta será la función central para procesamiento en paralelo,
  sin clases ni objetos ni dependecias externas
  todo en un solo lugar, siempre devuelve un diccionario, puede
  ser válido o no. Los mensajes de Excepción se guardan en el Log
  dentro del mismo diccionario, un solo objeto.

  :param str inputPDF_path: Path to the PDF File to be processed
  """
  try:
    result = {}
    pdf_path = Path(link_to_pdf) if isinstance(link_to_pdf, str) else link_to_pdf

    if not pdf_path.exists():
      return{ 

      }