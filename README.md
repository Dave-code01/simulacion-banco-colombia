# Simulación de cajas del Banco de Colombia – Actividad didáctica 2-M3

Modelo de simulación de eventos discretos (Python + SimPy) para decidir cuántas cajas
del banco deben atender exclusivamente retiros y cuántas pagos, y si hace falta un
cajero adicional.

## Problema

- 3 cajas, cada una modelada como un sistema **M/M/1 independiente**.
- Jornada de **8 horas** (480 min); los días se consideran iguales.
- 70 % de los usuarios hace **retiros** y 30 % **consignaciones o pagos**.
- 8 tipos de usuario (rápido, normal, lento y muy lento por acción) con tiempos
  exponenciales de llegada y de servicio (Tablas 1 y 2 del enunciado).

## Escenarios simulados

| Código | Configuración |
|---|---|
| E0 | 3 cajas mixtas (situación actual) |
| E1 | 1 caja de retiros + 2 de pagos |
| E2 | 2 cajas de retiros + 1 de pagos |
| E3 | 4 cajas mixtas (cajero adicional) |
| E4 | 2 de retiros + 2 de pagos (cajero adicional) |

En cada réplica los cinco escenarios reciben exactamente los mismos usuarios
(números aleatorios comunes), así las diferencias se deben solo a la configuración.

## Cómo ejecutar

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python simulacion_banco.py
```

El programa:

1. Corre un **piloto de 10 réplicas**.
2. Calcula las réplicas necesarias para estimar la espera promedio con un error
   del 10 % y 95 % de confianza: `n = (t · s / (0.10 · media))²`.
3. Corre la simulación definitiva con ese número (193 réplicas con la semilla 2025).
4. Calcula L, Lq, W, Wq y ρ de cada caja (teórico M/M/1 y simulado) y valida que ρ < 1.
5. Imprime las tablas en consola, guarda los CSV en `resultados/`, el libro
   `resultados_simulacion_banco.xlsx` y las gráficas en `figuras/`.

Opciones:

```bash
python simulacion_banco.py --piloto 10 --semilla 2025      # valores por defecto
python simulacion_banco.py --replicas 50                   # fija el número final de réplicas
python simulacion_banco.py --salida otra_carpeta
```

Tiempo de ejecución: unos 15 segundos.

## Resultados (semilla 2025, 193 réplicas)

| Escenario | Espera general (min) | Espera retiros | Espera pagos | Usuarios que esperan > 10 min |
|---|---|---|---|---|
| E0 – 3 mixtas | 3,38 ± 0,20 | 3,47 | 3,19 | 11,8 % |
| E1 – 1 retiro + 2 pago | 5,10 ± 0,38 | 6,18 | 2,45 | 19,0 % |
| E2 – 2 retiro + 1 pago | 3,82 ± 0,31 | 1,65 | 8,53 | 12,3 % |
| E3 – 4 mixtas | 2,11 ± 0,11 | 2,20 | 1,92 | 6,9 % |
| E4 – 2 retiro + 2 pago | 1,91 ± 0,09 | 1,65 | 2,45 | 5,7 % |

**Conclusión:** entre las dos opciones del banco conviene **2 cajas de retiros y 1 de
pagos** (E2). Para que ningún grupo espere más de 5 min en promedio, el cuarto cajero
debe dedicarse a **pagos** (E4).

## Archivos

| Archivo | Contenido |
|---|---|
| `simulacion_banco.py` | Modelo comentado, escenarios y cálculo de estadísticas |
| `graficas.py` | Gráficas del informe (matplotlib) |
| `exportar_excel.py` | Exportación de resultados a Excel con formato y fórmulas |
| `resultados_simulacion_banco.xlsx` | Todos los datos y resultados en Excel |
| `figuras/` | Gráficas en PNG (atención por cajero, usuarios por réplica, espera por escenario, convergencia) |
| `informe/` | Informe en Word y PDF |
| `resultados/metricas_colas_mm1.csv` | L, Lq, W, Wq y ρ por caja: teórico M/M/1 y simulado |
| `requirements.txt` | Dependencias |
| `resultados_consola.txt` | Salida completa de la ejecución |
| `resultados/replicas_necesarias.csv` | Piloto y número de réplicas requerido |
| `resultados/p1_tiempos_por_cajero.csv` | Punto 1: tiempo de atención, espera y utilización por cajero |
| `resultados/p2_promedio_tipo_por_cajero.csv` | Punto 2: usuarios promedio de cada tipo por cajero |
| `resultados/p3_usuarios_tipo_por_replica.csv` | Punto 3: usuarios de cada tipo en cada réplica |
| `resultados/p3_resumen_minimos.csv` | Punto 3: mínimo por tipo y réplica donde ocurre |
| `resultados/p3_cajero_con_menos_usuarios.csv` | Punto 3: cajero con menos usuarios de cada tipo |
| `resultados/p4_resumen_escenarios.csv` | Puntos 4-5: esperas por escenario con IC 95 % |
| `resultados/p4_espera_por_tipo.csv` | Puntos 4-5: espera por tipo de usuario y escenario |
| `resultados/p4_comparaciones_pareadas.csv` | Pruebas t pareadas entre escenarios |
| `resultados/p4_espera_por_escenario_replica.csv` | Indicadores de cada escenario en cada réplica |
| `resultados/resumen_cajeros_por_replica.csv` | Indicadores de cada cajero en cada réplica |
| `resultados/detalle_usuarios.csv.gz` | Registro de cada usuario simulado |
