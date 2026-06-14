# Skills disponibles en este proyecto

- **minuta** (`.claude/skills/minuta/SKILL.md`) — genera minutas de jurisprudencia sobre libre competencia chilena desde el corpus `raw-md/` y el grafo `graphify-out/`. Trigger: `/minuta`
When the user types `/minuta`, invoke the Skill tool with `skill: "minuta"` before doing anything else.

---

# Base de Conocimiento de Investigación – Chile Libre Competencia

> **Versión de trabajo (mayo 2026).** Este repositorio está en fase de prueba con contenido real. Cuando el pipeline esté validado se producirá una versión con `[placeholder]` para publicación como guía replicable para la comunidad.

## Qué es esto
Una base de conocimiento de práctica profesional y de investigación sobre la política y jurisprudencia de libre competencia en Chile. El corpus cubre la producción normativa y jurisprudencial del TDLC y la CS, la actividad de enforcement de la FNE, y la normativa regulatoria de base (DL 211, guías, reglamentos). El sistema está orientado a un economista abogado senior que litiga ante el TDLC e investiga ante la FNE, y que necesita conocer la valoración de las autoridades de competencia sobre distintos temas para refinar argumentos y análisis.

## Cómo está organizado

- `raw/` — documentos fuente en PDF, organizados por tipo. **No modificar.**
- `raw-md/` — versiones Markdown de los documentos en `raw/`, producidas con MarkItDown. **No modificar.**
- `graphify-out/wiki/` — wiki organizada por temas. **La IA la mantiene por completo.**
- `graphify-out/notes/` — notas personales del investigador: hipótesis, observaciones, preguntas abiertas. **El investigador las mantiene.** No son fuentes de autoridad jurídica y nunca deben citarse como tal.
- `outputs/` — minutas de jurisprudencia, informes comparativos y otros documentos generados. **La IA deposita aquí todos los outputs de consultas.**
- `code/` — scripts de descarga y transformación de documentos.

### Tamaño y composición del corpus

**Track A — Jurisprudencia (corpus procesado en el grafo: 520 docs)**

| Subcarpeta en raw-md/ | Tipo | N° |
|---|---|---|
| `sentencias-tdlc-md/` | Sentencias TDLC | 212 |
| `sentencias-cs-md/` | Sentencias Corte Suprema | 128 |
| `resoluciones-tdlc-md/` | Resoluciones TDLC | 89 |
| `resoluciones-cs-md/` | Resoluciones Corte Suprema | 13 |
| `ae-tdlc-md/` | Acuerdos Extrajudiciales (FNE–TDLC) | 38 |
| `ern-tdlc-md/` | Expedientes de Recomendación Normativa | 22 |
| `icg-tdlc-md/` | Instrucciones de Carácter General | 9 |

**Track C — Normativa de base (corpus procesado en el grafo)**

| Subcarpeta en raw-md/ | Tipo | N° |
|---|---|---|
| `normativa-fusiones-fne-md/` | Guías, reglamentos y formularios FNE (concentraciones) | 8 |
| `normativa-general-md/` | DL 211 refundido | 1 |

**Track B — Enforcement FNE (pendiente de incorporación al grafo)**

| Subcarpeta en raw/ | Tipo | N° aprox. |
|---|---|---|
| `investigaciones-fne/` | Investigaciones y resoluciones FNE | 2.641 |

### Tres tracks analíticos del corpus

El corpus opera en tres tracks con lógicas distintas:

**Track A — Jurisprudencia (TDLC + CS):** Produce doctrina y construye precedente vinculante. Incluye sentencias, resoluciones, acuerdos extrajudiciales (AE) e instrucciones de carácter general (ICG). Es el track principal para análisis jurisprudencial y preparación de argumentos en litigios. La jerarquía de autoridad aplica plenamente aquí.

