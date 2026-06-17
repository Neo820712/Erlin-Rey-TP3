# Prompts — API de análisis de activos financieros

Secuencia de prompts usados en ChatGPT Canvas para construir el OpenAPI YAML.
Una conversación, en orden.

---

## Prompt 1 — Artefacto base

Patrón 1 (describir el artefacto). El primer prompt da el contexto completo de una:
dominio, recursos con sus tipos, jerarquía de endpoints y esquema de errores.
La idea era que el modelo tuviera el cuadro entero antes de empezar a generar el YAML,
para evitar que tomara decisiones de diseño que después habría que deshacer.
Se eligió abrir describiendo el sistema real que tiene por detrás —agentes de análisis,
datos de mercado— para que el modelo entendiera el propósito antes de ver la spec.

```
Tengo un sistema que monitorea activos financieros — acciones y obligaciones negociables —
y corre agentes que hacen análisis técnico y de sentimiento sobre cada uno. Los agentes
ya funcionan, pero no tenemos nada documentado del backend. Antes de arrancar con la
implementación quiero tener el contrato de la API en un archivo OpenAPI para que sea
la referencia de todo lo que viene: qué endpoints existen, qué entra, qué sale,
qué errores pueden pasar.

Los dos recursos principales son el activo en sí (lo que estamos monitoreando)
y el análisis (el resultado que deposita el agente cuando termina de correr). El análisis
siempre pertenece a un activo — no tiene sentido fuera de él — así que la jerarquía
tiene que reflejarse en las URLs.

Necesito que armes un openapi.yaml en versión 3.1 para la API de análisis de activos financieros.

recursos:
  Activo(id: integer, ticker: string, nombre: string,
         tipo: enum[accion, ON], mercado: enum[BYMA, NYSE, NASDAQ])
  Analisis(id: integer, tipo: enum[tecnico, sentimiento],
           señal: enum[compra, venta, hold], confianza: number,
           resumen: string, created_at: date-time)

endpoints:
  GET    /activos                            → 200 array<Activo>
  POST   /activos                            → 201 Activo, 400 body inválido
  DELETE /activos/{id}                       → 204, 404 activo no encontrado
  GET    /activos/{id}/analisis              → 200 array<Analisis>, 404 activo no encontrado
  POST   /activos/{id}/analisis              → 201 Analisis, 400 body inválido, 404 activo no encontrado
  DELETE /activos/{id}/analisis/{analisisId} → 204, 404 análisis no encontrado

Errores con schema { message: string }. Todos los schemas con type, required y format donde aplique.
Abrilo en canvas.
```

---

## Prompt 2 — Corrección de confianza

El YAML que devolvió Canvas en el Prompt 1 tenía más de lo esperado: el modelo separó
solo los schemas de creación (`ActivoCreate`, `AnalisisCreate`) sin que se lo pidiera,
y todas las respuestas de error ya incluían el schema `ErrorResponse` con el campo
`message`. Lo único que faltaba era acotar el rango del campo `confianza` — salió con
`format: float` pero sin `minimum` ni `maximum`, y la description decía
"ej. 0.0 a 1.0, o porcentaje", que es ambiguo. El prompt 2 corrige solo eso.

```
Una corrección antes de seguir. El campo confianza en el schema Analisis
quedó con format: float pero sin restricciones de rango. Semánticamente
ese valor siempre es entre 0 y 1 — representa el nivel de certeza del agente,
no un porcentaje de 0 a 100. Hay que forzarlo en el spec.

En el schema Analisis (y también en AnalisisCreate), el campo confianza:
  type: number
  format: float
  minimum: 0
  maximum: 1
  description: Nivel de certeza del agente en la señal (0 = mínimo, 1 = máximo)
```

---

## Prompt 3 — Descriptions en schemas de creación

