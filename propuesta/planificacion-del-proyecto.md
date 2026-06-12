# Planificación del Proyecto — Dashboard de Análisis de Activos Financieros

**Materia:** Introducción al Desarrollo de Software Asistido por IA (CEIA — UBA)  
**TP:** 3 — Trabajo Final  
**Entrega final:** clase 8  

> **Naturaleza de este documento.** Es una **declaración de intención de diseño** del proyecto:
> define el alcance, la arquitectura y las reglas de construcción de cada artefacto. Describe
> el **qué** del sistema con el detalle necesario para que el spec técnico y la implementación
> se deriven de acá. Todo el proyecto se construye desde cero.

---

## 1. Descripción del proyecto

Sistema full-stack que expone como API REST y dashboard web una versión reducida del sistema
de análisis de activos financieros de la tesis de grado.

El usuario puede monitorear activos (acciones y ONs), ver las señales de análisis técnico y
de sentimiento generadas por agentes, y disparar señales simuladas directamente desde Claude Code
usando un slash command propio.

**Alcance deliberadamente acotado.** No integra los agentes reales ni los feeds de precios
en tiempo real. El valor está en la arquitectura y la configuración del entorno de desarrollo,
no en la complejidad del dominio. El sistema define un **contrato de API (`openapi.yaml`)** como
fuente de verdad, escrito como primer artefacto del proyecto; backend y frontend derivan de él.

**Fuera de alcance (decisiones explícitas, no omisiones):**
- Autenticación / autorización (401/403) y manejo de sesiones.
- Methods `PUT`/`PATCH` (el dominio no edita activos ni análisis existentes).
- Métricas y traces de observabilidad (solo logs en terminal).
- Feeds de precios reales y agentes de análisis reales (las señales son simuladas).

**Requisitos formales de la entrega:** backend (API REST) + frontend (HTML/CSS/JS vanilla) +
persistencia de datos + `CLAUDE.md` y `rules` definidos + `settings.json` con permisos + al
menos una skill propia invocable por slash command. El proyecto integra el dominio de la tesis.
La entrega final es una demo en vivo del proyecto terminado en la clase 8.

---

## 2. Tabla de elementos técnicos del curso

Mapeo de cada elemento técnico del curso a su implementación concreta en el proyecto.
Sirve como checklist de completitud.

| Elemento técnico | Semana | Requisito TP3 | Implementación en el proyecto |
|---|:---:|:---:|---|
| HTML semántico (`<header>`, `<main>`, `<section>`) | 2 | Frontend | Estructura del dashboard en `frontend/index.html` |
| CSS custom properties (variables) | 2 | Frontend | Paleta Intel + `--color-compra/venta/hold` en `:root` |
| CSS Flexbox/Grid | 2 | Frontend | Grid de cards de activos, flex en cada card |
| Estado + DOM + Eventos (triángulo JS) | 2 | Frontend | `state` global + `render()` + `addEventListener` |
| Paradigma single-file | 2 | Frontend | Todo en `frontend/index.html` — sin build steps |
| Protocolo HTTP (GET, POST, DELETE) | 3 | Backend | 7 endpoints implementados en FastAPI |
| REST: recursos y jerarquía de URLs | 3 | Backend | `/activos` y `/activos/{id}/analisis` anidados |
| REST: idempotencia | 3 | Backend | GET y DELETE son idempotentes |
| REST: stateless | 3 | Backend | Sin estado de sesión en el servidor |
| Status codes (200, 201, 204, 400, 404, 500) | 3 | Backend | Respuesta correcta en cada handler |
| Endpoint como contrato (5 piezas) | 3 | Backend | Pydantic schemas + status codes explícitos |
| Datos: relacional vs document | 3 | Persistencia | SQLite (relacional) — justificado en §4.4 |
| Modelo relacional (foreign key) | 3 | Persistencia | `Analisis.activo_id` → `Activo.id` |
| Errores y observabilidad (4xx/5xx, logs) | 3 | Backend | Schema `{ "message" }` + `logging` |
| OpenAPI como contrato | 3 | Backend | `openapi.yaml` como fuente de verdad (§4.6) |
| Paradigma agentic | 4 | — | Desarrollo asistido con Claude Code |
| Arquitectura ReAct (think → act → observe) | 4 | — | La skill `/generar-senal` implementa el ciclo |
| `CLAUDE.md` (jerarquía de contexto) | 4 | **Obligatorio** | Raíz del proyecto con stack, comandos y convenciones |
| Rules con Glob patterns | 4 | **Obligatorio** | `.claude/rules/backend.md` y `frontend.md` |
| `settings.json` con permisos | 4 | **Obligatorio** | `.claude/settings.json` con allow/deny |
| Skill propia + slash command | 4 | **Obligatorio** | `/generar-senal TICKER` crea un análisis |
| Permisos granulares (límites determinísticos) | 5 | **Obligatorio** | allow/deny y deny de comandos destructivos en `settings.json` |
| Subagentes para tareas aisladas | 5 | — | La skill aísla el dominio; subagentes durante el desarrollo |
| Desarrollo con plugin (Superpowers) | 6 | — | Flujo brainstorming → plan → ejecución → verificación |
| GitHub Flow (ramas + PR) | 6 | **Obligatorio** | Trabajo en ramas, merge a `main` vía PR |
| Repositorio GitHub | 1-6 | **Obligatorio** | Repo público con `README.md` y `openapi.yaml` |

