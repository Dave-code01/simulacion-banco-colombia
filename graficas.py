"""
Gráficas del informe (matplotlib).

Genera cuatro figuras PNG en la carpeta indicada:
  fig1_atencion_por_cajero.png    Punto 1: tiempo promedio de atención por cajero (E0)
  fig2_usuarios_por_replica.png   Punto 3: distribución del total de usuarios por réplica
  fig3_espera_por_escenario.png   Puntos 4-5: espera de retiros y pagos por escenario
  fig4_convergencia_replicas.png  Réplicas: media acumulada de la espera por escenario
"""

import os

import matplotlib

matplotlib.use("Agg")                     # sin ventana: solo guarda archivos
import matplotlib.pyplot as plt
import numpy as np

# Paleta (azul = retiro, naranja = pago; grises para texto y referencias)
AZUL, NARANJA = "#2a78d6", "#eb6834"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
TEXTO, TEXTO_2, GRIS, REJILLA = "#0b0b0b", "#52514e", "#8c8a85", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": GRIS, "axes.labelcolor": TEXTO_2,
    "xtick.color": TEXTO_2, "ytick.color": TEXTO_2,
    "axes.spines.top": False, "axes.spines.right": False,
})


def coma(v, dec=2):
    """Formato con coma decimal (español)."""
    return f"{v:.{dec}f}".replace(".", ",")


def _titulo(ax, titulo, subtitulo):
    ax.set_title(titulo, loc="left", fontsize=12, fontweight="bold", color=TEXTO, pad=24)
    ax.text(0, 1.02, subtitulo, transform=ax.transAxes, fontsize=9, color=TEXTO_2)


def fig_atencion(p1, ruta):
    """Punto 1: media e IC 95 % del tiempo de atención de cada cajero en E0."""
    d = p1[p1["escenario"].str.startswith("E0")].sort_values("cajero")
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    y = np.arange(len(d))[::-1]
    imin, imax = d["servicio_prom"].idxmin(), d["servicio_prom"].idxmax()
    for yi, (idx, r) in zip(y, d.iterrows()):
        color = AZUL if idx in (imin, imax) else GRIS
        ax.errorbar(r["servicio_prom"], yi, xerr=r["servicio_ic95"], fmt="o", ms=8,
                    color=color, ecolor=color, elinewidth=2, capsize=4)
        etiqueta = " (menor)" if idx == imin else " (mayor)" if idx == imax else ""
        ax.text(r["servicio_prom"] + r["servicio_ic95"] + 0.01, yi,
                f"{coma(r['servicio_prom'], 3)} min{etiqueta}", va="center", color=TEXTO)
    ax.set_yticks(y, [f"Cajero {c}" for c in d["cajero"]])
    ax.set_xlabel("Tiempo promedio de atención (min) · barra = IC 95 %")
    ax.set_xlim(3.0, 3.45)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: coma(v, 1)))
    ax.grid(axis="x", color=REJILLA)
    ax.set_axisbelow(True)
    _titulo(ax, "Los tres cajeros atienden al mismo ritmo",
            "Situación actual (3 cajas mixtas), 193 réplicas: los intervalos se traslapan")
    fig.tight_layout()
    fig.savefig(ruta, dpi=200)
    plt.close(fig)


def fig_usuarios(p3, ruta):
    """Punto 3: histograma del total de usuarios por réplica."""
    tot = p3["Total"]
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.hist(tot, bins=range(int(tot.min()) - 2, int(tot.max()) + 6, 5),
            color=GRIS, edgecolor="white", linewidth=1.5)
    ax.axvline(tot.mean(), color=AZUL, lw=2)
    ax.text(tot.mean() - 1, ax.get_ylim()[1] * 0.95, f"Promedio: {coma(tot.mean(), 1)}",
            color=TEXTO, ha="right", va="top")
    ax.annotate(f"Mínimo: {int(tot.min())} usuarios\n(réplica {int(tot.idxmin())})",
                xy=(tot.min() + 1, 1), xytext=(tot.min() + 2, ax.get_ylim()[1] * 0.55),
                color=TEXTO, arrowprops=dict(arrowstyle="-", color=TEXTO_2))
    ax.set_xlabel("Usuarios atendidos en el día")
    ax.set_ylabel("Número de réplicas")
    ax.grid(axis="y", color=REJILLA)
    ax.set_axisbelow(True)
    _titulo(ax, f"Llegan en promedio {coma(tot.mean(), 0)} usuarios por día",
            f"Total de usuarios por réplica, {len(tot)} réplicas")
    fig.tight_layout()
    fig.savefig(ruta, dpi=200)
    plt.close(fig)


