# TP1


## Bad UI — Selector de asientos

Un selector de asientos de cine que es completamente funcional 
y deliberadamente insoportable.

Construido para la materia Introducción al Desarrollo de Software Asistido por IA 
(CEIA — UBA), como ejercicio de vibe coding con ChatGPT Canvas.

---

### Qué hace

Podés reservar entre 1 y 6 asientos. Para confirmar la reserva tenés que:

1. Elegir cuántos asientos querés (con botones que intercambian su posición 
   después de cada click)
2. Seleccionar cada asiento sosteniéndolo durante 3 segundos sin soltar
3. Los asientos cambian de disponible a ocupado cada 2 segundos — incluso 
   los que ya seleccionaste, que vuelven a estar disponibles si caen en el flip
4. Cuando tenés todos, confirmar antes de que el tiempo te juegue en contra
5. Clickear un botón que salta por la pantalla cada medio segundo
6. Responder una multiplicación aleatoria de las tablas del 1 al 9

Si todo sale bien, la reserva se confirma. Si en algún paso cometés un error, 
volvés atrás.

---

### Cómo llegué acá

La idea original era simple: un mapa donde todos los asientos aparecen disponibles 
pero al clickear cualquiera te dice que está ocupado. Entendí rápido que eso no es 
una bad UI, es un muro — el usuario lo descubre en dos segundos y deja de intentar.

El primer cambio fue agregar el flip automático de colores para que pareciera que 
algunos estaban libres. Mejor visualmente, igual de imposible en la práctica.

El giro real fue hacer la selección posible pero costosa: sostener el click 3 segundos 
sobre un asiento verde. Ahí apareció la tensión. Pero calibrar los tiempos fue lo más 
difícil: con flip cada 1 segundo era imposible completar el hold, con 5 segundos era 
demasiado fácil. Dos segundos fue el punto donde se siente injusto pero tiene solución.

Después agregué la cantidad de asientos y que los ya seleccionados también pudieran 
perderse en el flip. Eso cambió todo — ya no era conseguir un asiento, era defenderlo 
mientras conseguías los demás. Para el selector de cantidad, la idea de que los botones 
"+" y "−" intercambien posición después de cada click fue la que mejor funcionó: dificulta 
sin bloquear.


El flujo de confirmación vino al final. El botón que se mueve por la pantalla requirió 
ajuste: a 200ms era imposible de clickear, a 500ms es difícil pero factible. 
La pregunta matemática fue el toque final — algo que rompe el ritmo justo cuando 
creés haber superado todo, pero lo suficientemente simple para que el artefacto 
siga siendo funcional.

---

### Qué funcionó y qué no

Funcionó bien la combinación de tiempos: el flip de 2 segundos contra el hold de 
3 segundos crea una carrera que se siente injusta pero tiene solución. 
También funcionó hacer que los asientos seleccionados fueran vulnerables — 
sin eso la segunda mitad del juego no tenía tensión.

Lo que costó más fue encontrar la velocidad correcta para el botón fugitivo. 
Demasiado rápido y nadie lo puede clickear, con lo cual no es una mala UI 
sino una UI rota. La diferencia entre frustrante y directamente imposible 
fue más delgada de lo esperado, y requirió varios ajustes.

También se probó con rangos de cantidad de asientos más grandes (hasta 10) 
pero resultaba en sesiones demasiado largas para una demo de 5 minutos. 
Seis asientos como máximo fue el límite que permitía que alguien completara 
el artefacto (con suerte) en el tiempo de presentación.

---

### Construido con

- HTML semántico, CSS con custom properties, vanilla JavaScript
- ChatGPT Canvas — una sola conversación, 5 prompts en orden
- Sin frameworks, sin dependencias externas

