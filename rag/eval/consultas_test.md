# Set de validación — consultas de prueba (RAG)

> Consultas con respuesta conocida (derivadas de `outputs/lista-apd-tdlc.md` y del
> corpus). Sirven para medir **recall de recuperación** (¿llega el chunk correcto?)
> antes de comprometer un modelo de embedding, y para validar la **cita** generada.
>
> Uso: para cada consulta, correr `rag_retrieve(q)` y verificar que el documento
> esperado aparece en el top-k. Luego `rag_ask(q)` y verificar la cita textual.

| # | Consulta | Documento(s) esperado(s) | Qué se valida |
|---|---|---|---|
| 1 | Estándar de abuso por estrangulamiento de márgenes en telecom | Sentencia 156/2017, 158/2017 | Recall conducta específica |
| 2 | Multa impuesta a la ANFP por abuso de posición dominante | Sentencia 173/2020 (3.145 UTA) | Dato numérico exacto + cita |
| 3 | Abuso de posición dominante de CENABAST frente a laboratorios | Sentencia 184/2022 | Recall por partes (CENABAST/ASILFA) |
| 4 | Caso EFE / GTD: ¿se acogió la demanda por abuso? | Sentencia 76/2008 (acoge parcial, 150 UTM) | Decisión + sentido |
| 5 | Empaquetamiento de productos bancarios por BancoEstado | Sentencia 174/2020 | Conducta + resultado (rechaza) |
| 6 | ¿La CS confirmó la condena del TDLC a Correos de Chile? | Sentencia 178/2021 + 178_2021_CS | Regla de tensión TDLC/CS |
| 7 | Negativa de venta a empresas de criptomonedas por bancos | Sentencia 189/2023 | Conducta + prescripción parcial |
| 8 | Discriminación del CDF en la venta de señal de fútbol | Sentencia N°191/2024 (32 UTA) | Recall reciente + multa |
| 9 | ¿Qué argumentos de defensa rechazó el TDLC en estrangulamiento? | 156/2017, 158/2017, 204/2025 | Síntesis multi-documento |
| 10 | Definición de mercado relevante en servicios portuarios | Sentencia 100/2010, 38/2006 | Recall transversal de concepto |

## Métricas a registrar en el piloto

- **Recall@k** por consulta y por modelo de embedding (bge-m3 vs multilingual-e5 vs voyage-law-2).
- **Precisión de la cita**: ¿el considerando citado existe y dice lo que se afirma?
- **Cumplimiento de reglas**: ¿aplicó jerarquía de autoridad y la regla de tensión TDLC/CS?
- **Costo/latencia** por consulta según modelo de generación (Haiku vs Sonnet).
