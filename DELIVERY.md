# Entrega de la evaluación

## Estado

- GitHub: https://github.com/leonel-cc/Spotter-Trip-Planner
- Aplicación pública: https://spotter-trip-planner-rosy.vercel.app
- Loom: pendiente de grabación por el candidato.

El código incluye Django, React, mapas, planificación HOS, hojas diarias completas, descarga PDF, impresión, exportación JSON, pruebas y configuración de despliegue. `PLAN.md` documenta el alcance inicial; `README.md` explica el comportamiento final y sus límites.

Los tres enlaces solicitados deben corresponder a recursos reales:

1. Repositorio GitHub del candidato con este código y su README.
2. Aplicación pública, accesible sin iniciar sesión.
3. Loom de 3–5 minutos grabado por el candidato.

No enviar enlaces de localhost como versión alojada. No incluir `.env`, API keys, documentos privados ni el entorno `.venv` en el repositorio. `.gitignore` ya excluye secretos y archivos generados.

## Guion sugerido de Loom (4 minutos)

- **0:00–0:30**: Presentarte y explicar: “Django calcula la ruta y el horario; React presenta mapa, itinerario y registros diarios”.
- **0:30–1:10**: Cargar el ejemplo, mostrar ubicación actual, pickup, drop-off y ciclo utilizado. Abrir historial y detalles. Explicar que el historial permite un recap real y que los datos del ejemplo son ficticios.
- **1:10–2:00**: Generar el plan. Mostrar millas, llegada, ruta, descanso nocturno y combustible. Abrir las instrucciones. Explicar el perfil de mapas realmente configurado y que los puntos de parada son estimados.
- **2:00–2:50**: Abrir ambas hojas. Señalar los cuatro estados, el total de 24 horas, los cambios verticales, la ubicación de cada cambio, los campos de transporte y el recap. Descargar el PDF y mostrar que contiene todas las hojas; también hay impresión y exportación JSON.
- **2:50–3:30**: Mostrar `scheduler.py`, `logs.py` y la separación del proveedor en `routing.py`. Destacar nombres descriptivos y unidades explícitas.
- **3:30–4:00**: Ejecutar las pruebas y explicar que el planificador elige un reinicio de 34 horas cuando se agota el ciclo de 70 horas. Cerrar con los supuestos documentados y el enlace público.

## Comprobación antes de enviar

- Ejecutar las pruebas y `npm run build`.
- En el sitio público probar una búsqueda, un viaje completo, ambas hojas y la impresión.
- Confirmar que el proveedor de mapas coincide con lo explicado en el Loom.
- Verificar que el README contiene instrucciones suficientes para otro programador.
- Comprobar los tres enlaces desde una ventana sin sesión.

## Texto para la entrega

Hi Ena,

I’ve completed the Full Stack Developer assessment. The application uses Django and React to generate a route, HOS-aware stops, and filled daily log sheets with location remarks and cycle recaps.

- GitHub: https://github.com/leonel-cc/Spotter-Trip-Planner
- Hosted application: https://spotter-trip-planner-rosy.vercel.app
- Loom walkthrough: [insert the actual Loom URL]

Setup instructions, tests, and assumptions are documented in the repository README.

Thank you,
Leonel
