# Análisis del llenado del log mostrado por Schneider

Fuente: https://www.youtube.com/watch?v=whxe41XYXS8

## Alcance de la revisión

Se recorrieron cronológicamente todas las secciones del video, desde 0:00 hasta el cierre de 6:45, con capturas a intervalos de 10–15 segundos y una revisión adicional de la hoja completa. Se contrastaron las imágenes con la transcripción automática completa. Esta revisión cubre la demostración y su explicación; no equivale a escuchar el audio completo ni a inspeccionar cada fotograma.

## Qué explica cada sección

| Tiempo aproximado | Contenido |
|---|---|
| 0:00–0:30 | Introducción y propósito del registro |
| 0:30–0:50 | Fecha, período de 24 horas y cuadrícula con marcas cada 15 minutos |
| 0:50–1:24 | Cuatro estados: Off Duty, Sleeper Berth, Driving y On Duty Not Driving |
| 1:24–1:45 | Remarks con ciudad, estado y actividad |
| 1:45–2:24 | Encabezado, conductor, firma, vehículo, terminal y envío |
| 2:24–3:40 | Inicio a las 06:30, inspección hasta las 07:00, cambio a conducción y corchete de parada |
| 3:40–4:12 | Conducción hasta las 08:30 y trabajo en balanza hasta las 09:00 |
| 4:12–4:44 | Conducción hasta las 13:00 y pausa hasta las 13:30 |
| 4:44–5:14 | Conducción hasta las 17:30, Off Duty hasta las 19:00 y Sleeper Berth hasta medianoche |
| 5:14–5:34 | Millas del conductor y del camión |
| 5:34–6:22 | Totales por estado, suma de 24 horas y total trabajado de 10,5 horas |
| 6:22–6:46 | Cierre |

## Cómo se completa la hoja

Primero se registra la fecha y la información del conductor, carrier, terminal, tractor, remolque y envío. En el ejemplo no hay segundo conductor; los campos no aplicables se completan con N/A. La firma es una certificación del conductor y no debe generarse automáticamente como si ya hubiera firmado.

La cuadrícula representa un día calendario completo. El eje horizontal es el tiempo y cada fila es un estado. Se dibuja una línea horizontal por cada intervalo y una línea vertical en la hora exacta de cambio. La conexión vertical no consume tiempo. Solo existe un estado a la vez.

Las cuatro filas se interpretan así:

1. Off Duty: fuera de servicio, sin realizar trabajo.
2. Sleeper Berth: tiempo en la litera del camión; identifica un lugar concreto, no cualquier descanso.
3. Driving: conducción del vehículo comercial.
4. On Duty Not Driving: trabajo como inspección, pesaje, carga, descarga y combustible.

Cada cambio de estado requiere una ubicación en Remarks. El ejemplo agrupa las entradas y salidas de una misma parada con un corchete horizontal debajo de la cuadrícula. De él sale una línea diagonal con ciudad/estado y actividad. El corchete muestra cuánto tiempo no se movió el camión en ese lugar; no agrega horas ni reemplaza los estados de la cuadrícula.

El video usa puntos rojos como ayuda para explicar el dibujo. Son un recurso didáctico, no un dato necesario del log. Los textos diagonales tampoco tienen que reproducirse exactamente si otra disposición conserva la asociación entre hora, lugar y actividad y resulta más legible.

## Cronología del ejemplo dibujado

| Inicio | Fin | Estado | Actividad o ubicación |
|---|---|---|---|
| 00:00 | 06:30 | Off Duty | Antes del comienzo del trabajo |
| 06:30 | 07:00 | On Duty Not Driving | Green Bay, WI; pre-trip / TIV |
| 07:00 | 08:30 | Driving | Primer tramo |
| 08:30 | 09:00 | On Duty Not Driving | Fond Du Lac, WI; Scale |
| 09:00 | 13:00 | Driving | Segundo tramo |
| 13:00 | 13:30 | Off Duty | Paw Paw, IL; pausa de 30 minutos |
| 13:30 | 17:30 | Driving | Tercer tramo |
| 17:30 | 19:00 | Off Duty | Edwardsville, IL; comienzo del descanso según el gráfico |
| 19:00 | 24:00 | Sleeper Berth | Descanso en litera |

