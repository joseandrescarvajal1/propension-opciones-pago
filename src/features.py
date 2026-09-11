"""Construcción de variables con corte temporal en t-1.

Es el mismo código que usan los notebooks 01 (bloques prob_, pag_, obl_, pagcli_, cli_, lag_, lagcli_)
y 06 (bloque fe_), pasado a funciones para que entrenamiento e inferencia batch usen exactamente la
misma lógica. Regla central: para una fila con etiqueta en el mes t, solo entra información de meses
estrictamente anteriores (<= t-1).

Uso:
    from features import construir_dataset
    train, test, columnas = construir_dataset("data")          # lee los CSV crudos de la competencia
    # train: 568.251 filas con var_rpta_alt; test: 112.549 filas de 2024-01 sin etiqueta

Índice de meses: 2023-01 = 0, ..., 2023-12 = 11, 2024-01 = 12.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

N_MESES = 13
KEYS = ["nit_enmascarado", "num_oblig_orig_enmascarado", "num_oblig_enmascarado", "fecha_var_rpta_alt"]
TARGET = "var_rpta_alt"
ID_COLS = KEYS + ["ID", "conjunto", "t", "t_1"]

ARCHIVOS = {
    "train": "prueba_op_base_pivot_var_rpta_alt_enmascarado_trtest.csv",
    "oot": "prueba_op_base_pivot_var_rpta_alt_enmascarado_oot.csv",
    "prob": "prueba_op_probabilidad_oblig_base_hist_enmascarado_completa.csv",
    "pagos": "prueba_op_maestra_cuotas_pagos_mes_hist_enmascarado_completa.csv",
    "cli": "prueba_op_master_customer_data_enmascarado_completa.csv",
}


# ----------------------------------------------------------------------------- utilidades temporales
def month_idx(yyyymm: pd.Series | int) -> pd.Series | int:
    """202301 -> 0, 202312 -> 11, 202401 -> 12."""
    return (yyyymm // 100 - 2023) * 12 + (yyyymm % 100 - 1)


def to_wide(idx: np.ndarray, col_t: np.ndarray, values: np.ndarray, n_rows: int, n_cols: int = N_MESES) -> np.ndarray:
    """Matriz entidad x mes (NaN donde no hay registro)."""
    M = np.full((n_rows, n_cols), np.nan)
    M[idx, col_t] = values
    return M


def window_sum_count(M: np.ndarray, r: np.ndarray, t: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Suma y conteo de no nulos de M[r, t-k : t] (los meses t-k .. t-1). r = -1 -> NaN."""
    V = np.nan_to_num(M, nan=0.0)
    C = (~np.isnan(M)).astype(float)
    cs = np.concatenate([np.zeros((M.shape[0], 1)), V.cumsum(axis=1)], axis=1)
    cc = np.concatenate([np.zeros((M.shape[0], 1)), C.cumsum(axis=1)], axis=1)
    lo = np.clip(t - k, 0, None)
    rr = np.clip(r, 0, None)
    s = cs[rr, t] - cs[rr, lo]
    c = cc[rr, t] - cc[rr, lo]
    s[r < 0] = np.nan
    c[r < 0] = np.nan
    return s, c


