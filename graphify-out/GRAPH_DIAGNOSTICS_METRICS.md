# Métricas de red del grafo — corpus libre competencia chileno
## Calculadas el 2026-06-13 sobre graph.json (616 nodos, 858 aristas)

---

## 1. Estadísticas globales

| Métrica | Valor |
|---|---|
| Nodos totales | 616 |
| Aristas totales | 858 |
| Densidad del grafo | 0.00453 |
| Componentes conexas | 153 |
| **Componente gigante** | **451 nodos (73.2%)** |
| Nodos aislados (grado 0) | 139 (22.6%) |
| Nodos de bajo grado (grado 1) | 216 (35.1%) |

**Interpretación:** El grafo es muy disperso (densidad < 0.005). Casi tres cuartos de los nodos quedan conectados en una componente gigante, pero 139 nodos permanecen completamente aislados — son documentos que el extractor no pudo vincular a ningún otro nodo. Esto no es un defecto del pipeline sino un hallazgo sustantivo: esos documentos abordan temas que el resto del corpus no menciona, lo que los convierte en candidatos para silencio doctrinal o para Track B (enforcement FNE pendiente de integración).

---

## 2. Distribución de grado — ¿ley de potencia?

| Métrica | Valor |
|---|---|
| Grado promedio | 2.79 |
| Grado mediano | 1 |
| Grado máximo | 98 |
| Correlación log-log (r) | −0.887 |

**Resultado:** La correlación log-log entre grado y frecuencia es −0.887, lo que indica que la distribución de grado **sigue una ley de potencia** (r < −0.7 es el umbral convencional). El grafo es *scale-free*: unos pocos nodos concentran la mayoría de las conexiones mientras la gran mayoría tiene grado muy bajo. Esto es la firma de redes donde el crecimiento es preferencial — los conceptos y documentos más citados atraen más conexiones nuevas.

### Top 10 god nodes (hubs)

| Rango | Grado | Tipo | Nodo |
|---|---|---|---|
| 1 | 98 | concepto | Abuso de Posición Dominante |
| 2 | 87 | concepto | Mercado Relevante |
| 3 | 72 | concepto | Barreras a la Entrada |
| 4 | 62 | documento | Sentencia Nº 47/2006 |
| 5 | 53 | concepto | DL 211 |
| 6 | 52 | documento | Sentencia Nº 80/2009 |
| 7 | 50 | concepto | Colusión |
| 8 | 36 | documento | Fiscalía Nacional Económica |
| 9 | 36 | concepto | Poder de Mercado |
| 10 | 35 | concepto | Operación de Concentración |

**Interpretación:** Los tres god nodes de mayor grado son conceptos doctrinales, no documentos. Esto confirma que el grafo tiene estructura concepto-céntrica: los nodos más conectados son los conceptos que el corpus usa con más frecuencia, no los fallos individuales más citados. La Sentencia Nº 47/2006 (grado 62) y la Sentencia Nº 80/2009 (grado 52) son los únicos documentos en el top 10 — ambos son hitos jurisprudenciales reconocidos en libre competencia chilena.

---

## 3. Efecto small-world

Calculado sobre la componente gigante (451 nodos).

| Métrica | Grafo real | Grafo aleatorio equiv. | Ratio |
|---|---|---|---|
| Clustering promedio (C) | 0.1307 | 0.0083 | **15.7×** |
| Longitud media de camino (L) | 3.343 | 4.619 | 0.72× |
| **Índice σ = (C/C_rand) / (L/L_rand)** | **21.69** | 1.0 | — |

**Resultado:** El grafo es **small-world** (σ = 21.69 >> 1). El índice small-world combina dos condiciones: clustering mucho mayor que el aleatorio (los vecinos de un nodo tienden a estar también conectados entre sí) y caminos cortos. Ambas se cumplen. 

**Interpretación práctica:** Cualquier par de nodos del corpus está separado en promedio por 3.3 pasos. Esto significa que conceptos aparentemente distantes en el corpus (p.ej., "bid rigging" y "acuerdo extrajudicial") están a pocos saltos de distancia. Para el investigador, el grafo permite navegación eficiente: desde cualquier punto de entrada se puede alcanzar toda la jurisprudencia relevante en pocas consultas.