---

## 3. Justificación de la arquitectura

### 3.1 Por qué FastAPI

FastAPI genera documentación Swagger automáticamente desde los tipos Python (Pydantic).
Esto permite verificar que la implementación matchea el `openapi.yaml` simplemente abriendo
`/docs` — sin herramientas adicionales.

Alternativa descartada: Flask + Marshmallow. Más verboso y sin documentación automática.

### 3.2 Por qué SQLite + SQLModel

SQLite es ideal para prototipos: almacena todo en un solo archivo y no requiere configuración
de servidor. SQLModel combina Pydantic (validación para FastAPI) y SQLAlchemy (ORM para SQLite)
en un solo paquete, reduciendo el boilerplate de mantener dos sistemas de tipos separados.

Alternativa descartada: PostgreSQL. Correcta para producción pero requiere instalar y
configurar un servidor — innecesario para el alcance del proyecto.

### 3.3 Por qué frontend single-file

El single-file tiene tres ventajas concretas para este contexto: el código es más corto
(entra en el contexto del modelo), no necesita build steps, y se puede probar abriendo el
archivo directamente. El dashboard no tiene la complejidad suficiente como para justificar
un framework.

### 3.4 Por qué un `openapi.yaml` como fuente de verdad

El contrato de la API se escribe **primero**, como artefacto fundacional del proyecto, y fija
las decisiones de diseño (recursos, methods, schemas, status codes) antes de implementar. Tanto
el backend como el frontend derivan de él, lo que evita tomar decisiones de contrato de forma
implícita en el código.

Además es contexto compacto: en lugar de cargar todo el código del backend para que el asistente
entienda los contratos, alcanza con el YAML. Es la información más densa posible consumiendo la
menor cantidad de tokens. Escribir y mantener el `openapi.yaml` es parte del trabajo (ver §4.6).

### 3.5 Por qué `/generar-senal` como skill

La skill conecta directamente con el dominio de la tesis (agentes de análisis) y materializa
el ciclo ReAct:

1. **Think:** ¿qué ticker se pide? ¿existe en la DB?
2. **Act:** GET /activos → POST /activos/{id}/analisis
3. **Observe:** ¿el análisis fue creado? ¿qué señal generó?

El "agente" hace algo real (llama a la API y persiste) aunque la señal sea simulada.

---

## 4. Arquitectura web

