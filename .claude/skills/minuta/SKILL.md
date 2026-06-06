# /minuta

Genera minutas profesionales de jurisprudencia sobre libre competencia chilena a partir del corpus `raw-md/` y el grafo `graphify-out/`. Cubre Track A (jurisprudencia TDLC + CS) y, si se pide, Track C (normativa).

## Uso

```
/minuta "<pregunta>"                      # minuta sobre un tema
/minuta "<pregunta>" --tribunal tdlc      # solo sentencias TDLC
/minuta "<pregunta>" --tribunal cs        # solo sentencias CS
/minuta "<pregunta>" --años 2015-2020     # filtrar por rango de años
/minuta "<pregunta>" --track AC           # incluir normativa (Track C)
```

## Qué produce

Una minuta profesional con: resumen ejecutivo, análisis por tribunal, tabla de sentencias con citas textuales, contradicciones TDLC/CS detectadas, y metodología de búsqueda. Al final pregunta si guardar en `outputs/`.

---

## Pasos (ejecutar en orden, no saltar ninguno)

### Paso 1 — Parsear la consulta

Del input del usuario, extraer:

- **Conceptos clave** (2–5 términos): el tema central y variantes morfológicas/sinónimos.
  Ejemplos:
  - "atenuantes en colusión" → `["atenuante", "atenuan", "circunstancia mitigadora", "colaboraci", "colusión", "multa"]`
  - "definición de mercado relevante" → `["mercado relevante", "mercado geográfico", "mercado producto", "definición de mercado"]`
- **Tribunal scope** (default: todos): TDLC, CS, o ambos.
- **Año scope** (default: todos).
- **Track scope** (default: A).

### Paso 2 — Integración con el grafo (3 sub-pasos siempre; mostrar menú solo si los 3 fallan)

El grafo es útil aunque el concepto buscado no sea un nodo. Lo que siempre tiene son: centralidad de documentos, comunidades temáticas, y vecinos de entidades nombradas. Estos tres elementos permiten priorizar qué leer — sin reemplazar el grep exhaustivo del Paso 3.

#### 2A — Cargar estructura del grafo

```bash
$(cat graphify-out/.graphify_python) -c "
import json
from pathlib import Path

data = json.loads(Path('graphify-out/graph.json').read_text())
nodes = data['nodes']

# graph.json (formato node_link) NO persiste 'degree' en los nodos: las aristas
# viven en data['links'] con source/target. Calcular el grado contando aristas,
# si no toda la priorización por centralidad colapsa a 0.
from collections import Counter
deg = Counter()
for e in data.get('links', []):
    deg[e['source']] += 1
    deg[e['target']] += 1

# God nodes: los 20 más conectados del corpus
god_nodes = sorted(
    [{'id': n['id'], 'label': n.get('label', n['id']),
      'degree': deg.get(n['id'], 0),
      'community': n.get('community', -1),
      'source_file': n.get('source_file', '')}
     for n in nodes],
    key=lambda x: x['degree'], reverse=True
)[:20]

# Índice comunidad → documentos (ordenados por degree)
communities = {}
for n in nodes:
    c = n.get('community', -1)
    if c not in communities:
        communities[c] = []
    communities[c].append({
        'id': n['id'],
        'label': n.get('label', n['id']),
        'degree': deg.get(n['id'], 0),
        'source_file': n.get('source_file', '')
    })
for c in communities:
    communities[c].sort(key=lambda x: x['degree'], reverse=True)

result = {
    'total_nodes': len(nodes),
    'god_nodes': god_nodes,
    'communities': communities
}
Path('/tmp/minuta_graph.json').write_text(json.dumps(result, ensure_ascii=False))
print(f'Grafo cargado: {len(nodes)} nodos, {len(communities)} comunidades')
print(f'God node #1: {god_nodes[0][\"label\"]} ({god_nodes[0][\"degree\"]} conexiones)')
" 2>/dev/null
```

#### 2B — Buscar en el grafo: concepto exacto + entidades nombradas de la consulta

Ejecutar en paralelo:

