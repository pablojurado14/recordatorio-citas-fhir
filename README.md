# Recordatorio de citas: FHIR + WhatsApp

Script en Python que hace, en pequeño, lo que hace una integración sanitaria:

1. Lee las citas confirmadas de un servidor **FHIR**, el estándar con el que los sistemas hospitalarios exponen sus datos.
2. Se queda solo con las citas futuras y descarta las que no tienen una fecha válida.
3. Si la cita no trae el nombre del paciente o del médico, sigue la referencia (`Patient/123`) y lo busca en su ficha.
4. Redacta un recordatorio y lo envía por la **WhatsApp Cloud API** de Meta.

Usa el servidor público de pruebas de HAPI FHIR, con pacientes ficticios. Los datos vienen incompletos, igual que en un sistema real: citas sin paciente, sin motivo o con referencias rotas. El programa las trata sin detenerse.

## Cómo ejecutarlo

```bash
pip install requests
python3 recordatorio_citas.py 10    # modo simulación: lee las citas y enseña los mensajes
```

Sin credenciales no envía nada.

## Envío real

```bash
export WHATSAPP_TOKEN="..."               # token de la app de Meta
export WHATSAPP_PHONE_NUMBER_ID="..."     # id del número emisor
export WHATSAPP_DESTINO="34600000000"     # número de destino, con prefijo y sin +
python3 recordatorio_citas.py 10
```

El token se lee del entorno y nunca se escribe en el código. El texto libre solo se entrega si el destinatario ha escrito al número en las últimas 24 horas; fuera de esa ventana WhatsApp exige una plantilla aprobada.

## Qué falta para que fuera un producto

- Leer el teléfono real del paciente y registrar su consentimiento.
- Usar plantillas aprobadas en lugar de texto libre.
- Recibir la respuesta del paciente por webhook y actualizar la cita en el sistema.
- Guardar qué se ha enviado para no repetir avisos.

## Cómo está hecho

Desarrollado con Claude como asistente de programación. Probado contra el servidor público HAPI FHIR y con un número de prueba de la WhatsApp Cloud API.
