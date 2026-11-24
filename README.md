# Recordatorio de citas: FHIR + WhatsApp

Script pequeño en Python que hace, en miniatura, lo que hace una integración sanitaria:

1. Lee citas confirmadas de un servidor **FHIR** (el estándar con el que los sistemas hospitalarios exponen sus datos).
2. Se queda con lo necesario de cada cita, aunque vengan campos vacíos.
3. Redacta un recordatorio y lo envía por la **WhatsApp Cloud API** de Meta.

Usa el servidor público de pruebas de HAPI FHIR, con pacientes ficticios.

## Cómo ejecutarlo

```bash
pip install requests
python recordatorio_citas.py        # modo simulación: lee las citas y enseña los mensajes
```

Sin credenciales no envía nada: solo muestra lo que enviaría.

## Envío real (opcional)

```bash
export WHATSAPP_TOKEN="..."               # token de la app de Meta
export WHATSAPP_PHONE_NUMBER_ID="..."     # id del número emisor
export WHATSAPP_DESTINO="34600000000"     # tu propio número, con prefijo y sin +
python recordatorio_citas.py 1
```

Los mensajes de texto libre solo se entregan si el destinatario ha escrito al número en las últimas 24 horas. Fuera de esa ventana, WhatsApp exige una plantilla aprobada.

## Qué falta para que fuera un producto

- Leer el teléfono real del paciente (recurso `Patient`) y pedir su consentimiento.
- Usar plantillas aprobadas en lugar de texto libre.
- Recibir la respuesta del paciente por webhook y actualizar la cita en el sistema.
- Guardar qué se ha enviado para no repetir avisos.