**Búsqueda 1 — concepto exacto** (puede fallar para conceptos abstractos):
```bash
$(cat graphify-out/.graphify_python) -c "
import json
try:
    from graphify.query import query
    result = query('CONCEPTO', graph_path='graphify-out/graph.json', limit=15, mode='bfs')
    files = list(set(n.get('source_file','') for n in result.get('nodes',[]) if n.get('source_file')))
    print(json.dumps({'found': len(files) > 0, 'source_files': files}))
except Exception as e:
    print(json.dumps({'found': False, 'source_files': [], 'error': str(e)}))
" 2>/dev/null
```

**Búsqueda 2 — entidades nombradas implícitas en la consulta:**
Del texto de la consulta, identificar entidades que probablemente SÍ son nodos: tribunales (FNE, TDLC, CS), empresas (CMPC, SCA, Biosano, etc.), números de sentencia mencionados, mercados específicos. Buscar coincidencias parciales en el grafo:

```bash
$(cat graphify-out/.graphify_python) -c "
import json
from pathlib import Path

graph = json.loads(Path('/tmp/minuta_graph.json').read_text())
_data = json.loads(Path('graphify-out/graph.json').read_text())
all_nodes = _data['nodes']

# Grado real desde las aristas (graph.json no persiste 'degree' en los nodos)
from collections import Counter
deg = Counter()
for e in _data.get('links', []):
    deg[e['source']] += 1
    deg[e['target']] += 1

# Entidades a buscar — reemplazar con las extraídas de la consulta
search_terms = ['FNE', 'TDLC']  # SUSTITUIR con entidades reales de la consulta

matches = []
for node in all_nodes:
    label = node.get('label', '').upper()
    for term in search_terms:
        if term.upper() in label:
            matches.append({
                'id': node['id'],
                'label': node.get('label', ''),
                'degree': deg.get(node['id'], 0),
                'community': node.get('community', -1),
                'source_file': node.get('source_file', '')
            })
            break

matches.sort(key=lambda x: x['degree'], reverse=True)
print(json.dumps({'found': len(matches) > 0, 'matches': matches[:30]}))
" 2>/dev/null
```

#### 2C — Construir lista de prioridad desde comunidades relevantes

Con los resultados de 2B:

1. Recolectar todas las comunidades de los nodos encontrados (por concepto exacto + por entidades relacionadas).
2. Para cada comunidad relevante, tomar los documentos ordenados por degree (del `/tmp/minuta_graph.json`).
3. Generar `PRIORITY_FILES`: `source_file` de esos documentos, de mayor a menor centralidad.
4. Guardar en `/tmp/minuta_priority.txt`.

```bash
$(cat graphify-out/.graphify_python) -c "
import json
from pathlib import Path

graph = json.loads(Path('/tmp/minuta_graph.json').read_text())

# Comunidades relevantes — reemplazar con las identificadas en 2B
relevant_communities = {-1}  # SUSTITUIR con comunidades reales

priority_files = []
seen = set()
for comm_id, nodes in graph['communities'].items():
    if int(comm_id) in relevant_communities:
        for n in nodes:  # ya ordenados por degree desc
            sf = n.get('source_file', '')
            if sf and sf not in seen:
                priority_files.append(sf)
                seen.add(sf)

# También añadir los god nodes como prioridad base
for gn in graph['god_nodes']:
    sf = gn.get('source_file', '')
    if sf and sf not in seen:
        priority_files.append(sf)
        seen.add(sf)

Path('/tmp/minuta_priority.txt').write_text('\n'.join(priority_files))
print(f'Archivos prioritarios desde el grafo: {len(priority_files)}')
" 2>/dev/null
```

**Si 2B y 2C no identificaron ningún nodo ni comunidad relevante** (el grafo no tiene nada relacionado con la consulta), mostrar menú antes de continuar:

```
⚠️ El grafo no contiene nodos relacionados con "[CONCEPTO]" ni con las entidades mencionadas.

Esto ocurre cuando el tema es muy específico o el corpus relevante aún no está indexado.

Opciones:
  A. Búsqueda textual exhaustiva sobre el corpus [RECOMENDADO — ~30-60s]
     → Grep sobre raw-md/. Cobertura completa pero sin priorización del grafo.
  B. Usar los 20 god nodes como semilla y buscar desde ahí.
     → Más rápido. Solo útil si el tema está en documentos muy conectados.
  C. Usar otro término → escríbelo.
  D. Cancelar.

[A recomendado]:
```

