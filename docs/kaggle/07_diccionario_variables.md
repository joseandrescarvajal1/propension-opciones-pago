<!-- Fuente: Metadata.xlsx adjunto en Kaggle. -->

# Diccionario de variables

## base_pivot_var_rpta_alt_enmasca

| name | type | comment |
|---|---|---|
| nit_enmascarado | bigint | numero identificador del cliente enmascarado |
| num_oblig_orig_enmascarado | bigint | Numero identificador de obligacion original de la obligacion |
| num_oblig_enmascarado | bigint | Numero identificador de obligacion actual |
| fecha_var_rpta_alt | bigint | Fecha mes de la variable respuesta  |
| var_rpta_alt | tinyint | Valor de la variable respuesta 1: acepto opcion de pago, 0: No acepto opcion de pago |
| tipo_var_rpta_alt | string | Tipo de variable respuesta, a_uno_tipo_1: acepta y aplica alternativa b_uno_tipo_2: acepta pero no se aplica c_uno_tipo_3: interesado mas no acepta (e) d_cero_tipo_1: ofrece pero no acepta e_cero_tipo_2: no sabemos si le ofrecen alternativa |
| banca | string | Tipo de banca o macrosegmento |
| segmento | string | Tipo de segmento del cliente |
| producto | string | tipo de producto del cliente |
| producto_cons | string | tipo del producto detallado |
| aplicativo | string | tipo de aplicativo del producto |
| min_mora | bigint | minimo de mora en el mes de la variable respuesta |
| max_mora | bigint | maximo de mora en el mes de la variable respuesta |
| dias_mora_fin | bigint | altura de mora en el ultimo dia del mes de la variable respuesta |
| rango_mora | string | rango de mora en el mes del clliente |
| vlr_obligacion | double | valor desembolsado de la obligacion, TDC es el cupo |
| vlr_vencido | double | Valor vencido o que se encuentra en mora actualmente |
| saldo_capital | double | Saldod e la obligacion actualmente |
| endeudamiento | double | valor del endeudamiento del cliente |
| desc_alternativa1 | string | descripcion de primera opcion de pago preaprobada |
| desc_alternativa2 | string | descripcion de segunda opcion de pago preaprobada |
| desc_alternativa3 | string | descripcion de tercera opcion de pago preaprobada |
| cant_alter_posibles | bigint | cantidad de opciones de pago preaprobadas |
| alter_posible1_2 | string | codigo de primera opcion de pago preaprobada |
| alter_posible2_2 | string | codigo de segunda opcion de pago preaprobada |
| alter_posible3_2 | string | codigo de tercera opcion de pago preaprobada |
| cant_gestiones | bigint | cantidad de gestiones en el mes realizadas |
| cant_gestiones_binario | tinyint | si el cliente tuvo gestiones o no |
| rpc | int | cantidad de contactos efectivos con el cliente  |
| promesas_cumplidas | bigint | cantidad de promesas de pago cumplidas en el mes |
| cant_promesas_cumplidas_binario | tinyint | si el cliente cumplio promesa de pago en el mes o no |
| cant_acuerdo | bigint | cantidad de acuerdos de pago en el mes |
| cant_acuerdo_binario | tinyint | Si el cliente hizo un acuerdo de pago ene l mes o no  |
| descripcion_ranking_mejor_ult | string | Cual fue la primera mejor gestion del cliente |
| descripcion_ranking_post_ult | string | Cual fue la  mejor gestion del cliente despues de la primera |
| marca_alt_rank | string | descripcion de la mejor opcion de pago acordada con el cliente en su obligacion en el mes |
| marca_alt_apli | string | Variable binaria si el cliente al final se  le aplico la alternativa despues de haber aceptada para su obligacion en el mes |
| valor_cuota_mes | double | valor de la cuota del mes del cliente |
| pago_cuota | double | valor pagado en el mes a la obligacion antes de vencerse  |
| porc_pago_cuota | double | porcentaje de pago cuota que hizo |
| pago_mes | double | valor total que pago en mes incluyendo despues de vencerse |
| porc_pago_mes | double | porcentaje de pago mes que hizo |
| pagos_tanque | string | si el cleinte hizo algun tipo de pago |
| marca_debito_mora | string | si se le realizo algun debito de mora |
| alternativa_aplicada_agr | string | Que tipo de opcion de pago se le aplico finalmente al cliente |
| marca_agrupada_rgo | string | Otra tipologia mas general de la opcion de pago aplicada |
| marca_pago | string | que tipo de abono hizo en el mes |
| marca_alternativa | string | si el cliente acepto una opcion de pago |
| marca_alternativa_orig | string | si el cliente acepta una opcion de pago originalmente |

