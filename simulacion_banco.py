"""
Simulación de cajas del Banco de Colombia (Actividad didáctica 2-M3)
=====================================================================

Modelo de eventos discretos construido con SimPy.

Supuestos del enunciado:
  * Jornada de 8 horas (480 minutos). Se cierra la puerta a los 480 min y se
    atiende a quienes ya estaban en la fila.
  * 70 % de los usuarios hace retiros y 30 % consignaciones o pagos.
  * Dentro de cada acción el tipo de usuario (rápido, normal, lento, muy lento)
    sigue las probabilidades de la Tabla 2.
  * El tiempo entre llegadas y el tiempo de servicio son exponenciales con las
    medias de la Tabla 1 según el tipo de usuario que llega.
  * Cada caja es un sistema M/M/1 independiente: tiene su propia fila, un solo
    servidor y disciplina FIFO. El usuario se asigna al azar (probabilidad
    uniforme) entre las cajas habilitadas para su acción; esa división
    aleatoria de un flujo de llegadas es la que mantiene independientes las
    colas.
  * Desplazamiento despreciable.

Escenarios evaluados:
  E0  3 cajas mixtas (situación actual)
  E1  1 caja exclusiva de retiros + 2 de pagos
  E2  2 cajas exclusivas de retiros + 1 de pagos
  E3  4 cajas mixtas (se agrega un cajero)
  E4  2 de retiros + 2 de pagos (se agrega un cajero a E2)

Se usan números aleatorios comunes: en la réplica r todos los escenarios
reciben exactamente los mismos usuarios (mismas llegadas, tipos y tiempos de
servicio). Así las diferencias entre escenarios se deben a la configuración
de las cajas y no al azar.

Uso:
    python simulacion_banco.py                # piloto de 10 + réplicas calculadas
    python simulacion_banco.py --replicas 50  # fija el número final de réplicas
"""

import argparse
import os

import numpy as np
import pandas as pd
import simpy
from scipy import stats

from exportar_excel import exportar_excel
from graficas import generar_graficas

# ---------------------------------------------------------------------------
# 1. Parámetros del problema (Tablas 1 y 2)
# ---------------------------------------------------------------------------
JORNADA_MIN = 8 * 60          # 480 minutos de atención al público
P_RETIRO = 0.70               # proporción de usuarios que hacen retiros

# (acción, tipo): (media de servicio, media entre llegadas, probabilidad dentro de la acción)
TIPOS = {
    ("Retiro", "Rápido"):    (1.0, 1.0, 0.23),
    ("Retiro", "Normal"):    (2.0, 2.0, 0.40),
    ("Retiro", "Lento"):     (3.0, 3.0, 0.17),
    ("Retiro", "Muy lento"): (4.0, 3.0, 0.20),
    ("Pago", "Rápido"):      (3.0, 1.0, 0.10),
    ("Pago", "Normal"):      (3.0, 2.0, 0.20),
    ("Pago", "Lento"):       (5.0, 3.0, 0.30),
    ("Pago", "Muy lento"):   (7.0, 4.0, 0.40),
}
LISTA_TIPOS = list(TIPOS.keys())
# Probabilidad total de cada tipo = P(acción) * P(tipo | acción)
PROB_TIPOS = np.array([
    (P_RETIRO if acc == "Retiro" else 1 - P_RETIRO) * TIPOS[(acc, t)][2]
    for acc, t in LISTA_TIPOS
])
assert abs(PROB_TIPOS.sum() - 1.0) < 1e-9, "Las probabilidades deben sumar 1"

# Cada escenario es una lista de cajas; cada caja indica qué acciones atiende.
MIXTA = ("Retiro", "Pago")
ESCENARIOS = {
    "E0 - 3 mixtas":          [MIXTA, MIXTA, MIXTA],
    "E1 - 1 retiro + 2 pago": [("Retiro",), ("Pago",), ("Pago",)],
    "E2 - 2 retiro + 1 pago": [("Retiro",), ("Retiro",), ("Pago",)],
    "E3 - 4 mixtas":          [MIXTA, MIXTA, MIXTA, MIXTA],
    "E4 - 2 retiro + 2 pago": [("Retiro",), ("Retiro",), ("Pago",), ("Pago",)],
}