Si A o Enter: continuar con Paso 3 sin lista de prioridad (grep puro).
Si B: usar `/tmp/minuta_graph.json` → campo `god_nodes` → sus `source_file` como PRIORITY_FILES.
Si C/D: igual que antes.

### Paso 3 — Descubrimiento del corpus (SIEMPRE, independiente del resultado del grafo)

Este paso es **obligatorio** aunque el grafo haya encontrado nodos. Garantiza que no se pierda ningún documento relevante.

Determinar carpetas según track scope:

```
Track A (default):
  raw-md/sentencias-tdlc-md/     ← incluye subcarpetas (find -name "*.md")
  raw-md/sentencias-cs-md/
  raw-md/resoluciones-tdlc-md/
  raw-md/resoluciones-cs-md/
  raw-md/ae-tdlc-md/
  raw-md/ern-tdlc-md/
  raw-md/icg-tdlc-md/

Track C (si --track AC):
  raw-md/normativa-fusiones-fne-md/
  raw-md/normativa-general-md/
```

```bash
# Total del corpus relevante
find raw-md/sentencias-tdlc-md/ raw-md/sentencias-cs-md/ \
     raw-md/resoluciones-tdlc-md/ raw-md/resoluciones-cs-md/ \
     raw-md/ae-tdlc-md/ raw-md/ern-tdlc-md/ raw-md/icg-tdlc-md/ \
     -name "*.md" | wc -l

# Archivos con menciones a los keywords
grep -rl "KEYWORD1\|KEYWORD2\|KEYWORD3" \
  raw-md/sentencias-tdlc-md/ \
  raw-md/sentencias-cs-md/ \
  raw-md/resoluciones-tdlc-md/ \
  raw-md/resoluciones-cs-md/ \
  raw-md/ae-tdlc-md/ \
  raw-md/ern-tdlc-md/ \
  raw-md/icg-tdlc-md/ \
  2>/dev/null | sort > /tmp/minuta_candidatos.txt

wc -l /tmp/minuta_candidatos.txt
cat /tmp/minuta_candidatos.txt
```

Reportar: `"Corpus: N archivos totales. Candidatos con menciones: M archivos. Prioritarios por grafo: P archivos."`

**Ordenar candidatos para lectura:** los archivos en `/tmp/minuta_candidatos.txt` que también aparezcan en `/tmp/minuta_priority.txt` van primero (ordenados por centralidad del grafo). El resto va después. Esto hace que los subagentes del Paso 4 lean primero los documentos más conectados del corpus — los más probablemente relevantes.

**Si M > 35:** avisar antes de continuar:
```
📋 Se encontraron M archivos con menciones. Leerlos todos puede demorar varios minutos.
¿Continuar con cobertura exhaustiva? [S/n]:
```
Si dice S o Enter: continuar. Si N: preguntar cuántos leer (top N por tamaño de archivo, como proxy de relevancia).

**Si M = 0:** informar que el corpus no contiene el término. Sugerir 2–3 sinónimos alternativos basados en el contexto jurídico chileno y ofrecer reintentar.

### Paso 4 — Leer los archivos candidatos

**OBLIGATORIO usar el Agent tool con subagentes paralelos.** No leer archivos uno a uno directamente.

Dividir `/tmp/minuta_candidatos.txt` en chunks de ~15 archivos. Despachar todos los subagentes en un solo mensaje (en paralelo).

Cada subagente recibe este prompt exacto (sustituir TEMA y ARCHIVOS):

