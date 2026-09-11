# Diccionario del dataset procesado

Generado por `notebooks/01_construccion_dataset.ipynb`.

- Filas train: 568,251 (2023-08 a 2023-12) | Filas test: 112,549 (2024-01)
- Etiqueta: `var_rpta_alt` | Identificadores: `nit_enmascarado`, `num_oblig_orig_enmascarado`, `num_oblig_enmascarado`, `fecha_var_rpta_alt`, `ID`, `conjunto`, `t`, `t_1`
- Variables: 133

## Bloques

- **prob_**: Scores de modelos internos del banco (fuente: probabilidades), mes t-1, t-2, t-3 (18 variables)
- **pag_**: Comportamiento de pago de la obligación en ventanas hasta t-1 (fuente: cuotas y pagos) (46 variables)
- **obl_**: Descriptores de la obligación en t-1 (fuente: cuotas y pagos) (3 variables)
- **pagcli_**: Carga financiera total del cliente en t-1 (fuente: cuotas y pagos) (6 variables)
- **cli_**: Demografía y finanzas del cliente, último corte <= t-1 (fuente: master customer) (25 variables)
- **lag_**: Historia de gestión y aceptación de la obligación antes de t (fuente: trtest rezagado) (32 variables)
- **lagcli_**: Historia de aceptación del cliente antes de t (fuente: trtest rezagado) (3 variables)

## Variables