**Track B — Enforcement FNE:** Revela el estándar práctico con que la FNE evalúa problemas de competencia: qué investiga, qué metodologías aplica, cuándo archiva y cuándo requiere. No produce doctrina en sentido estricto, pero es esencial para anticipar el comportamiento de la FNE como contraparte o requirente, y para entender el contexto de un mercado. Pendiente de incorporación al grafo (2.641 docs).

**Track C — Normativa de base:** Legislación y regulación aplicable (DL 211 refundido, guías FNE, reglamentos de notificación de concentraciones). Funciona como ancla normativa: los nodos del Track A deben conectarse a los artículos del DL 211 que invocan. Tiene prioridad de extracción para referencias cruzadas.

**Casos vinculados:** Cuando una investigación FNE derivó en requerimiento ante el TDLC y este tuvo pronunciamiento de la CS, los tres documentos son perspectivas del mismo conflicto. El sistema debe identificarlos como un caso vinculado y tratarlos de forma integrada. La señal de vinculación son las referencias textuales en las sentencias y resoluciones al rol de la investigación FNE de origen.

### Ponderación dentro del corpus FNE

| Tipo | Peso | Criterio |
|---|---|---|
| Investigación que derivó en requerimiento TDLC | Alto | Vincular al caso judicial correspondiente |
| Resolución de archivo con razonamiento sustantivo | Medio | Contexto de enforcement; metodología aplicada |
| Resolución de archivo rutinaria (esp. concentraciones) | Bajo | Solo para conteo y contexto de mercado |

Distribución actual por subcarpeta: `concentraciones-o-integraciones/` (1.341), `abusos-de-posicion-de-dominio/` (561), `acuerdos-colusorios/` (193), `actos-anticompetitivos-de-la-autoridad/` (146), `incumplimiento-de-sentencias-e-instrucciones/` (146), `restricciones-verticales/` (36), `competencia-desleal/` (52), `sin-categoria/` (73).

---

## Jerarquía de autoridad de las fuentes

1. **Sentencias y resoluciones de la Corte Suprema** — vinculantes; pueden confirmar, revocar o modificar al TDLC.
2. **Sentencias y resoluciones del TDLC** — tribunal especializado con ministros economistas; supeditado a la CS.
2b. **Instrucciones de Carácter General (ICG) del TDLC** — emitidas bajo Art. 18 N°3 DL 211; vinculantes para todos los agentes del mercado; no son sentencias pero tienen fuerza normativa general. Citar con la misma autoridad que una resolución TDLC.
2c. **Acuerdos Extrajudiciales (AE) aprobados por el TDLC** — resolución judicial que homologa un acuerdo FNE–particular; vinculantes para las partes; relevantes como señal de estándar de enforcement para terceros.
2d. **Expedientes de Recomendación Normativa (ERN)** — proposiciones del TDLC al Presidente de la República bajo Art. 18 N°4 DL 211; no vinculantes, pero revelan el análisis económico-jurídico del tribunal sobre mercados regulados.
3. **Decisiones y dictámenes de la FNE** — autoridad administrativa; la FNE puede ser requirente y parte en el mismo caso.
4. **Guías y reglamentos de la FNE** (multas, concentraciones, notificación, remedios) — no vinculantes; peso auxiliar en litigios y referencia práctica en procedimientos de notificación.
5. **Estudios de la FNE** (sectoriales, temáticos) — material de apoyo para mercados específicos.
6. **Informes económicos periciales** — valor probatorio relevante en el caso concreto; no vinculantes.
7. **Doctrina académica revisada por pares.**
0. **Notas personales del investigador (`graphify-out/notes/`)** — nivel cero; sin autoridad jurídica ni académica. Registran hipótesis de trabajo, observaciones analíticas y preguntas abiertas del investigador. En el grafo se extraen con `file_type: rationale` y sus aristas hacia documentos del corpus son siempre INFERRED con confidence máximo 0.65. **Nunca citar como fuente en minutas, informes ni artículos.**

