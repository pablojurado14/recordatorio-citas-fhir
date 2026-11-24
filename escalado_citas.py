"""Ejercicio de escalado: la misma consulta sobre 500.000 citas, sin índice, con índice y paginada.

Uso:
    python escalado_citas.py

No instala nada: usa SQLite, que viene incluido en Python. Crea un archivo citas.db y lo borra al terminar.
"""
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta, timezone

ARCHIVO = "citas.db"
TOTAL_CITAS = 500_000
HOSPITALES = 50
ESTADOS = ["booked", "booked", "booked", "cancelled", "fulfilled"]  # 3 de cada 5 confirmadas


def crear_y_cargar(conexion):
    """Crea la tabla y la llena con citas ficticias repartidas en dos años."""
    conexion.execute(
        """create table citas (
               id integer primary key,
               hospital_id integer not null,
               paciente text not null,
               medico text not null,
               inicio text not null,      -- fecha en formato ISO, que se ordena bien como texto
               estado text not null
           )"""
    )
    ahora = datetime.now(timezone.utc)
    filas = []
    for _ in range(TOTAL_CITAS):
        inicio = ahora - timedelta(days=365) + timedelta(seconds=random.randint(0, 730 * 24 * 3600))
        filas.append((
            random.randint(1, HOSPITALES),
            f"Paciente {random.randint(1, 20000)}",
            f"Dr. {random.randint(1, 300)}",
            inicio.isoformat(timespec="seconds"),
            random.choice(ESTADOS),
        ))
    conexion.executemany(
        "insert into citas (hospital_id, paciente, medico, inicio, estado) values (?, ?, ?, ?, ?)", filas
    )
    conexion.commit()


def medir(conexion, titulo, sql, parametros, repeticiones=20):
    """Ejecuta la consulta varias veces y enseña el tiempo medio y cómo la resuelve la base de datos."""
    plan = conexion.execute("explain query plan " + sql, parametros).fetchall()
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        filas = conexion.execute(sql, parametros).fetchall()
    milisegundos = (time.perf_counter() - inicio) / repeticiones * 1000
    print(f"{titulo}")
    print(f"   tiempo medio: {milisegundos:.3f} ms   filas devueltas: {len(filas)}")
    print(f"   cómo busca:   {plan[0][3]}\n")  # SCAN = recorre toda la tabla; SEARCH ... USING INDEX = va directo
    return milisegundos


def main():
    if os.path.exists(ARCHIVO):
        os.remove(ARCHIVO)
    conexion = sqlite3.connect(ARCHIVO)

    print(f"Cargando {TOTAL_CITAS} citas de {HOSPITALES} hospitales...")
    crear_y_cargar(conexion)

    ahora = datetime.now(timezone.utc)
    manana = ahora + timedelta(days=1)
    del_dia = (
        "select id, paciente, medico, inicio from citas "
        "where hospital_id = ? and estado = 'booked' and inicio >= ? and inicio < ? order by inicio"
    )
    parametros = (7, ahora.isoformat(timespec="seconds"), manana.isoformat(timespec="seconds"))

    print("\nConsulta: citas confirmadas del hospital 7 en las próximas 24 horas\n")
    sin_indice = medir(conexion, "1. Sin índice", del_dia, parametros)

    conexion.execute("create index citas_hospital_inicio on citas (hospital_id, inicio)")
    con_indice = medir(conexion, "2. Con índice por hospital y fecha", del_dia, parametros)

    paginada = (
        "select id, paciente, medico, inicio from citas "
        "where hospital_id = ? and estado = 'booked' and inicio >= ? order by inicio limit 20"
    )
    medir(conexion, "3. Paginada: solo las 20 próximas", paginada, parametros[:2])

    print(f"El índice hace la consulta unas {sin_indice / con_indice:.0f} veces más rápida.")

    conexion.close()
    os.remove(ARCHIVO)  # no deja nada en el disco


if __name__ == "__main__":
    main()