## probabilidad_oblig_base_hist_en

| name | type | comment |
|---|---|---|
| nit_enmascarado | bigint | numero identificador del cliente enmascarado |
| num_oblig_enmascarado | bigint | Numero identificador de obligacion actual |
| fecha_corte | bigint | año y mes de la informacion de la tabla |
| lote | tinyint | tipo de lote de priorizacion de la obligacion del cliente entre mas menor es mas prioritario  |
| prob_propension | double | Probabilidad de hacer un apgo en el proximo mes |
| prob_alrt_temprana | double | Probabildiad de entrar en mora en la obligacion en el proximo mes |
| prob_auto_cura | double | Probabilidad de que se ponbga aldia el cliente dado que esta en una mora menor a 15 dias sin ningun tipo de gestion directa o interaccion humana |

## master_customer_data_enmascarad

| name | type | comment |
|---|---|---|
| nit_enmascarado | bigint | numero identificador del cliente enmascarado |
| cod_tipo_doc | string | codigo de tipo de documentod el cliente |
| tipo_cli | varchar(200) | tipo de cliente en el banco |
| ctrl_terc | varchar(200) | estado del cleinte en el banco  |
| genero_cli | string | genero del cliente |
| ano_nac_cli | int | año de nacimiento del cliente |
| edad_cli | int | edad del cliente |
| estado_civil | varchar(200) | estado civil del cliente |
| tipo_vivienda | varchar(200) | tipo de vivienda del cliente |
| num_hijos | decimal(2,0) | numero de hijos del cliente |
| personas_dependientes | decimal(2,0) | cantidad de personas dependientes |
| nivel_academico | varchar(200) | nivel academico del cliente |
| ocup | varchar(200) | ocpuacion del cliente |
| act_econom | varchar(200) | actividad economica del cliente |
| sector | varchar(200) | sector del cliente |
| subsector | varchar(200) | subsector del cliente |
| declarante | string | si es marcado como declaracte de renta |
| total_ing | decimal(15,2) | total de ingresos mensuales estimados del cliente |
| tot_activos | decimal(15,2) | total de valor de activos del cliente en bancolombia |
| tot_pasivos | decimal(15,2) | total de pasivos o deudas del cliente en bancolombia |
| origen_fondos | varchar(200) | origenden de los ingresos del cliente |
| f_vinc | decimal(8,0) | fecha de vinculacion del cliente |
| f_ult_mantenimiento | decimal(8,0) | fecha de ultimo mantenimiento de esta informacion  |
| canal_actualizacion | char(3) | canal de actualizacion de la informacion  |
| cli_actualizado | string | si es un cliente q se encuentra con la informacion actualizada |
| segm | varchar(200) | descripcion del segmento del cliente |
| subsegm | varchar(200) | descripocion del subsegmento del cliente |
| nicho | string | cicho o caracteristica especial del cliente |
| region_of | string | region de vinculacion del cliente |
| nombre_dpto_dirp | string | nombre del departamento de cinculacion del cliente |
| egresos_mes | decimal(15,2) | cantidad de egresos estimados del cliente de manera mensual  |
| tot_patrimonio | decimal(15,2) | total de patrimanio del cliente |
| ciiu | string | descripcion del codigo ciiu del cliente |
| smmlv | double | salario minimo del mes de la informacion  |
| year | int | año de la informacion  |
| month | int | mes de la informacion |
| ingestion_day | int | dia de la informacion |

## maestra_cuotas_pagos_mes_hist_e

| name | type | comment |
|---|---|---|
| nit_enmascarado | bigint | numero identificador del cliente enmascarado |
| num_oblig_enmascarado | bigint | Numero identificador de obligacion actual |
| fecha_corte | bigint | año mes de la informacion |
| producto | string | descripcion producto del cleinte o obligacion |
| aplicativo | string | aplicativo de informacion del producto |
| segmento | string | segmento del cliente |
| valor_cuota_mes | double | valor de la cuota correspondiente del mes en la obligacion  |
| pago_total | double | Valor del pago total realizado por el cleinte en el mes |
| fecha_pago_minima | double | Fecha que realizo el valor de pago minimo  |
| fecha_pago_maxima | double | Fecha que realizo el ultimo valor de pago  |
| porc_pago | double | porcentaje de pago de la cuota realizado en el mes |
| marca_pago | string | si el cliente realizo pago o no |
| ajustes_banco | string | Si tuvo algun ajuste realizado por el banco en su cuota de pago  |