**Regla de conflicto:** Cuando fuentes de diferentes niveles aborden un mismo punto, cita la de mayor autoridad y señala cómo confirma, modifica o anula a la de menor autoridad. En caso de tensión TDLC (especialista) vs. CS (generalista), explicitar la tensión interpretativa y señalar cuál prima según el caso concreto (habitualmente la CS, anotando el disenso especializado).

**Regla de tensión TDLC/CS (obligatoria):** En toda respuesta que cite una sentencia o resolución del TDLC, indicar siempre si la CS se pronunció sobre el mismo punto — ya sea confirmando, modificando, revocando o simplemente no siendo recurrida. Si la CS no se pronunció, indicarlo explícitamente ("no fue recurrida" o "el recurso no abordó este punto"). Esta regla aplica incluso cuando la tensión es menor o la CS confirmó sin modificaciones.

---

## Ponderación por centralidad de nodo (Node Centrality Weighting)

El grafo de conocimiento rankea los documentos por cuántas conexiones tienen con otros documentos. Los documentos con más conexiones son "nodos dios" (god nodes) y reflejan el consenso del campo.

- Al generar artículos de wiki y sintetizar respuestas, dar mayor peso a los god nodes que a los documentos aislados.
- Si no hay sentencias de la CS en el corpus para un tema dado, aplicar esta regla a los documentos más citados y conectados disponibles.
- Un documento aislado (pocas conexiones) tiene menor peso en la síntesis, aunque puede ser relevante para identificar brechas o posiciones marginales.

---

## Conceptos centrales (anclas de extracción)

El sistema debe extraer estos términos como nodos de alta prioridad. Toda referencia a ellos en el corpus debe crear una arista con el documento fuente.

**Infracciones y conductas**
1. Colusión / acuerdo colusorio
2. Bid rigging / colusión en licitaciones públicas
3. Abuso de posición dominante
4. Precio predatorio
5. Negativa de venta / facilidades esenciales
6. Margin squeeze / estrangulamiento de márgenes
7. Operación de concentración

**Análisis de mercado**
8. Mercado relevante / definición de mercado
9. Mercado relevante geográfico
10. Poder de mercado / posición dominante
11. HHI / índice de concentración
12. Barreras de entrada

**Estándares de prueba y argumentos**
13. Estándar de prueba
14. Prueba indirecta / evidencia circunstancial
15. Argumento rechazado / criterio descartado
16. Eficiencias
17. Teoría del daño

**Remedios y sanciones**
18. Remedio estructural
19. Condición conductual
20. Multa / sanción / graduación de multa
21. Acuerdo extrajudicial / settlement
22. Desinversión

**Daños**
23. Nexo causal
24. Cálculo de daños / cuantificación de sobreprecio
25. Daño emergente / lucro cesante
26. Before-after / diferencias en diferencias (DiD)
27. Modelo contrafactual

**Normativa**
28. DL 211 / Decreto Ley 211
29. Artículo 3 DL 211
30. Notificación de concentración / umbrales de notificación

---

## Reglas de la wiki

Cada tema tiene su propio archivo `.md` en `wiki/`. Todo artículo sigue esta estructura fija:

**1. Resumen** — un párrafo construido prioritariamente desde los god nodes de ese cluster, no desde todas las fuentes en igual medida.

**2. Jurisprudencia (Track A)** — decisiones vinculantes del TDLC y la CS: doctrina establecida, evolución de criterios, tensiones TDLC/CS si las hay. Citar considerandos o párrafos específicos.

**3. Enforcement FNE (Track B)** — qué investigó la FNE sobre este tema, con qué metodología, con qué resultados (archivo vs. requerimiento). Énfasis en el razonamiento técnico-económico, no en la autoridad normativa.

**4. Casos vinculados** — solo cuando existan documentos de ambos tracks sobre el mismo conflicto. Presentar la secuencia completa: investigación FNE → requerimiento → sentencia TDLC → (si aplica) revisión CS. Omitir esta sección si no hay casos vinculados para el tema.

