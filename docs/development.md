# Desarrollo de MatchLab local

El código activo está en `backend/`, `frontend/` y `config/`. El historial Git conserva la implementación retirada.

## Capas

- `backend/app/domain`: contratos de partidos, mercados, cuotas y predicciones.
- `backend/app/providers`: normalización y acceso a las fuentes externas.
- `backend/app/repositories` y `db`: snapshots, caché, resultados y acceso serializado a DuckDB.
- `backend/app/models`: cálculos estadísticos independientes de HTTP y precios.
- `backend/app/learning`: datasets, entrenamiento, calibración, evaluación e inferencia local.
- `backend/app/services` y `jobs`: orquestación, análisis, ranking y actualización diaria.
- `backend/app/api`: rutas FastAPI; `frontend/src`: presentación y contratos TypeScript.

## Ejecución y comprobaciones

Consulta [setup_windows.md](setup_windows.md) para instalar y arrancar. Para desarrollar,
usa Uvicorn con recarga en el puerto 8000 y `npm run dev` en `frontend/`, puerto 3000.
Para validar desde la raíz:

```powershell
.\scripts\check.ps1
```

Comprueba sintaxis de PowerShell, Ruff, mypy, pytest y compilación TypeScript/Vite.
Las pruebas usan DuckDB en memoria y directorios temporales para no tocar datos o modelos reales.
La prueba de navegador se prepara con `backend/tests/export_ui_scenario.py` y se ejecuta con
Playwright según el README. Sus respuestas simuladas se interceptan solo en el navegador de prueba.

`backend/constraints.txt` fija las versiones verificadas de Python; se usa junto a los extras del
proyecto, sin obligar a instalar dependencias que no correspondan. Se valida en Windows y en CI.
`frontend/package-lock.json` fija las dependencias web. Al actualizarlas, repetir pruebas y auditorías.

La auditoría nativa requiere [Gitleaks](https://github.com/gitleaks/gitleaks) en PATH o en
`.tools/gitleaks/gitleaks.exe`. Ejecutar `scripts/security-check.ps1 -ExternalAudits` comprueba
historial, cambios preparados, archivos privados y vulnerabilidades Python/npm. Las auditorías
externas transmiten nombres y versiones de paquetes a los servicios de vulnerabilidades.

## Invariantes

- Un proceso de backend posee DuckDB; no iniciar otro worker o CLI contra la misma base.
- Persistir tiempos UTC; formar jornadas y horarios diarios con `Europe/Madrid`.
- Las observaciones de una predicción deben estar disponibles antes del saque inicial.
- Separar probabilidad, confianza, calidad y comparación de mercado.
- Mantener ausencias como ausencias; no convertir valores faltantes en ceros ni crear xG ficticio.
- Conservar los precios históricos y el primer pronóstico publicado utilizado por Performance.
- No registrar secretos ni enviar configuración de credenciales al navegador.
- Explicar supuestos estadísticos y decisiones temporales en comentarios; evitar repetir el código.

Un cambio debe mantener contratos y documentación coherentes y superar comprobaciones
proporcionales a su impacto. Los artefactos ML son locales, versionados por ejecución y excluidos
de Git; publicar un candidato requiere guardar su evaluación y superar los controles configurados.
