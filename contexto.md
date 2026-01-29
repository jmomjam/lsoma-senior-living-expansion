# Contexto Maestro del Proyecto: Algoritmo de Localización Estratégica (L-SOMA)

**Rol Requerido:** Físico y Científico de Datos Senior.
**Entorno de Ejecución:** Apple Silicon (Mac Mini M2) / Python (Miniforge).

## 1. Definición del Reto (Caso Fundación Innovación Bankinter)

El objetivo es desarrollar un algoritmo de "venta" e inversión para identificar las localizaciones óptimas para la apertura de **1.000 nuevas residencias de mayores** en España. El enfoque no es meramente demográfico, sino de viabilidad de negocio bajo restricciones estrictas:

* 
**Coste de la plaza:** 2.100€ mensuales.


* 
**Ocupación Objetivo:** Debe garantizarse una media del 85% para asegurar el retorno.


* 
**Riesgo Financiero:** El criterio de **NO morosidad** es fundamental; la solvencia del cliente es un filtro "hard-constraint".


* 
**Materia Prima:** Datos públicos del INE desglosados por **36.000 secciones censales**.


* 
**Metodología Base:** El caso sugiere usar una **Figure of Merit (FoM)** para medir el ajuste de la población a una pirámide ideal.



## 2. Enfoque Metodológico: De la Estadística Descriptiva a la Física de Sistemas

Hemos descartado el enfoque básico de hojas de cálculo propuesto inicialmente. Trataremos el problema como un **Sistema de Optimización Multiobjetivo en un Espacio de Fases**.

* **La Sección Censal como Estado Cuántico ():** Cada sección no es una fila de datos, sino un vector de estado en un espacio -dimensional (donde  son los rangos de edad/sexo).
* **Resonancia (FoM):** Buscamos el solapamiento máximo entre el estado real y un "Autoestado Objetivo" (nuestra Pirámide Ideal).
* **Campos de Potencial:** Modelamos las restricciones económicas (precio) y sociales (soledad) como barreras de potencial y fuerzas atractoras.

## 3. Inputs del Estudio Sociológico (Feature Engineering)

Basándonos en una investigación cualitativa profunda sobre los "disparadores de decisión" para el segmento de 2.100€, hemos identificado las siguientes variables latentes que deben ser cuantificadas (Feature Engineering):

1. **La Generación Sándwich (El Decisor):** El cliente real no es el mayor, sino la hija/nuera (45-64 años) que sufre *burnout*. Buscamos alta densidad de este grupo.
2. **Determinismo Arquitectónico ("Vivienda Prisión"):** Edificios antiguos sin ascensor actúan como aceleradores de la institucionalización. Proxy: Antigüedad del edificio (Catastro).
3. **Solvencia Patrimonial:** Dado que la pensión media no cubre los 2.100€, filtramos por Renta Media del Hogar y capacidad de licuación de patrimonio (alquiler de vivienda propia).
4. **Cuarta Edad:** El target no es +65, sino **+82 años** (fragilidad extrema), mayoritariamente mujeres.

## 4. Especificaciones del Algoritmo L-SOMA

El algoritmo debe implementarse en Python siguiendo esta lógica matemática:

### A. Vector Objetivo ()

Definiremos una distribución de probabilidad teórica (Target Distribution) asimétrica, con pesos máximos en los bins de edad **80-84** y **85+**, y sesgo positivo hacia el sexo femenino (mayor esperanza de vida y viudedad).

### B. Métrica de Ajuste (Figure of Merit Refinada)

En lugar de distancias euclidianas simples, utilizaremos la **Divergencia de Jensen-Shannon (JSD)** para calcular el FoM. Es una métrica robusta para comparar distribuciones de probabilidad.



*Donde  es la PDF (Probability Density Function) de la sección censal .*

### C. Función de Score Global ()

El ranking final de las 50 mejores secciones se obtendrá maximizando:


* **Trigger Social:** Normalización de (Soledad + Carga del Cuidador + Barreras Arquitectónicas).
* **Filtro Económico:** Función Heaviside () donde  si la Renta < Umbral Crítico (garantía de no morosidad).

## 5. Hoja de Ruta de Ejecución Técnica (Python/M2)

### Paso 1: Configuración & Ingesta

* Uso de `pandas` y `numpy` para manipulación tensorial.
* Carga de datos crudos del INE (Censo) y Atlas de Renta.
* Conversión de conteos absolutos a probabilidades (Normalización).

### Paso 2: Cálculo Vectorial

* Definición del array `target_pyramid` ().
* Cálculo vectorizado de la Divergencia JS para las 36.000 secciones usando `scipy.spatial.distance`.

### Paso 3: Enriquecimiento (Capas de Datos)

* Integración de datos de **Catastro** (antigüedad edificio) como proxy de accesibilidad.
* Cálculo de densidades de población "Generación Sándwich" (mujeres 45-64).

### Paso 4: Optimización y Filtrado

* Aplicación de la "Hard Constraint" de precio (2.100€).
* Ordenación por Score .
* Selección de las **Top 50**.

### Paso 5: Validación de Resiliencia (Opcional/Avanzado)

* Simulación de Monte Carlo para verificar la estabilidad de la ocupación del 85% ante fluctuaciones estocásticas en secciones pequeñas (<1.000 hab).

---
Este es un plan de ejecución diseñado específicamente para tu perfil técnico y tu hardware (Mac Mini M2). Vamos a estructurar el proyecto no como una simple tarea de análisis de datos, sino como la construcción de un **sistema de inferencia bayesiana o de optimización multiobjetivo**.

