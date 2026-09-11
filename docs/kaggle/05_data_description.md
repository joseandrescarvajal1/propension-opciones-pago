<!-- Fuente: Kaggle, competencia prueba-analitica-modelo-opciones-de-pago-season-3, pestaña 'data-description'. Texto copiado tal cual. -->

Se entregarán bases de datos en formato csv (separados con comas y codificación utf-8) con n columnas. En los adjuntos se encuentra el diccionario de variables en donde se hace una descripción de la mayoría de las columnas de cada tabla. 

## Descripción información

**prueba_op_base_pivot_var_rpta_alt_enmascarado_trtest:**Base de datos que contiene la variable respuesta y las principales características de la gestión, de resultados del pago y de características de las opciones de pago habilitadas para el cliente en el mes de gestión o de evaluación de la variable respuesta.

**prueba_op_probabilidad_oblig_base_hist_enmascarado_completa:** Información asociada con los resultados de los modelos analíticos existentes para la cobranza de Bancolombia. 
Alerta temprana: describe la probabilidad que un cliente en su obligación entre en mora en su próxima fecha de pago
Auto cura: Describe la probabilidad de que un cliente que esté en mora en su obligación pague por sí solo, o sin ninguna gestión directa (llamada)
Propensión de pago: Describe la probabilidad de que un cliente que esté en mora en su obligación haga un pago a su obligación.

**prueba_op_master_customer_data_enmascarado_completa:** Información asociada a las características generales del cliente o demográficas de forma mensual.

**prueba_op_maestra_cuotas_pagos_mes_hist_enmascarado_completa:** Información que describe el comportamiento de pagos del cliente en sus obligaciones a lo largo del tiempo.

## Files

*   **prueba_op_base_pivot_var_rpta_alt_enmascarado_trtest.csv*** - Información de variable objetivo para train
*   **prueba_op_base_pivot_var_rpta_alt_enmascarado_oot*** - lista de clientes y obligaciones a calificar en 2024/01
*   **prueba_op_probabilidad_oblig_base_hist_enmascarado_completa.csv*** - Información de probabilidades de modelos desarrollados
*   **prueba_op_master_customer_data_enmascarado_completa.csv*** - información demográfica cliente
*   **prueba_op_maestra_cuotas_pagos_mes_hist_enmascarado_completa.csv*** - información de pagos obligaciones

*   **sample_submission.csv** - Una muestra de cómo debería ser el archivo de sumisión
         Este archivo tiene una columna ID que se compone de  las columnas nit_enmascarado, 
         num_oblig_orig_enmascarado, num_oblig_enmascarado concatenado por el caracter "#"
*   **metadata.xlsx** - Metadata

\* El detalle de la descripción de la información se encuentra en la página general del reto.
