from enum import Enum

# Versioning and files
class Current(Enum):
  VERSION = '0.3.0'

class Chars(Enum):
  DEFAULT_EMPTY_CHAR = "·"

# VALUES OF LINES FOR TABLE AND TEXT EXTRACTION
#    py1  <- Vertical Values in PPi for the first paeg
#    px1  <- Horizontal Values in PPi for the first page
#    ry1  <- Vertical Values in PPi for the second page

#    PPi points per inch : 72 points per inch

py1 = 25.90
py2 = 42.00
py3 = 54.00
py4 = 65.50
py5 = 81.50
py6 = 93.00
py7 = 182.00
py8 = 195.00
py9 = 230.00
py10 = 215.27
py11 = 239.55
py12 = 274.50
py13 = 286.00
py14 = 363.00
py15 = 378.00
py16 = 545.00
py17 = 560.00
py18 = 572.00
py19 = 738.50
py20 = 793.65
py21 = 763.00
py22 = 837.67
py23 = 845.77

py24 = 263.00
py25 = 575.00
py26 = 580.00

py27 = 106.00
py28 = 116.00


px1 = 27.52
px2 = 84.00
px3 = 205.56
px4 = 228.50
px5 = 286.50
px6 = 270.30
px7 = 340.00
px8 = 346.38
px9 = 503.00
px10 = 567.76

px11 = 57.00
px12 = 385.00
px13 = 418.00

px14 = 225.00
px15 = 108.00
px16 = 210.00

px17 = 420.00
px18 = 465.00

px19 = 254.00
px20 = 338.00

ry1 = 25.90
ry2 = 45.00
ry3 = 55.50
ry4 = 68.50
ry5 = 72.84
ry6 = 73.00
ry7 = 687.00
ry8 = 715.00
ry9 = 726.31
ry10= 737.00
ry11= 748.00
ry12= 749.00
ry13= 770.00


itemX1 = 28
itemY1 = 92

itemX2 = 41
itemY2 = 117.85

deltaY = 28.32

deltaXactiv1 = 15
anchoActiv = 36

deltaEvento = 53
anchoEvento = 298

deltaLMT = 340
anchoLMT = 397

deltaTipo = 440
anchoTipo = 490

deltaInicio = 491
anchoFecha = 37

deltaFin = 529.5

kilomY = 58
KilomD = 9
kmInicioX1 = 140
kmInicioX2 = 55

kmFinalX1 = 267
kmFinalX2 = 55

kmRecorX1 = 417
kmRecorX2 = 55

vehicX1 = 125
placaX1 = 190
rentadoX1 = 286
choferX1 = 342
vehicDl = 27

vehicY1 = 46.5 
vehiYdl = 9

firmasX1 = 85
firmasAncho = 159
firmasDelta = 160

firmasY1 = 740
firmasAlto = 23.4

fechaInicioY1 = 265
fechaDeltaY   = 9

fechaInicioX1 = 100
fechaAncho    = 170

duracionX1    = 483
duracionAncho = 80



class BoxesValues(Enum):
  ID_OT                = ( px9 ,py1  , px10, py2 )
  NUMERO_OT            = ( px9 ,py2  , px10, py3 )
  GERENCIA             = ( px5 ,py3  , px9 , py4 )
  SITIO                = ( px11,py4  , px12, py5 )
  FECHA_INICIAL_UNO    = ( px13,py4  , px10, py5 )

  RESPONSABLE           = ( px2 ,py27  , px20, py28 )
  COLABORADORES_NOMBRES = ( px2 ,py28  , px19, py7 )
  COLABORADORES_CARGOS  = ( px19,py28  , px20, py7  )

  DATOS_VEHICULO_HOJA_1 = ( px7 ,py6  , px10, py7 )
  TIPOS_TRABAJO         = ( px1 ,py8  , px10, py9 )
  DESCRIPCION           = ( px1 ,py11 , px10, py24)
  FECHA_INICIO_TESTIMADO= ( px1 ,py24 , px10, py12)
  RIESGOS_EPPS          = ( px1 ,py13 , px10, py14)
  MEDIDAS_SEGURIDAD     = ( px1 ,py15 , px10, py16)
  PRECAUCIONES          = ( px1 ,py17 , px10, py18)
  CARENCIAS             = ( px1 ,py25 , px10, py26)
  FIRMAS                = ( px1 ,py19 , px10, py21)

  FECHA_STRING      = (fechaInicioX1, fechaInicioY1, fechaInicioX1+fechaAncho, fechaInicioY1+ fechaDeltaY)
  DURACION          = (duracionX1, fechaInicioY1, duracionX1+duracionAncho, fechaInicioY1+ fechaDeltaY)


  # Hoja 2
  CUADRILLA_NOMBRE      = ( px1 ,ry1  , px14,ry2 )
  ACTIVIDADES           = ( px1 ,ry6  , px10,ry7 )
  OBSERVACIONES         = ( px15,ry7  , px10,ry8 )
  ESTADO_OT             = ( px15,ry9  , px16,ry10)
  FECHA_FINAL           = ( px15,ry10 , px16,ry11)
  ACCIDENTES            = ( px17,ry12 , px18,ry13)

  VEHICULO              = ( vehicX1, vehicY1 , vehicX1 + vehicDl*1.2, vehicY1+vehiYdl )
  PLACA                 = ( placaX1, vehicY1 , placaX1 + vehicDl*2, vehicY1+vehiYdl )
  RENTADO               = ( rentadoX1, vehicY1 , rentadoX1 + vehicDl*0.8, vehicY1+vehiYdl )
  CHOFER                = ( choferX1, vehicY1 , choferX1 + vehicDl*8, vehicY1+vehiYdl )

  KILOMETRAJE           = ( px1 ,ry3  , px10,ry4 )

  KMI             = (kmInicioX1, kilomY , kmInicioX1 + kmInicioX2,kilomY+KilomD)
  KMF             = (kmFinalX1, kilomY , kmFinalX1 + kmFinalX2,kilomY+KilomD)
  KMT             = (kmRecorX1, kilomY , kmRecorX1 + kmRecorX2,kilomY+KilomD)