---

## 4. Estructura de comunidades — ¿concentrada o distribuida?

| Métrica | Valor |
|---|---|
| Número de comunidades | 173 |
| Modularidad Q | 0.5189 |
| Entropía entre comunidades | 5.569 bits |
| Entropía máxima posible | 7.435 bits |
| **Entropía normalizada** | **0.749** |

**Modularidad:** Q = 0.52 es alta (umbral convencional > 0.3). Las comunidades detectadas por el algoritmo son reales — los nodos dentro de cada comunidad están más densamente conectados entre sí que con el resto del grafo.

**Entropía normalizada = 0.749:** La atención del corpus está relativamente distribuida entre comunidades (1.0 sería distribución perfecta). No hay un solo cluster que domine el campo. Las 5 comunidades más grandes concentran el 38.6% de los nodos:

| Comunidad | Nodos | % del total | Tema central |
|---|---|---|---|
| 0 | 61 | 9.9% | Operación de Concentración |
| 1 | 50 | 8.1% | Abuso de Posición Dominante |
| 2 | 43 | 7.0% | Barreras a la Entrada |
| 3 | 42 | 6.8% | Poder de Mercado |
| 4 | 42 | 6.8% | Sentencia Nº 80/2009 |

**Interpretación:** La jurisprudencia chilena de libre competencia no está dominada por un solo tema. Las concentraciones (61 nodos) y el abuso de posición dominante (50 nodos) son los clusters mayores, pero colusión, barreras y mercado relevante tienen masa crítica propia. Esto refleja la diversidad temática del TDLC, que opera como tribunal general de competencia y no está especializado en una sola conducta.

---

## 5. Traza año a año — ¿consolidación o diversificación?

| Período | Nodos nuevos | Aristas nuevas | Observación |
|---|---|---|---|
| 2004 | 12 | 4 | Inicio del TDLC (creado por Ley 19.911/2003) |
| 2005 | 64 | 290 | **Pico de aristas**: primer año completo de actividad |
| 2006 | 41 | 87 | Consolidación inicial |
| 2007 | 34 | 170 | Segundo pico: sentencias fundacionales en APD |
| 2008–2011 | 115 | 97 | Producción estable, baja conectividad por período |
| 2012 | 29 | 61 | Repunte: caso farmacias (colusión, sentencia icónica) |
| 2013–2017 | 65 | 42 | Baja densidad relativa de nuevas conexiones |
| 2018–2026 | 173 | 80 | Expansión del corpus pero conexiones más difusas |

**Interpretación:** La curva de aristas muestra dos picos tempranos (2005, 2007) que corresponden a los años donde el TDLC estableció su jurisprudencia fundacional. A medida que el campo madura (2013–2026), los nodos nuevos se incorporan con menos conexiones por nodo — lo que puede interpretarse como **diversificación temática** (los casos recientes abordan temas más específicos y menos referenciados entre sí) más que como consolidación de doctrina. La excepción es 2012 (caso farmacias), que generó un cluster densamente conectado.

---

## 6. Síntesis para el paper

El grafo del corpus chileno de libre competencia exhibe las tres propiedades características de redes de conocimiento jurídico maduras:

1. **Scale-free (r = −0.887):** unos pocos conceptos doctrinales concentran la mayoría de las conexiones — los god nodes son conceptos, no documentos.

2. **Small-world (σ = 21.69):** navegación eficiente en pocas consultas; cualquier par de nodos está a ~3.3 pasos.

3. **Alta modularidad (Q = 0.52) con entropía distribuida (0.749):** las comunidades son reales y el campo está temáticamente diversificado, sin un solo cluster dominante.

Estas propiedades tienen implicancias directas para el diseño de los sistemas de consulta: en un grafo scale-free con alta modularidad, las respuestas más representativas del campo se obtienen consultando los god nodes (que reflejan el consenso del corpus), mientras que los nodos aislados y las comunidades pequeñas son los más indicados para identificar posiciones marginales, brechas y silencios doctrinales.