Esta sección define la arquitectura concreta del sistema: cliente-servidor, HTTP, REST, los
contratos de cada endpoint, la capa de datos, el manejo de errores, el contrato OpenAPI y el
frontend. Es el detalle del **qué** del que deriva la implementación.

### 4.0 Decisiones de contrato (leer primero)

Dos decisiones transversales que fija el contrato y que el resto del documento asume:

| Punto | **Decisión** | Por qué |
|---|---|---|
| Host y prefijo | `http://localhost:8000` (sin `/v1`) | Demo simple, un solo origen, sin versionado innecesario para el alcance |
| Claves de señal | `senal`, `senales_recientes` (ASCII, sin ñ) | Evita bugs de encoding al consumir el JSON desde JavaScript |

Enums del dominio: `tipo` activo `{accion, ON}`; `mercado` `{BYMA, NYSE, NASDAQ}`; `senal`
`{compra, venta, hold}`; `tipo` análisis `{tecnico, sentimiento}`.

### 4.1 Modelo cliente-servidor y HTTP

Un **servidor** (FastAPI) espera pedidos y responde; un **cliente** (el dashboard, `curl`, o la
skill de Claude Code) pide primero. El cliente habla, el servidor contesta — esa asimetría es
toda la arquitectura.

El idioma entre los dos es **HTTP**, un protocolo de pedido/respuesta:

- **Request** = `method` + `URL` + `headers` + `body` (opcional).
- **Response** = `status code` + `headers` + `body`.

**Methods usados** (el proyecto usa 3):

| Method | Semántica | Uso en el proyecto |
|---|---|---|
| `GET` | leer un recurso, sin efectos | listar activos, ver detalle, listar análisis |
| `POST` | crear un recurso nuevo | alta de activo, alta de análisis |
| `DELETE` | borrar un recurso | baja de activo, baja de análisis |

`PUT`/`PATCH` no se usan: un análisis es un evento inmutable (se crea o se borra) y los activos
no se editan. Es una decisión de contrato, no un olvido.

**Status codes que el sistema emite** (el primer dígito dice de qué lado fue la falla):

- `200` — GET con datos. `201` — POST que creó. `204` — DELETE sin body.
- `400` — body inválido (faltan campos requeridos o tipos incorrectos).
- `404` — el activo o el análisis no existe.
- `500` — error interno (bug, DB caída): se diagnostica con los logs del servidor (§4.5).

### 4.2 REST: recursos y jerarquía

HTTP define cómo viajan los datos; **REST** define qué se transporta y cómo se nombra. La regla:
**el method dice qué hacer; la URL dice sobre qué**. Las URLs nombran **recursos** (sustantivos),
nunca acciones.

**Recursos del sistema:**

- `Activo` — un instrumento financiero monitoreado (acción u ON).
- `Analisis` — una señal generada por un agente sobre un activo. No flota suelto: pertenece a un
  activo, por eso se anida.

**Mapa de recursos:**

```
/activos                              colección de activos
/activos/{id}                         un activo (item)
/activos/{id}/analisis                colección de análisis de ESE activo (anidado)
/activos/{id}/analisis/{analisisId}   un análisis puntual (item anidado)
```

Se anida `analisis` bajo `activos` porque la pertenencia es estructural: un análisis sin activo
no tiene sentido.

**Las cuatro reglas REST en el sistema:**

1. **Recursos en plural** — `/activos`, no `/activo`.
2. **Jerarquía cuando hay relación** — `/activos/{id}/analisis`.
3. **Idempotencia** — `GET` y `DELETE` son idempotentes (llamarlos dos veces deja el sistema
   igual); `POST` no lo es (dos POST crean dos análisis). Consecuencia: un GET/DELETE que falla
   se reintenta sin riesgo; un POST que se reintenta duplica.
4. **Stateless** — el servidor no guarda contexto de sesión entre requests; cada request trae
   todo lo necesario.

### 4.3 Los 7 endpoints como contratos (las 5 piezas)

