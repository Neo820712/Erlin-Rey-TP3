# Prompts — Selector de asientos (Bad UI)

Secuencia de prompts usados en Gemini + Canvas para construir el artefacto.
Una conversación, en orden.

---

## Prompt 1 — Estructura base y selector de cantidad

Patrón 1 (describir el artefacto). El primer prompt define todo de una:
la estructura semántica con header/main/footer, el layout con Grid para el mapa
y Flexbox para el resto, el comportamiento base del flip automático de asientos
y la dificultad del selector de cantidad (los botones + y − se intercambian
después de cada click). La idea era largar todo el contexto de una para que
el modelo tuviera el cuadro completo antes de empezar a escribir código.

```
Creá un selector de asientos de cine en un solo archivo HTML con vanilla JS, sin frameworks.

Estructura con etiquetas semánticas: un <header> con el título, un <main> con dos zonas
— un panel superior para configurar la cantidad de asientos y el mapa de asientos debajo —
y un <footer> con el resumen y el botón Confirmar.

El panel de cantidad tiene un número grande en el centro y dos botones, uno para subir
y otro para bajar (rango de 1 a 6). La dificultad: cada vez que hacés click en cualquiera
de los dos botones, los botones + y − intercambian su posición, así que nunca sabés
cuál va a sumar y cuál va a restar en el próximo click.

El mapa es un grid de 8 filas × 6 columnas con etiquetas semánticas para las filas (A–H)
y columnas (1–6). Todos los asientos arrancan en verde con ✓. Cada 2 segundos, 6 asientos
al azar se ponen en rojo con ✗ y otros 6 vuelven a verde, sin parar.

Layout con Flexbox para el header y footer, Grid para el mapa de asientos.
Fondo oscuro, tipografía clara. El botón Confirmar arranca deshabilitado.
```

---

## Prompt 2 — Hold de 3 segundos y asientos seleccionados

Patrón 2 (iterar sobre el estado). Este prompt agrega el estado central
del artefacto: el hold en progreso, la lista de asientos seleccionados
y el contador contra el objetivo. Lo más importante fue aclarar que el flip
de 2 segundos también afecta a los asientos ya confirmados (los dorados),
porque sin eso una vez que seleccionabas un asiento quedaba a salvo y
la tensión desaparecía.

```
Agregá la mecánica de selección por hold y el tracking de cuántos asientos confirmó el usuario.

Estado a manejar: la cantidad objetivo (la que eligió el usuario), la lista de asientos
ya seleccionados, el asiento que se está intentando sostener ahora y el progreso del hold.

Ciclo evento → estado → DOM para el hold:
- mousedown en rojo: dialog "Este asiento está ocupado."
- mousedown en verde: iniciar hold, mostrar barra de progreso debajo del asiento
  que se llena en 3 segundos.
- Soltar antes: cancelar, mostrar "Soltaste antes de los 3 segundos."
- Si el cambio de 2 segundos convierte el asiento que estás sosteniendo en rojo:
  cancelar, mostrar "El asiento se ocupó justo cuando lo ibas a agarrar."
- Completar 3 segundos en verde: agregar el asiento a la lista de seleccionados,
  marcarlo en dorado con ★.

El cambio automático de 2 segundos también afecta a los asientos ya seleccionados
(los dorados): si un asiento seleccionado cae en el flip, vuelve a verde con ✓,
se saca de la lista de seleccionados, y se muestra un banner breve
"Perdiste el asiento [ID]. Tenés que volver a seleccionarlo."

El footer muestra en tiempo real cuántos asientos llevas vs cuántos necesitás.
Cuando la lista de seleccionados llega a la cantidad objetivo, mostrar el dialog
de confirmación (que se agrega en el próximo prompt).
```

---

## Prompt 3 — Flujo de confirmación

Patrón 2 otra vez (más iteración de estado, pero sobre el flujo final).
Este fue el prompt más largo porque encadena tres pasos: el dialog de
confirmación, el botón que se mueve y la pregunta matemática. Los tres
comparten el mismo ciclo evento → estado → DOM, por eso tenía sentido
meterlos juntos. Separarlo en tres prompts distintos hubiera fragmentado
demasiado el contexto.

```
Cuando el usuario completa la cantidad de asientos requerida, disparar el flujo
de confirmación en tres pasos:

Paso 1 — ¿Estás seguro?: mostrar un <dialog> con el resumen de los asientos elegidos
y dos botones, "Sí, confirmar" y "Cancelar". Si cancela, cerrar el dialog y que pueda
seguir (pero los asientos siguen expuestos al flip de 2 segundos mientras el dialog
está abierto, así que puede perder alguno antes de decidir).

Paso 2 — Botón fugitivo: cerrar el dialog anterior y mostrar un botón "CONFIRMAR RESERVA"
que cambia de posición aleatoria dentro de la ventana cada 500ms. El estado que cambia
es su posición (top/left en porcentajes aleatorios). El DOM refleja eso actualizando
el style del botón en cada intervalo. Si el usuario lo clickea, pasar al paso 3.

Paso 3 — Pregunta matemática: mostrar un <dialog> con una multiplicación aleatoria
de las tablas del 1 al 9 (por ejemplo "¿Cuánto es 6 × 7?"), un campo de texto para
la respuesta y un botón Enviar. Si la respuesta es incorrecta: limpiar el campo y
mostrar "Respuesta incorrecta. Intentá de nuevo." (sin cerrar el dialog, que el botón
fugitivo sigue corriendo de fondo). Si es correcta: cerrar todo y mostrar
"¡Reserva confirmada! Asientos: [lista]. Que disfrutes la película."
```

---

## Prompt 4 — Layout

Patrón 3 (arreglar el layout). Con el comportamiento ya funcionando,
este prompt se focalizó solo en la presentación visual: alinear el header
y footer con Flexbox, agregar los encabezados de fila y columna al grid,
y darle espacio al mapa para que no se sienta apretado.

```
Ajustá el layout de los contenedores principales con Flexbox:
- El <header> en una sola fila, título a la izquierda y un subtítulo o tagline a la derecha.
- El panel de cantidad centrado, con el número grande y los botones en fila con buen espacio
  entre ellos para que el intercambio de posición sea visible.
- El <footer> centrado, con el conteo de asientos y el botón Confirmar en fila.
- Suficiente padding en el <main> para que el mapa respire.

El mapa ya usa Grid; agregale encabezados de columna arriba y etiquetas de fila a la izquierda.
```

---

## Prompt 5 — Tematizar

Patrón 4 (tematizar y pulir). El último paso: sacar todos los colores y
espaciados hardcodeados a custom properties en :root para que todo el tema
viva en un solo lugar. También bordes redondeados y sombras para que el
resultado se vea prolijo — hay algo irónico en que una UI tan frustrante
sea visualmente agradable.

```
Extraé todos los colores y espaciados hardcodeados a custom properties en :root
y reemplazá cada uso por su variable. Asegurate de cubrir los colores de asiento disponible,
ocupado, seleccionado y el botón fugitivo. Pulí los bordes redondeados de asientos y dialogs,
y agregá una sombra sutil a los asientos.
```