def fig_espera(p4, ruta, limite=5.0):
    """Puntos 4-5: espera promedio de retiros y pagos por escenario con IC 95 %."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(p4))
    w = 0.36
    for k, (col, nombre, color) in enumerate([("espera_retiro", "Retiro", AZUL),
                                              ("espera_pago", "Pago", NARANJA)]):
        pos = x + (k - 0.5) * (w + 0.02)
        ax.bar(pos, p4[col], w, color=color, label=nombre,
               yerr=p4[col + "_ic95"], error_kw=dict(ecolor=TEXTO, lw=1.2, capsize=3))
        for xi, v, h in zip(pos, p4[col], p4[col + "_ic95"]):
            ax.text(xi, v + h + 0.2, coma(v), ha="center", fontsize=9, color=TEXTO,
                    fontweight="bold" if v > limite else "normal")
    ax.axhline(limite, color=GRIS, ls="--", lw=1.5)
    ax.text(len(p4) - 0.5, limite + 0.15, f"Límite de servicio: {coma(limite, 0)} min",
            ha="right", color=TEXTO_2, fontsize=9)
    etiquetas = [e.replace(" - ", "\n") for e in p4["escenario"]]
    ax.set_xticks(x, etiquetas)
    ax.set_ylabel("Espera promedio en fila (min)")
    ax.set_ylim(0, max(p4["espera_pago"].max(), p4["espera_retiro"].max()) + 2)
    ax.grid(axis="y", color=REJILLA)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left", ncol=2)
    _titulo(ax, "Con 3 cajas especializadas un grupo pasa de 5 min; con 4 cajas, ninguno",
            "Espera promedio por acción y escenario · barras de error: IC 95 %")
    fig.tight_layout()
    fig.savefig(ruta, dpi=200)
    plt.close(fig)


def fig_convergencia(por_rep, n_piloto, ruta):
    """Media acumulada de la espera de cada escenario a medida que se suman réplicas."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    piv = por_rep.pivot(index="replica", columns="escenario", values="espera_prom")
    acum = piv.expanding().mean()
    n = len(acum)
    # posiciones de las etiquetas finales, separadas para que no se encimen
    finales = acum.iloc[-1].sort_values()
    pos, previo = {}, -np.inf
    for esc, v in finales.items():
        pos[esc] = max(v, previo + 0.32)
        previo = pos[esc]
    for color, esc in zip(SERIES, acum.columns):
        ax.plot(acum.index, acum[esc], color=color, lw=2)
        ax.text(n + 3, pos[esc], esc, va="center", fontsize=8.5, color=TEXTO)
    ax.axvline(n_piloto, color=GRIS, ls=":", lw=1.5)
    ax.text(n_piloto + 2, ax.get_ylim()[1] * 0.97, f"Piloto ({n_piloto})", color=TEXTO_2,
            fontsize=9, va="top")
    ax.set_xlim(1, n * 1.32)
    ax.set_xlabel("Número de réplicas")
    ax.set_ylabel("Espera promedio acumulada (min)")
    ax.grid(axis="y", color=REJILLA)
    ax.set_axisbelow(True)
    _titulo(ax, f"Las medias se estabilizan antes de las {n} réplicas usadas",
            "Promedio acumulado de la espera en fila por escenario")
    fig.tight_layout()
    fig.savefig(ruta, dpi=200)
    plt.close(fig)


def generar_graficas(t, carpeta):
    """Crea todas las figuras a partir del diccionario de tablas de resultados."""
    os.makedirs(carpeta, exist_ok=True)
    fig_atencion(t["p1"], f"{carpeta}/fig1_atencion_por_cajero.png")
    fig_usuarios(t["p3"], f"{carpeta}/fig2_usuarios_por_replica.png")
    fig_espera(t["p4"], f"{carpeta}/fig3_espera_por_escenario.png")
    fig_convergencia(t["por_rep"], t.get("n_piloto", 10), f"{carpeta}/fig4_convergencia_replicas.png")
