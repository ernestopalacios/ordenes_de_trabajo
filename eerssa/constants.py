from enum import Enum

# Versioning and files
class Current(Enum):
  VERSION = '0.12.0'


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

  # Hoja 2
  CUADRILLA_NOMBRE      = ( px1 ,ry1  , px14,ry2 )
  VEHICULO              = ( px1 ,ry2  , px10,ry3 )
  KILOMETRAJE           = ( px1 ,ry3  , px10,ry4 )
  ACTIVIDADES           = ( px1 ,ry6  , px10,ry7 )
  OBSERVACIONES         = ( px15,ry7  , px10,ry8 )
  ESTADO_OT             = ( px15,ry9  , px16,ry10)
  FECHA_FINAL           = ( px15,ry10 , px16,ry11)
  ACCIDENTES            = ( px17,ry12 , px18,ry13)