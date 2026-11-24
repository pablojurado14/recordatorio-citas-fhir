# Recordatorio de citas: FHIR + WhatsApp

Tres ejercicios pequeños en Python sobre lo que hace, en miniatura, una integración sanitaria con agentes. Todos usan datos ficticios.

| Archivo | Qué hace |
|---|---|
| `recordatorio_citas.py` | Lee citas de un servidor FHIR y envía un recordatorio por la WhatsApp Cloud API |
| `agente_pacientes.py` | Responde preguntas de pacientes con los documentos del hospital y deriva a una persona cuando no debe contestar |
| `escalado_citas.py` | Mide la misma consulta sobre 500.000 citas sin índice, con índice y paginada |

## 1. Recordatorio de citas

1. Lee citas confirmadas de un servidor **FHIR** (el estándar con el que los sistemas hospitalarios exponen sus datos).
2. Se queda con lo necesario de cada cita, aunque vengan campos vacíos.
3. Redacta un recordatorio y lo envía por la **WhatsApp Cloud API** de Meta.

Usa el servidor público de pruebas de HAPI FHIR, con pacientes ficticios.

```bash
pip install requests
python recordatorio_citas.py        # modo simulación: lee las citas y enseña los mensajes
```

Sin credenciales no envía nada: solo muestra lo que enviaría.

### Envío real (opcional)

```bash
export WHATSAPP_TOKEN="..."               # token de la app de Meta
export WHATSAPP_PHONE_NUMBER_ID="..."     # id del número emisor
export WHATSAPP_DESTINO="34600000000"     # tu propio número, con prefijo y sin +
python recordatorio_citas.py 1
```

Los mensajes de texto libre solo se entregan si el destinatario ha escrito al número en las últimas 24 horas. Fuera de esa ventana, WhatsApp exige una plantilla aprobada.

### Qué falta para que fuera un producto

- Leer el teléfono real del paciente (recurso `Patient`) y pedir su consentimiento.
- Usar plantillas aprobadas en lugar de texto libre.
- Recibir la respuesta del paciente por webhook y actualizar la cita en el sistema.
- Guardar qué se ha enviado para no repetir avisos.

## 2. Agente de preguntas de pacientes

Un ejercicio para entender dónde falla la recuperación de documentos (RAG) y cuándo debe parar un agente.

```bash
python agente_pacientes.py                         # preguntas de ejemplo
python agente_pacientes.py "¿Tengo que ayunar?"    # una pregunta concreta
python agente_pacientes.py --detalle "..."         # enseña la puntuación de cada fragmento
```

- Busca el fragmento más parecido en tres documentos ficticios y responde citando la fuente.
- Si el parecido no llega a un umbral, o la pregunta es clínica, no contesta: deriva a una persona con un resumen.

No usa ningún modelo de lenguaje, a propósito: aísla la recuperación y la decisión de derivar.

### Limitaciones conocidas

- Busca por palabras, no por significado: "¿Tengo que ayunar?" no encuentra el fragmento que dice "ayunas". Se resuelve con embeddings.
- Detecta lo clínico con una lista de palabras. En un sistema real lo haría un modelo, con la lista como segunda barrera.

## 3. Escalado de una consulta

```bash
python escalado_citas.py
```

Crea una base de datos SQLite con 500.000 citas ficticias, mide la consulta "citas confirmadas de un hospital en las próximas 24 horas" sin índice, con índice y paginada, y enseña el plan de ejecución de cada una. Borra la base de datos al terminar.

---

Desarrollado con Claude como asistente de programación.