Revisando el output del Prompt 2,  el modelo había separado
`ActivoCreate` y `AnalisisCreate` espontáneamente (buena práctica), pero esos schemas
no tenían `description` en sus campos individuales, a diferencia de `Activo` y `Analisis`
que sí los tenían. En Swagger UI se nota: al hacer un POST los campos aparecen sin
ningún contexto de qué se espera en cada uno.

```
Revisando el YAML noto que los schemas de creación (ActivoCreate y AnalisisCreate)
no tienen description en sus campos individuales, a diferencia del schema Activo
que sí los tiene. Si alguien los mira en Swagger no va a saber qué se espera
en cada campo al momento de hacer un POST.

Agregá description a cada propiedad de ActivoCreate y AnalisisCreate,
usando las mismas descripciones que ya tiene el schema Activo/Analisis
donde el campo coincida.
```

---

## Prompt 4 — Endpoint de resumen (iteración nueva)

Con los schemas bien documentados, el YAML base estaba completo. Revisándolo como
si fuera el frontend el que lo consume, apareció un problema de uso: para mostrar
en un dashboard la señal actual de cada activo había que hacer tres llamadas por separado
— traer el activo, traer sus análisis técnicos, traer sus análisis de sentimiento — y
quedarse con el más reciente de cada tipo. Eso es demasiado para una pantalla que
necesita mostrar muchos activos a la vez. Canvas devolvió el YAML con los cambios
aplicados pero truncó la salida usando marcadores `// existing code` para omitir
las secciones sin cambios — lo que hizo que el archivo en pantalla quedara incompleto
y no pudiera usarse directamente.

```
Pensando en cómo lo va a usar el frontend me di cuenta de que falta algo importante:
un endpoint que devuelva un activo con las señales más recientes de cada tipo de análisis
ya incluidas. Ahora mismo para saber qué dicen los agentes sobre GGAL hoy tenés que
hacer tres llamadas: traer el activo, traer sus análisis técnicos y quedarte con el más
reciente, traer sus análisis de sentimiento y quedarte con el más reciente.
Eso es innecesariamente pesado para una pantalla de dashboard.

Agregá GET /activos/{id} sin modificar los endpoints existentes.

Response 200: schema Activo más campo extra señales_recientes:
  type: object
  properties:
    tecnico:
      allOf: [{ $ref: '#/components/schemas/Señal' }]
      nullable: true
      description: señal más reciente del análisis técnico, null si no hay
    sentimiento:
      allOf: [{ $ref: '#/components/schemas/Señal' }]
      nullable: true
      description: señal más reciente del análisis de sentimiento, null si no hay

Definí Señal en components/schemas: type: string, enum: [compra, venta, hold]
Response 404: activo no encontrado, schema Error.
```

---

## Prompt 5 — Archivo completo sin truncar

Canvas aplicó los cambios del Prompt 4 correctamente pero usó marcadores para omitir
las partes sin modificar, dejando el YAML incompleto en pantalla. Para poder copiar
y validar el archivo había que pedirle explícitamente que lo mostrara entero.
La salida completa también mostró que el modelo tomó algunas decisiones mejores
que las especificadas: modeló `ActivoDetalle` con `allOf` para extender `Activo`
en lugar de duplicar campos, extrajo `Señal` como schema independiente y lo referenciò
con `$ref` desde `Analisis` y `AnalisisCreate`, y agregó una URL de servidor de producción
además de la local.

```
¿Podés darme el código completo en el canvas sin incluir "existing code"
para omitir lo previo o posterior?
```

---

## Prompt 6 — Corrección de errores de validación Swagger

