# Preferencias globales

Estas instrucciones aplican a **todos** mis proyectos. Las reglas específicas de
un repo viven en su propio CLAUDE.md y tienen prioridad sobre estas.

## Idioma
- Respóndeme **en español**. El código, nombres de variables, comentarios,
  mensajes de commit y términos técnicos van en inglés.

## Cómo quiero que trabajes

### Pensamiento crítico (lo más importante)
- **No asumas que lo que pido es la mejor opción.** Analiza pros y contras y dame
  una respuesta honesta, aunque contradiga mi idea inicial.
- Siempre sopesa opciones y alternativas **antes** de avanzar.
- Si existe una alternativa superadora que no mencioné o que no se había pensado
  hasta ese momento, **propónla**. Lo que importa es el mejor camino para hacer
  las cosas, no complacerme.
- Si algo es ambiguo o hay un trade-off real que sea decisión mía, pregunta antes
  de avanzar.

### Estilo de respuesta
- **Conciso**: ve al grano, sin relleno ni resúmenes innecesarios. Da detalle
  extra solo cuando lo pida.

### Seguridad al modificar
- **Confirma antes de cambios grandes**: refactors amplios, borrar archivos,
  tocar muchos archivos a la vez, o cualquier acción difícil de revertir.
- No ejecutes notebooks (`.ipynb`). Yo los corro para ver el avance en vivo;
  tú construye y verifica con smoke scripts y avísame cuando estén listos.

### Git / commits
- Usa **Conventional Commits**: `feat/fix/docs/refactor/chore(scope): descripción`.
- Crea o haz push de commits solo cuando lo pida explícitamente.

## Estilo de código
- **Sin emojis** en el código ni en los comentarios.
- Comentarios solo los importantes (el porqué de algo no obvio), no sobre-comentar
  lo que el código ya dice.
- **Nada de meta-comentarios de asistente**: prohibido `# lo solicitado`,
  `# esta fue la corrección`, `# cambiado de X a Y`, `# aquí agrego...`, etc.
  El código debe parecer escrito por un humano, sin rastros de edición por IA.

## Notebooks (.ipynb)
Estructura cada paso como un sándwich texto–código–texto:
1. **Celda markdown previa**: título de la sección (si aplica) + qué hace el código
   que viene a continuación.
2. **Celda de código**.
3. **Celda markdown posterior**: interpretación de los resultados obtenidos.
- En celdas de **entrenamiento, comparación, evaluación o revisión** de resultados,
  incluye las **ayudas visuales típicas de ese tipo de análisis** (p. ej. matriz de
  confusión, curvas ROC/PR, importancia de features, learning curves, distribuciones,
  scatter de predicho vs real, tablas comparativas de métricas), cuando aporten a
  entender el resultado.

## Entorno y stack habitual
- **SO**: Windows 11. Shell por defecto **PowerShell** (sintaxis PowerShell, no bash,
  salvo que use la Bash tool explícitamente).
- **Python**: pandas, scikit-learn, Jupyter para data science / ML.
- **LLMs locales**: Ollama (modelo actual `qwen3.5:9b`).
- Bases de datos locales en SQLite (`.db`) cuando aplique.
