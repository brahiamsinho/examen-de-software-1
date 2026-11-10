# Defensa: cómo usamos deep learning en Modelia

Hoja de una página para explicarlo y mostrarlo. Las rutas y líneas son de `backend/apps/ai_assistant/`.

## Lo que se dice (30 segundos)

> Usamos deep learning de dos formas. Primero, un **modelo de lenguaje grande** (una red neuronal profunda tipo
> transformer) que conversa con el equipo y propone cambios al diagrama. Segundo, un **modelo de embeddings**
> (otra red profunda) que convierte cada mensaje en un vector que representa su significado; así la IA tiene
> **memoria semántica** entre diagramas. No entrenamos los modelos: los **integramos** con herramientas, memoria y
> control humano. La IA nunca modifica el diagrama sola: deja borradores y una persona los aprueba.

## Qué mostrar en el código (en este orden)

| # | Idea | Dónde | Qué señalar |
|---|---|---|---|
| 1 | Qué modelo se usa | `llm_provider.py:20` `get_active_llm_client` | Un interruptor (`LLM_PROVIDER`): Gemini, OpenAI o **local**. Cambiar de modelo no toca el resto |
| 2 | Hablar con el modelo | `openai_client.py:90` `generate_function_calls` | Se envía la conversación y el modelo responde **llamando a herramientas** (function calling) |
| 3 | Las herramientas | `tools.py:335` `reply_in_chat`, `tools.py:318` `suggest_uml_additions` | Lo único que la IA puede hacer: responder en el chat o sugerir cambios |
| 4 | Comportamiento | `chat.py:40` `_CHAT_INSTRUCTION` | Instrucciones: mentor, llama por su nombre a quien pregunta, explica con ejemplos del diagrama |
| 5 | Sabe quién pregunta | `chat.py` `_transcript` | Cada línea de la conversación lleva su autor (`Ana: ...`) |
| 6 | Memoria corta | `chat.py:32` `CONTEXT_MESSAGES = 30` | Recibe los últimos 30 mensajes del chat |
| 7 | Memoria semántica | `openai_client.py:62` `embed`, `memory.py:138` `recall`, `memory.py:114` `_cosine` | Texto → vector → similitud coseno → los mensajes más parecidos en significado (umbral `MIN_SIMILARITY` 0.35) |
| 8 | Control humano | `proposals.py:320` `approve_proposal` | La IA solo crea borradores; aprobar o rechazar es de un EDITOR/OWNER |
| 9 | Modelo en el celular | `mobile/lib/features/local_assistant/` | Un modelo corre dentro del teléfono (`flutter_gemma`), sin internet |

## Demostración (2 minutos)

1. En un diagrama escribe: «la clase Cliente debe tener un correo único».
2. En **otro** diagrama de la misma organización pregunta: «@IA ¿qué sabemos del correo de Cliente?».
3. La IA responde recordando lo de antes y dice de qué diagrama viene.
4. Pídele: «@IA agrega el atributo teléfono a Cliente». Aparece un **borrador** en «Propuestas de la IA»; apruébalo.
5. En el celular: abre el diagrama y muestra la pestaña «Diagrama» (vista previa de solo lectura).

## Preguntas probables

- **¿Entrenaron un modelo?** No. Usamos modelos preentrenados y construimos la integración: herramientas, memoria,
  aprobación humana y ejecución local. Entrenar necesitaría datos que no tenemos; la integración sí es nuestra.
- **¿Cómo recuerda la IA?** El modelo no recuerda solo. Guardamos un vector por mensaje y, al preguntar, buscamos
  los más parecidos en significado y se los mostramos junto con la pregunta.
- **¿Qué es un embedding?** Una lista de números que representa el significado de un texto. Textos parecidos
  quedan cerca; se miden con similitud coseno.
- **¿Es seguro?** La IA no escribe en el diagrama sin aprobación. La memoria solo busca dentro de la organización
  de quien pregunta (hay un test que lo comprueba, y se verificó rompiendo la protección a propósito).
- **¿Corre en local?** Sí: `LLM_PROVIDER=local` usa un modelo en la máquina (o en Google Colab), y la app móvil
  tiene un modelo propio en el teléfono.
- **¿Qué límites tiene?** Un modelo local pequeño (4B parámetros) explica peor que uno grande; la memoria no existe
  con Gemini (no tiene embeddings aquí); y todos los mensajes del chat se envían al proveedor de embeddings.

## Antes de presentar

- `.env`: `LLM_PROVIDER=local` para poder decir «corre en nuestra máquina» (necesita Ollama encendido y
  `ollama pull nomic-embed-text` una vez). Con `openai` también funciona, y es un cambio de una línea.
- Backend encendido y celular en la misma red wifi.
- Si la memoria no encuentra nada en la demo: `docker compose exec backend python manage.py embed_chat_memory`.