Cada endpoint es una promesa de 5 piezas: `method` · `path` · `schema de entrada` · `schema de
salida` · `códigos posibles`. **Dónde viajan los datos:** el path identifica (`{id}`), el query
modifica (no se usa en este sistema), el body transporta el contenido nuevo (JSON en POST). El
**controller** es la función del servidor que atiende cada promesa.

```
1. GET /activos
   entrada:  —
   salida 200: [ Activo, ... ]                      (lista, puede ser vacía)

2. POST /activos
   entrada (body): ActivoCreate
     ticker   string, requerido
     nombre   string, requerido
     tipo     enum {accion, ON}, requerido
     mercado  enum {BYMA, NYSE, NASDAQ}, requerido
   salida 201: Activo  (ActivoCreate + id autogenerado)
   salida 400: { message } si falta un campo o el tipo es inválido

3. GET /activos/{id}
   entrada:  id en el path
   salida 200: ActivoDetalle = Activo + senales_recientes:
                 { tecnico: Senal|null, sentimiento: Senal|null }
               (la señal MÁS reciente de cada tipo; null si no hay)
   salida 404: { message } si el activo no existe

4. DELETE /activos/{id}
   entrada:  id en el path
   salida 204: sin body  (borra el activo y, en cascada, sus análisis)
   salida 404: { message } si el activo no existe

5. GET /activos/{id}/analisis
   entrada:  id en el path
   salida 200: [ Analisis, ... ]  (historial completo, orden descendente por fecha)
   salida 404: { message } si el activo no existe

6. POST /activos/{id}/analisis
   entrada: id en el path + body AnalisisCreate
     tipo       enum {tecnico, sentimiento}, requerido
     senal      enum {compra, venta, hold}, requerido
     confianza  number 0..1, requerido
     resumen    string, requerido
   salida 201: Analisis  (AnalisisCreate + id + created_at autogenerados)
   salida 400: { message } body inválido
   salida 404: { message } si el activo no existe

7. DELETE /activos/{id}/analisis/{analisisId}
   entrada:  id y analisisId en el path
   salida 204: sin body
   salida 404: { message } si el activo o el análisis no existen
```

`Senal` es el enum `{compra, venta, hold}`. `confianza` es un `float` validado en `[0,1]` por
Pydantic (un body con `confianza: 1.5` devuelve `400`, no se guarda). El backend habilita
**CORS** para `http://localhost:3000` (origen del frontend).

### 4.4 Capa de datos: modelo relacional

**Por qué una base de datos:** persistencia (sobrevivir reinicios), eficiencia de consulta
(índices) e **integridad** (no permitir un análisis cuyo `activo_id` no existe). Un archivo de
texto no da ninguna de las tres.

**Relacional vs document:** el sistema tiene dos entidades con una relación clara (un activo
tiene muchos análisis) y requiere integridad referencial — el caso de uso de **relacional/SQL**.
Un modelo *document* (anidar los análisis dentro del activo) solo convendría si siempre se leyera
"todo de un activo" junto, pero el sistema también borra un análisis puntual y los lista por
separado. Se usa **SQLite**: cero configuración, la base entera en `data/activos.db`.

**Schema:**

```
activos
  id       INTEGER  primary key, autogenerado
  ticker   TEXT     not null
  nombre   TEXT     not null
  tipo     TEXT     not null   -- 'accion' | 'ON'
  mercado  TEXT     not null   -- 'BYMA' | 'NYSE' | 'NASDAQ'

analisis
  id          INTEGER   primary key, autogenerado
  activo_id   INTEGER   not null, FOREIGN KEY -> activos.id
  tipo        TEXT      not null   -- 'tecnico' | 'sentimiento'
  senal       TEXT      not null   -- 'compra' | 'venta' | 'hold'
  confianza   REAL      not null   -- 0.0 .. 1.0
  resumen     TEXT      not null
  created_at  TEXT      not null   -- ISO 8601 (UTC)
```