**5. Lo que las fuentes no abordan** — preguntas adyacentes que el corpus deja abiertas. Los silencios son tan informativos como el contenido.

Reglas adicionales:
- Vincula temas relacionados usando el formato `[[nombre-del-tema]]`
- Mantén un `INDEX.md` que liste cada tema con una descripción de una línea
- Cuando se agreguen nuevas fuentes, actualiza los artículos relevantes de la wiki

---

## Perspectiva de uso (User Perspective)

El usuario es un **economista abogado senior de libre competencia con práctica transversal** (no hay un sector dominante; trabaja en todos los mercados). Opera en tres roles distintos según el caso, y usa el sistema en este orden de frecuencia: primero para **mapear el terreno** antes de definir la estrategia, luego para **respaldar argumentos** al redactar escritos, y finalmente para **anticipar a la contraparte** (FNE o requirente). El sistema debe identificar desde el contexto de la consulta cuál es el rol relevante y adaptar el ángulo de la respuesta en consecuencia.

### Rol A — Defensa del requerido (litigio ante TDLC o investigación FNE)
El usuario representa a una empresa investigada o requerida. Necesita:
1. **Anticipar qué argumentos ya fueron rechazados** por el TDLC o la CS, para no repetirlos o para construir una distinción del caso actual respecto de los precedentes adversos.
2. **Identificar el estándar de prueba exigible** en el tipo de infracción imputada, y qué nivel de evidencia ha satisfecho o no satisfecho a las autoridades en casos comparables.
3. **Conocer los factores que mitigan la sanción o favorecen la absolución**: eficiencias acreditadas, ausencia de poder de mercado, falta de nexo causal, conducta cooperativa, acuerdos extrajudiciales y sus condiciones.
4. **Evaluar la solidez metodológica** de los análisis económicos de la FNE o de peritos contrarios, a la luz de lo que el TDLC y la CS han aceptado o rechazado.

### Rol B — Demandante o requirente (litigio ofensivo)
El usuario presenta un requerimiento o acción ante el TDLC. Necesita:
1. **Identificar el fallo líder** que sienta el estándar aplicable y los considerandos más citados en casos similares.
2. **Conocer qué elementos probatorios han resultado suficientes** para fundar una condena en casos análogos.
3. **Detectar tensiones TDLC vs. CS** que puedan afectar la solidez del caso en segunda instancia.

### Rol C — Asesoría preventiva en operaciones de concentración
El usuario asesora a partes en una fusión o adquisición que debe ser notificada o evaluada ante la FNE. Sus dos necesidades prioritarias son:
1. **Cómo han definido las autoridades el mercado relevante en ese sector específico**: pronunciamientos del TDLC (sentencias, resoluciones, ERN), resoluciones FNE sobre operaciones en el mismo mercado, y acuerdos extrajudiciales vinculados. El sistema debe entregar los mercados geográficos y de producto que las autoridades han usado, con las referencias exactas.
2. **Qué condiciones impuso la FNE en operaciones similares y por qué**: qué remedios exigió (estructurales o conductuales), cuál fue el razonamiento económico, y en qué casos aprobó sin condiciones. Esto permite evaluar el riesgo de la operación actual y anticipar la negociación.
3. **Cuándo la FNE aprobó sin condiciones y cuándo objetó**: umbrales prácticos y criterios que determinaron el resultado, más allá de los umbrales formales de notificación.
4. **Argumentos de eficiencia que han funcionado**: qué argumentos pro-competitivos consideró suficientes la FNE o el TDLC para aprobar o mitigar condiciones.

### Regla de enfoque para el sistema
Al responder, el sistema debe: (a) identificar desde la consulta en qué rol opera el usuario, (b) priorizar los documentos del corpus más relevantes para ese rol, y (c) señalar explícitamente si la respuesta cambia de perspectiva según el rol (ej. un mismo precedente puede ser favorable para la defensa y desfavorable para el demandante).

