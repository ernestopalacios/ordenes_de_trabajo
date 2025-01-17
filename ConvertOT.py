
from eerssa import gestionOT
from eerssa import matrizActividades
from pprint import pprint
from pathlib import Path
import pandas as pd

test_path = '/home/vlad/GIT/eerssa_gh/ordenes_de_trabajo/tests/ot_test/'
list_pdfs = []
for path in Path( test_path ).glob("**/*.pdf"):
  list_pdfs.append( str(path) )
  list_pdfs.sort()
len(list_pdfs)

obj_lists = []
obj_data  = []
for file in list_pdfs:
  ot = gestionOT.GestionOt( file )
  ot.load_ot()
  obj_lists.append( ot )
  obj_data.append( ot.data )

  ot_as_pd = pd.DataFrame( obj_data )

matriz_test = matrizActividades.ConvertirOT_a_ActividadesCSV(  ot_as_pd.iloc[3] )

print(matriz_test)