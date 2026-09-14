# MatchLab · Football Analytics AI

Aplicación local para analizar la jornada de fútbol, comparar probabilidades propias con cuotas de **Betfair Exchange, Bet365 y Winamax**, y consultar modelos estadísticos, machine learning y deep learning.

> Repositorio propietario y privado. Consulta [LICENSE](LICENSE) y [NOTICE.md](NOTICE.md).

## Iniciar en Windows

Requisitos para una instalación nueva: Python 3.12 y Node.js 22. En este equipo también se reconocen los runtimes portables de `.tools/`.

```powershell
cd "C:\Users\Alex\Documents\Apuestas API"
.\start.ps1 -Setup
```

Después de instalar:

```powershell
.\start.ps1
```

Abre **http://localhost:3000**. API y documentación: http://localhost:8000/docs.

```powershell
.\stop.ps1
```

**Inicio y cierre manuales.** Usa los accesos directos **MatchLab** y **Detener MatchLab**, o los comandos anteriores. No se instala inicio con Windows ni tareas programadas. Cerrar la pestaña del navegador no detiene el servidor: antes de jugar, utiliza **Detener MatchLab** o `stop.ps1`. Esto cierra los procesos del proyecto, sus trabajos y la bandeja, conservando los datos y modelos ya guardados.

La apertura reutiliza la web compilada salvo cambios en el código. El backend y la web usan prioridad baja en Windows; las librerías numéricas y DuckDB tienen dos hilos y las redes usan CPU. La caché evita repetir inferencias idénticas. Estos límites reducen el consumo, sin prometer ausencia de lag en cualquier equipo.

El arranque es nativo: FastAPI + DuckDB y React/Vite. Sus registros están en `.runtime/`. `-NoBrowser` evita abrir una pestaña y `-NoBuild` reutiliza la compilación web. Para crear los accesos directos en otra instalación: `scripts/install-desktop.ps1`.

## Qué hace

- Today muestra todos los partidos devueltos por API-Football para la fecha de Madrid, incluidos los que no tienen datos suficientes.
- Top 5 por probabilidad del mercado, cuota mínima inicial 1,35 y filtros de casa, país, liga, hora, confianza, calidad, edge y EV. Las cuotas antiguas y los partidos iniciados quedan fuera del Top.
- Detalle con forma de los últimos 5/10/20 partidos, casa/fuera, clasificación, H2H, matriz de marcadores, goles y córners esperados, modelos individuales y explicación en español.
- Goles: Poisson, corrección Dixon–Coles local regularizada, binomial negativa, forma reciente, casa/fuera y xG cuando realmente existe. Predicción externa identificada por separado.
- Córners: Poisson, binomial negativa, forma reciente y casa/fuera.
- Model Lab: **CatBoost, LightGBM, XGBoost, red MLP y red GRU**, entrenamiento local, calibración, separación temporal y métricas reales. Una familia participa en la mezcla solo si supera su referencia estadística en la evaluación configurada; peso aprendido máximo del 20%.
- Performance registra el primer pronóstico prepartido de cada mercado y acumula resultados, Brier, log loss, intervalos de frecuencia y ROI bruto simulado con cuotas registradas.
- Comparación de tres casas, precio back/lay de Betfair, de-vig cuando hay ambos lados, cuotas manuales etiquetadas y snapshots de precios.

Las cuotas nunca son entradas del modelo deportivo. No hay apuestas automáticas ni dependencia de OpenAI. Las explicaciones son deterministas; Ollama queda reservado como opción futura.

La selección por liga compara modelos estadísticos y familias ML por separado para goles y córners. Model Lab muestra qué candidato pasó sus controles, con muestra mínima y bloques temporales separados. La selección específica cubre las cinco ligas del histórico; otras ligas usan la referencia estadística con los datos disponibles.

## Actualización diaria de partidos y análisis

**La cartelera y las predicciones se actualizan cuando abres MatchLab.** Si sigue abierto, el ciclo diario vence a las **06:00 Europe/Madrid**; si estaba cerrado, recupera la actualización al siguiente arranque. Recalcula las predicciones de los partidos pendientes y guarda fecha, número de partidos analizados y errores. El estado aparece en Today. Con MatchLab detenido no se descargan datos ni se ejecutan análisis.