---

## Áreas de enfoque (Focus Areas)

1. Colusión horizontal y bid rigging — estándares de prueba, argumentos de defensa, criterios de descarte
2. Abuso de posición dominante — definición de mercado, poder de mercado, conducta, nexo causal
3. Cálculo de daños e indemnización civil — metodologías validadas, nexo causal, cuantificación
4. Operaciones de concentración — umbrales, análisis de efectos, remedios, negociación con FNE
5. Multas y sanciones — graduación, factores atenuantes, acuerdos extrajudiciales

---

## Foco de investigación (Research Focus)

Preguntas que el sistema debe estar posicionado para responder desde la perspectiva del defensor.

**P1 – Argumentos rechazados por materia:**
¿Qué argumentos de defensa ha rechazado explícitamente el TDLC o la CS en casos de (a) colusión, (b) abuso de posición dominante, y (c) concentraciones? Para cada argumento rechazado: sentencia que lo descarta, razón del descarte, y si existe algún caso posterior donde un argumento similar fue acogido.

**P2 – Estándar probatorio por tipo de infracción:**
¿Qué nivel de evidencia exige el TDLC para condenar en cada categoría? ¿Acepta prueba indirecta (plus factors)? ¿Cuándo ha absuelto por insuficiencia probatoria? Identificar los casos en que la CS revocó condenas del TDLC por razones probatorias.

**P3 – Metodologías económicas validadas y rechazadas:**
¿Qué metodologías de análisis económico ha aceptado o rechazado el TDLC/CS? Para cada una: sentencia líder, razonamiento económico, y si hay divergencia TDLC vs. CS. Incluir metodologías usadas por la FNE que aún no han sido validadas judicialmente.

**P4 – Factores que mitigan sanción o favorecen la defensa de fondo:**
¿Qué circunstancias han llevado al TDLC a absolver, reducir la multa, o acoger una excepción de fondo? Identificar: eficiencias aceptadas, ausencia de poder de mercado acreditada, falta de nexo causal, acuerdos extrajudiciales y sus condiciones.

**P5 – Posición de la FNE como contraparte:**
¿Qué estándar aplica la FNE en investigaciones y en notificaciones de concentración? ¿En qué casos archiva y por qué? ¿Qué condiciones impone en acuerdos extrajudiciales? ¿Cómo ha evolucionado su posición doctrinal en los últimos 5 años?

---

## Reglas de extracción de proposiciones (Claim Extraction Rules)

Para cada documento del corpus, extraer la lista de proposiciones afirmativas que contiene. Cada proposición lleva tres elementos:

- **Premisa:** el hecho o dato empírico que la sustenta, con referencia al considerando, recital o párrafo específico.
- **Inferencia:** la conclusión jurídica o económica que el documento extrae de esa premisa.
- **Puntero:** referencia exacta al texto del documento (ej. "Sentencia TDLC N°123/2018, Considerando 14°").

Adjuntar cada proposición al nodo-documento como nodo hijo. Las proposiciones son consultables junto a los nodos de concepto.

**Propósito:** Dos documentos que parecen alineados a nivel de documento pueden defender proposiciones incompatibles. La extracción a nivel de proposición hace visible esa incompatibilidad, que es el insumo directo para el registro de hipótesis y para la investigación académica.

---

## Particularidades institucionales del sistema chileno

- El TDLC es un tribunal especializado con ministros economistas. Sus fallos reflejan un enfoque interdisciplinario del derecho de la competencia.
- La Corte Suprema aplica una interpretación generalista al conocer recursos contra el TDLC.
- La FNE puede actuar como requirente (iniciando el procedimiento) y como parte en litigio dentro del mismo caso.
- Las guías de la FNE no son vinculantes pero tienen peso auxiliar en litigios y decisiones internas.
- El análisis debe reflejar estas tensiones institucionales siempre que sean relevantes para el punto consultado.

---

## Tipos de documentos considerados en el corpus

