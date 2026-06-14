# Frontend Dashboard Implementation Plan (Plan 3 de 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el dashboard web: un único `frontend/index.html` (HTML + CSS + JS vanilla) que lista activos con sus señales, permite dar de alta activos, y muestra el historial de análisis de cada uno, consumiendo la API REST.

**Architecture:** Single-file sin build ni frameworks. Triángulo `state` → `render()` → eventos: el `state` es la única fuente de verdad; toda mutación llama a `render()`, la única función que toca el DOM. Se sirve en `http://localhost:3000` (coincide con el CORS del backend). Todo `fetch` maneja loading/éxito/error.

**Tech Stack:** HTML5 semántico, CSS (custom properties, Grid/Flex), JavaScript vanilla (`fetch`).

> **Decomposición.** Es un solo archivo cohesivo y NO hay runner de tests de JS, así que no aplica
> TDD. Se construye el archivo completo (Task 1) y se verifica en el navegador por secciones
> (Tasks 2-4), con el backend corriendo y sembrado. La verificación en navegador la hace el humano.

**Contexto de referencia:** spec §4.0 (claves ASCII `senal`/`senales_recientes`), §4.3 (contratos), §4.7 (anatomía del frontend y paleta Intel). El backend ya está en `main` (7 endpoints).

**Contratos que consume:**
- `GET /activos` → `[ {id, ticker, nombre, tipo, mercado}, ... ]` (sin señales).
- `GET /activos/{id}` → `{..., senales_recientes: {tecnico: senal|null, sentimiento: senal|null}}`.
- `POST /activos` (body `{ticker, nombre, tipo, mercado}`) → 201 / 400.
- `GET /activos/{id}/analisis` → `[ {id, tipo, senal, confianza, resumen, created_at}, ... ]` desc.

**Decisión de carga:** para mostrar los badges de señal en cada card, tras `GET /activos` se pide el detalle (`GET /activos/{id}`) de cada activo (N+1, aceptable con 3-4 activos) y se guarda el `ActivoDetalle` en `state.activos`.

**Convenciones:** Español, sin emojis. No `innerHTML` con datos del servidor sin escapar (XSS): se usa `textContent` o un helper de escape. Todos los colores vía custom properties.

---

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `frontend/index.html` | Todo el dashboard: `<style>` (paleta + layout) + HTML semántico + `<script>` (state/render/eventos/fetch) |

---

## Task 0: Carpeta y verificación de servido

**Files:**
- Create: `frontend/index.html` (placeholder mínimo en este task)

- [ ] **Step 1: Crear un `frontend/index.html` mínimo**

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Dashboard de Activos</title>
</head>
<body>
  <p>placeholder</p>
