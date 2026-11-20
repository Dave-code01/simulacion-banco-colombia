"""
Exporta los resultados de la simulación a un libro de Excel con formato.

Hojas:
  Leeme                      Parámetros del modelo (Tablas 1 y 2) y guía de hojas
  Replicas_necesarias        Piloto y cálculo del número de réplicas
  P1_Atencion_cajero         Punto 1: atención, espera y utilización por cajero
  P2_Usuarios_tipo_cajero    Punto 2: promedio de usuarios por tipo y cajero (E0)
  P3_Usuarios_por_replica    Punto 3: usuarios por tipo en cada réplica, con
                             fórmulas de total, mínimo, réplica del mínimo,
                             promedio, desviación y máximo
  P4_Escenarios              Puntos 4-5: esperas por escenario con IC 95 %
  P4_Espera_por_tipo         Espera promedio por tipo de usuario y escenario
  P4_Comparaciones           Pruebas t pareadas entre escenarios
  Metricas_colas             L, Lq, W, Wq y rho: teórico M/M/1 vs simulado
  Escenarios_por_replica     Indicadores de cada escenario en cada réplica
  Cajeros_por_replica        Indicadores de cada cajero en cada réplica
"""

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

FUENTE = "Arial"
ENCABEZADO = PatternFill("solid", start_color="1E3C72")
RESUMEN = PatternFill("solid", start_color="E8EEF7")
BORDE = Border(bottom=Side(style="thin", color="BFBFBF"))

# Nombres legibles de columnas
NOMBRES = {
    "escenario": "Escenario", "cajero": "Cajero", "atiende": "Atiende", "replica": "Réplica",
    "servicio_prom": "Atención prom. (min)", "servicio_desv": "Desv. atención (min)",
    "servicio_ic95": "IC 95 % ± (min)", "espera_prom": "Espera prom. (min)",
    "espera_ic95": "IC 95 % espera ± (min)", "usuarios_prom": "Usuarios por día",
    "utilizacion_prom": "Utilización", "utilizacion": "Utilización", "usuarios": "Usuarios",
    "espera_max": "Espera máx. (min)", "sistema_prom": "Tiempo en sistema (min)",
    "hora_ultimo": "Salida último usuario (min)",
    "espera_retiro": "Espera retiros (min)", "espera_pago": "Espera pagos (min)",
    "pct_espera_mas_10": "% espera > 10 min", "cierre_real": "Salida último usuario (min)",
    "media_piloto": "Espera media piloto (min)", "desv_piloto": "Desv. piloto (min)",
    "n_para_10pct": "Réplicas error 10 %", "n_para_5pct": "Réplicas error 5 %",
    "n_final_usado": "Réplicas usadas",
    "A": "Escenario A", "B": "Escenario B", "dif_media_A_menos_B": "Diferencia A − B (min)",
    "ic95_inf": "IC 95 % inferior", "ic95_sup": "IC 95 % superior", "p_valor": "Valor p",
    "lambda_teo": "λ teórica (usu/min)", "mu_teo": "μ teórica (usu/min)", "rho_teo": "ρ teórica",
    "estable": "Estable (ρ<1)", "L_teo": "L teórico", "Lq_teo": "Lq teórico",
    "W_teo": "W teórico (min)", "Wq_teo": "Wq teórico (min)", "lambda_sim": "λ simulada",
    "rho_sim": "ρ simulada", "L_sim": "L simulado", "Lq_sim": "Lq simulado",
    "W_sim": "W simulado (min)", "Wq_sim": "Wq simulado (min)",
}