La **foreign key** `analisis.activo_id → activos.id` la hace cumplir el motor: rechaza un
análisis con `activo_id` inexistente, y el `DELETE` de un activo borra sus análisis en cascada.
El campo `senales_recientes` del endpoint 3 se resuelve tomando, por cada `tipo`, el análisis de
`created_at` máximo.

**Modelos SQLModel (tres clases por recurso):** `XxxBase` (campos comunes), `XxxCreate(XxxBase)`
(body del POST, sin `id`), `Xxx(XxxBase, table=True)` (tabla, con `id`). Así se separa el schema
de entrada del de salida.

**Datos de ejemplo (seed):** el sistema incluye una forma de poblar 3-4 activos con señales para
tener una demo poblada (la skill `/generar-senal` cumple ese rol — §5.4).

### 4.5 Errores y observabilidad

**Los errores tienen dueño:** leer el primer dígito antes de tocar nada. `4xx` = el cliente se
equivocó (mirar el request); `5xx` = el servidor se cayó (mirar logs y código).

**Schema de error único en todo el sistema:**

```json
{ "message": "El activo solicitado no fue encontrado." }
```

Se emite con `HTTPException(status_code=404, detail={"message": "..."})`. Todos los errores (400,
404, 500) usan esta misma forma — un cliente que parsea errores no adivina la estructura.

**Logs:** el backend usa `logging` (nunca `print()`). Cada request relevante deja una línea con
`method`, `path` y resultado; un POST que falle por violación de integridad debe mostrar la causa
(p. ej. `IntegrityError`). El **stack trace**, si aparece, se lee buscando la primera línea de
código del proyecto (no del framework): ahí vive la causa. La observabilidad del sistema se limita
a logs en terminal — suficiente para una demo local.

### 4.6 OpenAPI: el contrato escrito

Las 5 piezas del §4.3 se formalizan en un archivo `openapi.yaml` (versión 3.1). Mapeo uno a uno:

- `method` → key HTTP (`get`, `post`, `delete`) bajo `paths`.
- `path` → keys de `paths`, con `{id}` para variables.
- `schema-in` → `requestBody`.
- cada `schema-out` → entry en `responses`, indexada por código (`'201'`, `'400'`, `'404'`).
- los errores (400, 404) son responses como cualquier otro — contrato, no adorno.

Por qué el contrato vive en un **archivo** y no en un prompt: (1) **menos ambigüedad** — `type`,
`format`, `required`, `enum` quedan fijos; (2) **codegen** — del mismo YAML salen las docs Swagger
(`/docs`), un cliente, mocks o tests de contrato; (3) **durabilidad** — vive en git, se versiona
y se le hace code review.

El `openapi.yaml` se escribe como **primer artefacto** del proyecto y es la fuente de verdad: el
backend deriva de él y FastAPI lo regenera en `/docs` para verificar, sin herramientas extra, que
la implementación matchea el contrato.

### 4.7 Frontend: anatomía y estructura del dashboard

**HTML semántico (estructura como sustantivos):**

```
<header>   título del dashboard + (opcional) contador de activos
<main>
  <section id="alta-activo">   formulario para agregar un activo (POST /activos)
  <section id="lista-activos"> grid de cards de activos
<footer>   créditos / link al repo
```

Sin *div soup*: cada bloque con su etiqueta. El formulario usa `<form>` + `<label>` + `<input>`
y un `<button>` de submit.

**CSS — las 4 primitivas:**

1. **Modelo de caja** — padding/margin consistentes vía variables de espaciado (`--space-*`)
   para que las cards respiren.
2. **Layout** — `display: grid` con `grid-template-columns: repeat(auto-fill, minmax(260px, 1fr))`
   para el grid de cards; `flex` dentro de cada card (ticker a un lado, badges al otro).
3. **Tipografía y color** — una sans-serif para todo; paleta Intel + colores de señal.
4. **Variables CSS** — todos los colores y espaciados en `:root` (no hardcodear hex en las
   reglas). Una variable es el punto de entrada para cambiar el tema en una línea.