- Sentencias del TDLC y de la Corte Suprema
- Resoluciones del TDLC y de la Corte Suprema
- Investigaciones e informes de la FNE (incluyendo resoluciones de archivo y condiciones en concentraciones)
- Guías de la FNE
- Estudios sectoriales de la FNE
- Informes económicos periciales (de cualquiera de las partes o requeridos por el tribunal)

El sistema debe etiquetar cada documento con su tipo para aplicar correctamente la jerarquía de autoridad.

---

## Resultados deseados (Consultas objetivo)

### Consulta 1 – Interpretación de un artículo del DL 211
**Objetivo:** Para un artículo específico del DL 211 (ej. Art. 3, Art. 3 bis), mostrar cómo lo han interpretado la FNE, el TDLC y la CS, y señalar explícitamente contradicciones entre esas interpretaciones.
**Formato:** Tabla con: fuente, fecha, extracto de la interpretación, columna "Contradicción detectada (sí/no/cuál)".

### Consulta 2 – Comparación con borrador de informe económico
**Objetivo:** Al señalar un borrador de informe económico, compararlo con decisiones y dictámenes previos que aborden metodologías similares (tests de mercado, análisis de rentabilidad, cálculo de sobreprecios, definición de mercado relevante). Identificar inconsistencias metodológicas y doctrinales.
**Formato:** Listado de coincidencias y desviaciones, con referencias a los documentos previos que sustentan la comparación.

### Consulta 3 – Minuta de jurisprudencia completa
**Objetivo:** Minuta "muy completa" sobre un tema determinado, cubriendo interpretaciones del TDLC, FNE y CS, evolución cronológica, citas textuales de párrafos clave, tendencias, cambios de doctrina y puntos no resueltos.
**Formato:** Estilo minuta profesional con índice, resumen ejecutivo, desarrollo y sección "Contradicciones y tensiones no resueltas".

### Consulta 4 – Mapa de argumentos rechazados
**Objetivo:** Para un argumento específico que el usuario quiere usar en su defensa, identificar si fue rechazado antes, en qué contexto, y si existe alguna vía para distinguirlo o rehabilitarlo.
**Formato:** Tabla con: argumento, caso donde fue rechazado, razón del rechazo, casos donde fue acogido (si existen), estrategia de distinción posible.

### Consulta 5 – Perfil de enforcement de la FNE sobre un mercado
**Objetivo:** Para un sector o industria, sintetizar cómo ha actuado la FNE: investigaciones abiertas, archivadas, requerimientos presentados, condiciones impuestas en concentraciones, acuerdos extrajudiciales.
**Formato:** Línea de tiempo con hitos clave + tabla de casos por tipo de resultado.

---

## Reglas de respuesta (Response Rules)

Reglas que aplican a toda respuesta del sistema, independientemente del tipo de consulta.

**1. Citas textuales — obligatorio.**
Siempre incluir el texto exacto del considerando o párrafo relevante, con referencia precisa (nombre del documento y número de considerando o sección). No parafrasear sin citar el texto original. Si el corpus tiene el fragmento, copiarlo literalmente entre comillas. Formato: *"[texto exacto]" (Sentencia TDLC N°XX/YYYY, Considerando N°)*.

**2. Nivel de detalle económico — intermedio aplicado.**
Explicar qué aceptó o rechazó el tribunal y las razones económicas centrales (supuestos cuestionados, lógica de la decisión). No desarrollar la metodología estadística o econométrica en detalle salvo que el usuario lo pida explícitamente. El destinatario es un economista abogado que conoce los conceptos pero necesita saber cómo los valoró el tribunal, no el manual del método.

**3. Doctrina comparada — alerta cuando no hay precedente local.**
El sistema opera principalmente sobre el corpus chileno. Si una consulta no tiene precedente en el corpus, indicarlo explícitamente: *"No hay precedente chileno disponible sobre este punto en el corpus"*, y sugerir en qué tipo de fuente externa buscar (ej. jurisprudencia de la Comisión Europea, lineamientos DOJ/FTC, directrices OCDE). No inventar jurisprudencia extranjera.