</body>
</html>
```

- [ ] **Step 2 (humano): verificar que se sirve en :3000**

Run (desde `frontend/`): `python -m http.server 3000`
Abrir `http://localhost:3000` → muestra "placeholder". Frenar con Ctrl+C.

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "chore: frontend/index.html placeholder servible en :3000"
```

---

## Task 1: Dashboard completo (HTML + CSS + JS)

Reemplazar el placeholder por el dashboard completo.

**Files:**
- Modify: `frontend/index.html` (contenido completo abajo)

- [ ] **Step 1: Escribir `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard de Análisis de Activos</title>
  <style>
    :root {
      --color-bg:           #f3f6fb;
      --color-surface:      #ffffff;
      --color-primary:      #0068b5;
      --color-primary-dark: #00285a;
      --color-accent:       #00c7fd;
      --color-text:         #1a1a1a;
      --color-text-muted:   #6c757d;
      --color-border:       #d9e2ec;

      --color-compra:    #1e7d34;
      --color-venta:     #c62828;
      --color-hold:      #f9a825;
      --color-sin-senal: #9aa5b1;

      --bg-compra:    #d4edda;
      --bg-venta:     #f8d7da;
      --bg-hold:      #fff3cd;
      --bg-sin-senal: #e9ecef;

      --space-sm: 8px;  --space-md: 16px;  --space-lg: 24px;
      --radius:   8px;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: var(--color-bg);
      color: var(--color-text);
    }
    header {
      background: var(--color-primary);
      color: #fff;
      padding: var(--space-md) var(--space-lg);
      display: flex;
      align-items: baseline;
      gap: var(--space-md);
    }
    header h1 { margin: 0; font-size: 1.3rem; }
    header .contador { color: #cfe8ff; font-size: 0.9rem; }
    main { padding: var(--space-lg); max-width: 1100px; margin: 0 auto; }
    section { margin-bottom: var(--space-lg); }
    h2 { color: var(--color-primary-dark); font-size: 1.05rem; }

    form { display: flex; flex-wrap: wrap; gap: var(--space-md); align-items: flex-end; }
    .campo { display: flex; flex-direction: column; gap: 4px; }
    label { font-size: 0.8rem; color: var(--color-text-muted); }
    input, select {
      padding: var(--space-sm); border: 1px solid var(--color-border);
      border-radius: var(--radius); font-size: 0.9rem;
    }
    input:focus, select:focus { outline: 2px solid var(--color-accent); border-color: var(--color-accent); }
    button {
      padding: var(--space-sm) var(--space-md); border: none; border-radius: var(--radius);
      background: var(--color-primary); color: #fff; font-size: 0.9rem; cursor: pointer;
    }
    button:hover { background: var(--color-primary-dark); }
    button:disabled { background: var(--color-sin-senal); cursor: not-allowed; }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: var(--space-md);
    }
    .card {
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius);
      padding: var(--space-md);
      cursor: pointer;
    }
    .card:hover { border-color: var(--color-accent); }
    .card-top { display: flex; justify-content: space-between; align-items: flex-start; }
    .ticker { font-size: 1.2rem; font-weight: 700; color: var(--color-primary-dark); }
    .nombre { color: var(--color-text-muted); font-size: 0.85rem; }
    .meta { color: var(--color-text-muted); font-size: 0.8rem; margin-top: 4px; }
    .badges { display: flex; gap: var(--space-sm); margin-top: var(--space-md); }
    .badge {
      font-size: 0.72rem; padding: 4px var(--space-sm); border-radius: 999px;
      color: #fff; white-space: nowrap;
    }
    .badge .etq { opacity: 0.85; margin-right: 4px; }
    .badge.compra { background: var(--color-compra); }
    .badge.venta  { background: var(--color-venta); }
    .badge.hold   { background: var(--color-hold); color: #5a4500; }
    .badge.sin    { background: var(--color-sin-senal); }

    .historial { margin-top: var(--space-md); border-top: 1px solid var(--color-border); padding-top: var(--space-sm); }
    .analisis-item { font-size: 0.82rem; padding: var(--space-sm) 0; border-bottom: 1px dashed var(--color-border); }
    .analisis-item .linea1 { display: flex; gap: var(--space-sm); align-items: center; }
    .pill { font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; }
    .pill.compra { background: var(--bg-compra); color: var(--color-compra); }
    .pill.venta  { background: var(--bg-venta);  color: var(--color-venta); }
    .pill.hold   { background: var(--bg-hold);   color: #5a4500; }
    .fecha { color: var(--color-text-muted); }
    .resumen { color: var(--color-text); margin-top: 2px; }

    .estado { padding: var(--space-sm) var(--space-md); border-radius: var(--radius); margin-bottom: var(--space-md); }
    .estado.error { background: var(--bg-venta); color: var(--color-venta); }
    .estado.loading { background: var(--bg-sin-senal); color: var(--color-text-muted); }
    .vacio { color: var(--color-text-muted); }
    footer { text-align: center; color: var(--color-text-muted); font-size: 0.8rem; padding: var(--space-lg); }
  </style>
</head>
<body>
  <header>
    <h1>Dashboard de Análisis de Activos</h1>
    <span class="contador" id="contador"></span>
  </header>
  <main>
    <section id="estado-global"></section>

    <section id="alta-activo">
      <h2>Agregar activo</h2>
      <form id="form-activo">
        <div class="campo">
          <label for="f-ticker">Ticker</label>
          <input id="f-ticker" name="ticker" required maxlength="12" autocomplete="off">
        </div>
        <div class="campo">
          <label for="f-nombre">Nombre</label>
          <input id="f-nombre" name="nombre" required maxlength="80" autocomplete="off">
        </div>
        <div class="campo">
          <label for="f-tipo">Tipo</label>
          <select id="f-tipo" name="tipo">
            <option value="accion">accion</option>
            <option value="ON">ON</option>
          </select>
        </div>
        <div class="campo">
          <label for="f-mercado">Mercado</label>
          <select id="f-mercado" name="mercado">
            <option value="BYMA">BYMA</option>
            <option value="NYSE">NYSE</option>
            <option value="NASDAQ">NASDAQ</option>
          </select>
        </div>
        <button type="submit" id="btn-alta">Agregar</button>
      </form>
    </section>

    <section id="lista-activos">
      <h2>Activos monitoreados</h2>
      <div class="grid" id="grid"></div>
    </section>
  </main>
  <footer>
    TP3 — CEIA UBA · <a href="https://github.com/Neo820712/Erlin-Rey-TP3">repositorio</a>
  </footer>

  <script>
    const API_BASE = 'http://localhost:8000';

    const state = {
      activos: [],            // ActivoDetalle (con senales_recientes)
      selectedActivoId: null, // card expandida, o null
      analisis: [],           // historial del activo expandido
      loading: false,
      error: null,
    };

    // --- utilidades ---
    function esc(texto) {
      const div = document.createElement('div');
      div.textContent = texto == null ? '' : String(texto);
      return div.innerHTML;
    }
    function claseSenal(senal) {
      return senal ? senal : 'sin';
    }

    // --- fetch helpers (todos manejan loading/error en quien los llama) ---
    async function api(path, opciones) {
      const resp = await fetch(`${API_BASE}${path}`, opciones);
      if (resp.status === 204) return null;
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(body.message || `Error ${resp.status}`);
      }
      return body;
    }

    async function cargarActivos() {
      state.loading = true; state.error = null; render();
      try {
        const lista = await api('/activos');
        const detalles = await Promise.all(lista.map((a) => api(`/activos/${a.id}`)));
        state.activos = detalles;
      } catch (e) {
        state.error = `No se pudieron cargar los activos: ${e.message}`;
      } finally {
        state.loading = false; render();
      }
    }

    async function altaActivo(datos) {
      state.loading = true; state.error = null; render();
      try {
        await api('/activos', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(datos),
        });
        document.getElementById('form-activo').reset();
        await cargarActivos();
      } catch (e) {
        state.error = `No se pudo agregar el activo: ${e.message}`;
        state.loading = false; render();
      }
    }

    async function cargarAnalisis(activoId) {
      state.loading = true; state.error = null; render();
      try {
        state.analisis = await api(`/activos/${activoId}/analisis`);
        state.selectedActivoId = activoId;
      } catch (e) {
        state.error = `No se pudo cargar el historial: ${e.message}`;
      } finally {
        state.loading = false; render();
      }
    }

    // --- render (única función que toca el DOM) ---
    function render() {
      document.getElementById('contador').textContent =
        state.activos.length ? `${state.activos.length} activos` : '';

      const estado = document.getElementById('estado-global');
      if (state.error) {
        estado.innerHTML = `<div class="estado error">${esc(state.error)}</div>`;
      } else if (state.loading) {
        estado.innerHTML = `<div class="estado loading">Cargando…</div>`;
      } else {
        estado.innerHTML = '';
      }

      document.getElementById('btn-alta').disabled = state.loading;

      const grid = document.getElementById('grid');
      if (!state.activos.length && !state.loading) {
        grid.innerHTML = `<p class="vacio">No hay activos. Agregá uno con el formulario.</p>`;
        return;
      }
      grid.innerHTML = state.activos.map(cardHTML).join('');

      // listeners de cada card (no inline onclick para evitar acoplar markup y datos)
      grid.querySelectorAll('.card').forEach((el) => {
        el.addEventListener('click', () => {
          const id = Number(el.dataset.id);
          if (state.selectedActivoId === id) {
            state.selectedActivoId = null; state.analisis = []; render();
          } else {
            cargarAnalisis(id);
          }
        });
      });
    }

    function badgeHTML(etiqueta, senal) {
      const clase = claseSenal(senal);
      const texto = senal ? senal : 'sin datos';
      return `<span class="badge ${clase}"><span class="etq">${etiqueta}</span>${esc(texto)}</span>`;
    }

    function cardHTML(activo) {
      const sr = activo.senales_recientes || {};
      const expandida = state.selectedActivoId === activo.id;
      const historial = expandida ? historialHTML() : '';
      return `
        <div class="card" data-id="${activo.id}">
          <div class="card-top">
            <div>
              <div class="ticker">${esc(activo.ticker)}</div>
              <div class="nombre">${esc(activo.nombre)}</div>
            </div>
          </div>
          <div class="meta">${esc(activo.tipo)} · ${esc(activo.mercado)}</div>
          <div class="badges">
            ${badgeHTML('Técnico', sr.tecnico)}
            ${badgeHTML('Sentim.', sr.sentimiento)}
          </div>
          ${historial}
        </div>`;
    }

    function historialHTML() {
      if (state.loading) return `<div class="historial">Cargando historial…</div>`;
      if (!state.analisis.length) return `<div class="historial vacio">Sin análisis todavía.</div>`;
      const items = state.analisis.map((a) => {
        const pct = Math.round((a.confianza || 0) * 100);
        return `
          <div class="analisis-item">
            <div class="linea1">
              <span class="pill ${claseSenal(a.senal)}">${esc(a.senal)}</span>
              <span>${esc(a.tipo)} · ${pct}%</span>
              <span class="fecha">${esc(a.created_at)}</span>
            </div>
            <div class="resumen">${esc(a.resumen)}</div>
          </div>`;
      }).join('');
      return `<div class="historial">${items}</div>`;
    }

    // --- eventos ---
    document.getElementById('form-activo').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const f = ev.target;
      altaActivo({
        ticker: f.ticker.value.trim(),
        nombre: f.nombre.value.trim(),
        tipo: f.tipo.value,
        mercado: f.mercado.value,
      });
    });

    cargarActivos();
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: dashboard single-file (grid, alta, historial, paleta Intel)"
```

---

## Task 2: Verificación — grid y señales (humano)

Requiere backend corriendo y sembrado.

- [ ] **Step 1:** Backend: `uv run uvicorn backend.main:app --reload --port 8000`. Seed: `uv run python scripts/seed.py`.
- [ ] **Step 2:** Frontend: desde `frontend/`, `python -m http.server 3000`. Abrir `http://localhost:3000`.
- [ ] **Step 3:** Verificar: aparecen AAPL/GOOGL/MSFT como cards en grid; cada una con `ticker`, `nombre`, `tipo · mercado` y dos badges (Técnico con color según la señal; Sentim. en gris "sin datos"). El contador del header dice "3 activos".