Al pegar el YAML completo en editor.swagger.io aparecieron dos rondas de errores.
La primera: un error de sintaxis genérico que apuntaba a la línea 190. La segunda,
después de pedir una corrección a Canvas: errores más específicos — el schema `Señal`
usaba `ñ` (inválida en nombres de componentes OpenAPI), todos los `$ref` que lo
apuntaban fallaban como URIs, y `nullable: true` no existe en OpenAPI 3.1.
Canvas corrigió los errores de validación pero el bloque `servers:` persistía
malformateado en cada salida: generaba las entradas sin el prefijo `-` de lista YAML,
lo que hacía el archivo inválido cada vez que se copiaba. Ese error estructural
se corrigió directamente en el archivo, sin volver a Canvas.

Prompt enviado para los errores de validación:
```
El YAML tiene errores de validación en Swagger. Dos cosas a corregir:

1. El schema "Señal" tiene la letra ñ que no es válida en nombres de componentes.
   Renombralo a "Senal" (sin tilde) y actualizá todos los $ref que lo referencian.

2. En OpenAPI 3.1 nullable: true no es válido. En ActivoDetalle, los campos
   tecnico y sentimiento deben usar la sintaxis correcta:
     tecnico:
       oneOf:
         - $ref: '#/components/schemas/Senal'
         - type: "null"
       description: señal más reciente del análisis técnico, null si no hay
     sentimiento:
       oneOf:
         - $ref: '#/components/schemas/Senal'
         - type: "null"
       description: señal más reciente del análisis de sentimiento, null si no hay

Dame el archivo completo sin truncar.
```

---

## Prompt 7 — Corrección de errores de validación Swagger

Con el error de sintaxis resuelto, el YAML ya renderizaba en Swagger pero el validador
seguía marcando errores. Dos causas: el nombre del schema `Señal` tiene `ñ`, que no es
válida en identificadores de componentes OpenAPI (solo acepta `[a-zA-Z0-9\.\-_]+`),
y eso rompía también todos los `$ref` que lo apuntaban. Además, `nullable: true` no
existe en OpenAPI 3.1 — en esa versión los tipos nullables se expresan con `oneOf`
y un tipo `"null"` explícito.

```
El YAML tiene errores de validación en Swagger. Dos cosas a corregir:

1. El schema "Señal" tiene la letra ñ que no es válida en nombres de componentes.
   Renombralo a "Senal" (sin tilde) y actualizá todos los $ref que lo referencian.

2. En OpenAPI 3.1 nullable: true no es válido. En ActivoDetalle, los campos
   tecnico y sentimiento deben usar la sintaxis correcta:
     tecnico:
       oneOf:
         - $ref: '#/components/schemas/Senal'
         - type: "null"
       description: señal más reciente del análisis técnico, null si no hay
     sentimiento:
       oneOf:
         - $ref: '#/components/schemas/Senal'
         - type: "null"
       description: señal más reciente del análisis de sentimiento, null si no hay

Dame el archivo completo sin truncar.
```

---

## Prompt 8 — Ejemplos por campo

Con el YAML validando sin errores en Swagger, los schemas se veían bien estructurados
pero sin valores de ejemplo. Al expandir un endpoint para probarlo, los campos aparecen
vacíos — no hay ninguna referencia de qué formato mandar. Los ejemplos con datos reales
del mercado argentino hacen que el spec sea autoexplicativo para cualquiera que lo abra.
Canvas aplicó la conversión correctamente pero repitió el problema del `servers:` sin `-`.
Los cambios se aplicaron directamente al archivo ya formateado.

```
Lo pegué en editor.swagger.io y valida sin errores. Pero si alguien que no conoce
el sistema abre la doc no va a saber qué mandar en cada campo al hacer un POST.
Quiero agregar ejemplos con valores reales del mercado argentino para que el spec
sea autoexplicativo.

Para cada propiedad de los schemas Activo, ActivoCreate, Analisis y AnalisisCreate
agregá un campo example con un valor realista. Ejemplos orientativos:
  ticker:    "GGAL"
  nombre:    "Grupo Financiero Galicia S.A."
  tipo:      "accion"
  mercado:   "BYMA"
  señal:     "compra"
  confianza: 0.82
  resumen:   "RSI en zona de sobreventa con cruce alcista en MACD."
```