# ---------------------------------------------------------------------------
# 2. Generación de los usuarios de un día
# ---------------------------------------------------------------------------
def generar_usuarios(rng):
    """Crea la lista de usuarios que llegan durante la jornada.

    Para cada usuario se sortea primero su tipo (Tablas 1 y 2) y después el
    tiempo que tarda en llegar desde el anterior, con la media de llegada de
    su tipo. El tiempo de servicio también se sortea aquí para que todos los
    escenarios reciban el mismo usuario (números aleatorios comunes).
    """
    usuarios = []
    reloj = 0.0
    while True:
        idx = rng.choice(len(LISTA_TIPOS), p=PROB_TIPOS)
        accion, tipo = LISTA_TIPOS[idx]
        media_serv, media_lleg, _ = TIPOS[(accion, tipo)]
        reloj += rng.exponential(media_lleg)
        if reloj > JORNADA_MIN:          # la puerta se cierra a los 480 min
            break
        usuarios.append({
            "id": len(usuarios) + 1,
            "accion": accion,
            "tipo": tipo,
            "llegada": reloj,
            "servicio": rng.exponential(media_serv),
            "u_ruteo": rng.random(),     # número para elegir caja al azar
        })
    return usuarios


# ---------------------------------------------------------------------------
# 3. Modelo de simulación con SimPy
# ---------------------------------------------------------------------------
def atender(env, usuario, caja, n_caja, registro):
    """Proceso de un usuario: espera en la fila de su caja y es atendido."""
    with caja.request() as turno:
        yield turno                                  # espera su turno (FIFO)
        inicio = env.now
        yield env.timeout(usuario["servicio"])       # tiempo de atención
        registro.append({
            **{k: usuario[k] for k in ("id", "accion", "tipo", "llegada", "servicio")},
            "cajero": n_caja,
            "inicio": inicio,
            "fin": env.now,
            "espera": inicio - usuario["llegada"],
            "tiempo_sistema": env.now - usuario["llegada"],
        })


def llegadas(env, usuarios, cajas, config, registro):
    """Libera a cada usuario en su hora de llegada y lo envía a una caja."""
    for u in usuarios:
        yield env.timeout(u["llegada"] - env.now)
        # cajas que atienden la acción del usuario
        habilitadas = [i for i, acciones in enumerate(config) if u["accion"] in acciones]
        # asignación aleatoria uniforme -> cada caja se comporta como M/M/1
        i = habilitadas[int(u["u_ruteo"] * len(habilitadas))]
        env.process(atender(env, u, cajas[i], i + 1, registro))


def simular_dia(usuarios, config):
    """Simula un día completo para una configuración de cajas."""
    env = simpy.Environment()
    cajas = [simpy.Resource(env, capacity=1) for _ in config]
    registro = []
    env.process(llegadas(env, usuarios, cajas, config, registro))
    env.run()          # corre hasta que se atiende al último usuario
    return pd.DataFrame(registro)