---

## Task 3: Verificación — alta y historial (humano)

- [ ] **Step 1:** En el formulario, agregar un activo (ej. ticker `YPF`, nombre `YPF S.A.`, tipo `accion`, mercado `BYMA`) y Agregar → aparece una card nueva sin señales (badges en gris). El botón se deshabilita mientras carga.
- [ ] **Step 2:** Generar una señal para ese activo desde Claude Code: `uv run python scripts/generar_senal.py YPF` (o `AAPL`). Recargar el dashboard → el badge Técnico del activo toma color.
- [ ] **Step 3:** Click en una card → se expande y muestra el historial de análisis (señal como pill de color, tipo, confianza en %, fecha, resumen). Click de nuevo → se colapsa.
- [ ] **Step 4:** Probar un error: frenar el backend y recargar → se ve el mensaje de error en rojo (no una pantalla en blanco).

---

## Self-Review (autor del plan)

**Cobertura del spec (subsistema C, §4.7):**
- HTML semántico (`header`/`main`/`section`/`footer`): Task 1. ✓
- Paleta Intel + colores de señal en `:root` (custom properties): Task 1. ✓
- Grid `auto-fill minmax(260px,1fr)` + flex en cards: Task 1. ✓
- Triángulo `state` → `render()` → eventos; `render()` única función que toca el DOM: Task 1. ✓
- Tres vistas (grid con badges, formulario de alta, card expandida con historial): Task 1 / verif. Tasks 2-3. ✓
- `fetch` con loading/éxito/error; error visible, nunca tragado: helper `api()` + estados. ✓
- No `innerHTML` con datos del servidor sin escapar: helper `esc()` aplicado a todo dato dinámico. ✓
- Claves ASCII `senal`/`senales_recientes` consumidas tal cual (§4.0): Task 1. ✓
- Single-file, sin build, servido en :3000 (coincide con CORS): Task 0/1. ✓

**Consistencia con los contratos del backend:**
- `GET /activos` (sin señales) + `GET /activos/{id}` (con `senales_recientes`) → `state.activos` = ActivoDetalle. ✓
- `POST /activos` con `{ticker,nombre,tipo,mercado}`; error 400 → `body.message` mostrado. ✓
- `GET /activos/{id}/analisis` → historial desc; `confianza` mostrada como %. ✓
- 204 (DELETE) manejado en `api()` aunque el frontend no expone borrado (fuera de las 3 vistas del spec). ✓

**Nota:** el spec no incluye borrar activos/análisis desde el dashboard (las 3 vistas son grid, alta y card expandida), así que el frontend no expone DELETE — los endpoints existen y se prueban por curl/tests. Mantener el alcance del spec (YAGNI).