| variable                         | bloque   | tipo     |   nulos_train_% |   nulos_test_% |
|:---------------------------------|:---------|:---------|----------------:|---------------:|
| prob_prob_propension_t1          | prob     | float64  |             0.3 |            0.2 |
| prob_prob_alrt_temprana_t1       | prob     | float64  |             0.3 |            0.2 |
| prob_prob_auto_cura_t1           | prob     | float64  |             0.3 |            0.2 |
| prob_lote_t1                     | prob     | float64  |             0.3 |            0.2 |
| prob_prob_propension_t2          | prob     | float64  |             1   |            1   |
| prob_prob_alrt_temprana_t2       | prob     | float64  |             1   |            1   |
| prob_prob_auto_cura_t2           | prob     | float64  |             1   |            1   |
| prob_lote_t2                     | prob     | float64  |             1   |            1   |
| prob_prob_propension_t3          | prob     | float64  |             3.3 |            3.8 |
| prob_prob_alrt_temprana_t3       | prob     | float64  |             3.3 |            3.8 |
| prob_prob_auto_cura_t3           | prob     | float64  |             3.3 |            3.8 |
| prob_lote_t3                     | prob     | float64  |             3.3 |            3.8 |
| prob_prob_propension_mean3       | prob     | float64  |             0.3 |            0.2 |
| prob_prob_propension_delta13     | prob     | float64  |             3.3 |            3.8 |
| prob_prob_alrt_temprana_mean3    | prob     | float64  |             0.3 |            0.2 |
| prob_prob_alrt_temprana_delta13  | prob     | float64  |             3.3 |            3.8 |
| prob_prob_auto_cura_mean3        | prob     | float64  |             0.3 |            0.2 |
| prob_prob_auto_cura_delta13      | prob     | float64  |             3.3 |            3.8 |
| pag_meses_historial              | pag      | float64  |             0   |            0.2 |
| pag_meses_desde_ultimo_pago      | pag      | float64  |             5.5 |            5.5 |
| pag_pago_total_sum_1m            | pag      | float64  |             0   |            0.2 |
| pag_pago_total_mean_1m           | pag      | float64  |             0   |            0.2 |
| pag_cuota_mean_1m                | pag      | float64  |             0   |            0.2 |
| pag_porc_pago_mean_1m            | pag      | float64  |             0   |            0.2 |
| pag_n_pago_flag_1m               | pag      | float64  |             0   |            0.2 |
| pag_n_no_pago_1m                 | pag      | float64  |             0   |            0.2 |
| pag_n_pago_mas_1m                | pag      | float64  |             0   |            0.2 |
| pag_n_rediferido_1m              | pag      | float64  |             0   |            0.2 |
| pag_n_ajuste_1m                  | pag      | float64  |             0   |            0.2 |
| pag_n_cancelado_1m               | pag      | float64  |             0   |            0.2 |
| pag_pago_total_sum_3m            | pag      | float64  |             0   |            0.2 |
| pag_pago_total_mean_3m           | pag      | float64  |             0   |            0.2 |
| pag_cuota_mean_3m                | pag      | float64  |             0   |            0.2 |
| pag_porc_pago_mean_3m            | pag      | float64  |             0   |            0.2 |
| pag_n_pago_flag_3m               | pag      | float64  |             0   |            0.2 |
| pag_n_no_pago_3m                 | pag      | float64  |             0   |            0.2 |
| pag_n_pago_mas_3m                | pag      | float64  |             0   |            0.2 |
| pag_n_rediferido_3m              | pag      | float64  |             0   |            0.2 |
| pag_n_ajuste_3m                  | pag      | float64  |             0   |            0.2 |
| pag_n_cancelado_3m               | pag      | float64  |             0   |            0.2 |
| pag_pago_total_sum_6m            | pag      | float64  |             0   |            0.2 |
| pag_pago_total_mean_6m           | pag      | float64  |             0   |            0.2 |
| pag_cuota_mean_6m                | pag      | float64  |             0   |            0.2 |
| pag_porc_pago_mean_6m            | pag      | float64  |             0   |            0.2 |
| pag_n_pago_flag_6m               | pag      | float64  |             0   |            0.2 |
| pag_n_no_pago_6m                 | pag      | float64  |             0   |            0.2 |
| pag_n_pago_mas_6m                | pag      | float64  |             0   |            0.2 |
| pag_n_rediferido_6m              | pag      | float64  |             0   |            0.2 |
| pag_n_ajuste_6m                  | pag      | float64  |             0   |            0.2 |
| pag_n_cancelado_6m               | pag      | float64  |             0   |            0.2 |
| pag_pago_total_sum_12m           | pag      | float64  |             0   |            0.2 |
| pag_pago_total_mean_12m          | pag      | float64  |             0   |            0.2 |
| pag_cuota_mean_12m               | pag      | float64  |             0   |            0.2 |
| pag_porc_pago_mean_12m           | pag      | float64  |             0   |            0.2 |
| pag_n_pago_flag_12m              | pag      | float64  |             0   |            0.2 |
| pag_n_no_pago_12m                | pag      | float64  |             0   |            0.2 |
| pag_n_pago_mas_12m               | pag      | float64  |             0   |            0.2 |
| pag_n_rediferido_12m             | pag      | float64  |             0   |            0.2 |
| pag_n_ajuste_12m                 | pag      | float64  |             0   |            0.2 |
| pag_n_cancelado_12m              | pag      | float64  |             0   |            0.2 |
| pag_ratio_pago_cuota_3m          | pag      | float64  |             0.7 |            1.9 |
| pag_cuota_trend_1_vs_6           | pag      | float64  |             0.4 |            0.4 |
| pag_marca_pago_t1                | pag      | category |             0.2 |            0.2 |
| pag_ajustes_banco_t1             | pag      | category |             0.2 |            0.2 |
| obl_producto                     | obl      | category |             0.2 |            0.2 |
| obl_aplicativo                   | obl      | category |             0.2 |            0.2 |
| obl_segmento                     | obl      | category |             0.2 |            0.2 |
| pagcli_n_oblig_t1                | pagcli   | float64  |             0.1 |            0.1 |
| pagcli_cuota_total_t1            | pagcli   | float64  |             0.1 |            0.1 |
| pagcli_pago_total_t1             | pagcli   | float64  |             0.1 |            0.1 |
| pagcli_n_no_pago_t1              | pagcli   | float64  |             0.1 |            0.1 |
| pagcli_n_rediferido_t1           | pagcli   | float64  |             0.1 |            0.1 |
| pagcli_ratio_pago_cuota_t1       | pagcli   | float64  |             0.9 |            1.4 |
| cli_t_corte                      | cli      | float64  |            19.7 |           19.6 |
| cli_edad_cli                     | cli      | float64  |            22   |           22.1 |
| cli_num_hijos                    | cli      | float64  |            21.8 |           21.8 |
| cli_personas_dependientes        | cli      | float64  |            21.8 |           21.8 |
| cli_total_ing                    | cli      | float64  |            19.7 |           19.6 |
| cli_tot_activos                  | cli      | float64  |            19.7 |           19.6 |
| cli_tot_pasivos                  | cli      | float64  |            19.7 |           19.6 |
| cli_egresos_mes                  | cli      | float64  |            19.7 |           19.6 |
| cli_tot_patrimonio               | cli      | float64  |            19.7 |           19.6 |
| cli_tipo_cli                     | cli      | category |            19.7 |           19.6 |
| cli_genero_cli                   | cli      | category |            21.8 |           21.8 |
| cli_estado_civil                 | cli      | category |            25.9 |           25.6 |
| cli_tipo_vivienda                | cli      | category |            73.5 |           73.2 |
| cli_nivel_academico              | cli      | category |            63.4 |           63.8 |
| cli_ocup                         | cli      | category |            24   |           23.7 |
| cli_declarante                   | cli      | category |            19.7 |           19.7 |
| cli_segm                         | cli      | category |            19.7 |           19.6 |
| cli_subsegm                      | cli      | category |            22.2 |           21.7 |
| cli_region_of                    | cli      | category |            19.7 |           19.6 |
| cli_cli_actualizado              | cli      | category |            19.7 |           19.6 |
| cli_nicho                        | cli      | category |            62   |           61.5 |
| cli_antiguedad_meses             | cli      | float64  |            19.8 |           19.7 |
| cli_ratio_pasivo_activo          | cli      | float64  |            24.3 |           23.8 |
| cli_ratio_egreso_ingreso         | cli      | float64  |            23.8 |           23.3 |
| cli_corte_posterior              | cli      | int64    |             0   |            0   |
| lag_var_rpta_alt_ult             | lag      | float64  |            70.5 |           51.4 |
| lag_meses_desde_ultima_gestion   | lag      | float64  |            70.5 |           51.4 |
| lag_n_meses_vistos               | lag      | float64  |             0   |            0   |
| lag_n_aceptos                    | lag      | float64  |             0   |            0   |
| lag_tasa_acepto                  | lag      | float64  |            70.5 |           51.4 |
| lag_acepto_t1                    | lag      | float64  |            78.1 |           74.2 |
| lag_cant_alter_posibles_ult      | lag      | float64  |            70.5 |           51.4 |
| lag_cant_gestiones_ult           | lag      | float64  |            71.2 |           52.5 |
| lag_rpc_ult                      | lag      | float64  |            70.5 |           51.4 |
| lag_promesas_cumplidas_ult       | lag      | float64  |            70.5 |           51.4 |
| lag_cant_acuerdo_ult             | lag      | float64  |            71.2 |           52.5 |
| lag_min_mora_ult                 | lag      | float64  |            70.5 |           51.4 |
| lag_max_mora_ult                 | lag      | float64  |            70.5 |           51.4 |
| lag_dias_mora_fin_ult            | lag      | float64  |            70.5 |           51.4 |
| lag_vlr_obligacion_ult           | lag      | float64  |            70.5 |           51.4 |
| lag_vlr_vencido_ult              | lag      | float64  |            70.5 |           51.4 |
| lag_saldo_capital_ult            | lag      | float64  |            70.5 |           51.4 |
| lag_endeudamiento_ult            | lag      | float64  |            70.5 |           51.4 |
| lag_valor_cuota_mes_ult          | lag      | float64  |            70.5 |           51.4 |
| lag_pago_mes_ult                 | lag      | float64  |            70.5 |           51.4 |
| lag_porc_pago_cuota_ult          | lag      | float64  |            70.5 |           51.4 |
| lag_producto_ult                 | lag      | category |            70.5 |           51.4 |
| lag_producto_cons_ult            | lag      | category |            70.5 |           51.4 |
| lag_banca_ult                    | lag      | category |            70.5 |           51.4 |
| lag_segmento_ult                 | lag      | category |            70.5 |           51.4 |
| lag_aplicativo_ult               | lag      | category |            70.5 |           51.4 |
| lag_rango_mora_ult               | lag      | category |            70.5 |           51.4 |
| lag_desc_alternativa1_ult        | lag      | category |            70.5 |           51.4 |
| lag_alter_posible1_2_ult         | lag      | category |            70.5 |           51.4 |
| lag_marca_alt_rank_ult           | lag      | category |            70.5 |           51.4 |
| lag_alternativa_aplicada_agr_ult | lag      | category |            95.2 |           87.4 |
| lag_marca_pago_ult               | lag      | category |            70.5 |           51.4 |
| lagcli_n_oblig_gestionadas       | lagcli   | float64  |             0   |            0   |
| lagcli_n_aceptos                 | lagcli   | float64  |             0   |            0   |
| lagcli_tasa_acepto               | lagcli   | float64  |            62.5 |           37.3 |