# Plan de implementación del assessment de Spotter AI

## Objetivo y fuentes

Construir una aplicación Django + React que reciba ubicación actual, pickup, dropoff y horas usadas del ciclo, y genere ruta, paradas, descansos y hojas diarias de log. Este plan responde al pedido de analizar y planificar; no publica ni entrega el assessment.

Fuentes revisadas:
- `new-full-stack-dev-assessment.docx`: consigna completa.
- Guía FMCSA de abril de 2022: reglas HOS y ejemplos de registros diarios, especialmente páginas 6–11 y 15–19.
- https://www.youtube.com/watch?v=whxe41XYXS8 : transcripción automática completa y revisión visual cronológica de todas las secciones mediante capturas distribuidas desde 0:00 hasta 6:45. No se verificó cada fotograma ni el audio completo. El método, la cronología y una inconsistencia de inspección final se documentan en `VIDEO-ANALYSIS.md`.
- `blank-paper-log.png`: referencia visual del formulario.
- `fmsca-image.png`: índice con secciones destacadas de la guía.
- Resumen oficial vigente: https://www.fmcsa.dot.gov/regulations/hours-service/summary-hours-service-regulations

## Requisitos de la consigna

- Backend Django y frontend React.
- Inputs: Current location, Pickup location, Dropoff location, Current Cycle Used (Hrs).
- Ruta e información de paradas y descansos en un mapa con API gratuita.
- Hojas diarias dibujadas y completadas; múltiples hojas cuando corresponda.
- Requisito adicional del usuario: completar todos los campos de la plantilla y escribir debajo de la cuadrícula la ubicación correspondiente a cada cambio de estado.
- Conductor de carga, régimen 70 horas / 8 días, sin condiciones adversas.
- Repostar al menos una vez cada 1.000 millas.
- Una hora de pickup y una hora de dropoff.
- Buena UI/UX y exactitud de resultados.
- Entrega final: repositorio GitHub, versión alojada y Loom de 3–5 minutos.
- Máximo 4 días y 16 horas de trabajo según el mensaje de contratación.

## Decisiones propuestas y supuestos explícitos

La consigna no define hora de salida, estado previo, historial diario del ciclo, combustible inicial, duración del repostaje ni datos personales del conductor.

- Añadir fecha/hora de salida y zona horaria de la terminal como opciones con valores iniciales visibles. Usar la misma zona para todas las hojas, aunque la ruta cruce otras zonas.
- Suponer 10 horas consecutivas de descanso antes de la salida: límites de turno disponibles, pero conservar las horas previas del ciclo.
- Validar horas de ciclo entre 0 y 70, inclusive; aceptar decimales.
- Sin historial diario no se puede calcular con exactitud qué horas antiguas salen de la ventana móvil de ocho días. Conservar conservadoramente el saldo previo hasta un restart de 34 horas. Mostrar esta política en la UI y README. No inventar un recap diario.
- Cuando haga falta recuperar ciclo para continuar conduciendo, programar 34 horas consecutivas de descanso. Es una política del planificador; el restart es opcional en la normativa.
- Suponer combustible suficiente al salir y repostaje de 30 minutos, contabilizado como On Duty Not Driving. Mantener distancia desde el último repostaje entre ambos tramos y entre días.
- Descansos de 10/34 horas como Off Duty por defecto. No asumir que el camión tiene sleeper berth. Mostrar las cuatro filas de todos modos; Sleeper Berth puede tener cero horas.
- Sin split sleeper berth, excepciones short haul, equipo de dos conductores ni tráfico en tiempo real en el MVP.
- Paradas intermedias calculadas sobre la ruta como posiciones estimadas; no presentarlas como estaciones o estacionamientos verificados. La búsqueda de lugares reales queda fuera del alcance inicial.
- Incluir una sección de datos del log para conductor, carrier, oficina, terminal, vehículo y envío. Completar todos los campos aplicables antes de producir una hoja final. Usar N/A únicamente para campos realmente no aplicables; pedir los datos faltantes cuando sean necesarios, sin fabricar identidad, firma ni historial. El modo de ejemplo puede usar datos ficticios claramente identificados.
- El recap inferior requiere historial de horas por día. Ofrecer su entrada en la sección de datos del log y validar su coherencia con Current Cycle Used. El valor agregado del ciclo no permite deducir ese historial. No entregar un recap arbitrario para aparentar que está completo.
- Inventariar cada campo de la plantilla adjunta y asignarle una fuente: input del usuario, cálculo o N/A justificado. Si se incorpora una firma, debe ser aportada por el conductor; no simular certificación automática.
- Las hojas representan un plan estimado de viaje. Antes de la salida y después del final se completa Off Duty para cerrar cada día de 24 horas, según el supuesto declarado.