**4. Ventana temporal — sin corte fijo; criterio es el último pronunciamiento relevante.**
No existe un año de corte rígido. El criterio vigente sobre un punto es el del último pronunciamiento que lo abordó directamente, cualquiera sea su fecha. Si ese pronunciamiento es antiguo (anterior a 2016, reforma DL 211), advertirlo: *"Este es el último pronunciamiento disponible sobre el punto, de [año], previo a la reforma de la Ley 20.945. No consta que haya sido actualizado"*. Incluir pronunciamientos históricos solo cuando ilustren la evolución o cuando no haya jurisprudencia reciente.

**5. Precedentes recientes — énfasis en los últimos 5-7 años.**
Al sintetizar doctrina, dar mayor peso a pronunciamientos desde 2018 en adelante (post-reforma). Citar pronunciamientos anteriores cuando son el origen del criterio actual o cuando no hay doctrina reciente sobre el punto.

---

## Módulo de diagnóstico (Diagnostic Module)

Después de cada build o actualización del grafo, calcular las propiedades de red del grafo y reportarlas en `GRAPH_REPORT.md`:

- **Distribución de grado:** ¿sigue una ley de potencia? Indica si el grafo tiene hubs dominantes.
- **Coeficiente de clustering + longitud media de camino:** determina si el grafo es small-world.
- **Entropía entre comunidades:** ¿la atención del corpus está concentrada en pocos clusters o distribuida?
- **Traza año a año:** ¿el campo se consolida o diversifica con el tiempo?
- Si hay más de una versión del grafo disponible, comparar métricas y reportar divergencias.

---

## Registro de hipótesis (Hypothesis Register)

- Cada vez que una consulta revele una contradicción interpretativa entre fuentes de igual o distinta jerarquía, generar una hipótesis y registrarla en `hypotheses.md` con: fecha, consulta que la originó, documentos involucrados y tipo de inconsistencia.
- Cuando se actualice el corpus, re-evaluar todas las hipótesis activas y actualizar el registro con el resultado.
- Las hipótesis son el insumo principal para el artículo de investigación académica.

---

## Memoria de sesión

El contexto persistente del proyecto y del usuario vive en el sistema de memoria del harness (`~/.claude/projects/.../memory/`: `MEMORY.md` como índice + `user_profile.md`, `project_context.md`, `feedback_graphify.md`), que se carga automáticamente al inicio de cada sesión. Cuando se aprenda información nueva relevante (decisiones de diseño, preferencias, cambios en el corpus), actualizar el archivo correspondiente de ese sistema. No usar archivos de memoria en la raíz del repo (se eliminaron por estar duplicados y desactualizados).

---

## Nota para el asistente (IA)

Este archivo `CLAUDE.md` es la guía principal para organizar, ponderar y consultar la base de conocimiento. Instrucciones de prioridad:

1. Aplicar siempre la jerarquía de autoridad de las fuentes.
2. Aplicar la ponderación por centralidad de nodo al sintetizar respuestas.
3. Preferir referencias concretas (artículos, considerandos, recitales o párrafos) antes que resúmenes genéricos.
4. Indicar explícitamente cuando no exista información en el corpus sobre un punto. No inventar ni extrapolar desde otras jurisdicciones a menos que se pida explícitamente.
5. Depositar todos los documentos generados (minutas, informes, comparaciones) en `outputs/`.
6. Registrar en `hypotheses.md` toda contradicción interpretativa detectada.
7. Al buscar en el corpus: consultar `graphify-out/wiki/` primero; si se requiere ir a `raw-md/`, usar siempre `grep -n -A 12 -B 3 "patrón" archivo(s)` en lugar de `sed` con rangos amplios. Nunca leer secciones largas de archivos si un grep con contexto es suficiente.
