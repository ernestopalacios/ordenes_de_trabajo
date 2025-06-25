#import "templateReporte.typ": *

#show: dvdtyp.with(
  title: "Reporte de Orden de Trabajo",
  subtitle: [ ],
  author: "EN CURSO",
  abstract: "Zamora Z1 (Cuadrilla. Nro. 6) \n sábado, 26 de abril del 2025 \n SILVA ARMIJOS ROMEL EDUARDO",
)

#outline()

= Errores Falatales

#problema[
  Tipo FATAL. 
  $
    "no contiene Fecha Inicial"
  $ 

]

#error("Euclid")[
  infinite primes what???
]


#revisar[
  Algo para revisar. posiblemente cambiar
]

#informativo("Creacion")[
  Datos generales
]



#proof[
  $ "hi"="hello"="greeting" $
]

= Novedades en actividades.


#error("SE LABORA")[
  No se ha enconetrado el ITEM Se Labora.

]


to make your own theorem enviorments, you can use the `builder-thmbox` and `builder-thmline` functions to generate _theorem styles_ and then use those to make theorems (idk if this is too convoluted or not, make an issue on github if you have a better idea).

```typ
#let theorem-style = builder-thmbox(color: colors.at(6), shadow: (offset: (x: 3pt, y: 3pt), color: luma(70%)))
#let theorem = theorem-style("theorem", "Theorem")
#let lemma = theorem-style("lemma", "Lemma")

#let definition-style = builder-thmline(color: colors.at(8))
#let definition = definition-style("definition", "Definition")
#let proposition = definition-style("proposition", "Proposition")

```
There is also a color pallete

#{
  let nums = range(16)

  align(
    center,

    table(
      columns: 16,
      stroke: 0pt,
      inset: 0em,
      ..nums.map(i => rect([#i], fill: colors.at(i), width: 2em, height: 2em)),
    ),
  )
}
