# Diagnóstico de red del grafo  (2026-06-06)

Fuente: `graphify-out/graph.json`  ·  generado por `code/graph_diagnostics.py`

## 1. Estructura general

- Nodos: **616** · Aristas: **858** · Grado medio: **2.79**
- Densidad: 0.00453
- Componentes conexas: **153** (componente gigante: 451 nodos = 73%)
- Nodos aislados (grado 0): 139 · hojas (grado 1): 216 (35%)

## 2. Distribución de grado

- Grado máx: 98 · medio: 2.79 · mediana: 1
- Gini del grado: **0.681** (0 = parejo, →1 = todo concentrado en pocos hubs)
- Ajuste ley de potencia: α = 2.15, x_min = 5, KS = 0.248 → ajuste débil — no claramente ley de potencia
  - *(heurístico MLE+KS sobre la cola, n=55; no es un test riguroso power-law vs lognormal)*

Top 10 nodos por grado (con tipo):

| Grado | Nodo | file_type |
|---|---|---|
| 98 | Abuso de Posición Dominante | concept |
| 87 | Mercado Relevante | concept |
| 72 | Barreras a la Entrada | concept |
| 62 | Sentencia Nº 47/2006 | document |
| 53 | DL 211 | concept |
| 52 | Sentencia Nº 80/2009 | document |
| 50 | Colusión | concept |
| 36 | Fiscalía Nacional Económica | document |
| 36 | Poder de Mercado | concept |
| 35 | Operación de Concentración | concept |

## 3. Clustering y small-world

- Coef. de clustering medio: **0.0957** · transitividad: 0.0331
- Sobre la componente gigante (451 nodos): camino medio = 3.34, diámetro = 8
- Referencia aleatoria (ER): C_rand ≈ 0.0083, L_rand ≈ 4.63
- σ = (C/C_rand)/(L/L_rand) = **15.90** → **small-world** (σ > 1)

## 4. Entropía entre comunidades

- Comunidades: **173** · entropía = 5.57 bits · normalizada = **0.749** (1 = atención repartida pareja)
- Comunidad mayor: 61 nodos (10% del grafo) · top-5 suman 238 (39%)

## 5. Composición por tipo y centralidad cruzada

Distribución de `file_type`:

- `document`: 589 (96%)
- `concept`: 27 (4%)

- Grado medio de nodos concepto/rationale: 22.15
- Grado medio del resto (entidades/documentos): 1.90
- Primer nodo concepto/rationale en el ranking de grado: posición **#1**.

## 6. Traza año a año (¿consolida o diversifica?)

| Año | Nodos | Comunidades activas | Entropía norm. |
|---|---|---|---|
| 2004 | 12 | 10 | 0.98 |
| 2005 | 64 | 31 | 0.92 |
| 2006 | 41 | 25 | 0.96 |
| 2007 | 34 | 16 | 0.91 |
| 2008 | 33 | 18 | 0.95 |
| 2009 | 27 | 12 | 0.73 |
| 2010 | 29 | 22 | 0.95 |
| 2011 | 26 | 17 | 0.92 |
| 2012 | 29 | 13 | 0.92 |
| 2013 | 10 | 6 | 0.98 |
| 2014 | 16 | 8 | 0.88 |
| 2015 | 11 | 8 | 0.95 |
| 2016 | 19 | 14 | 0.95 |
| 2017 | 11 | 8 | 0.95 |
| 2018 | 32 | 20 | 0.93 |
| 2019 | 25 | 9 | 0.91 |
| 2020 | 14 | 8 | 0.97 |
| 2021 | 19 | 9 | 0.85 |
| 2022 | 24 | 16 | 0.95 |
| 2023 | 15 | 9 | 0.90 |
| 2024 | 28 | 16 | 0.89 |
| 2025 | 19 | 5 | 0.70 |
| 2026 | 4 | 3 | 0.95 |

- Tendencia: la entropía temática media pasa de 0.92 (años tempranos) a 0.91 (recientes) → el campo se está **consolidándose**.
- *(Sesgo: refleja la cobertura del corpus por año, no solo la actividad real del campo.)*

---

_Regenerar tras cada build con: `python code/graph_diagnostics.py`_