---

## Prompt 9 — Corrección de warnings: example → examples

El panel derecho de Swagger renderizaba correctamente pero el validador mostraba
warnings en todas las propiedades con `example` (singular): en OpenAPI 3.1 ese campo
está deprecado y hay que reemplazarlo por `examples` (plural) con formato de array.
Además se aprovechó el prompt para pedirle explícitamente a Canvas que mostrara el
bloque `servers:` con el formato correcto de lista, ya que en cada salida anterior
lo generaba sin los `-` y había que corregirlo a mano.

```
El validador de Swagger muestra warnings porque example (singular) está deprecado
en OpenAPI 3.1. Hay que reemplazarlo por examples (plural) con formato de array
en cada propiedad de schema donde aparezca.

El formato correcto es:
  ticker:
    type: string
    description: Símbolo de cotización del activo.
    examples:
      - "GGAL"

Reemplazá todos los campos example: valor por examples: seguido de - valor
en los schemas Activo, ActivoCreate, Senal, Analisis, AnalisisCreate y ErrorResponse,
y también en los parámetros de path donde haya example.

Importante: mostrá el archivo YAML completo sin usar "existing code" ni ningún
marcador para omitir secciones. El bloque servers debe quedar exactamente así:

servers:
  - url: https://api.midominio.com/v1
    description: Servidor de producción
  - url: http://localhost:8080/v1
    description: Servidor de desarrollo local
```

---

## Prompt 10 — Corrección de formato examples en parameters

Al pegar el YAML en Swagger aparecieron nuevos errores: `"examples" members must be
Example Object`. La causa fue que en OpenAPI 3.1 el keyword `examples` tiene dos
formatos distintos según el contexto. En propiedades de schema sigue JSON Schema
y acepta un array (`- valor`). En parameters sigue el estándar OpenAPI y requiere
un mapa nombrado con objetos `value:`. El prompt anterior había usado el formato
de array en todos lados, lo que rompía los parameters. Se corrigió diferenciando
explícitamente los dos contextos.

```
El YAML tiene errores en Swagger: "examples members must be Example Object"
en los path parameters. El problema es que examples tiene dos formatos distintos
en OpenAPI 3.1 según el contexto:

En propiedades de schema (correcto, no tocar):
  ticker:
    type: string
    examples:
      - "GGAL"

En parameters (hay que corregir):
  parameters:
    - name: id
      in: path
      schema:
        type: integer
      examples:
        ejemplo:
          value: 1

Corregí todos los path parameters (id y analisisId) para que usen el formato
de mapa nombrado con value:. Las propiedades de schema quedan con el formato
de array. Mostrá el archivo completo sin truncar y con servers bien formateado:

servers:
  - url: https://api.midominio.com/v1
    description: Servidor de producción
  - url: http://localhost:8080/v1
    description: Servidor de desarrollo local
```

---

## Prompt 11 — Organización final

El YAML ya tenía el bloque `info` completo y los tags aplicados a cada endpoint
desde el Prompt 4. Lo que faltaba era el bloque raíz `tags:` con las descripciones
de cada grupo — sin eso Swagger UI muestra los tags pero sin ningún texto explicativo
al lado. Canvas generó el bloque `tags:` con el contenido correcto pero sin los `-`
de lista, igual que el `servers:`. Ambos se aplicaron directamente al archivo.

```
Ya está casi listo. Solo falta definir los tags en el bloque raíz del documento
para que Swagger UI los muestre con descripción, no solo como etiquetas vacías.

Agregá el bloque tags: al root del YAML con:
  - name: Activos
    description: Gestión de los activos financieros monitoreados por el sistema.
  - name: Análisis
    description: Registro y consulta de análisis generados por los agentes de IA.

Mostrá el archivo completo sin truncar y con el bloque servers usando - url: correctamente.
```
