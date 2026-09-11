<!-- Fuente: Kaggle, competencia prueba-analitica-modelo-opciones-de-pago-season-3, pestaña 'Evaluation cuantitativa parte 1 prueba'. Texto copiado tal cual. -->

La métrica para evaluar este modelo estará basada en el **F1 score** para el mes de **enero de 2024**, se considera que es una muestra fuera de tiempo. La cantidad de sumisiones posibles es una vez al día y solo podrán hacer sobre una muestra del 30% de los clientes totales, de la muestra fuera de tiempo.
El formato del archivo que deben entregar y calificar se describe a continuación

## Archivo de sumisión
Para cada combinación cliente-obligación entregada en el archivo de calificación de la muestra fuera de tiempo, se debe predecir la variable respuesta llamada (var_rpta_alt), que será un valor de cero o uno. El archivo deberá contener el siguiente formato:

ID						var_rpta_alt
250631#175418#912682	1
217161#1054045#26297	0
443187#754930#325412	1
224370#328405#754753	0
etc.

Donde, la columna ID se compone de las columnas nit_enmascarado, num_oblig_orig_enmascarado, num_oblig_enmascarado concatenado por el carácter "#"