# ---------------------------------------------------------------------------
# 4. Estadísticas
# ---------------------------------------------------------------------------
def intervalo(x, conf=0.95):
    """Media, desviación estándar y semiancho del IC con t de Student."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    s = x.std(ddof=1)
    h = stats.t.ppf(1 - (1 - conf) / 2, n - 1) * s / np.sqrt(n)
    return x.mean(), s, h


def replicas_necesarias(x, error_rel=0.05, conf=0.95):
    """n = (t * s / e)^2 para que el semiancho sea error_rel * media."""
    x = np.asarray(x, dtype=float)
    t = stats.t.ppf(1 - (1 - conf) / 2, len(x) - 1)
    e = error_rel * x.mean()
    return int(np.ceil((t * x.std(ddof=1) / e) ** 2))


def resumen_por_cajero(df, config):
    """Indicadores de cada caja en una réplica."""
    filas = []
    fin_dia = max(JORNADA_MIN, df["fin"].max())
    for i in range(1, len(config) + 1):
        d = df[df["cajero"] == i]
        filas.append({
            "cajero": i,
            "atiende": "/".join(config[i - 1]),
            "usuarios": len(d),
            "servicio_prom": d["servicio"].mean(),
            "espera_prom": d["espera"].mean(),
            "espera_max": d["espera"].max(),
            "sistema_prom": d["tiempo_sistema"].mean(),
            "utilizacion": d["servicio"].sum() / fin_dia,
            "hora_ultimo": d["fin"].max(),
        })
    return pd.DataFrame(filas)


def parametros_teoricos(acciones):
    """Tasa de servicio de una caja según las acciones que atiende.

    Devuelve E[S] (media del tiempo de servicio de la mezcla de usuarios que
    llega a esa caja) y la proporción del flujo total que corresponde a esas
    acciones.
    """
    prob = {}
    for (acc, tipo), p in zip(LISTA_TIPOS, PROB_TIPOS):
        if acc in acciones:
            prob[(acc, tipo)] = p
    total = sum(prob.values())
    media_serv = sum(p * TIPOS[k][0] for k, p in prob.items()) / total
    return media_serv, total


def metricas_colas(cajeros, n_dias):
    """Indicadores L, Lq, W, Wq y rho de cada caja: teóricos M/M/1 y simulados.

    Teórico (fórmulas M/M/1 de la guía):
        lambda = tasa de llegada a la caja, mu = 1 / E[S], rho = lambda / mu
        L = rho/(1-rho), Lq = rho^2/(1-rho), W = 1/(mu-lambda), Wq = rho/(mu-lambda)
    Simulado: W y Wq medidos; L y Lq con la ley de Little (L = lambda*W).
    """
    media_lleg = float(np.dot(PROB_TIPOS, [TIPOS[k][1] for k in LISTA_TIPOS]))
    lam_total = 1 / media_lleg                       # usuarios por minuto
    filas = []
    for esc, config in ESCENARIOS.items():
        for i, acciones in enumerate(config, start=1):
            media_serv, prop = parametros_teoricos(acciones)
            # cajas que comparten el mismo flujo (misma lista de acciones)
            n_iguales = sum(1 for c in config if c == acciones)
            lam = lam_total * prop / n_iguales
            mu = 1 / media_serv
            rho = lam / mu
            estable = rho < 1                         # validación de estabilidad
            g = cajeros[(cajeros["escenario"] == esc) & (cajeros["cajero"] == i)]
            lam_sim = g["usuarios"].mean() / JORNADA_MIN
            wq_sim, w_sim = g["espera_prom"].mean(), g["sistema_prom"].mean()
            filas.append({
                "escenario": esc, "cajero": i, "atiende": "/".join(acciones),
                "lambda_teo": lam, "mu_teo": mu, "rho_teo": rho, "estable": estable,
                "L_teo": rho / (1 - rho) if estable else np.inf,
                "Lq_teo": rho ** 2 / (1 - rho) if estable else np.inf,
                "W_teo": 1 / (mu - lam) if estable else np.inf,
                "Wq_teo": rho / (mu - lam) if estable else np.inf,
                "lambda_sim": lam_sim, "rho_sim": g["utilizacion"].mean(),
                "L_sim": lam_sim * w_sim, "Lq_sim": lam_sim * wq_sim,
                "W_sim": w_sim, "Wq_sim": wq_sim,
            })
    tabla = pd.DataFrame(filas)
    if not tabla["estable"].all():
        print("ADVERTENCIA: hay cajas con rho >= 1 (sistema inestable)")
    return tabla


def correr_replicas(n, semilla):
    """Ejecuta n réplicas de todos los escenarios con números aleatorios comunes."""
    detalle, cajeros = [], []
    for r in range(1, n + 1):
        rng = np.random.default_rng(semilla + r)   # misma semilla para todos los escenarios
        usuarios = generar_usuarios(rng)
        for nombre, config in ESCENARIOS.items():
            df = simular_dia(usuarios, config)
            df["replica"], df["escenario"] = r, nombre
            detalle.append(df)
            rc = resumen_por_cajero(df, config)
            rc["replica"], rc["escenario"] = r, nombre
            cajeros.append(rc)
    return pd.concat(detalle, ignore_index=True), pd.concat(cajeros, ignore_index=True)


# ---------------------------------------------------------------------------
# 5. Programa principal
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--piloto", type=int, default=10, help="réplicas de la corrida piloto (mín. 10)")
    ap.add_argument("--replicas", type=int, default=0,
                    help="forzar el número final de réplicas (0 = calcularlo con el piloto)")
    ap.add_argument("--semilla", type=int, default=2025, help="semilla base")
    ap.add_argument("--salida", default="resultados", help="carpeta de resultados")
    args = ap.parse_args()
    os.makedirs(args.salida, exist_ok=True)

    # --- Etapa 1: corrida piloto de 10 réplicas para estimar la variabilidad
    det_p, _ = correr_replicas(args.piloto, args.semilla)
    esp_p = det_p.groupby(["escenario", "replica"])["espera"].mean()
    nrep = [{"escenario": esc,
             "media_piloto": g.mean(), "desv_piloto": g.std(ddof=1),
             "n_para_10pct": replicas_necesarias(g, 0.10),
             "n_para_5pct": replicas_necesarias(g, 0.05)}
            for esc, g in esp_p.groupby(level="escenario")]
    nrep = pd.DataFrame(nrep)
    # número final: el mayor requerido entre escenarios (error relativo 10 %)
    n_final = args.replicas or max(args.piloto, int(nrep["n_para_10pct"].max()))
    nrep["n_final_usado"] = n_final
    nrep.to_csv(f"{args.salida}/replicas_necesarias.csv", index=False)

    # --- Etapa 2: corrida definitiva con n_final réplicas
    detalle, cajeros = correr_replicas(n_final, args.semilla)
    detalle.to_csv(f"{args.salida}/detalle_usuarios.csv.gz", index=False)  # comprimido
    cajeros.to_csv(f"{args.salida}/resumen_cajeros_por_replica.csv", index=False)

    base = detalle[detalle["escenario"] == "E0 - 3 mixtas"]

    # --- Punto 1: cajero con menor y mayor tiempo promedio de atención -----
    p1 = []
    for (esc, caj), g in cajeros.groupby(["escenario", "cajero"]):
        m, s, h = intervalo(g["servicio_prom"])
        me, _, he = intervalo(g["espera_prom"])
        p1.append({"escenario": esc, "cajero": caj, "atiende": g["atiende"].iloc[0],
                   "servicio_prom": m, "servicio_desv": s, "servicio_ic95": h,
                   "espera_prom": me, "espera_ic95": he,
                   "usuarios_prom": g["usuarios"].mean(),
                   "utilizacion_prom": g["utilizacion"].mean()})
    p1 = pd.DataFrame(p1)
    p1.to_csv(f"{args.salida}/p1_tiempos_por_cajero.csv", index=False)

    # --- Punto 2: promedio de usuarios de cada tipo por cajero (E0) --------
    conteo = (base.groupby(["replica", "cajero", "accion", "tipo"]).size()
              .unstack(["accion", "tipo"], fill_value=0))
    orden = pd.MultiIndex.from_tuples(LISTA_TIPOS, names=["accion", "tipo"])
    p2 = conteo.groupby(level="cajero").mean().T.reindex(orden)
    p2["Total 3 cajeros"] = p2.sum(axis=1)
    p2.to_csv(f"{args.salida}/p2_promedio_tipo_por_cajero.csv")

    # --- Punto 3: total de usuarios de cada tipo en cada réplica ----------
    p3 = (base.groupby(["replica", "accion", "tipo"]).size()
          .unstack(["accion", "tipo"], fill_value=0).reindex(columns=orden, fill_value=0))
    p3["Total"] = p3.sum(axis=1)
    p3.to_csv(f"{args.salida}/p3_usuarios_tipo_por_replica.csv")
    # resumen: réplica con menos usuarios de cada tipo y estadísticas del total
    p3r = pd.DataFrame({
        "minimo": p3.min(), "replica_minimo": p3.idxmin(),
        "promedio": p3.mean(), "desv": p3.std(ddof=1),
        "maximo": p3.max(), "replica_maximo": p3.idxmax(),
    })
    p3r.to_csv(f"{args.salida}/p3_resumen_minimos.csv")
    # cajero (modelo M/M/1) con menos usuarios promedio de cada tipo
    p3c = p2.drop(columns="Total 3 cajeros").idxmin(axis=1).rename("cajero_con_menos")
    p3c.to_csv(f"{args.salida}/p3_cajero_con_menos_usuarios.csv")

    # --- Puntos 4 y 5: tiempos de espera por escenario -------------------
    por_rep = (detalle.groupby(["escenario", "replica"])
               .apply(lambda d: pd.Series({
                   "espera_prom": d["espera"].mean(),
                   "espera_retiro": d.loc[d["accion"] == "Retiro", "espera"].mean(),
                   "espera_pago": d.loc[d["accion"] == "Pago", "espera"].mean(),
                   "pct_espera_mas_10": (d["espera"] > 10).mean() * 100,
                   "espera_max": d["espera"].max(),
                   "cierre_real": d["fin"].max(),
               }), include_groups=False).reset_index())
    por_rep.to_csv(f"{args.salida}/p4_espera_por_escenario_replica.csv", index=False)

    p4 = []
    for esc, g in por_rep.groupby("escenario"):
        fila = {"escenario": esc}
        for col in ["espera_prom", "espera_retiro", "espera_pago", "pct_espera_mas_10",
                    "espera_max", "cierre_real"]:
            m, _, h = intervalo(g[col])
            fila[col], fila[col + "_ic95"] = m, h
        p4.append(fila)
    p4 = pd.DataFrame(p4)
    p4.to_csv(f"{args.salida}/p4_resumen_escenarios.csv", index=False)

    # espera por tipo de usuario en cada escenario
    p4b = (detalle.groupby(["escenario", "replica", "accion", "tipo"])["espera"].mean()
           .groupby(["escenario", "accion", "tipo"]).mean().unstack("escenario"))
    p4b.to_csv(f"{args.salida}/p4_espera_por_tipo.csv")

    # diferencias pareadas entre escenarios (números aleatorios comunes)
    piv = por_rep.pivot(index="replica", columns="escenario", values="espera_prom")
    comparaciones = [("E1 - 1 retiro + 2 pago", "E2 - 2 retiro + 1 pago"),
                     ("E0 - 3 mixtas", "E2 - 2 retiro + 1 pago"),
                     ("E0 - 3 mixtas", "E3 - 4 mixtas"),
                     ("E2 - 2 retiro + 1 pago", "E4 - 2 retiro + 2 pago")]
    pares = []
    for a, b in comparaciones:
        dif = piv[a] - piv[b]
        m, _, h = intervalo(dif)
        pares.append({"A": a, "B": b, "dif_media_A_menos_B": m,
                      "ic95_inf": m - h, "ic95_sup": m + h,
                      "p_valor": stats.ttest_rel(piv[a], piv[b]).pvalue})
    pares = pd.DataFrame(pares)
    pares.to_csv(f"{args.salida}/p4_comparaciones_pareadas.csv", index=False)

    # --- Métricas de colas (L, Lq, W, Wq, rho): teóricas M/M/1 y simuladas
    colas = metricas_colas(cajeros, n_final)
    colas.to_csv(f"{args.salida}/metricas_colas_mm1.csv", index=False)

    # --- Excel con todos los datos y gráficas para el informe -------------
    tablas = {"replicas_necesarias": nrep, "p1": p1, "p2": p2, "p3": p3, "p3_resumen": p3r,
              "p4": p4, "p4_tipo": p4b, "pares": pares, "colas": colas,
              "por_rep": por_rep, "cajeros": cajeros, "n_piloto": args.piloto,
              "param": {"TIPOS": TIPOS, "P_RETIRO": P_RETIRO, "JORNADA_MIN": JORNADA_MIN}}
    exportar_excel(tablas, "resultados_simulacion_banco.xlsx")
    generar_graficas(tablas, "figuras")

    # --- impresión en consola -------------------------------------------
    pd.set_option("display.width", 200, "display.max_columns", 30)
    print(f"Piloto: {args.piloto} réplicas -> réplicas finales: {n_final}  |  semilla base: {args.semilla}\n")
    print("RÉPLICAS NECESARIAS (espera promedio, 95 % de confianza)")
    print(nrep.round(3).to_string(index=False), "\n")
    print("PUNTO 1 - Tiempo promedio de atención por cajero (min)")
    print(p1.round(3).to_string(index=False), "\n")
    print("PUNTO 2 - Promedio de usuarios por tipo y cajero (E0)")
    print(p2.round(2).to_string(), "\n")
    print("PUNTO 3 - Total de usuarios por tipo en cada réplica (E0)")
    print(p3.head(10).to_string(), "\n(ver CSV para todas las réplicas)\n")
    print(p3r.round(2).to_string(), "\n")
    print(p3c.to_string(), "\n")
    print("PUNTOS 4-5 - Espera por escenario (min)")
    print(p4.round(2).to_string(index=False), "\n")
    print(p4b.round(2).to_string(), "\n")
    print(pares.round(3).to_string(index=False), "\n")
    print("MÉTRICAS DE COLAS POR CAJA (teórico M/M/1 vs simulado)")
    print(colas.round(3).to_string(index=False))
    print("\nExcel: resultados_simulacion_banco.xlsx  |  Gráficas: carpeta figuras/")


if __name__ == "__main__":
    main()