def last_valid_before(M: np.ndarray, r: np.ndarray, t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Último valor no nulo de M[r, :t] y el mes en que ocurrió."""
    F = pd.DataFrame(M).ffill(axis=1).to_numpy()
    idx = np.where(np.isnan(M), np.nan, np.arange(M.shape[1])[None, :])
    L = pd.DataFrame(idx).ffill(axis=1).to_numpy()
    rr = np.clip(r, 0, None)
    val = F[rr, t - 1]
    when = L[rr, t - 1]
    val[r < 0] = np.nan
    when[r < 0] = np.nan
    return val, when


def ventana(M: np.ndarray, r: np.ndarray, t: np.ndarray, k: int) -> np.ndarray:
    """Matriz (n, k) con M[r, t-k .. t-1]; NaN donde no hay fila o el mes es negativo."""
    cols = t[:, None] - k + np.arange(k)[None, :]
    ok = (cols >= 0) & (r[:, None] >= 0)
    W = np.full(cols.shape, np.nan)
    rr = np.clip(r, 0, None)[:, None] * np.ones_like(cols)
    W[ok] = M[rr[ok], cols[ok]]
    return W


def pendiente(W: np.ndarray) -> np.ndarray:
    """Pendiente de mínimos cuadrados por fila ignorando NaN (x = 0..k-1); NaN con menos de 3 puntos."""
    k = W.shape[1]
    x = np.arange(k, dtype=float)[None, :]
    m = ~np.isnan(W)
    n = m.sum(1)
    Wz = np.nan_to_num(W)
    sx = (x * m).sum(1)
    sy = Wz.sum(1)
    sxy = (x * Wz).sum(1)
    sxx = (x * x * m).sum(1)
    den = n * sxx - sx**2
    with np.errstate(invalid="ignore", divide="ignore"):
        s = (n * sxy - sx * sy) / den
    s[(n < 3) | (den == 0)] = np.nan
    return s


def racha_final(W: np.ndarray) -> np.ndarray:
    """Meses consecutivos con valor 0 al final de la ventana (NaN corta la racha)."""
    Z = np.where(np.isnan(W), 0, (W == 0).astype(int))
    out = np.zeros(len(W))
    vivo = np.ones(len(W), bool)
    for j in range(W.shape[1] - 1, -1, -1):
        vivo &= Z[:, j] == 1
        out += vivo
    return out


def racha_max(W: np.ndarray) -> np.ndarray:
    Z = np.where(np.isnan(W), 0, (W == 0).astype(int))
    cur = np.zeros(len(W))
    mx = np.zeros(len(W))
    for j in range(W.shape[1]):
        cur = (cur + 1) * Z[:, j]
        mx = np.maximum(mx, cur)
    return mx


def meses_desde(M_flag: np.ndarray, r: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Meses desde el último mes (< t) con flag == 1."""
    idx = np.where(M_flag == 1, np.arange(M_flag.shape[1])[None, :], np.nan)
    L = pd.DataFrame(idx).ffill(axis=1).to_numpy()
    out = t - L[np.clip(r, 0, None), t - 1]
    out[r < 0] = np.nan
    return out


# ----------------------------------------------------------------------------- carga
def cargar_crudos(data_dir: str | Path) -> dict[str, pd.DataFrame]:
    d = Path(data_dir)
    tr = pd.read_csv(d / ARCHIVOS["train"], low_memory=False)
    oot = pd.read_csv(d / ARCHIVOS["oot"])
    prob = pd.read_csv(d / ARCHIVOS["prob"])
    prob["t"] = month_idx(prob.fecha_corte)
    prob = prob.drop_duplicates(["num_oblig_enmascarado", "t"])
    pag = pd.read_csv(d / ARCHIVOS["pagos"], low_memory=False)
    pag["t"] = month_idx(pag.fecha_corte // 100)
    pag = pag.drop_duplicates(["num_oblig_enmascarado", "t"])
    pag["porc_pago"] = pag.porc_pago.replace([np.inf, -np.inf], np.nan).clip(upper=500)
    pag["pago_flag"] = (pag.pago_total > 0).astype(float)
    pag["no_pago"] = (pag.marca_pago == "NO_PAGO").astype(float)
    pag["pago_mas"] = (pag.marca_pago == "PAGO_MAS").astype(float)
    pag["cancelado"] = (pag.marca_pago == "CANCELADO").astype(float)
    pag["rediferido"] = (pag.ajustes_banco == "REDIFERIDOS").astype(float)
    pag["ajuste"] = (pag.ajustes_banco != "NO").astype(float)
    pag["pago_completo"] = (pag.porc_pago >= 100).astype(float)
    cli = pd.read_csv(d / ARCHIVOS["cli"], low_memory=False)
    cli["t"] = month_idx(cli.year * 100 + cli.month)
    cli = cli.sort_values(["nit_enmascarado", "t"]).drop_duplicates(["nit_enmascarado", "t"], keep="last")
    return {"tr_raw": tr, "oot_raw": oot, "prob": prob, "pag": pag, "cli": cli}


def construir_base(tr_raw: pd.DataFrame, oot_raw: pd.DataFrame) -> pd.DataFrame:
    """Esqueleto: llaves + etiqueta (train) y llaves (test), con t y t_1."""
    a = tr_raw[KEYS + [TARGET]].drop_duplicates(KEYS).copy()
    a["conjunto"] = "train"
    b = oot_raw[KEYS].copy()
    b[TARGET] = np.nan
    b["conjunto"] = "test"
    base = pd.concat([a, b], ignore_index=True)
    base["t"] = month_idx(base.fecha_var_rpta_alt)
    base["t_1"] = base["t"] - 1
    base["ID"] = base.nit_enmascarado.astype(str) + "#" + base.num_oblig_orig_enmascarado.astype(str) + "#" + base.num_oblig_enmascarado.astype(str)
    return base


# ----------------------------------------------------------------------------- bloques del notebook 01
def feat_prob(base: pd.DataFrame, prob: pd.DataFrame) -> pd.DataFrame:
    cols = ["prob_propension", "prob_alrt_temprana", "prob_auto_cura", "lote"]
    out = base[["num_oblig_enmascarado", "t"]].copy()
    for k in (1, 2, 3):
        lag = prob[["num_oblig_enmascarado", "t"] + cols].copy()
        lag["t"] = lag["t"] + k
        out = out.merge(lag.rename(columns={c: f"prob_{c}_t{k}" for c in cols}), on=["num_oblig_enmascarado", "t"], how="left")
    for c in cols[:3]:
        out[f"prob_{c}_mean3"] = out[[f"prob_{c}_t{k}" for k in (1, 2, 3)]].mean(axis=1)
        out[f"prob_{c}_delta13"] = out[f"prob_{c}_t1"] - out[f"prob_{c}_t3"]
    return out.drop(columns=["num_oblig_enmascarado", "t"])


def feat_pagos(base: pd.DataFrame, pag: pd.DataFrame) -> pd.DataFrame:
    oi = pd.Index(pag.num_oblig_enmascarado.unique())
    rp = oi.get_indexer(pag.num_oblig_enmascarado)
    r = oi.get_indexer(base.num_oblig_enmascarado)
    t = base.t.to_numpy()
    mats = {v: to_wide(rp, pag.t.to_numpy(), pag[v].to_numpy(), len(oi)) for v in ["valor_cuota_mes", "pago_total", "porc_pago", "pago_flag", "no_pago", "pago_mas", "cancelado", "rediferido", "ajuste"]}
    f = pd.DataFrame(index=base.index)
    _, n_hist = window_sum_count(mats["pago_flag"], r, t, 12)
    f["pag_meses_historial"] = n_hist
    _, ult = last_valid_before(np.where(mats["pago_flag"] == 1, 1.0, np.nan), r, t)
    f["pag_meses_desde_ultimo_pago"] = t - ult
    for k in (1, 3, 6, 12):
        s, c = window_sum_count(mats["pago_total"], r, t, k)
        f[f"pag_pago_total_sum_{k}m"] = s
        f[f"pag_pago_total_mean_{k}m"] = s / c.clip(min=1)
        s, c = window_sum_count(mats["valor_cuota_mes"], r, t, k)
        f[f"pag_cuota_mean_{k}m"] = s / c.clip(min=1)
        s, c = window_sum_count(mats["porc_pago"], r, t, k)
        f[f"pag_porc_pago_mean_{k}m"] = s / c.clip(min=1)
        for v in ["pago_flag", "no_pago", "pago_mas", "rediferido", "ajuste", "cancelado"]:
            s, _ = window_sum_count(mats[v], r, t, k)
            f[f"pag_n_{v}_{k}m"] = s
    f["pag_ratio_pago_cuota_3m"] = f["pag_pago_total_sum_3m"] / f["pag_cuota_mean_3m"].replace(0, np.nan) / 3
    f["pag_cuota_trend_1_vs_6"] = f["pag_cuota_mean_1m"] / f["pag_cuota_mean_6m"].replace(0, np.nan)
    estado = pag[["num_oblig_enmascarado", "t", "marca_pago", "ajustes_banco", "producto", "aplicativo", "segmento"]].copy()
    estado["t"] = estado["t"] + 1
    estado = estado.rename(columns={"marca_pago": "pag_marca_pago_t1", "ajustes_banco": "pag_ajustes_banco_t1", "producto": "obl_producto", "aplicativo": "obl_aplicativo", "segmento": "obl_segmento"})
    f = f.join(base[["num_oblig_enmascarado", "t"]].merge(estado, on=["num_oblig_enmascarado", "t"], how="left").drop(columns=["num_oblig_enmascarado", "t"]))
    return f


def feat_pagcli(base: pd.DataFrame, pag: pd.DataFrame) -> pd.DataFrame:
    g = (pag.groupby(["nit_enmascarado", "t"]).agg(pagcli_n_oblig_t1=("num_oblig_enmascarado", "nunique"), pagcli_cuota_total_t1=("valor_cuota_mes", "sum"), pagcli_pago_total_t1=("pago_total", "sum"),
                                                     pagcli_n_no_pago_t1=("no_pago", "sum"), pagcli_n_rediferido_t1=("rediferido", "sum")).reset_index())
    g["t"] = g["t"] + 1
    f = base[["nit_enmascarado", "t"]].merge(g, on=["nit_enmascarado", "t"], how="left").drop(columns=["nit_enmascarado", "t"])
    f["pagcli_ratio_pago_cuota_t1"] = f.pagcli_pago_total_t1 / f.pagcli_cuota_total_t1.replace(0, np.nan)
    return f


CLI_NUM = ["edad_cli", "num_hijos", "personas_dependientes", "total_ing", "tot_activos", "tot_pasivos", "egresos_mes", "tot_patrimonio"]
CLI_CAT = ["tipo_cli", "genero_cli", "estado_civil", "tipo_vivienda", "nivel_academico", "ocup", "declarante", "segm", "subsegm", "region_of", "cli_actualizado", "nicho"]


def feat_cli(base: pd.DataFrame, cli: pd.DataFrame) -> pd.DataFrame:
    cli = cli.copy()
    for c in CLI_NUM:
        cli[c] = pd.to_numeric(cli[c], errors="coerce")
    cli.loc[(cli.edad_cli <= 0) | (cli.edad_cli > 100), "edad_cli"] = np.nan
    for c in ["total_ing", "tot_activos", "tot_pasivos", "egresos_mes", "tot_patrimonio"]:
        cli[c] = np.log1p(cli[c].clip(lower=0))
    fv = pd.to_numeric(cli.f_vinc, errors="coerce")
    cli["antiguedad_meses"] = (cli.year * 12 + cli.month) - (fv // 10000 * 12 + fv // 100 % 100)
    cli["antiguedad_meses"] = cli.antiguedad_meses.where(cli.antiguedad_meses.between(0, 900))
    cli["ratio_pasivo_activo"] = np.expm1(cli.tot_pasivos) / np.expm1(cli.tot_activos).replace(0, np.nan)
    cli["ratio_egreso_ingreso"] = np.expm1(cli.egresos_mes) / np.expm1(cli.total_ing).replace(0, np.nan)
    feats = CLI_NUM + CLI_CAT + ["antiguedad_meses", "ratio_pasivo_activo", "ratio_egreso_ingreso"]
    small = cli[["nit_enmascarado", "t"] + feats].rename(columns={c: f"cli_{c}" for c in feats}).rename(columns={"t": "cli_t_corte"})
    small["cli_t_corte"] = small.cli_t_corte.astype("int64")
    small["nit_enmascarado"] = small.nit_enmascarado.astype("int64")
    small = small.sort_values("cli_t_corte")
    q = base[["nit_enmascarado", "t_1"]].astype({"nit_enmascarado": "int64", "t_1": "int64"}).reset_index().sort_values("t_1")
    back = pd.merge_asof(q, small, left_on="t_1", right_on="cli_t_corte", by="nit_enmascarado", direction="backward")
    fwd = pd.merge_asof(q, small, left_on="t_1", right_on="cli_t_corte", by="nit_enmascarado", direction="forward")
    sin = back.cli_t_corte.isna()
    f = back.copy()
    f.loc[sin, fwd.columns] = fwd.loc[sin].values
    f["cli_corte_posterior"] = (sin & f.cli_t_corte.notna()).astype(int)
    return f.set_index("index").sort_index().drop(columns=["nit_enmascarado", "t_1"])


LAG_NUM = ["var_rpta_alt", "cant_alter_posibles", "cant_gestiones", "rpc", "promesas_cumplidas", "cant_acuerdo", "min_mora", "max_mora", "dias_mora_fin",
           "vlr_obligacion", "vlr_vencido", "saldo_capital", "endeudamiento", "valor_cuota_mes", "pago_mes", "porc_pago_cuota"]
LAG_CAT = ["producto", "producto_cons", "banca", "segmento", "aplicativo", "rango_mora", "desc_alternativa1", "alter_posible1_2", "marca_alt_rank", "alternativa_aplicada_agr", "marca_pago"]


def feat_lag(base: pd.DataFrame, tr_raw: pd.DataFrame) -> pd.DataFrame:
    tr = tr_raw.drop_duplicates(KEYS).copy()
    tr["t"] = month_idx(tr.fecha_var_rpta_alt)
    oi = pd.Index(tr.num_oblig_enmascarado.unique())
    rt = oi.get_indexer(tr.num_oblig_enmascarado)
    r = oi.get_indexer(base.num_oblig_enmascarado)
    t = base.t.to_numpy()
    f = pd.DataFrame(index=base.index)
    for v in LAG_NUM:
        M = to_wide(rt, tr.t.to_numpy(), pd.to_numeric(tr[v], errors="coerce").to_numpy(), len(oi))
        val, when = last_valid_before(M, r, t)
        f[f"lag_{v}_ult"] = val
        if v == "var_rpta_alt":
            f["lag_meses_desde_ultima_gestion"] = t - when
            s, c = window_sum_count(M, r, t, 12)
            f["lag_n_meses_vistos"] = np.nan_to_num(c, nan=0.0)
            f["lag_n_aceptos"] = np.nan_to_num(s, nan=0.0)
            f["lag_tasa_acepto"] = np.where(c > 0, s / np.where(c > 0, c, 1), np.nan)
            a = M[np.clip(r, 0, None), t - 1]
            a[r < 0] = np.nan
            f["lag_acepto_t1"] = a
    for v in LAG_CAT:
        cat = tr[v].astype("category")
        M = to_wide(rt, tr.t.to_numpy(), cat.cat.codes.astype(float).to_numpy(), len(oi))
        val, _ = last_valid_before(M, r, t)
        codes = np.where(np.isnan(val), -1, val).astype(int)
        f[f"lag_{v}_ult"] = pd.Categorical.from_codes(codes, categories=cat.cat.categories)
    ni = pd.Index(tr.nit_enmascarado.unique())
    cm = tr.groupby(["nit_enmascarado", "t"]).agg(n=("num_oblig_enmascarado", "nunique"), a=(TARGET, "sum")).reset_index()
    rn = ni.get_indexer(cm.nit_enmascarado)
    Mn = to_wide(rn, cm.t.to_numpy(), cm.n.to_numpy().astype(float), len(ni))
    Ma = to_wide(rn, cm.t.to_numpy(), cm.a.to_numpy().astype(float), len(ni))
    rb = ni.get_indexer(base.nit_enmascarado)
    sn, _ = window_sum_count(Mn, rb, t, 12)
    sa, _ = window_sum_count(Ma, rb, t, 12)
    f["lagcli_n_oblig_gestionadas"] = np.nan_to_num(sn, nan=0.0)
    f["lagcli_n_aceptos"] = np.nan_to_num(sa, nan=0.0)
    f["lagcli_tasa_acepto"] = np.where(sn > 0, sa / np.where(sn > 0, sn, 1), np.nan)
    return f


# ----------------------------------------------------------------------------- bloque del notebook 06
def feat_nuevas(base: pd.DataFrame, parcial: pd.DataFrame, pag: pd.DataFrame, prob: pd.DataFrame, tr_raw: pd.DataFrame) -> pd.DataFrame:
    """23 variables fe_: tendencias de pago, trayectoria de scores, contexto del cliente, tasas históricas, historial del cliente, interacciones."""
    t = base.t.to_numpy()
    f = pd.DataFrame(index=base.index)
    # A. tendencia y ritmo de pago
    oi = pd.Index(pag.num_oblig_enmascarado.unique())
    rp = oi.get_indexer(pag.num_oblig_enmascarado)
    r = oi.get_indexer(base.num_oblig_enmascarado)
    M = {v: to_wide(rp, pag.t.to_numpy(), pag[v].to_numpy(), len(oi)) for v in ["porc_pago", "pago_total", "pago_flag", "pago_completo", "rediferido", "valor_cuota_mes"]}
    f["fe_pend_porc_pago_6m"] = pendiente(ventana(M["porc_pago"], r, t, 6))
    f["fe_pend_pago_total_6m"] = pendiente(np.log1p(np.clip(ventana(M["pago_total"], r, t, 6), 0, None)))
    W12 = ventana(M["pago_flag"], r, t, 12)
    f["fe_racha_sin_pago_actual"] = racha_final(W12)
    f["fe_racha_sin_pago_max12"] = racha_max(W12)
    f["fe_meses_desde_pago_completo"] = meses_desde(M["pago_completo"], r, t)
    f["fe_meses_desde_rediferido"] = meses_desde(M["rediferido"], r, t)
    Wc = ventana(M["valor_cuota_mes"], r, t, 6)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["fe_cuota_ratio_t1_t6"] = Wc[:, -1] / np.where(Wc[:, 0] > 0, Wc[:, 0], np.nan)
    # B. trayectoria de scores
    oi2 = pd.Index(prob.num_oblig_enmascarado.unique())
    rp2 = oi2.get_indexer(prob.num_oblig_enmascarado)
    r2 = oi2.get_indexer(base.num_oblig_enmascarado)
    for v in ["prob_propension", "prob_alrt_temprana", "prob_auto_cura"]:
        Mv = to_wide(rp2, prob.t.to_numpy(), prob[v].to_numpy(), len(oi2))
        f[f"fe_pend_{v}_6m"] = pendiente(ventana(Mv, r2, t, 6))
        if v == "prob_alrt_temprana":
            f["fe_alerta_sobre_05_3m"] = (np.nanmax(ventana(Mv, r2, t, 3), axis=1) >= 0.5).astype(float)
    Ml = to_wide(rp2, prob.t.to_numpy(), prob["lote"].to_numpy().astype(float), len(oi2))
    Wl = ventana(Ml, r2, t, 3)
    f["fe_lote_cambio_3m"] = Wl[:, -1] - Wl[:, 0]
    # C. contexto del cliente
    with np.errstate(invalid="ignore", divide="ignore"):
        f["fe_cuota_share_cliente"] = (parcial["pag_cuota_mean_1m"] / parcial["pagcli_cuota_total_t1"].replace(0, np.nan)).clip(upper=1).to_numpy()
        f["fe_share_oblig_sin_pago"] = (parcial["pagcli_n_no_pago_t1"] / parcial["pagcli_n_oblig_t1"].replace(0, np.nan)).to_numpy()
    cm = pag.groupby(["nit_enmascarado", "t"]).rediferido.max().reset_index()
    ni = pd.Index(cm.nit_enmascarado.unique())
    Mr = to_wide(ni.get_indexer(cm.nit_enmascarado), cm.t.to_numpy(), cm.rediferido.to_numpy(), len(ni))
    f["fe_cliente_rediferido_12m"] = (np.nansum(ventana(Mr, ni.get_indexer(base.nit_enmascarado), t, 12), axis=1) > 0).astype(float)
    # D. tasas históricas por grupo (solo meses < t, mínimo 50 filas)
    tr = tr_raw.copy()
    tr["t"] = month_idx(tr.fecha_var_rpta_alt)

    def tasa_hist(col_tr, col_base, normalizar=False):
        k_tr = tr[col_tr].astype(str)
        k_b = parcial[col_base].astype(str)
        if normalizar:
            k_tr = k_tr.str.upper().str.strip()
            k_b = k_b.str.upper().str.strip()
        cats = pd.Index(sorted(set(k_tr.unique())))
        g = tr.assign(k=k_tr).groupby(["k", "t"])[TARGET].agg(["sum", "size"]).reset_index()
        Sy = to_wide(cats.get_indexer(g.k), g.t.to_numpy(), g["sum"].to_numpy().astype(float), len(cats))
        Sn = to_wide(cats.get_indexer(g.k), g.t.to_numpy(), g["size"].to_numpy().astype(float), len(cats))
        cy = np.nancumsum(np.nan_to_num(Sy), axis=1)
        cn = np.nancumsum(np.nan_to_num(Sn), axis=1)
        rb = cats.get_indexer(k_b)
        ok = rb >= 0
        y_ = np.where(ok, cy[np.clip(rb, 0, None), t - 1], np.nan)
        n_ = np.where(ok, cn[np.clip(rb, 0, None), t - 1], np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(n_ >= 50, y_ / n_, np.nan)

    f["fe_tasa_hist_producto"] = tasa_hist("producto", "obl_producto")
    f["fe_tasa_hist_aplicativo"] = tasa_hist("aplicativo", "obl_aplicativo")
    f["fe_tasa_hist_segmento"] = tasa_hist("segmento", "obl_segmento", normalizar=True)
    # E. historial del cliente
    cm2 = tr.assign(aplic=(tr.marca_alt_apli == "SI").astype(float)).groupby(["nit_enmascarado", "t"]).agg(acepto=(TARGET, "max"), aplic=("aplic", "max")).reset_index()
    ni2 = pd.Index(cm2.nit_enmascarado.unique())
    rn = ni2.get_indexer(cm2.nit_enmascarado)
    rb = ni2.get_indexer(base.nit_enmascarado)
    f["fe_meses_desde_acepto_cli"] = meses_desde(to_wide(rn, cm2.t.to_numpy(), cm2.acepto.to_numpy(), len(ni2)), rb, t)
    f["fe_meses_desde_aplicacion_cli"] = meses_desde(to_wide(rn, cm2.t.to_numpy(), cm2.aplic.to_numpy(), len(ni2)), rb, t)
    f["fe_en_espera"] = (f.fe_meses_desde_aplicacion_cli <= 3).astype(float)
    # F. interacciones
    f["fe_propension_x_impago"] = (parcial["prob_prob_propension_t1"] * (1 - (parcial["pag_porc_pago_mean_3m"].clip(0, 100) / 100))).to_numpy()
    f["fe_mora_x_opciones"] = (parcial["lag_dias_mora_fin_ult"] * parcial["lag_cant_alter_posibles_ult"]).to_numpy()
    return f


# ----------------------------------------------------------------------------- ensamble
def construir_dataset(data_dir: str | Path, out_dir: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Construye train y test con las 156 columnas (133 del notebook 01 + 23 del 06) desde los CSV crudos. Devuelve (train, test, columnas)."""
    return construir_desde_crudos(cargar_crudos(data_dir), out_dir)


def construir_desde_crudos(d: dict[str, pd.DataFrame], out_dir: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Igual que construir_dataset pero a partir de las tablas ya cargadas (dict con tr_raw, oot_raw, prob, pag, cli)."""
    base = construir_base(d["tr_raw"], d["oot_raw"])
    parcial = pd.concat([base, feat_prob(base, d["prob"]), feat_pagos(base, d["pag"]), feat_pagcli(base, d["pag"]), feat_cli(base, d["cli"]), feat_lag(base, d["tr_raw"])], axis=1)
    dataset = pd.concat([parcial, feat_nuevas(base, parcial, d["pag"], d["prob"], d["tr_raw"])], axis=1)
    for c in dataset.columns:
        if dataset[c].dtype == object:
            dataset[c] = dataset[c].astype("category")
    columnas = [c for c in dataset.columns if c not in ID_COLS + [TARGET]]
    train = dataset[dataset.conjunto == "train"].drop(columns=["conjunto"]).reset_index(drop=True)
    test = dataset[dataset.conjunto == "test"].drop(columns=["conjunto", TARGET]).reset_index(drop=True)
    if out_dir is not None:
        o = Path(out_dir)
        o.mkdir(parents=True, exist_ok=True)
        train.to_parquet(o / "train_fe.parquet", index=False)
        test.to_parquet(o / "test_fe.parquet", index=False)
    return train, test, columnas