## Legibilidad del código

Requisito del usuario: el código debe ser fácil de entender, evaluar y modificar por otro programador.

- Usar nombres descriptivos en inglés para variables, funciones, clases y campos de API, coherentes con la entrega en inglés.
- Preferir `remaining_driving_seconds`, `cycle_used_seconds`, `distance_since_last_fuel_miles`, `pickup_location` y `daily_log_segments` frente a abreviaturas como `rem`, `hrs`, `dist`, `loc` o `segs`.
- Incluir unidades en nombres de cantidades cuando puedan confundirse: `_seconds`, `_hours`, `_miles`, `_meters`. Convertir unidades en puntos explícitos del código.
- Nombrar constantes por su significado, como `MAX_DRIVING_SECONDS_PER_SHIFT` y `REQUIRED_DAILY_REST_SECONDS`, evitando números sin explicación dentro del algoritmo.
- Usar funciones pequeñas con una responsabilidad concreta y nombres que expresen la acción, como `calculate_remaining_driving_time`, `schedule_required_rest` y `split_events_into_daily_logs`.
- Usar tipos explícitos para eventos, estados y respuestas; evitar diccionarios o estructuras ambiguas cuando un tipo sencillo aclare el contrato.
- Preferir flujo de control directo y condiciones claras. Evitar expresiones compactas, abstracciones innecesarias y funciones genéricas difíciles de seguir.
- Comentar el motivo de una regla HOS o de una decisión no evidente, sin repetir lo que ya expresa el código.
- Mantener vocabulario consistente entre backend, API y frontend: pickup, dropoff, driving, off duty, sleeper berth, on duty y cycle.
- Revisar nombres y responsabilidades como parte de la revisión final del código.

## Arquitectura

- React + TypeScript + Vite; estilos con Tailwind o CSS según familiaridad.
- Leaflet / React Leaflet para mapa y marcadores.
- Django + Django REST Framework para validación, integración de mapas y cálculo.
- OpenRouteService como candidato principal para geocodificación, geometría, duraciones e instrucciones. Permite perfil heavy vehicle y servicios gratuitos con cuotas: https://openrouteservice.org/services/ . Verificar cuota y restricciones del perfil con una ruta larga antes de desarrollar.
- API key solo en variables de entorno del servidor. Cliente selecciona ubicaciones resueltas, no envía nombres ambiguos sin confirmación.
- Proveedor de tiles configurable; atribución y política de uso: https://operations.osmfoundation.org/policies/tiles/ .
- Sin autenticación ni historial persistente en el MVP. Cálculo sin estado, sin necesidad de una base de datos de viajes.
- React sirve el resultado; SVG para líneas del log, encabezados y remarks, con vista de impresión. Puede incorporar la plantilla PNG como fondo, siempre que el contenido y la impresión sean legibles.
- Un solo repositorio con `backend/`, `frontend/`, README y configuración de despliegue.

## Flujo de datos y API