**Paleta de colores — basada en la identidad de www.intel.com:**

```css
:root {
  /* Chrome de la app — azules Intel */
  --color-bg:           #f3f6fb;   /* fondo de página, gris azulado muy claro */
  --color-surface:      #ffffff;   /* cards y formulario */
  --color-primary:      #0068b5;   /* Intel Blue — header, botones, acentos */
  --color-primary-dark: #00285a;   /* Intel Classic Blue oscuro — hover, títulos */
  --color-accent:       #00c7fd;   /* Energy Blue — focus, detalles */
  --color-text:         #1a1a1a;   /* carbón — texto principal */
  --color-text-muted:   #6c757d;   /* gris neutro — metadatos */
  --color-border:       #d9e2ec;   /* bordes sutiles */

  /* Señales — convención financiera universal (verde/rojo/amarillo) */
  --color-compra:    #1e7d34;   /* verde */
  --color-venta:     #c62828;   /* rojo */
  --color-hold:      #f9a825;   /* amarillo */
  --color-sin-senal: #9aa5b1;   /* gris */

  /* Fondos tenues de los badges de señal */
  --bg-compra:    #d4edda;
  --bg-venta:     #f8d7da;
  --bg-hold:      #fff3cd;
  --bg-sin-senal: #e9ecef;

  --space-sm: 8px;  --space-md: 16px;  --space-lg: 24px;
  --radius:   8px;
}
```

Las señales mantienen verde/rojo/amarillo (convención financiera de lectura inmediata); el chrome
(header, botones, focus) usa los azules Intel para la identidad visual.

**Triángulo estado → DOM → eventos.** El estado es la única fuente de verdad; el DOM es su
reflejo:

```js
const API_BASE = 'http://localhost:8000';
const state = {
  activos: [],            // array de ActivoDetalle (con senales_recientes)
  selectedActivoId: null, // id de la card expandida, o null
  loading: false,
  error: null,
};
function render() { /* única función que toca el DOM */ }
// Regla: tras cualquier mutación de state -> render().
```

**Las tres vistas y su ciclo evento → estado → DOM:**

1. **Grid de cards.** Cada card muestra `ticker` (grande), `nombre`, `tipo`, `mercado`, y dos
   **badges** de señal (técnico y sentimiento) coloreados por `senal` o gris "sin datos" si es
   `null`.
2. **Formulario de alta.** `submit` → `POST /activos` → actualizar `state.activos` → `render()`.
   Mientras espera: `loading=true` (botón deshabilitado). Si falla: `state.error` visible.
3. **Card expandida.** Click en una card → `state.selectedActivoId = id` → `GET
   /activos/{id}/analisis` → render del historial (cada análisis: `tipo`, `senal`, `confianza`
   como %, `created_at`, `resumen`).

**Manejo de `fetch`:** todo `fetch` maneja loading, éxito y error con `try/catch/finally`; el
error se muestra al usuario, nunca se traga en silencio. No usar `innerHTML` con datos del
servidor sin sanitizar (riesgo XSS).

**Single-file:** todo (HTML + `<style>` + `<script>`) en `frontend/index.html`. Sin frameworks,
sin build, sin `node_modules`.

---

## 5. Reglas de creación de los artefactos de Claude Code

Define cómo se construye cada artefacto obligatorio del entorno de Claude Code.

> **Creación interactiva.** Estos cuatro artefactos no se generan en automático. Al crear cada
> uno, el asistente **primero pregunta qué se quiere incluir** —presentando como base los puntos
> de la subsección correspondiente— y espera la confirmación o los agregados del usuario antes de
> escribir el archivo.

### 5.1 `CLAUDE.md` (raíz del proyecto)

**Qué incluye:** stack (tabla capa→tecnología), comandos clave (levantar backend/frontend, crear
la DB, ver `/docs`), estructura de carpetas, reglas de arquitectura (el `openapi.yaml` como fuente
de verdad; schema de error único; CORS) y convenciones de código de backend y frontend.

