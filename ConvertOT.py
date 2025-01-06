
from eerssa import gestionOT

path_to_pdf = '/home/vlad/OneDrive/01 JEZO/01 ACTIVIDADES DIARIAS DE TRABAJO DE LAS AGENCIAS/2024/12 DICIEMBRE/03 CUADRILLA ALUMBRADO ZAMORA/Orden de trabajo Alumbrado Zamora 03-12-2024 (LM).pdf'

ot_test = gestionOT.GestionOt(path_to_pdf)

print( ot_test.valido )
print( ot_test.version )

ot_test.load_ot()

print("Hola Mundo!")