---
paths: ["frontend/**/*.{html,js,css}"]
---

# Reglas del frontend

- **Vanilla single-file:** todo en `frontend/index.html` (HTML + `<style>` + `<script>`). Sin
  frameworks, sin build, sin `node_modules`.
- **`fetch` completo:** loading, éxito y error con `try/catch/finally`. El error se muestra al
  usuario, nunca se traga en silencio.
- **Custom properties para todos los colores:** paleta Intel + colores de señal en `:root`. No
  hardcodear hex en las reglas.
- **Layout con Flexbox/Grid**, nunca `float`.
- **No usar `innerHTML` con datos del servidor sin sanitizar** (riesgo XSS).
- **API base:** `const API_BASE = 'http://localhost:8000'`.
- **Claves del JSON en ASCII:** el backend usa `senal` y `senales_recientes` (sin ñ). Consumirlas
  así tal cual desde JavaScript; evita bugs de encoding al parsear la respuesta.

## Triángulo state -> render() -> eventos

El `state` es la única fuente de verdad; el DOM es su reflejo. Tras **cualquier** mutación de
`state`, llamar a `render()`, que es la única función que toca el DOM:

```js
const state = {
  activos: [],            // ActivoDetalle (con senales_recientes)
  selectedActivoId: null, // card expandida, o null
  loading: false,
  error: null,
};
function render() { /* única función que toca el DOM */ }
// Regla: tras mutar state -> render().
```