**Reglas de construcción:**

- Mantenerlo cerca de 200 líneas: archivos más largos pierden adherencia.
- No usar `@path` para importar el `openapi.yaml` (insertaría el YAML completo en el contexto en
  cada sesión, ~3000 tokens). Mejor: que Claude Code lo lea cuando lo necesite.
- Debe alcanzar para entender el proyecto sin repetir nada en el prompt.

### 5.2 `.claude/rules/` (reglas por path)

Dos archivos, cada uno con front matter `paths:` (Glob) para carga selectiva:

```
.claude/rules/backend.md    paths: ["backend/**/*.py"]
.claude/rules/frontend.md   paths: ["frontend/**/*.html", "frontend/**/*.js", "frontend/**/*.css"]
```

**Reglas de construcción:**

- Siempre con `paths:`. Una rule sin `paths:` se carga en cada sesión; con `paths:` solo se activa
  cuando Claude Code lee un archivo que matchea el patrón.
- **`backend.md`** fija: FastAPI + SQLModel + SQLite; los tres modelos por recurso
  (`Base`/`Create`/`table`); status codes (201 POST, 204 DELETE); `HTTPException` con
  `{ "message" }`; dependency injection para la sesión de DB (nunca sesiones globales); `logging`
  en vez de `print()`; no hardcodear la ruta de la DB (leer `DATABASE_URL`).
- **`frontend.md`** fija: vanilla JS, single-file, `fetch`; patrón `state` + `render()`; manejo de
  loading/éxito/error; custom properties para todos los colores (incluida la paleta Intel del
  §4.7); flex/grid (no `float`); no `innerHTML` sin sanitizar.

### 5.3 `.claude/settings.json` (permisos del harness)

Define qué herramientas están disponibles en cualquier sesión: el límite determinístico del
sistema, distinto de las instrucciones blandas del `CLAUDE.md`.

**Reglas de construcción:**

- **`allow`** explícito para lo que el proyecto necesita: `uv run/add/init`, `python`, `uvicorn`,
  `curl`, y los `git` de trabajo (`status`, `log`, `diff`, `add`, `commit`, `checkout`, `branch`).
- **`deny`** para lo destructivo e irreversible: `git push --force*`, `rm -rf *`, `git reset --hard*`.
- **`env`** con `DATABASE_URL`, `CORS_ORIGINS=http://localhost:3000`, `PYTHONPATH=.`.
- Criterio: permitir lo cotidiano sin fricción, bloquear lo destructivo de forma determinística.

### 5.4 Skill propia `/generar-senal` (slash command + ReAct)

Vive en `.claude/skills/generar-senal/SKILL.md`. Es la skill propia invocable por comando de barra
y el ejemplo de arquitectura ReAct del sistema.

**Reglas de construcción:**

- **Front matter** con `name` y `description` breve: el sistema lo usa para saber que la skill
  existe y cargar el cuerpo completo solo cuando se invoca (no ocupa contexto el resto del tiempo).
- **Interfaz:** `/generar-senal TICKER [tipo]` — `tipo` = `tecnico` (default) | `sentimiento`.
- **Flujo ReAct explícito:**
  1. *Think:* verificar que el backend responde (`GET /activos`); encontrar el activo por `ticker`
     (case-insensitive); si no existe, informar y detener.
  2. *Act:* generar un análisis coherente con el `tipo` (señal + confianza en rango + resumen con
     terminología real: RSI/MACD/SMA para técnico, noticias/flujo de capitales para sentimiento) y
     `POST /activos/{id}/analisis`.
  3. *Observe:* confirmar el `201`; informar ticker, tipo, señal, confianza, resumen e id creado.
- La skill hace algo real (llama a la API y persiste) aunque la señal sea simulada.

---

## 6. Estructura de archivos del proyecto

