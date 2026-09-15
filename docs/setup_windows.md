# Windows: instalación y funcionamiento diario

## Instalación manual

Instala Python 3.12 y Node.js 22. Desde la raíz del repositorio:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -c backend/constraints.txt -e "backend[dev,learning]"
```

Si no tienes un `.env` de la raíz con credenciales:

```powershell
Copy-Item backend/.env.example backend/.env
notepad backend/.env
```

No sobrescribas un archivo existente. La configuración del proceso tiene prioridad; después se lee `backend/.env` por encima de `.env` de la raíz.

```powershell
cd frontend
npm ci
npm run build
cd ..
.\start.ps1 -NoBuild
```

Para desarrollar con recarga, utiliza dos terminales:

```powershell
# Terminal 1, raíz del proyecto
$env:ENABLE_SCHEDULER = "false"
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

```powershell
# Terminal 2
cd frontend
npm run dev
```

No mantengas el servidor del arranque nativo abierto a la vez que otro backend con `--reload`.
En este modo se desactiva el arranque automático de trabajos para no repetir actualizaciones
con cada recarga del código; puedes solicitarlas desde la web. Para salir, pulsa **Ctrl+C en
ambas terminales** y, en la terminal del backend, ejecuta `Remove-Item Env:ENABLE_SCHEDULER`.
El cierre con `stop.ps1` está destinado a los procesos del arranque normal; no lo uses como
sustituto de cerrar los supervisores de desarrollo. Una terminal nueva recupera la configuración
habitual de `.env`. Para instalar en el equipo de un compañero, sigue la [guía de colaboración](collaboration.md).

## Uso manual y cierre antes de jugar

Abre **MatchLab** desde el escritorio o ejecuta `start.ps1`. Para cerrar el proyecto, usa
**Detener MatchLab**, `stop.ps1` o **Detener para jugar** en la bandeja. Se cierran el servidor,
la web, los trabajos del proyecto y la bandeja. Los datos y modelos publicados se conservan;
si interrumpes un entrenamiento antes de su publicación, se conserva la versión anterior.

Cerrar la pestaña del navegador no detiene el backend. Antes de jugar, utiliza el cierre anterior
y cierra también la pestaña. El proyecto no inicia con Windows y no tiene una tarea diaria instalada.

Para crear los dos accesos directos en otra instalación:

```powershell
.\scripts\install-desktop.ps1
```

## Actualización diaria mientras está abierto

Al abrir MatchLab se revisa la jornada. El ciclo diario vence a las 06:00 Europe/Madrid y se
recupera al siguiente arranque si el programa estaba cerrado. Mientras permanece abierto hay
actualizaciones adicionales de datos y análisis; detenido, no realiza ningún trabajo.
`GET /api/refresh/status` muestra el estado del ciclo. El histórico y los modelos se revisan al abrir; si cambió el histórico, falta un modelo o caducó, se entrenan automáticamente. Sin novedades se conserva la versión vigente. La barra global incluye datos, modelos y análisis; la aplicación y la bandeja avisan al finalizar, indicando posibles errores. En Model Lab puedes forzar la revisión con **Entrenar modelos**.

```powershell
# Actualizacion puntual solicitada manualmente
.\scripts\daily-refresh.ps1 -WaitForCompletion
```

El comando anterior puede ejecutar un worker temporal con la aplicación cerrada porque lo has
solicitado explícitamente; termina al finalizar y `stop.ps1` también puede detenerlo.
`config/refresh.yaml` controla la hora diaria interna y los intervalos. `config/learning.yaml`
configura el histórico y el entrenamiento automático mientras está abierto. `threads: auto` permite aprovechar todos los procesadores disponibles mientras está abierto; la prioridad de Windows es normal. **Detener MatchLab** termina también un entrenamiento en curso, de modo que no sigue consumiendo recursos al cerrar.

## Diagnóstico

- **No hay partidos:** revisa Settings → API-Football. Configurar un histórico de entrenamiento no proporciona una cartelera diaria. Una respuesta vacía, un plan sin cobertura o una clave ausente permanecen visibles.
- **Sin cuotas:** confirma las cuentas y mercados disponibles. Puedes introducir cuotas manuales; se etiquetan y caducan igual que las demás.
- **HTTP 429:** el cliente respeta el límite y conserva caché. Ajusta el presupuesto a tu plan, no a un número arbitrario superior.
- **PulseScore refresca despacio:** el intervalo se adapta al presupuesto mensual y páginas consumidas. Las cuotas viejas no se reutilizan como actuales en el Top.
- **DuckDB ocupado por otro proceso:** detén el segundo servidor/CLI de este proyecto. Un único backend debe poseer `data/football.duckdb`.
- **Puertos ocupados:** el arranque no sustituye procesos ajenos. Revisa qué aplicación utiliza 3000/8000 antes de arrancar.
- **Cambios en `.env`:** reinicia con `stop.ps1` y `start.ps1`. Cerrar el navegador no detiene el servidor.
- **Cambio de código web:** ejecuta `start.ps1` después de detener para recompilar. El arranque detecta cambios y compila solo cuando hacen falta; `-NoBuild` reutiliza explícitamente el bundle anterior.
- **Error de una familia ML:** Model Lab conserva la causa y el modelo anterior. Las probabilidades estadísticas siguen disponibles con muestras suficientes.

Registros: `.runtime/backend-error.log`, `.runtime/backend.log`, `.runtime/frontend-error.log` y `.runtime/daily-refresh.log`. Datos: `data/football.duckdb`, `data/historical/`, `data/models/`. Para una copia coherente de DuckDB y artefactos, detén el backend y copia la carpeta `data/`.
