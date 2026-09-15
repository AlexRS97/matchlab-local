# Empezar a usar y mejorar MatchLab

Guía para el compañero al que Alex autorice a trabajar en el proyecto. Repositorio:
[AlexRS97/matchlab-local](https://github.com/AlexRS97/matchlab-local).
El código y la documentación se comparten desde Git; cada equipo instala sus dependencias
y mantiene sus propios datos y modelos.

## Acceso y contenido de la entrega

El repositorio es privado. Alex puede añadir al compañero desde **Settings → Collaborators →
Add people**, usando su cuenta de GitHub. El compañero debe aceptar la invitación antes de
clonar el repositorio. [Instrucciones de GitHub](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository).

Para colaborar conviene clonar: conserva el historial y permite enviar ramas y pull requests.
También se puede entregar un ZIP del código para instalarlo o leerlo; ese archivo no contiene
el historial Git. [Archivos de código de GitHub](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives).
Se mantienen [LICENSE](../LICENSE), [NOTICE](../NOTICE.md) y las condiciones de las
[contribuciones autorizadas](../CONTRIBUTING.md).

| Incluido en Git y en el ZIP del código | Se genera o configura en cada equipo; no se publica |
| --- | --- |
| Backend, web, configuración, pruebas y documentación | `.env`, certificados y claves de las cuentas |
| Dependencias declaradas y versiones fijadas | `.venv/`, `node_modules/` y herramientas de `.tools/` |
| Scripts de instalación, arranque, cierre y accesos directos | Accesos `.lnk`, icono instalado y rutas personales |
| Logo en `assets/` y plantillas `.env.example` | DuckDB, CSV descargados, modelos, datasets y reportes de `data/` |
| CI y plantillas de issues y pull requests | Logs, capturas y resultados temporales de `.runtime/` |

No es necesario copiar la carpeta de Alex. Los accesos directos se crean en el equipo del
compañero y el histórico se descarga de nuevo. Un clon reciente puede producir una versión
distinta de los modelos porque las fuentes incorporan resultados y correcciones.

## Instalar en Windows desde cero

La aplicación de escritorio se prepara para Windows de 64 bits. Instala **Python 3.12**, con su
launcher `py`, **Node.js 22** y **Git**. GitHub CLI es opcional. Los instaladores están en
[Python](https://www.python.org/downloads/), [Node.js](https://nodejs.org/en/download) y
[Git](https://git-scm.com/downloads/win). Las dependencias de ML necesitan varios GB de disco
y acceso a Internet; no se ha definido un mínimo de RAM validado para todos los equipos.
No hace falta Docker, PostgreSQL, Redis, Ollama ni una clave de OpenAI.

Desde PowerShell, en la carpeta donde quieras guardar el proyecto:

```powershell
git clone https://github.com/AlexRS97/matchlab-local.git
cd matchlab-local
py -3.12 --version
node --version
py -3.12 -m venv backend/.venv
```

Git pedirá autenticar la cuenta que tiene acceso al repositorio. Si recibiste un ZIP, extrae
la carpeta completa y abre PowerShell en la raíz que contiene `start.ps1`; omite `git clone`
y crea igualmente el entorno Python. Los comandos Git de colaboración requieren un clon.

Para instalar PyTorch CPU con las mismas versiones fijadas que usa CI, y después el resto:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install --no-deps -c backend/constraints.txt torch --index-url https://download.pytorch.org/whl/cpu
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 -Setup -NoBrowser
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-desktop.ps1
```

La primera línea instala el paquete CPU; `-Setup` instala sus dependencias y el resto del
proyecto, compila la web y arranca los servidores. Crea `backend/.env` desde la plantilla
solo si no existe ningún `.env` de configuración. La opción de ejecución de PowerShell se
aplica a ese proceso, sin cambiar la política permanente de Windows.

Abre **MatchLab** desde el escritorio o entra en **http://localhost:3000**. La documentación
de la API está en **http://localhost:8000/docs**. El primer arranque descarga los CSV y entrena
si hay muestra suficiente: espera al estado final de la barra y consulta los avisos.
No hay que crear la base de datos a mano.

Se crean dos accesos: **MatchLab** para abrir y **Detener MatchLab** para cerrar todos los
procesos del arranque normal. Si mueves la carpeta, vuelve a ejecutar `install-desktop.ps1`.
Cerrar la pestaña del navegador no detiene el backend. También puedes cerrar con:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop.ps1
```

No se instala inicio con Windows. Las actualizaciones diarias se ejecutan con la aplicación
abierta y se recuperan al volver a abrirla. `threads: auto` utiliza los procesadores disponibles
en cada equipo; el número 24 de la validación de Alex no es un requisito. La configuración
actual de las redes utiliza CPU. Los controles de GitHub Actions se ejecutan en GitHub.

## Qué funciona sin claves y cómo configurar las fuentes

| Fuente | Uso | Configuración local |
| --- | --- | --- |
| Football-Data | Resultados y estadísticas históricas de cinco ligas para entrenar | CSV públicos; sin clave en este adaptador |
| API-Football | Jornada, estadísticas previas y resultados operativos | `API_FOOTBALL_KEY` y presupuesto diario |
| Betfair oficial | Precios Exchange de solo lectura | Usuario, contraseña, app key y certificados si procede |
| PulseScore | Precios de Bet365 y Winamax | `PULSESCORE_API_KEY` y presupuesto mensual |

Edita tu `backend/.env` y reinicia la aplicación. Usa tus cuentas y configura sus presupuestos
reales. La cobertura efectiva depende de cada proveedor y plan; el histórico público no
proporciona una cartelera actual ni cuotas. Sin credenciales puedes usar el laboratorio,
leer el código y ejecutar las pruebas; Today y las cuotas mostrarán las fuentes que faltan.
La instalación de Alex aún no tiene esas credenciales operativas verificadas.
Detalles y campos: [proveedores](providers.md) y [plantilla de configuración](../backend/.env.example).

No adjuntes `.env`, certificados ni respuestas privadas en issues o pull requests. Los datos
y modelos de Alex no se incluyen en la entrega del código. Para una comparación exacta se
necesita además el mismo snapshot de datos y sus reportes, compartidos por separado cuando
corresponda: consulta [reproducción de experimentos](#investigar-sin-alterar-la-versión-de-uso-diario).

## Recorrido para entender el proyecto

1. [README](../README.md): alcance y uso; [validación](validation.md): qué se comprobó realmente.
2. [Arquitectura](architecture.md) y [desarrollo](development.md): capas, contratos y flujo.
3. [Metodología](methodology.md): datos anteriores al partido, modelos y límites de la evaluación.
4. [Proveedores](providers.md) y [mercados](markets.md): fuentes, normalización y comparaciones.
5. [Revisión y mejoras pendientes](review.md): propuestas concretas que aún no están implementadas.

| Trabajo | Puntos de entrada |
| --- | --- |
| Cambiar una fuente o comprobar su calidad | `backend/app/providers/`, `repositories/historical_repository.py` |
| Revisar Poisson, Dixon–Coles, dispersión o córners | `backend/app/models/`, `config/model_weights.yaml` |
| Revisar variables, periodos o entrenar candidatos | `backend/app/learning/dataset.py`, `features.py`, `training.py` |
| Calibrar y elegir por liga | `backend/app/learning/evaluation.py`, `league_selection.py` |
| Revisar actualización, progreso o recálculo | `backend/app/jobs/`, `services/runtime.py`, `learning/service.py` |
| Revisar predicciones publicadas y resultados | `backend/app/services/prediction_service.py`, `performance_service.py` |
| Cambiar la web | `frontend/src/pages/`, `components/`, `hooks/` |
| Instalación, recursos y cierre | `scripts/`, `backend/app/core/resources.py` |

Las rutas abreviadas de la tabla pertenecen a `backend/app/`. El stack anterior está retirado;
no hay que recuperar sus contenedores ni sus servicios para trabajar con esta versión.

## Investigar sin alterar la versión de uso diario

Empieza por un issue de **Investigación de datos o modelos** y usa la
[plantilla de experimento](experiments/template.md). Formula una hipótesis medible y registra
el resultado incluso cuando no haya mejora. No existe una familia ganadora permanente.

Prioridades de investigación ya identificadas: evaluación con ventanas temporales repetidas,
periodos prospectivos nuevos, comparación con el modelo publicado, seguimiento de calibración
por liga y fuentes con fechas de publicación verificables. Los modelos jerárquicos y nuevas
variables son candidatos a comparar, no mejoras demostradas. Véase el [plan de investigación](review.md#siguientes-mejoras-con-mayor-valor).

- Trabaja en una rama y, para entrenamientos experimentales, en un clon separado con su propio
  entorno y `data/`. Un `git switch` en el mismo clon **no aísla** la base ni los artefactos.
- Para usar una copia de un snapshot, detén primero su backend. Conserva juntos el archivo
  DuckDB, los CSV y el directorio completo del modelo con `current.json`. No sobrescribas una
  carpeta de datos que ya contenga trabajo de otro experimento. Esa copia no se publica en Git.
- El comando `python -m app.learning --train` **actualiza el histórico antes de entrenar**.
  Para una comparación congelada utiliza la función `train` de `learning/training.py` sobre
  una base de experimento fija y un directorio de salida propio, sin invocar el actualizador.
- Conserva `report.json`, configuración, semilla, versiones, revisión y huella de los datos,
  huella del código, periodos y número de muestras. Los reportes están en
  `data/models/<run_id>/`; el informe resumido del experimento puede ir a `docs/experiments/`.
- Usa solo información disponible antes de cada partido. No ajustes variables, escalado,
  hiperparámetros ni calibración con el periodo reservado para evaluar. Anota la reutilización
  del test y reserva evidencia posterior para una decisión de promoción nueva.
- Compara las mismas ligas, mercados y partidos; muestra cobertura, Brier, log loss,
  calibración e incertidumbre, además del coste de entrenamiento. Conserva ausencias como
  ausencias. Una mejora histórica no demuestra rentabilidad ni mejor cobertura diaria.

La selección actual y sus umbrales están documentados en [metodología](methodology.md).
Los modelos se publican automáticamente en el directorio del clon donde entrenas; por eso
el experimento debe usar su propio almacenamiento.

## Colaborar con código y pruebas

Desde un clon limpio y con la aplicación detenida:

```powershell
git switch main
git pull --ff-only
git switch -c research/nombre-del-experimento
```

Antes de tu primer commit configura la identidad de Git con tu nombre y una dirección
verificada o la dirección privada `noreply` de tu cuenta de GitHub:

```powershell
git config user.name "Tu nombre"
git config user.email "Tu dirección de GitHub"
```

Sustituye esos dos valores por los tuyos; la configuración se aplica solo a este repositorio.

Edita, ejecuta las comprobaciones relevantes y prepara únicamente los archivos de la mejora:

```powershell
.\scripts\check.ps1
git status --short
git add docs/experiments/mi-experimento.md
.\scripts\security-check.ps1
git commit -m "Document evaluation of the candidate model"
git push -u origin research/nombre-del-experimento
```

`git add` es un ejemplo: sustituye la ruta por los archivos que realmente hayas cambiado.
`security-check.ps1` necesita Gitleaks en PATH o `.tools/gitleaks/gitleaks.exe`; la
[guía de desarrollo](development.md) explica los requisitos y las auditorías opcionales.
Abre un pull request hacia `main` con la hipótesis, cambios, resultados y limitaciones.
Revisa los controles de Actions y solicita la revisión de Alex antes de fusionar.
No hagas push directo a `main`: actualmente esta regla es de colaboración y **no está impuesta
por una protección obligatoria de rama**. [Configuración del repositorio](github-governance.md).

Para comprobar la web, con el arranque normal abierto:

```powershell
.\backend\.venv\Scripts\python.exe backend/tests/export_ui_scenario.py
Push-Location frontend
npx.cmd playwright install chromium
npx.cmd playwright test
Pop-Location
.\stop.ps1
```

Las pruebas de backend y el escenario de navegador aíslan los datos de prueba. Para desarrollar
con recarga, consulta [las dos terminales de desarrollo](setup_windows.md): se cierran con
**Ctrl+C en ambas terminales**, incluido el supervisor de recarga. No mezcles ese modo con el
arranque del escritorio ni abras dos servidores sobre el mismo DuckDB.

## Si algo no funciona

Ejecuta `scripts/doctor.ps1` y consulta [diagnóstico de Windows](setup_windows.md#diagnóstico).
En un issue incluye sistema, versión de Python/Node, commit, pasos, resultado esperado y real,
fuentes configuradas (solo sus nombres) y el error relevante sin credenciales. Distingue
una fuente no disponible de un fallo del modelo. La evidencia de referencia de Alex está en
[validation.md](validation.md); no sustituye una instalación comprobada en el equipo del compañero.