```
Eres un asistente de investigación jurídica en libre competencia chilena.

Lee los siguientes archivos de sentencias y extrae información sobre [TEMA].

Archivos a leer:
[lista de rutas absolutas]

Para cada archivo donde encuentres información relevante sobre [TEMA], extrae:
1. Identificador: nombre del archivo → número de sentencia/resolución y año
2. Tribunal: TDLC / CS / Resolución TDLC / Resolución CS / AE / ERN / ICG
3. Año del documento
4. Cita textual exacta del considerando o párrafo más relevante (entre comillas, copiado literalmente)
5. Número de considerando o sección donde aparece la cita
6. Resumen en 2-3 oraciones de qué dice el documento sobre [TEMA]
7. Tensión TDLC/CS: si este documento revisa, confirma o modifica un fallo de otro tribunal sobre el mismo punto, indicarlo. Si no aplica: escribir "N/A".
8. Atenuantes/agravantes acogidos o rechazados (si el tema lo requiere): listarlos con efecto cuantitativo si está disponible.

Formato de output: JSON array. Cada elemento tiene los campos:
{
  "archivo": "nombre_archivo.md",
  "tribunal": "TDLC|CS|...",
  "anio": 2020,
  "concepto": "descripción breve de qué aspecto de [TEMA] aborda",
  "cita_textual": "texto exacto...",
  "considerando": "C. 45° / Sección 3.2 / etc.",
  "resumen": "...",
  "tension_tdlc_cs": "Confirma TDLC 145/2015 / Revoca / N/A",
  "notas_adicionales": "cualquier otro dato relevante"
}

Si un archivo no contiene información relevante sobre [TEMA], omitirlo completamente del output.
Si un archivo es demasiado largo para leer completo, buscar primero con grep las secciones con los keywords y leer solo esas secciones (±50 líneas de contexto).

Output: solo el JSON array, sin texto adicional.
```

Reunir todos los JSON de los subagentes. Consolidar en una lista única, deduplicando archivos duplicados (quedarse con el resultado más completo si un archivo aparece en varios chunks).

### Paso 5 — Generar la minuta

Con la lista consolidada, generar la minuta con esta estructura exacta:

---

```
═══════════════════════════════════════════════════════
MINUTA DE JURISPRUDENCIA — LIBRE COMPETENCIA CHILE
═══════════════════════════════════════════════════════
Tema:        [TEMA]
Elaborada:   [fecha]
Corpus:      [M candidatos de N totales] · [X sentencias con información relevante]
Tracks:      [A / AC]
Metodología: [Grafo + textual / Solo textual / Solo grafo]
═══════════════════════════════════════════════════════

ÍNDICE
1. Resumen ejecutivo
2. Marco normativo y jerarquía de fuentes
3. Análisis jurisprudencial
   3.1. Sentencias y resoluciones TDLC
   3.2. Revisión por la Corte Suprema
4. Tabla de sentencias
5. Contradicciones y tensiones no resueltas
6. Lo que el corpus no aborda
7. Metodología
```

**1. Resumen ejecutivo**
3–5 párrafos. Construir principalmente desde los documentos más conectados en el grafo (god nodes) y los más citados en el corpus. Indicar si existe doctrina consolidada o si el campo está en disputa. Si hay tensión TDLC/CS activa, mencionarla en el primer párrafo.

**2. Marco normativo**
Artículos del DL 211 invocados en los documentos. Si Track C: incluir guías FNE y normativa relevante.

**3.1. TDLC — análisis cronológico**
Por cada sentencia/resolución relevante:
- Encabezado: `**Sentencia TDLC N° XXX/YYYY — [partes principales]**`
- Cita textual del considerando más relevante: *"[texto exacto]" (C. N°)*
- Qué dijo el tribunal sobre el tema (2–3 párrafos)
- Al final: estado de revisión CS (obligatorio, siempre):
  - `→ CS: Confirmó (Rol N° XXX-YYYY)`
  - `→ CS: Redujo la multa (Rol N° XXX-YYYY) — [razón breve]`
  - `→ CS: No fue recurrida.`
  - `→ CS: Recurso no abordó este punto.`
  - `→ CS: Sin información en corpus.`

**3.2. CS — análisis**
Por cada fallo CS que revisó un punto del tema:
- Qué confirmó, modificó o revocó
- Cita textual del razonamiento de la CS
- Si la CS introdujo doctrina propia distinta a la del TDLC: destacarlo