def _escribir(ws, df, fila0=1, formatos=None):
    """Escribe un DataFrame con encabezado formateado desde la fila fila0."""
    formatos = formatos or {}
    for j, col in enumerate(df.columns, start=1):
        c = ws.cell(fila0, j, NOMBRES.get(col, col))
        c.font = Font(name=FUENTE, bold=True, color="FFFFFF")
        c.fill = ENCABEZADO
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    for i, fila in enumerate(df.itertuples(index=False), start=fila0 + 1):
        for j, v in enumerate(fila, start=1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            c = ws.cell(i, j, v.item() if hasattr(v, "item") else v)
            c.font = Font(name=FUENTE)
            c.border = BORDE
            col = df.columns[j - 1]
            if col in formatos:
                c.number_format = formatos[col]
            elif isinstance(v, float):
                c.number_format = "0.000"
    for j, col in enumerate(df.columns, start=1):
        ancho = max(len(str(NOMBRES.get(col, col))), *(len(str(x)) for x in df[col].head(50)))
        ws.column_dimensions[get_column_letter(j)].width = min(max(10, ancho * 0.9 + 2), 34)
    ws.row_dimensions[fila0].height = 32
    ws.freeze_panes = ws.cell(fila0 + 1, 1)


def _hoja_leeme(wb, param):
    TIPOS, P_RETIRO, JORNADA_MIN = param["TIPOS"], param["P_RETIRO"], param["JORNADA_MIN"]
    ws = wb.active
    ws.title = "Leeme"
    ws["A1"] = "Simulación de cajas – Banco de Colombia (Actividad 2-M3)"
    ws["A1"].font = Font(name=FUENTE, bold=True, size=14)
    ws["A3"] = "Parámetros del modelo (Tablas 1 y 2 del enunciado; valores dados por el enunciado)"
    ws["A3"].font = Font(name=FUENTE, bold=True)
    tabla = pd.DataFrame([{"Acción": a, "Tipo": t, "Media servicio (min)": v[0],
                           "Media llegada (min)": v[1], "Prob. dentro de la acción": v[2]}
                          for (a, t), v in TIPOS.items()])
    _escribir(ws, tabla, fila0=4, formatos={"Prob. dentro de la acción": "0.00"})
    ws.freeze_panes = None
    ws["A14"] = "Proporción de retiros"
    ws["B14"] = P_RETIRO
    ws["B14"].number_format = "0%"
    ws["A15"] = "Jornada (min)"
    ws["B15"] = JORNADA_MIN
    ws["A17"] = "Hojas del libro"
    ws["A17"].font = Font(name=FUENTE, bold=True)
    for k, linea in enumerate(__doc__.strip().splitlines()[3:], start=18):
        ws.cell(k, 1, linea.strip())
    for fila in ws.iter_rows(min_row=14):
        for c in fila:
            if c.value is not None and not c.font.bold:
                c.font = Font(name=FUENTE)
    ws.column_dimensions["A"].width = 30


def _hoja_p3(wb, p3):
    """Punto 3 con fórmulas de Excel para el total y las estadísticas."""
    ws = wb.create_sheet("P3_Usuarios_por_replica")
    df = p3.drop(columns="Total").copy()
    df.columns = [f"{a} {t.lower()}" for a, t in df.columns]
    df.insert(0, "Réplica", p3.index.values)
    df["Total"] = None
    _escribir(ws, df)
    n = len(df)
    ult = n + 1                                  # última fila de datos
    col_tot = get_column_letter(df.shape[1])
    col_ult_tipo = get_column_letter(df.shape[1] - 1)
    for i in range(2, ult + 1):                  # total por réplica = suma de tipos
        ws[f"{col_tot}{i}"] = f"=SUM(B{i}:{col_ult_tipo}{i})"
        ws[f"{col_tot}{i}"].font = Font(name=FUENTE, bold=True)
    etiquetas = ["Mínimo", "Réplica del mínimo", "Promedio", "Desv. estándar", "Máximo"]
    for k, et in enumerate(etiquetas):
        f = ult + 2 + k
        ws.cell(f, 1, et).font = Font(name=FUENTE, bold=True)
        for j in range(2, df.shape[1] + 1):
            L = get_column_letter(j)
            rango = f"{L}2:{L}{ult}"
            formula = {
                "Mínimo": f"=MIN({rango})",
                "Réplica del mínimo": f"=INDEX($A$2:$A${ult},MATCH(MIN({rango}),{rango},0))",
                "Promedio": f"=AVERAGE({rango})",
                "Desv. estándar": f"=STDEV({rango})",
                "Máximo": f"=MAX({rango})",
            }[et]
            c = ws.cell(f, j, formula)
            c.font = Font(name=FUENTE, bold=True)
            c.fill = RESUMEN
            c.number_format = "0.00" if et in ("Promedio", "Desv. estándar") else "0"
        ws.cell(f, 1).fill = RESUMEN


def exportar_excel(t, ruta):
    """Crea el libro de Excel a partir del diccionario de tablas de resultados."""
    wb = Workbook()
    _hoja_leeme(wb, t["param"])
    pct = {"utilizacion_prom": "0.0%", "utilizacion": "0.0%", "rho_teo": "0.000",
           "pct_espera_mas_10": "0.0", "p_valor": "0.0000"}

    hojas = [
        ("Replicas_necesarias", t["replicas_necesarias"]),
        ("P1_Atencion_cajero", t["p1"]),
        ("P2_Usuarios_tipo_cajero",
         t["p2"].reset_index().rename(columns={"accion": "Acción", "tipo": "Tipo",
                                               1: "Cajero 1", 2: "Cajero 2", 3: "Cajero 3"})),
    ]
    for nombre, df in hojas:
        _escribir(wb.create_sheet(nombre), df, formatos=pct)

    _hoja_p3(wb, t["p3"])

    hojas = [
        ("P4_Escenarios", t["p4"]),
        ("P4_Espera_por_tipo", t["p4_tipo"].reset_index().rename(
            columns={"accion": "Acción", "tipo": "Tipo"})),
        ("P4_Comparaciones", t["pares"]),
        ("Metricas_colas", t["colas"]),
        ("Escenarios_por_replica", t["por_rep"]),
        ("Cajeros_por_replica", t["cajeros"][["escenario", "replica", "cajero", "atiende",
                                              "usuarios", "servicio_prom", "espera_prom",
                                              "espera_max", "sistema_prom", "utilizacion",
                                              "hora_ultimo"]]),
    ]
    for nombre, df in hojas:
        _escribir(wb.create_sheet(nombre), df, formatos=pct)

    wb.save(ruta)
