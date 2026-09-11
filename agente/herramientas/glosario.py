"""Glosario de las variables del modelo en lenguaje de negocio, para que el agente explique los factores SHAP
sin exponer nombres técnicos al cliente ni al gestor."""

from __future__ import annotations

GLOSARIO = {
    "pag_marca_pago_t1": "comportamiento de pago del mes anterior (pagó más, igual, menos o no pagó)",
    "fe_meses_desde_acepto_cli": "meses desde la última vez que el cliente aceptó una opción de pago",
    "pagcli_cuota_total_t1": "cuota total del cliente en todas sus obligaciones el mes anterior",
    "lagcli_tasa_acepto": "proporción histórica de opciones aceptadas por el cliente",
    "prob_prob_propension_t1": "score de propensión de pago del banco el mes anterior",
    "prob_prob_auto_cura_t1": "score de auto-cura del banco (probabilidad de ponerse al día solo)",
    "prob_prob_alrt_temprana_t1": "score de alerta temprana del banco",
    "fe_mora_x_opciones": "combinación de días de mora y opciones disponibles",
    "fe_meses_desde_pago_completo": "meses desde el último pago completo de la cuota",
    "cli_region_of": "región de la oficina del cliente",
    "lag_dias_mora_fin_ult": "días de mora al cierre de la última gestión",
    "lag_max_mora_ult": "mora máxima alcanzada en la última gestión",
    "lag_var_rpta_alt_ult": "resultado de la última gestión (aceptó o no)",
    "lag_n_aceptos": "número de opciones aceptadas antes en esta obligación",
    "lag_cant_alter_posibles_ult": "número de alternativas posibles en la última gestión",
    "lag_meses_desde_ultima_gestion": "meses desde la última gestión de cobranza",
    "lag_vlr_vencido_ult": "valor vencido en la última gestión",
    "lag_endeudamiento_ult": "nivel de endeudamiento en la última gestión",
    "lag_alternativa_aplicada_agr_ult": "tipo de la última opción aplicada",
    "fe_meses_desde_aplicacion_cli": "meses desde la última opción aplicada al cliente",
    "fe_en_espera": "si la obligación está en periodo de espera por una opción reciente",
    "fe_racha_sin_pago_actual": "meses seguidos sin pago",
    "fe_racha_sin_pago_max12": "racha máxima de meses sin pago en el último año",
    "pag_n_no_pago_3m": "meses sin pago en los últimos 3",
    "pag_n_no_pago_6m": "meses sin pago en los últimos 6",
    "pag_n_pago_flag_3m": "meses con pago en los últimos 3",
    "pag_n_pago_flag_6m": "meses con pago en los últimos 6",
    "pag_n_pago_flag_12m": "meses con pago en el último año",
    "pag_porc_pago_mean_3m": "porcentaje promedio de la cuota pagado en los últimos 3 meses",
    "pag_porc_pago_mean_6m": "porcentaje promedio de la cuota pagado en los últimos 6 meses",
    "pag_pago_total_mean_3m": "pago promedio mensual en los últimos 3 meses",
    "pag_cuota_mean_1m": "valor de la cuota del mes anterior",
    "pag_n_rediferido_6m": "rediferidos en los últimos 6 meses",
    "pag_meses_historial": "meses de historial de pagos disponibles",
    "obl_producto": "tipo de producto",
    "obl_segmento": "segmento comercial",
    "obl_aplicativo": "sistema origen de la obligación",
    "pagcli_n_oblig_t1": "número de obligaciones del cliente",
    "pagcli_pago_total_t1": "pago total del cliente el mes anterior",
    "pagcli_n_no_pago_t1": "obligaciones del cliente sin pago el mes anterior",
    "cli_total_ing": "ingresos totales declarados",
    "cli_egresos_mes": "egresos mensuales declarados",
    "cli_ratio_egreso_ingreso": "relación egresos sobre ingresos",
    "cli_edad_cli": "edad del cliente",
    "cli_antiguedad_meses": "antigüedad como cliente en meses",
    "cli_segm": "segmento del cliente",
    "cli_ocup": "ocupación",
    "fe_tasa_hist_producto": "tasa histórica de aceptación en el producto",
    "fe_tasa_hist_segmento": "tasa histórica de aceptación en el segmento",
    "fe_propension_x_impago": "propensión de pago combinada con el impago reciente",
    "fe_cuota_share_cliente": "peso de esta cuota dentro de la carga total del cliente",
    "fe_pend_porc_pago_6m": "tendencia del porcentaje pagado en 6 meses",
    "fe_alerta_sobre_05_3m": "meses con alerta temprana alta en los últimos 3",
}


def describir(variable: str, valor, sentido: str) -> str:
    base = GLOSARIO.get(variable, variable.replace("_", " "))
    v = "sin dato" if valor is None else (f"{valor:,.2f}".rstrip("0").rstrip(".") if isinstance(valor, float) else str(valor))
    efecto = "aumenta" if sentido == "sube" else "reduce"
    return f"{base} (valor: {v}) {efecto} la probabilidad de aceptar"