Mientras el backend sigue abierto, también revisa partidos cada 30 minutos, estadísticas según su caché y cuotas según la configuración y el presupuesto. La fecha cambia automáticamente al pasar de día. El histórico se comprueba diariamente mientras la aplicación esté abierta. **El entrenamiento automático está desactivado**: los modelos guardados siguen calculando predicciones, y solo se vuelven a entrenar cuando pulsas “Entrenar modelos” en Model Lab. El entrenamiento manual utiliza dos hilos por modelo.

Puedes lanzar una actualización puntual manualmente. Este comando es una acción explícita: si la aplicación está cerrada, abre un worker temporal que termina al finalizar; `stop.ps1` también puede detenerlo:

```powershell
.\scripts\daily-refresh.ps1 -WaitForCompletion
```

## Progreso de las actualizaciones y entrenamientos

El panel **Actividad de MatchLab**, visible en todas las páginas, muestra porcentaje completado,
porcentaje restante, fase actual, tiempo transcurrido y detalle de las fases. Sigue por separado
la jornada, el histórico o entrenamiento y las actualizaciones periódicas de cuotas.

Al arrancar se revisan la jornada y el histórico. **Actualizar** en Today vuelve a solicitar ambos
para hoy. En Model Lab, **Entrenar modelos** muestra la preparación de datos, cada una de las cinco
familias, calibración, comparación y guardado. Las redes muestran épocas completadas y los árboles,
objetivos completados. El porcentaje mide avance por fases, no una estimación de tiempo restante.

El 100% confirma que el trabajo terminó; si hubo fuentes ausentes o errores parciales, aparece
**Terminado con avisos**. Un fallo que interrumpe el trabajo conserva el porcentaje alcanzado.
Los contadores se consultan cada 1,5 segundos, sin peticiones solapadas, y el sondeo se pausa al
ocultar la pestaña. El cierre manual detiene los procesos del proyecto.

## Configurar las fuentes

El backend lee `.env` de la raíz y después `backend/.env`; los valores de este último tienen prioridad. Se preserva el `.env` existente. No copies una plantilla vacía encima de credenciales ya configuradas.

```dotenv
API_FOOTBALL_KEY=
API_FOOTBALL_DAILY_CALL_BUDGET=100
BETFAIR_USERNAME=
BETFAIR_PASSWORD=
BETFAIR_APP_KEY=
PULSESCORE_API_KEY=
PULSESCORE_MONTHLY_BUDGET=500
APP_TIMEZONE=Europe/Madrid
```

Completa las claves de tus cuentas y reinicia el backend. Las credenciales nunca se devuelven al navegador. [Guía de proveedores](docs/providers.md).

**Sin esas credenciales, no se puede verificar ni cargar la cartelera y las cuotas reales de las tres APIs.** La aplicación sigue funcionando y el laboratorio utiliza CSV históricos públicos de Football-Data. Un histórico descargado no implica que exista una cuota actual ni una cartelera mundial disponible.

## Entrenar y validar

En **Model Lab**, pulsa “Actualizar datos” o “Entrenar modelos”. El entrenamiento funciona en segundo plano dentro del backend. Con la aplicación detenida también puedes usar:

```powershell
.\backend\.venv\Scripts\python.exe -m app.learning --train
```

Los artefactos, datasets y reportes viven en `data/models/<versión>/`; `current.json` apunta a la versión publicada. DuckDB admite un proceso de aplicación: **no ejecutes el CLI de entrenamiento a la vez que el servidor**, ni varios workers de Uvicorn.

```powershell
.\scripts\check.ps1
```

Para la comprobación de navegador, con la aplicación arrancada:

```powershell
.\backend\.venv\Scripts\python.exe backend/tests/export_ui_scenario.py
cd frontend
npx playwright install chromium
npx playwright test
```

El escenario del navegador usa una base en memoria y respuestas interceptadas. Nunca inserta partidos ni cuotas ficticias en tu base real.

## Documentación

- [Arquitectura](docs/architecture.md), [metodología y límites](docs/methodology.md), [mercados](docs/markets.md).
- [Instalación y problemas habituales de Windows](docs/setup_windows.md).
- [Plan y estado de implementación](docs/implementation_plan.md).
- [Validación local y entrenamiento ejecutado](docs/validation.md).

El proyecto está en `backend/`, `frontend/`, `config/` y `assets/`. Se han retirado el código, los contenedores y las instrucciones del stack anterior. El historial Git conserva las versiones previas; las bases, credenciales y artefactos locales están excluidos de la publicación. Consulta la [revisión y mejoras](docs/review.md).