**4. Tabla de sentencias**

| Documento | Tribunal | Año | Aspecto del tema | Cita (extracto 30 palabras) | CS |
|---|---|---|---|---|---|
| Sentencia N° X/YYYY | TDLC | YYYY | [concepto específico] | "[extracto...]" | Confirmó / Redujo / No recurrida |

**5. Contradicciones y tensiones no resueltas**
Listar cada contradicción detectada:

```
Tensión [N]: [Documento A] vs [Documento B]
Descripción: [qué dice cada uno sobre el mismo punto]
Prima: [cuál tiene mayor jerarquía o es más reciente] / Sin resolver
```

Si no hay contradicciones detectadas: decirlo explícitamente ("No se detectaron contradicciones en el corpus analizado sobre este punto.").

**6. Lo que el corpus no aborda**
Preguntas adyacentes que el análisis deja abiertas. Ser específico — no genérico. Los silencios del corpus son información.

**7. Metodología**
```
Conceptos buscados en el grafo: [lista con resultado para cada uno: "nodo encontrado" / "no encontrado"]
Método aplicado: [grafo / textual / combinado]
Carpetas exploradas: [lista]
Total archivos en corpus relevante: N
Archivos candidatos (con menciones): M
Archivos leídos con información: X
Keywords de grep: [lista]
Comandos ejecutados: [lista de find/grep/graphify usados]
```

---

### Paso 6 — Contradicciones → hypotheses.md

Si en el Paso 5 se detectaron contradicciones:

```
⚠️ Se detectaron [N] tensiones interpretativas (ver Sección 5 de la minuta).

¿Registrar en graphify-out/notes/hypotheses.md para seguimiento en la investigación? [S/N]:
```

Si S: **verificar si el archivo existe** (`Read graphify-out/notes/hypotheses.md`). Si no existe, crearlo con encabezado básico. Agregar cada tensión con este formato:

```markdown
## Hipótesis [N+1] — [tema breve] ([fecha])

**Originada en:** Consulta `/minuta [query original]`
**Documentos involucrados:** [lista]
**Tipo de tensión:** TDLC vs CS | Temporal (evolución) | Entre instancias
**Descripción:** [texto de la contradicción]
**Estado:** Abierta
```

### Paso 7 — Guardar output

```
✅ Minuta completada. [X] sentencias con información relevante sobre "[TEMA]".

¿Guardar en outputs/minuta_[tema_slug]_[fecha].md? [S/N]:
```

- `[tema_slug]` = tema en minúsculas, espacios reemplazados por `_`, sin tildes, máx 40 chars.
- `[fecha]` = AAAAMMDD.

Si S: guardar con `Write`. Confirmar ruta completa al usuario.
Si N: la minuta queda solo en el chat.

---

## Reglas que aplican a toda minuta

**Citas textuales — obligatorio:** Siempre texto exacto del considerando, copiado literalmente, entre comillas. Formato: *"[texto exacto]" (Sentencia TDLC N°XX/YYYY, Considerando N°)*. No parafrasear sin citar primero.

**Jerarquía de fuentes:** CS > TDLC > Resoluciones TDLC/CS > ICG > AE > ERN > FNE (enforcement) > Guías FNE. Aplicar siempre al sintetizar: citar la fuente de mayor jerarquía, señalar cómo las de menor jerarquía confirman o difieren.

**Tensión TDLC/CS — obligatoria:** Para cada sentencia TDLC citada, indicar siempre si la CS se pronunció. No omitir este dato aunque sea "no fue recurrida".

**Sin invención:** Si el corpus no tiene precedente sobre un punto, decirlo: *"No hay precedente chileno disponible sobre este punto en el corpus analizado."* No extrapolar desde otras jurisdicciones salvo que el usuario lo pida.

**Transparencia metodológica:** El usuario debe saber si la respuesta viene del grafo, del texto, o de ambos. Siempre reportar en la Sección 7.

**Notas sin autoridad:** Si la consulta origina información desde `graphify-out/notes/`, aclarar que son notas de investigación sin autoridad jurídica. No citar como fuente en la minuta.