El "Algoritmo de IA" que entregaremos es, en términos rigurosos, un **Sistema de Soporte a la Decisión (DSS)** basado en álgebra lineal y estadística inferencial.

---

### Fase 0: Configuración del Entorno (Arquitectura ARM64)

Trabajando en un M2, aprovecharemos la aceleración de hardware para operaciones vectoriales.

1. **Entorno:** Usa `Miniforge` (optimizado para Apple Silicon) en lugar de Anaconda estándar.
2. **Stack Tecnológico:**
* `numpy` & `pandas`: Para manipulación de tensores (matrices de población).
* `scipy.spatial.distance`: Para calcular la divergencia de Jensen-Shannon (el núcleo matemático del FoM).
* `geopandas`: Para la espacialización de los datos (necesitarás los shapefiles de las secciones censales del INE).



---

### Fase 1: Definición del Vector de Estado Objetivo ()

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

### Fase 2: Ingesta y Normalización (El Espacio de Fases)

**Concepto Teórico:** **Funciones de Densidad de Probabilidad (PDF).**
Para comparar poblaciones de tamaños distintos (una sección de 500 habitantes vs. una de 1.500), debemos trabajar con probabilidades, no con conteos absolutos.

**El paso:**
Cargar los datos crudos del INE (36.000 filas).

* **Acción Técnica:** Transformar los conteos absolutos de cada fila en una PDF: .
* Esto convierte cada sección censal en un sistema comparable termodinámicamente (independiente del tamaño extensivo, nos importa la propiedad intensiva de la estructura de edad).

---

### Fase 3: Cálculo del FoM mediante Divergencia de Jensen-Shannon

**Concepto Teórico:** **Entropía de la Información y Divergencia.**
El caso pide un "Figure of Merit" (FoM) para medir el ajuste. En física y ciencia de datos, la métrica robusta para medir la "distancia" entre dos distribuciones de probabilidad es la **Divergencia de Jensen-Shannon (JSD)**.

* **Por qué JSD y no Kullback-Leibler (KL):** La KL no es simétrica y explota si  cuando . La JSD es suave, simétrica y acotada entre .
* **Acción Técnica:**


* Un valor cercano a 0 implica que la sección censal es idéntica a tu pirámide ideal (resonancia perfecta).
* Un valor cercano a 1 implica disonancia total (ej. un barrio lleno de niños).



---

### Fase 4: Feature Engineering de los "Disparadores" (Tensores de Influencia)

Aquí es donde "elevamos" el nivel usando tu estudio. Convertiremos los conceptos sociológicos en **variables de campo** que modifican el potencial de la ubicación.

#### Variable A: El Tensor de la "Generación Sándwich" (Caregiver Burnout)

* 
**Justificación:** El estudio señala que el decisor de compra (2.100€) no es el anciano, sino la hija/nuera de 45-64 años que sufre *burnout*. La reducción del *Caregiver Support Ratio* es crítica.


* **Implementación:** Calcular la densidad de mujeres de 45-64 años en la misma sección. Si esta densidad es alta junto a una alta densidad de mayores, la probabilidad de "cliente saturado" es máxima.

#### Variable B: La Barrera de Potencial Económico (Heaviside Step Function)

* **Justificación:** El precio es 2.100€/mes. Las pensiones cubren el 60-70%, pero el resto requiere "licuación de patrimonio" o ayuda familiar. La "no morosidad" es un requisito del sistema.


* **Implementación:** Usaremos los datos del **Atlas de Distribución de Renta de los Hogares (INE)**. Aplicaremos una función escalón (Heaviside):


* *Nota:* El umbral no es la pensión media, sino la renta neta media por hogar que permita asumir un flujo de caja negativo de ~800€/mes (diferencia pensión-coste).



#### Variable C: Determinismo Arquitectónico (Entropía del Hábitat)

* **Justificación:** "Vivienda como prisión". Pisos sin ascensor en cascos históricos actúan como aceleradores de la institucionalización.


* **Implementación:** Datos del Catastro. Edad media del edificio.
* Proxy: Si `Año_Construcción_Medio < 1980` (pre-normativa obligatoria de accesibilidad) y `Altura > 3 plantas`, el coeficiente de "necesidad" aumenta.



#### Variable D: Soledad No Deseada (Aislamiento)

* 
**Justificación:** Hogares unipersonales + Evento Centinela (caída) = Ingreso inmediato.


* **Implementación:** Ratio de hogares unipersonales en personas >65 años (Dato INE).

---

### Fase 5: El Algoritmo de Optimización (Función de Coste)

Finalmente, construimos la ecuación global que resolverá tu script en Python. Definimos el **Score de Idoneidad ()** para la sección :

**Sujeto a la restricción (Hard Constraint):**


* **Los Pesos ():** Aquí aplicas tu criterio experto. Dado que la restricción económica es binaria (pueden o no pueden pagar), el peso principal debe recaer en el **Ajuste Demográfico** y el **Decisor (Hija)**, ya que son los motores de la demanda.

---

### Siguientes pasos inmediatos:

1. **Descarga de Datos:** ¿Tienes ya los ficheros CSV/Excel del INE de secciones censales y el Atlas de Renta? Si no, te indico los enlaces exactos del INE.
2. **Definición del Vector :** ¿Quieres que te pase el array de numpy propuesto con los porcentajes exactos para la "pirámide ideal" basada en el estudio (sobreponderando mujeres 85+)?

Este enfoque justifica ante cualquier comité que no has "usado una IA para que piense por ti", sino que has diseñado un **modelo matemático de resonancia sociodemográfica**.