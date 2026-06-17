# TP2

## API de análisis de activos financieros — OpenAPI spec

Un contrato de API REST para un sistema que monitorea activos financieros
y registra las señales generadas por agentes de análisis técnico y de sentimiento.

Construido para la materia Introducción al Desarrollo de Software Asistido por IA
(CEIA — UBA), como ejercicio de diseño de contratos con ChatGPT Canvas.

---

### Qué documenta

El spec cubre dos recursos y siete endpoints:

**Activos** — los instrumentos financieros que el sistema monitorea (acciones y ONs).
Podés listarlos, agregar uno nuevo al seguimiento o darlo de baja.

**Análisis** — los resultados que depositan los agentes cuando terminan de correr.
Cada análisis pertenece a un activo y registra el tipo (técnico o sentimiento),
la señal generada (compra / venta / hold), el nivel de confianza del agente y
un resumen en texto.

El endpoint de resumen (`GET /activos/{id}`) devuelve el activo con las señales
más recientes de cada tipo ya incluidas, para que el frontend no tenga que
hacer tres llamadas para armar un dashboard.

---

### Cómo llegué acá

El dominio viene de mi proyecto de tesis de grado: un sistema que busca precios
de acciones y obligaciones negociables y corre agentes que hacen análisis técnico
y de sentimiento, generando tableros de noticias, briefings de datos y señales
de oportunidades de inversión. El TP fue una excusa para empezar a pensar en cómo
ese sistema podría exponer una API — algo que va a necesitar cuando crezca.

La jerarquía de recursos la dictó la lógica del sistema: los agentes trabajan
sobre tickers, no sobre carteras. El activo es el objeto central, y cada análisis
pertenece a uno — sin el activo no tiene contexto. Eso hizo que la decisión de
anidar fuera directa: si sacás un activo del seguimiento, sus análisis no tienen
razón de existir.

El endpoint de resumen apareció al pensar en cómo lo usaría un dashboard del sistema:
para mostrar la señal actual de cada activo habría que hacer tres llamadas separadas.
Un solo endpoint que devuelva el activo con las señales recientes ya incluidas
resuelve eso, y fue un buen ejercicio para verificar que el YAML era editable
sin tener que regenerarlo desde cero.

---

### Qué funcionó y qué no

El primer prompt generó más de lo que se pedía: el modelo separó solo los schemas
de creación (`ActivoCreate`, `AnalisisCreate`) — una buena práctica que no estaba
en la spec — y todas las respuestas de error ya incluían el schema `ErrorResponse`
correctamente referenciado. La jerarquía de recursos y los path parameters
también salieron consistentes desde el primer intento.

Lo que requirió corrección fue el campo `confianza`: salió con `format: float`
pero sin `minimum` ni `maximum`, y con una descripción ambigua que no dejaba claro
si era un valor entre 0 y 1 o un porcentaje. Es el tipo de error que el validador
de YAML no marca porque es sintácticamente válido, pero que importa cuando el código
que se genere a partir del spec tiene que validar los datos de entrada.

Otra cosa que apareció al revisar con más calma: el modelo había separado
`ActivoCreate` y `AnalisisCreate` por cuenta propia —  algo que no se le pidió —
pero esos schemas quedaron sin `description` en sus campos individuales.
En Swagger UI se nota enseguida: al expandir un POST los campos aparecen
sin ningún contexto. Se corrigió en el tercer prompt reutilizando las descripciones
que ya tenían los schemas de respuesta.

Dos comportamientos de Canvas que no estaban en el plan. El primero: al agregar
el endpoint de resumen, Canvas aplicó los cambios correctamente pero truncó el archivo
con marcadores `// existing code` para las secciones sin modificar. El YAML en pantalla quedó
incompleto y hubo que pedir explícitamente el archivo entero en un prompt separado.
Es un comportamiento que aparece cuando el canvas es largo y el modelo decide
"optimizar" la salida — la solución es pedirle el código completo sin omisiones.

El segundo: al pegar en Swagger aparecieron errores en dos rondas. Primero un error
de sintaxis genérico; después, tras una corrección de Canvas, errores más específicos:
el schema `Señal` usaba `ñ` (inválida en nombres de componentes OpenAPI) y `nullable: true`
no existe en OpenAPI 3.1. Canvas corrigió esos dos problemas, pero el bloque `servers:`
persistía malformateado en cada salida — generaba las entradas sin el prefijo `-` de lista
YAML, lo que invalidaba el archivo cada vez que se copiaba. Ese error estructural se
corrigió directamente en el archivo en lugar de seguir con rounds adicionales a Canvas.

Un tercer ajuste surgió al migrar `example` a `examples`: en OpenAPI 3.1 ese keyword
tiene dos formatos distintos según el contexto — array en propiedades de schema,
mapa nombrado con `value:` en parameters. El modelo los unificó en un solo formato,
lo que generó una nueva ronda de errores en Swagger que requirió otra corrección.

En esa misma salida también aparecieron decisiones que el modelo tomó mejor que la spec: modeló `ActivoDetalle` con `allOf` para extender `Activo` sin duplicar
campos, y extrajo `Señal` como schema independiente referenciado con `$ref`.

Lo más interesante fue verificar el YAML en Swagger UI antes de darlo por terminado.
Verlo renderizado hizo evidente que los campos, aunque bien tipados, no tenían ejemplos:
alguien que quiera probar un POST no tiene referencia de qué formato mandar.
Agregar ejemplos del mercado argentino transformó el spec de "contrato técnico"
a algo que cualquier miembro del equipo puede leer y usar directamente.

---

### Construido con

- OpenAPI 3.1 — formato del contrato
- ChatGPT Canvas — generación e iteración del YAML, una sola conversación, 11 prompts
- editor.swagger.io — verificación y renderizado del spec final