Los intervalos de esta tabla reproducen el gráfico demostrado, no resuelven la inconsistencia de inspección final señalada abajo.

| Estado | Total del ejemplo |
|---|---:|
| Off Duty | 8 h 30 min |
| Sleeper Berth | 5 h |
| Driving | 9 h 30 min |
| On Duty Not Driving | 1 h |
| Total del día | 24 h |

El ejemplo registra 472 millas. Como no tiene otro conductor, las millas conducidas por él y las recorridas por el camión coinciden. Para el ciclo, Driving + On Duty Not Driving = 9,5 + 1 = 10,5 horas. No confundir 10 horas 30 minutos con 10,30 horas decimales.

## Precauciones al trasladar el ejemplo al proyecto

La anotación en Edwardsville incluye `Post-trip/TIV-6 min`, pero el gráfico pasa directamente de Driving a Off Duty a las 17:30 y el total On Duty contiene solo las dos medias horas previas. No representa esos seis minutos de inspección. Si nuestra aplicación incluye esa actividad, debe registrarla como On Duty Not Driving y ajustar el comienzo del descanso, el ciclo y los totales. No copiar esa omisión.

La hoja solo muestra el descanso hasta medianoche. Las 1,5 horas Off Duty más 5 horas Sleeper Berth suman 6,5 horas en ese día; no prueban por sí solas que ya se completó el descanso de 10 horas. Para calcular la siguiente conducción hay que continuar el intervalo en la hoja siguiente.

El formulario del video es propio de Schneider y contiene campos adicionales, incluida una sección canadiense y un reporte de inspección. La plantilla adjunta al assessment es otra. Debemos trasladar el método de llenado a la plantilla solicitada, sin copiar campos exclusivos de Schneider ni cambiar el régimen indicado de 70 horas / 8 días.

Los datos de identidad, carrier, firma y envío del video son datos del ejemplo. No son los datos del usuario ni valores de producción de la aplicación.

## Consecuencias para el código

- Generar segmentos con `start_time`, `end_time`, `duty_status`, `location` y `activity_description`.
- Representar paradas físicas por separado cuando contengan varios estados, para poder dibujar el corchete y asociar sus remarks.
- Mantener el orden de las cuatro filas y las marcas de 15 minutos, con posición temporal proporcional a la duración real.
- Conservar intervalos exactos; una marca de cuadrícula de 15 minutos no justifica redondear una actividad de seis minutos.
- Calcular totales a partir de los segmentos, nunca desde textos de remarks.
- Dividir cada día a medianoche y mantener la continuidad del estado y de los relojes entre hojas.
- Verificar que cada día suma 24 horas y que Driving + On Duty Not Driving coincide con las horas trabajadas.
- Usar esta cronología como referencia de renderizado. Si se reproduce literalmente el gráfico para una prueba, documentar la omisión de la inspección; no usarlo como ejemplo normativo completo.
- Mantener Off Duty como descanso predeterminado del MVP; usar Sleeper Berth solo cuando se indique que el descanso ocurre en la litera.

## Aplicación a la plantilla adjunta

- Fecha: fecha del día representado.
- From / To: origen y destino pertinentes al viaje, evitando confundirlos con las remarks de cada parada.
- Millas: distancia conducida en ese día, distribuida desde los eventos de ruta.
- Vehículo, carrier, oficina y terminal: datos suministrados en el formulario; completarlos antes de generar la hoja final, sin inventarlos.
- Cuadrícula: segmentos temporales en las cuatro filas con conexiones verticales.
- Total Hours: sumatoria por estado y comprobación de 24 horas.
- Remarks: cambios y paradas con hora, ciudad/estado y motivo.
- Shipping Documents: información de envío suministrada; usar N/A solo si realmente no aplica.
- Recap: requiere historial diario. El dato agregado Current Cycle Used no permite completar fielmente todas las casillas del recap de la plantilla; solicitar el historial necesario en lugar de repartir arbitrariamente esas horas.

Requisito confirmado por el usuario: todos los campos de la plantilla deben estar completos. Inventariar los campos y validar su fuente antes de producir la hoja final. Cada cambio de estado debe quedar asociado a su ubicación debajo de la cuadrícula, incluso cuando dos cambios ocurran en la misma parada.
