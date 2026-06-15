# Set de validación — consultas de prueba (RAG)

> Dos consultas de referencia que cubren los dos casos de uso más exigentes del
> sistema: síntesis doctrinaria multi-documento y detección de tensión TDLC/CS.
> Cada consulta tiene un resultado esperado verificable contra el corpus.
>
> Uso: correr `./rag/ask.sh "<pregunta>"` y verificar que (a) los documentos
> esperados aparecen en los fragmentos recuperados y (b) la respuesta aplica
> correctamente las reglas de jerarquía y tensión TDLC/CS.

---

## Consulta 1 — Síntesis doctrinaria

**Pregunta:**

> ¿Cuál es el estándar jurídico y probatorio que aplica el TDLC para condenar
> por colusión horizontal? Identifica los requisitos que la jurisprudencia ha
> establecido, cita los considerandos centrales e indica si la CS ha confirmado
> o modificado ese estándar.

**Documentos esperados:** sentencias sobre colusión horizontal (farmacias,
pollos, navieras, papel tissue). Deben aparecer tanto sentencias TDLC como
sentencias CS sobre los mismos casos.

**Qué se valida:**
- Recuperación de doctrina consolidada a partir de múltiples sentencias
- Cita textual de considerandos con referencia precisa
- Aplicación de la jerarquía CS > TDLC
- Indicación explícita de si la CS confirmó, modificó o revocó el estándar

---

## Consulta 2 — Tensión TDLC/CS

**Pregunta:**

> ¿En qué casos la Corte Suprema ha modificado la multa impuesta por el TDLC,
> ya sea aumentándola, reduciéndola o cambiando su base de cálculo? Explica el
> criterio de la CS, compáralo con el del TDLC y cita ambas sentencias.

**Documentos esperados:** casos donde existe divergencia CS/TDLC en materia de
multas (base de cálculo de ventas afectadas, beneficio económico obtenido,
factores atenuantes). En particular: S. 167/2019 (CS duplica la multa del TDLC
al ampliar la base de «ventas afectadas») y S. 148/2015 (CS elimina el factor
«beneficio no acreditado»).

**Qué se valida:**
- Recuperación de pares de documentos vinculados (TDLC + CS sobre el mismo caso)
- Identificación de la divergencia doctrinaria concreta
- Aplicación de la regla de tensión TDLC/CS: indicar cuál prima y por qué
- Cita textual de considerandos de ambas instancias

---

## Ajustes disponibles

El comportamiento del RAG puede modificarse sin tocar el pipeline:

| Parámetro | Ubicación | Efecto |
|---|---|---|
| `top_k` | `ask.sh` (argumento 2) o `TOP_K` en `config.R` | Número de fragmentos recuperados por consulta. Default: 12. Subir a 15–20 mejora recall en documentos largos (dispositivos CS al final del texto). |
| `GEN_MODEL` | `config.R` | Modelo de generación. `GEN_FAST` (Haiku) para lookups; `GEN_SMART` (Sonnet) para minutas; `GEN_TOP` (Opus) para síntesis del paper. |
| `EMBED_PROFILE` | `config.R` | Modelo de embedding. Default: `bge_m3` (Ollama, local). Cambiar a `"bm25"` para fallback léxico sin Ollama. |
| System prompt | `R/prompt_rules.R` | Reglas de dominio (jerarquía de autoridad, citas obligatorias). Editar para adaptar a otro corpus jurídico. |

```bash
# Ejemplo: consulta con top_k=20 para capturar dispositivos al final de sentencias CS
./rag/ask.sh "¿Confirmó la CS la condena del TDLC en el caso pollos?" 20
```
