# Gobierno del repositorio GitHub

Repositorio: `AlexRS97/matchlab-football-analytics`

## Controles activos

- visibilidad privada;
- sin colaboradores externos, salvo alta explícita posterior;
- `main` como rama predeterminada;
- squash merge como única estrategia de fusión;
- borrado automático de ramas fusionadas;
- sign-off obligatorio para commits creados desde la web;
- `CODEOWNERS` asignado a `@AlexRS97`;
- GitHub Actions con permisos de contenido de solo lectura;
- workflows sin permiso para aprobar pull requests;
- solo acciones oficiales de GitHub y referencias fijadas por SHA completo;
- CI de backend, frontend y contenedores;
- Gitleaks automático sobre el historial;
- Dependabot Alerts y correcciones automáticas;
- actualizaciones semanales de dependencias mediante pull requests;
- plantillas de pull request e incidencias;
- licencia propietaria, aviso de terceros y política de seguridad.

## Limitaciones verificadas del plan

En un repositorio privado de la cuenta actual, GitHub ha rechazado:

- branch protection para `main`, indicando que requiere GitHub Pro o hacer público el repositorio;
- secret scanning y push protection nativos;
- el endpoint de private vulnerability reporting.

Hacer público el repositorio para obtener algunas funciones gratuitas no es una compensación
aceptable para un proyecto propietario. Por ello se mantiene privado.

## Controles compensatorios

- Gitleaks se ejecuta localmente antes de publicar y en GitHub después de cada push.
- `.env`, claves, certificados, bases locales, backups e informes quedan excluidos de Git.
- El token de Actions es de solo lectura y las dependencias de Actions están fijadas.
- Todos los cambios automáticos de Dependabot llegan como pull requests; no existe auto-merge.
- La rama principal se verifica con CI aunque el plan no pueda bloquear técnicamente un push directo.

`CODEOWNERS` documenta propiedad, pero no puede exigir aprobación por sí solo sin protección de
rama. Si se añade GitHub Pro, la primera medida debe ser exigir pull request, historial lineal,
resolución de conversaciones y los checks `Backend quality`, `Frontend build`, `Container builds`
y `Secret history scan`.

## Revisión de accesos

Trimestralmente y después de cualquier incidente:

1. revisar colaboradores, deploy keys, webhooks, GitHub Apps y tokens;
2. eliminar accesos inactivos;
3. comprobar autenticación multifactor del propietario;
4. revisar ejecuciones de Actions y alertas de Dependabot;
5. rotar credenciales con sospecha de exposición;
6. restaurar una copia de seguridad de prueba.