1. Buscar y seleccionar las tres ubicaciones, restringiendo el MVP a Estados Unidos continental.
2. Obtener los tramos actual → pickup y pickup → dropoff, con geometría, distancia, duración y pasos.
3. Convertir los tramos en unidades con tiempo y distancia acumulados.
4. Ejecutar planificador HOS; insertar pickup, dropoff, fuel y descansos.
5. Ubicar las paradas usando progreso sobre geometría y tiempos de pasos; no interpolar directamente entre las ciudades.
6. Resolver ciudad/estado para remarks mediante geocodificación inversa y caché cuando sea necesario. Si falla, indicar coordenadas y ubicación estimada; no inventar una localidad.
7. Dividir eventos por medianoche para construir hojas diarias sin reiniciar relojes HOS.
8. Devolver ruta, instrucciones, eventos, hojas, resumen y supuestos en una única respuesta.

Endpoints propuestos:
- `GET /api/locations?q=...`: candidatos de ubicación.
- `POST /api/trips/plan`: ubicaciones resueltas, cycle_used_hours, salida, zona y datos opcionales.
- `GET /api/health`: comprobación del backend.

Un evento contiene inicio, fin, duty_status, tipo, razón de parada, ubicación, progreso sobre ruta y millas recorridas. Las hojas contienen segmentos, totales por estado, millas, encabezados y remarks. Mapa, timeline y logs consumen esos mismos eventos; React no recalcula las reglas.

## Motor HOS

Implementarlo como funciones Python independientes de Django y del proveedor de rutas. Usar segundos enteros internamente, sin redondear viajes a bloques de 15 minutos. La cuadrícula puede marcar cuartos de hora sin alterar los eventos calculados.

Relojes:
- Conducción del turno: máximo 11 horas tras descanso válido.
- Ventana del turno: 14 horas transcurridas desde inicio de trabajo; una pausa normal no la detiene.
- Conducción desde la última interrupción consecutiva de al menos 30 minutos: máximo 8 horas antes de seguir conduciendo.
- Ciclo: Driving + On Duty Not Driving, con límite de 70 horas antes de continuar conduciendo.
- Millas desde repostaje: máximo 1.000 antes del siguiente tramo que lo excedería.

En cada paso, avanzar hasta el próximo límite relevante o el final de la actividad. Procesar eventos coincidentes para evitar pausas duplicadas o intervalos de cero duración.

Pickup y dropoff de una hora califican como interrupción de conducción de 30 minutos; no añadir otra pausa innecesaria. Un repostaje de 30 minutos también puede satisfacerla, pero sigue consumiendo ciclo. Un descanso diario puede satisfacer a la vez el requisito de pausa. El restart de 34 horas reinicia ciclo y límites de turno; 10 horas reinician turno, pero no ciclo.

Las 14 y 70 horas restringen seguir conduciendo; no son una prohibición general de hacer trabajo sin conducir. El motor debe conservar esta distinción al finalizar pickup/dropoff y al decidir si es necesario un descanso antes del próximo tramo de conducción.

## Pantalla

- Formulario compacto con las cuatro entradas obligatorias, opciones de salida y botón de cálculo.
- Estado inicial con un viaje de ejemplo seleccionable.
- Resumen: millas, conducción, tiempo total, llegada y cantidad de días.
- Mapa con ruta completa y marcadores diferenciados para pickup, entrega, fuel y descansos.
- Itinerario por día con hora, duración, lugar y motivo de cada parada; instrucciones de navegación accesibles.
- Hojas diarias con selector de día, cuatro estados, línea horizontal por intervalo y conexión vertical por cambio, totales y remarks.
- Debajo de cada cambio de estado, asociar una marca temporal con ciudad y estado y la actividad correspondiente. Para cambios en el mismo lugar, conservar la asociación de cada cambio aunque se agrupe visualmente la parada con un corchete. Evitar textos superpuestos.
- Botón imprimir; CSS de impresión con una hoja por página cuando sea posible.
- Tomar el método del video para el trazado: conexiones verticales, remarks asociados a cada cambio y corchetes opcionales para la duración de una parada física. Los puntos rojos del tutorial no forman parte obligatoria de la hoja.
- Mantener coherencia entre actividades y estados: toda inspección incluida debe consumir On Duty Not Driving, aunque el ejemplo del video omita gráficamente los seis minutos de su inspección final.
- Loading, errores de ubicaciones, límites de API y reintento claros. Sin presentar datos de ejemplo como resultados reales.
- UI y README en inglés para la evaluación.

