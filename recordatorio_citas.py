"""Recordatorio de citas: lee citas de un servidor FHIR y prepara un WhatsApp por cada una.

Uso:
    python recordatorio_citas.py            # lee 5 citas y enseña los mensajes (no envía nada)
    python recordatorio_citas.py 10         # lo mismo con 10 citas

Para enviar de verdad hacen falta tres variables de entorno (ver README):
    WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_DESTINO
"""
import os
import sys
from datetime import date, datetime, timezone

import requests

# --- Configuración -----------------------------------------------------------
# Se lee del entorno para no escribir nunca un token dentro del código.
FHIR_BASE = os.environ.get("FHIR_BASE", "https://hapi.fhir.org/baseR4")  # servidor público de pruebas
GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v26.0")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
DESTINO = os.environ.get("WHATSAPP_DESTINO")  # mi propio número: nunca se escribe a pacientes


def obtener_citas(cuantas):
    """Pide al servidor FHIR las citas confirmadas y devuelve la lista de recursos Appointment."""
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # fecha y hora actuales, no solo el día
    respuesta = requests.get(
        f"{FHIR_BASE}/Appointment",
        params={
            "status": "booked",
            "date": f"ge{ahora}",  # solo citas desde este momento ("ge" = mayor o igual)
            "_sort": "date",                           # las más próximas primero
            "_count": cuantas,
        },
        headers={"Accept": "application/fhir+json"},
        timeout=20,
    )
    respuesta.raise_for_status()  # si el servidor contesta 4xx o 5xx, salta un error
    bundle = respuesta.json()     # FHIR devuelve un "Bundle": un sobre con una lista de entradas
    return [entrada["resource"] for entrada in bundle.get("entry", [])]


def resumir_cita(recurso):
    """Saca de un Appointment solo lo que hace falta. Los datos reales vienen incompletos:
    cada campo se lee con .get() para que una cita rara no rompa el resto."""
    cita = {
        "id": recurso.get("id", "sin id"),
        "paciente": None, "ref_paciente": None,
        "medico": None, "ref_medico": None,
        "motivo": recurso.get("description", "consulta"),
        "inicio": leer_fecha(recurso.get("start")),
    }
    for participante in recurso.get("participant", []):
        actor = participante.get("actor", {})
        referencia = actor.get("reference", "")
        if referencia.startswith("Patient/"):
            cita["paciente"] = actor.get("display")  # el nombre, si la cita lo trae
            cita["ref_paciente"] = referencia        # y dónde buscarlo si no lo trae
        if referencia.startswith("Practitioner/"):
            cita["medico"] = actor.get("display")
            cita["ref_medico"] = referencia
    return cita


def nombre_de(referencia):
    """Sigue una referencia FHIR (por ejemplo 'Patient/830611') y devuelve el nombre de esa persona.
    Devuelve None si no hay referencia, si la ficha no existe o si no tiene nombre."""
    if not referencia:
        return None
    try:
        respuesta = requests.get(f"{FHIR_BASE}/{referencia}", headers={"Accept": "application/fhir+json"}, timeout=20)
        respuesta.raise_for_status()
    except requests.RequestException:
        return None
    nombres = respuesta.json().get("name", [])
    if not nombres:
        return None
    nombre = nombres[0]  # FHIR guarda el nombre por partes: tratamiento, nombre de pila y apellido
    partes = nombre.get("prefix", []) + nombre.get("given", []) + [nombre.get("family", "")]
    return nombre.get("text") or " ".join(partes).strip() or None


def completar_nombres(cita):
    """Si la cita no traía el nombre del paciente o del médico, lo busca en su ficha."""
    cita["paciente"] = cita["paciente"] or nombre_de(cita["ref_paciente"]) or "paciente"
    cita["medico"] = cita["medico"] or nombre_de(cita["ref_medico"]) or "su médico"
    return cita


def leer_fecha(texto_iso):
    """Convierte el texto de fecha de FHIR en una fecha de Python. Devuelve None si falta o no se entiende."""
    if not texto_iso:
        return None
    try:
        # Algunas fechas acaban en "Z" (hora UTC); Python 3.9 solo las entiende escritas como +00:00
        fecha = datetime.fromisoformat(texto_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if fecha.tzinfo is None:  # si no trae zona horaria, se toma como UTC para poder compararla
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha


def es_futura(cita):
    """True si la cita tiene fecha válida y todavía no ha pasado."""
    return cita["inicio"] is not None and cita["inicio"] > datetime.now(timezone.utc)


def construir_mensaje(cita):
    return (
        f"Hola, {cita['paciente']}. Le recordamos su cita con {cita['medico']} ({cita['motivo']}): "
        f"{cita['inicio'].strftime('%d/%m/%Y a las %H:%M')}. Responda a este mensaje para confirmarla o cambiarla."
    )


def enviar_whatsapp(texto):
    """Envía un mensaje de texto por la WhatsApp Cloud API de Meta.
    Ojo: el texto libre solo se entrega si el destinatario ha escrito en las últimas 24 h;
    fuera de esa ventana hay que usar una plantilla aprobada."""
    respuesta = requests.post(
        f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": DESTINO,
            "type": "text",
            "text": {"body": texto},
        },
        timeout=20,
    )
    respuesta.raise_for_status()
    return respuesta.json()["messages"][0]["id"]  # identificador que devuelve Meta


def main():
    cuantas = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    envio_real = all([WHATSAPP_TOKEN, PHONE_NUMBER_ID, DESTINO])

    try:
        citas = [resumir_cita(recurso) for recurso in obtener_citas(cuantas)]
    except requests.HTTPError as error:
        print(f"El servidor FHIR ha contestado {error.response.status_code}: {error.response.text[:200]}")
        sys.exit(1)
    except requests.RequestException as error:  # sin red, tiempo agotado, DNS...
        print(f"No se ha podido conectar con el servidor FHIR: {error}")
        sys.exit(1)

    futuras = [completar_nombres(cita) for cita in citas if es_futura(cita)]  # solo se buscan nombres de las que se van a avisar
    print(f"{len(citas)} citas leídas de {FHIR_BASE}")
    print(f"{len(citas) - len(futuras)} descartadas por estar ya pasadas o no tener una fecha válida\n")
    for cita in futuras:
        mensaje = construir_mensaje(cita)
        if not envio_real:
            print(f"[simulación] cita {cita['id']}: {mensaje}")
            continue
        try:
            id_mensaje = enviar_whatsapp(mensaje)
            print(f"[enviado] cita {cita['id']} -> {id_mensaje}")
        except requests.HTTPError as error:
            print(f"[error] cita {cita['id']}: Meta ha contestado {error.response.status_code}: {error.response.text[:200]}")


if __name__ == "__main__":
    main()