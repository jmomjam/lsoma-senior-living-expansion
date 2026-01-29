## Ideas

* Tener en cuenta el tiempo de construcción de la residencia
* Tener en cuenta el rango de edad de las mujeres cuidadoras no solo de la edad de los ancianos
* Tener en cuenta que rentas muy altas pueden no salir rentables por el precio del suelo y por estilo de vida de las personas

## Fase 1: Definición del Vector de Estado Objetivo (Q)

**Concepto Teórico:** **Espacio de Hilbert**.
Consideramos que la distribución demográfica de una sección censal no es un escalar (media de edad), sino un vector de estado  en un espacio -dimensional, donde  son los rangos de edad (bins) del censo (0-4, 5-9... 100+).

**El paso:**
Debemos construir tu "Pirámide Ideal" (), que actuará como el *Ground Truth* o la señal de referencia con la que compararemos todas las secciones.

* **Justificación del Estudio:**
* El estudio indica que la edad media de ingreso se ha retrasado a los **82 años** (la "cuarta edad").


* La crisis de cuidados tiene "rostro de mujer" y ellas tienen mayor esperanza de vida y resiliencia.




* **Acción Técnica:**
Crearás un array de numpy `target_distribution`. En lugar de una distribución uniforme o gaussiana, será una distribución asimétrica (skewed) con pesos máximos en los bins de **80-84** y **85+**, y ponderación extra en el vector correspondiente a mujeres.

---

### 1. Explicación Teórica General: El Espacio de Hilbert y el Vector de Estado

El Problema del Escalar (Pérdida de Información): En estadística tradicional, tendemos a comprimir la información. Si describes una población solo con su "Edad Media" (un escalar, un solo número), estás proyectando un sistema complejo en una sola dimensión.

Ejemplo de fallo: Un grupo de niños de 5 años y ancianos de 95 años tiene una media de 50 años. Un grupo de adultos de 50 años también tiene una media de 50. Para el escalar, son idénticos. Para tu negocio, son opuestos (uno es viable, el otro no).

La Solución Vectorial (Espacio de Hilbert): Un Espacio de Hilbert es, simplificando para este contexto, un espacio vectorial euclidiano de dimensiones infinitas (o finitas pero muy altas, n) que permite medir distancias y ángulos entre estados.

Vector de Estado (P): En lugar de un número, representamos la sección censal como una lista ordenada de valores (un vector). Si el censo divide la edad en 100 tramos (0 años, 1 año... 99+ años), nuestro espacio tiene n=100 dimensiones.

El Estado: La sección censal ya no es un punto en una recta, es una "forma" o una "onda" en ese espacio multidimensional. Contiene toda la estructura demográfica sin pérdida de información.

El Vector Objetivo (Q): En física, esto sería el "autoestado" o la resonancia que buscamos. Es la plantilla perfecta. No buscamos cualquier población envejecida; buscamos una distribución de probabilidad específica que maximice la rentabilidad y minimice el riesgo.

### 2. Aplicación al Caso Práctico: Por qué y Cómo

Aquí es donde la teoría aterriza en la realidad del negocio de residencias de 2.100€/mes.

Por qué aplicamos esto (Justificación del Negocio):

La "Cuarta Edad" (82+ años): El párrafo menciona que la edad de ingreso se ha retrasado. Una distribución gaussiana (campana) centrada en 70 años es ineficiente; captaría jubilados activos que no van a pagar una residencia. Necesitamos una distribución asimétrica negativa (left-skewed) hacia el final de la vida.

Rostro de Mujer (Supervivencia y Viudedad): Las mujeres tienen mayor esperanza de vida y, sociológicamente, en esas generaciones hay mayor tasa de viudedad en edades avanzadas, lo que elimina el cuidado conyugal y precipita la institucionalización. El vector debe pesar más la columna "Mujer" que "Hombre".

Ground Truth (La Verdad Terreno): Al definir Q (tu Pirámide Ideal), estableces el estándar de oro. Cualquier sección censal (P) se comparará contra Q. Si P se parece mucho a Q, la "distancia" matemática será corta (alta idoneidad).

Cómo se aplica la asimetría: No buscamos una curva suave. Buscamos un pico de Dirac o una distribución muy concentrada en los bins (contenedores) de 80, 85 y 90 años. Los bins de 0 a 65 años deben tener un peso cercano a cero en nuestro vector objetivo Q, porque la presencia de población joven, aunque no es negativa per se, diluye la densidad del cliente objetivo en esa zona geográfica ("ruido" en la señal).