## Verificación prioritaria

Tests del motor con rutas sintéticas para separar cálculo de fallos del proveedor:
- Viaje corto sin pausa obligatoria y pickup/dropoff de una hora.
- Exactamente 8 horas de conducción y un tramo que requiere continuar: pausa solo cuando corresponde.
- Pickup/fuel que satisfacen pausa y reinician contador de 8 horas.
- Límites de 11 horas y ventana de 14 horas, incluyendo on-duty intermedio.
- Descanso cruzando medianoche: relojes siguen, hojas se dividen.
- Cycle Used = 0, 69, 70 y valores inválidos; restart cuando hace falta conducir.
- Repostaje antes de exceder 1.000 millas, acumuladas entre pickup y entrega.
- Ruta de varios días y descanso de 34 horas que cruza fechas.
- Coincidencia de fuel, pausa y límite diario sin eventos duplicados.

Invariantes: eventos ordenados y sin solapamiento; cada hoja suma 24 horas; totales de millas coherentes; no conducción fuera de límites; no redondeo que produzca violaciones; ciclo cuenta carga, descarga y fuel.

Verificar además un flujo real desplegado, errores del proveedor, impresión y lectura en móvil. Añadir timeout, validación, límite de longitud de viaje y rate limiting básico a endpoints públicos.

Revisar también el inventario completo de campos de la plantilla: todos deben estar completados con datos calculados, suministrados o N/A cuando corresponda. Cada cambio de estado debe tener una ubicación asociada en Remarks debajo de la cuadrícula.

## Presupuesto de 16 horas en 4 días

| Día | Trabajo | Horas |
|---|---|---:|
| 1 | Confirmar supuestos, probar proveedor y despliegue mínimo | 1 |
| 1 | Estructura Django/React, endpoints y adaptador de rutas | 3 |
| 2 | Motor HOS, eventos y tests de límites | 4 |
| 3 | Formulario, mapa, itinerario y resumen | 2 |
| 3 | Hojas SVG, remarks e impresión | 2 |
| 4 | Integración y verificación de casos reales | 1.5 |
| 4 | Despliegue final y documentación | 1 |
| 4 | Guion y grabación Loom de 3–5 minutos | 0.5 |
| 4 | Reserva para errores | 1 |
| | Total | 16 |

Registrar tiempo real desde la revisión inicial y descontarlo de este presupuesto si cuenta para el assessment.

## Despliegue y entrega futura

Una opción simple es servir el build React desde Django con WhiteNoise en un único servicio. Otra es frontend en Vercel y Django en un servicio separado. Elegir tras el smoke test inicial, para evitar problemas de CORS al final.

Render permite servicios gratuitos, pero suspende tras 15 minutos sin tráfico y el arranque puede tardar aproximadamente un minuto: https://render.com/docs/free . Si se elige, la UI debe gestionar esa espera. No depender de SQLite persistente en disco efímero.

README: setup reproducible, variables de entorno, arquitectura, reglas implementadas, supuestos, limitaciones del proveedor, pruebas y enlaces finales. `.env.example` sin secretos y API key ausente del frontend y Git.

Loom: mostrar entradas y resultado, un viaje largo con descansos y varias hojas, el motor Python y sus tests, y explicar brevemente el supuesto de ciclo incompleto.

Prioridad de implementación: proveedor y backend desplegado → motor probado → integración de eventos → mapa → hojas → pulido y entrega. Extras como login, histórico, edición manual, lugares reales de parada y exportación PDF dedicada quedan para después del MVP.