```
activos-dashboard/           ← raíz del proyecto (repo GitHub)
├── CLAUDE.md                ← contexto para Claude Code (§5.1)
├── openapi.yaml             ← contrato de la API, fuente de verdad (§4.6)
├── README.md                ← documentación del proyecto
├── prompts.md               ← registro de prompts del desarrollo
├── .claude/
│   ├── settings.json        ← permisos de Claude Code (§5.3)
│   ├── rules/
│   │   ├── backend.md       ← reglas para backend/**/*.py (§5.2)
│   │   └── frontend.md      ← reglas para frontend/** (§5.2)
│   └── skills/
│       └── generar-senal/
│           └── SKILL.md     ← slash command /generar-senal (§5.4)
├── backend/
│   ├── main.py              ← app FastAPI, routes, CORS
│   ├── models.py            ← SQLModel (Activo, Analisis + variantes Create)
│   └── database.py          ← engine, Session dependency, create_db()
├── frontend/
│   └── index.html           ← dashboard single-file
└── data/
    └── .gitkeep             ← carpeta en repo, activos.db en .gitignore
```

---

## 7. Checklist de entrega

### Código funcional
- [ ] Backend corriendo: `uv run uvicorn backend.main:app --reload --port 8000`
- [ ] Los 7 endpoints responden según el `openapi.yaml` (§4.3)
- [ ] SQLite persiste datos entre reinicios del servidor
- [ ] FK `analisis.activo_id` con borrado en cascada (§4.4)
- [ ] Frontend muestra activos con señales actuales (badges por color)
- [ ] Formulario para agregar activos funciona
- [ ] Click en activo muestra sus análisis
- [ ] Todos los `fetch` manejan loading y error visibles

### Configuración Claude Code
- [ ] `CLAUDE.md` en la raíz, ~200 líneas, sin `@import` del yaml (§5.1)
- [ ] `.claude/rules/backend.md` con `paths: ["backend/**/*.py"]`
- [ ] `.claude/rules/frontend.md` con `paths: ["frontend/**/*.{html,js,css}"]`
- [ ] `.claude/settings.json` con allow/deny y env (§5.3)
- [ ] `/generar-senal TICKER` crea un análisis en la DB (§5.4)

### Repositorio GitHub
- [ ] Repo público
- [ ] `openapi.yaml` commiteado
- [ ] `README.md` con descripción, proceso y decisiones
- [ ] `prompts.md` con los prompts del desarrollo
- [ ] `data/activos.db` en `.gitignore`

---

## 8. Mapa de los tres niveles de ingeniería

Cada artefacto del sistema opera en uno de tres niveles: Prompt, Context o Harness Engineering.

| Artefacto / Práctica | Nivel | Por qué actúa en ese nivel |
|---|:---:|---|
| `/generar-senal TICKER` al invocarse | **Prompt Eng.** | Una invocación = una interacción con contexto estructurado |
| `openapi.yaml` cargado en sesión | **Context Eng.** | Controla qué ve el modelo en una sesión (contexto de alta densidad) |
| `CLAUDE.md` | **Context Eng. + Harness** | Carga en cada sesión (context) y persiste entre sesiones (harness) |
| Carga selectiva de rules por paths | **Context Eng.** | Qué ve el modelo depende de qué archivos lee en esa sesión |
| `.claude/settings.json` | **Harness Eng.** | Define qué herramientas están disponibles en cualquier sesión |
| `.claude/rules/backend.md` y `frontend.md` | **Harness Eng.** | Reglas del runtime: activas según el patrón Glob |
| `/generar-senal` como skill registrada | **Harness Eng.** | Herramienta disponible permanentemente, no por sesión |

Los tres niveles operan en simultáneo: el prompt define qué se pide en cada interacción; el
`openapi.yaml` define qué ve el modelo en cada sesión; `CLAUDE.md` + `rules/` + `settings.json` +
skills definen qué puede hacer en cualquier sesión.
