# Seguridad de la aplicación local

La versión activa ejecuta FastAPI y React/Vite en loopback y guarda datos en DuckDB.
No incorpora cuentas de usuario y está destinada al uso personal local.

## Fronteras y controles implementados

```text
API-Football / Betfair / PulseScore / Football-Data
                     |
         adaptadores HTTP, validación y caché
                     |
        FastAPI 127.0.0.1:8000 ---- DuckDB local
                     |
           React/Vite 127.0.0.1:3000
```

El backend guarda las claves como configuración privada y devuelve únicamente su estado de
disponibilidad. `.env`, certificados, bases de datos y artefactos quedan fuera de Git.
Los logs de transporte no incluyen cabeceras de autenticación ni cuerpos con secretos.

FastAPI restringe hosts y orígenes del navegador y rechaza mutaciones procedentes de orígenes
ajenos. Añade cabeceras contra interpretación de tipos y carga en marcos. Estos controles no
sustituyen una autenticación para acceso remoto.

Betfair utiliza una lista de operaciones de consulta permitidas; no hay operaciones de órdenes.
Las respuestas externas se validan antes de usarse. Timeouts, reintentos acotados, presupuestos y
circuit breaker contienen los fallos de proveedores. Una asociación ambigua entre eventos no
adjunta cuotas al partido.

Los scripts de arranque no reemplazan servicios ajenos que ocupen los puertos. El cierre identifica
procesos de este proyecto por su ruta absoluta y sus descendientes. La configuración actual es
manual, sin inicio con Windows ni tareas instaladas. El worker puntual reutiliza la API si está
activa para evitar un segundo proceso conectado a DuckDB; véase la guía de Windows.

Los modelos de árboles se guardan en formatos nativos y PyTorch carga pesos con `weights_only`.
Solo deben cargarse artefactos producidos por este proyecto y conservados bajo control del usuario.
El identificador de la versión se valida antes de formar la ruta. Las pruebas utilizan almacenes
aislados y no insertan datos de demostración en la base operativa.

## Operación

Mantén las credenciales en `.env` de la raíz o `backend/.env`, nunca en variables `VITE_*`.
Si una clave se expone, revócala en su proveedor y reinicia con una nueva. Para copiar DuckDB
coherentemente, detén el backend y copia `data/`.

Exponer esta aplicación a Internet requeriría autenticación, autorización, TLS y una revisión
del modelo de despliegue. La configuración actual no pretende cubrir ese escenario.
