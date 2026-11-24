"""Mini agente de preguntas de pacientes: busca la respuesta en los documentos del hospital
y, si no la encuentra o la pregunta es clínica, pasa el caso a una persona (handoff).

Uso:
    python3 agente_pacientes.py                         # prueba con las preguntas de ejemplo
    python3 agente_pacientes.py "¿puedo ir en coche?"   # una pregunta concreta
    python3 agente_pacientes.py --detalle "..."         # enseña además la puntuación de cada fragmento

No usa ningún modelo de lenguaje: aísla las dos decisiones que más fallan en un agente real,
qué fragmento se recupera y cuándo hay que parar y pasar a una persona.
Los documentos son ficticios.
"""
import sys
import unicodedata

# --- Documentos del hospital (ficticios) --------------------------------------
DOCUMENTOS = {
    "preparacion_colonoscopia.txt": [
        "El día anterior a la colonoscopia solo puede tomar líquidos claros: agua, caldo colado o infusiones.",
        "Debe estar en ayunas completas desde seis horas antes de la prueba.",
        "Venga acompañado a la colonoscopia: tras la sedación no puede conducir ni volver solo a casa.",
    ],
    "horarios_y_ubicacion.txt": [
        "Las consultas externas abren de lunes a viernes de 8:00 a 20:00 y los sábados de 9:00 a 14:00.",
        "El aparcamiento para el coche de los pacientes está en la planta -1 y es gratuito las dos primeras horas.",
        "Las extracciones de sangre se hacen de 7:30 a 10:30 sin cita previa.",
    ],
    "gestion_de_citas.txt": [
        "Puede cambiar o cancelar su cita hasta 24 horas antes respondiendo al mensaje de recordatorio.",
        "Si llega más de 15 minutos tarde, la cita puede reprogramarse para otro día.",
        "Para pedir una cita nueva necesita su número de historia o su DNI.",
    ],
}

UMBRAL = 0.5  # si el mejor fragmento contiene menos de la mitad de las palabras de la pregunta, el agente no contesta
PALABRAS_CLINICAS = {"dolor", "duele", "sangrado", "fiebre", "mareo", "pecho", "respirar",
                     "dosis", "medicacion", "pastilla", "pastillas", "alergia", "urgencia", "urgencias", "embarazada", "vómito" }
PALABRAS_VACIAS = {"a", "al", "con", "de", "del", "el", "en", "es", "la", "las", "lo", "los", "me", "mi",
                   "o", "para", "por", "que", "se", "si", "su", "un", "una", "y", "puedo", "puede", "tengo",
                   "hay", "como", "cuando", "donde", "cual", "hasta", "desde", "debe", "ir", "voy", "despues", "antes", "hago"}


def palabras(texto):
    """Pasa un texto a una lista de palabras en minúsculas, sin acentos, sin signos, sin palabras vacías
    y en singular aproximado (quita la "s" final), para que "sábados" y "sábado" cuenten como la misma."""
    sin_acentos = unicodedata.normalize("NFD", texto.lower())
    sin_acentos = "".join(letra for letra in sin_acentos if unicodedata.category(letra) != "Mn")
    limpio = "".join(letra if letra.isalnum() else " " for letra in sin_acentos)
    utiles = [palabra for palabra in limpio.split() if palabra not in PALABRAS_VACIAS]
    return [palabra[:-1] if len(palabra) > 3 and palabra.endswith("s") else palabra for palabra in utiles]


def parecido(palabras_pregunta, palabras_fragmento):
    """Qué parte de las palabras de la pregunta aparece en el fragmento: 0 = ninguna, 1 = todas."""
    if not palabras_pregunta:
        return 0.0
    encontradas = [palabra for palabra in palabras_pregunta if palabra in palabras_fragmento]
    return len(encontradas) / len(palabras_pregunta)


def recuperar(pregunta):
    """Compara la pregunta con cada fragmento y devuelve la lista ordenada de mayor a menor parecido."""
    palabras_pregunta = palabras(pregunta)
    resultados = []
    for documento, fragmentos in DOCUMENTOS.items():
        for fragmento in fragmentos:
            resultados.append({
                "documento": documento,
                "fragmento": fragmento,
                "puntuacion": parecido(palabras_pregunta, palabras(fragmento)),
            })
    return sorted(resultados, key=lambda resultado: resultado["puntuacion"], reverse=True)


def handoff(pregunta, motivo, mejor):
    """Prepara el paso a una persona: qué preguntó el paciente, por qué no se contesta y qué se encontró."""
    return {
        "accion": "handoff",
        "motivo": motivo,
        "resumen": f"El paciente pregunta: «{pregunta}». Fragmento más cercano: {mejor['documento']} "
                   f"(parecido {mejor['puntuacion']:.2f}).",
        "mensaje_al_paciente": "Prefiero no darle una respuesta que pueda no ser exacta. "
                               "Le paso con una persona del equipo, que ya tiene su pregunta.",
    }


def responder(pregunta):
    """Decide entre contestar con un fragmento o hacer handoff. Las preguntas clínicas nunca se contestan."""
    resultados = recuperar(pregunta)
    mejor = resultados[0]
    if set(palabras(" ".join(PALABRAS_CLINICAS))) & set(palabras(pregunta)):  # se comparan con el mismo tratamiento de texto
        return handoff(pregunta, "pregunta clínica: la responde un profesional", mejor), resultados
    if mejor["puntuacion"] < UMBRAL:
        return handoff(pregunta, "no hay un documento que responda con suficiente confianza", mejor), resultados
    return {
        "accion": "responder",
        "mensaje_al_paciente": mejor["fragmento"],
        "fuente": mejor["documento"],
        "puntuacion": mejor["puntuacion"],
    }, resultados


def mostrar(pregunta, detalle):
    decision, resultados = responder(pregunta)
    print(f"Pregunta: {pregunta}")
    if decision["accion"] == "responder":
        print(f"  [respuesta] {decision['mensaje_al_paciente']}")
        print(f"  [fuente]    {decision['fuente']} (parecido {decision['puntuacion']:.2f})")
    else:
        print(f"  [handoff]   {decision['motivo']}")
        print(f"  [resumen]   {decision['resumen']}")
        print(f"  [paciente]  {decision['mensaje_al_paciente']}")
    if detalle:  # para depurar: qué fragmentos se han considerado y con qué puntuación
        for resultado in resultados[:3]:
            print(f"      {resultado['puntuacion']:.2f}  {resultado['documento']}: {resultado['fragmento'][:60]}...")
    print()


PREGUNTAS_DE_EJEMPLO = [
    "¿A qué hora abren las consultas el sábado?",
    "¿Puedo conducir después de la colonoscopia?",
    "¿Hasta cuándo puedo cancelar mi cita?",
    "¿Cuánto cuesta una resonancia?",
    "Me duele el pecho desde ayer, ¿qué hago?",
    "¿Dónde dejo el coche?",
]


def main():
    argumentos = sys.argv[1:]
    detalle = "--detalle" in argumentos
    preguntas = [argumento for argumento in argumentos if argumento != "--detalle"] or PREGUNTAS_DE_EJEMPLO
    for pregunta in preguntas:
        mostrar(pregunta, detalle)


if __name__ == "__main__":
    main()
