# Gobierno del repositorio GitHub

Repositorio privado: [AlexRS97/matchlab-local](https://github.com/AlexRS97/matchlab-local).
La publicación de este rework conserva el historial Git y mantiene el repositorio anterior separado.

## Controles configurados

- Visibilidad privada, sin publicar bases, claves ni artefactos locales.
- Squash merge habilitado; merge commits y rebase merge deshabilitados.
- Borrado de ramas fusionadas habilitado y wiki deshabilitada.
- Alertas de vulnerabilidades habilitadas.
- CODEOWNERS asignado a @AlexRS97 y política propietaria conservada.
- Workflows con token de contenido de solo lectura y Actions fijadas por SHA.
- CI para Ruff, mypy, pruebas Python, compilación web y escenarios de navegador aislados.
- Gitleaks sobre el historial y comprobación local de los cambios preparados antes del push.
- Dependabot para backend, frontend y GitHub Actions; sin fusión automática.

Las auditorías externas de dependencias se pueden ejecutar desde Security mediante el parámetro
`external_dependency_audit`; también existe `scripts/security-check.ps1 -ExternalAudits`.
Transmiten nombres y versiones a los servicios de vulnerabilidades de Python/npm.

## Límites

No se ha configurado protección obligatoria de rama ni se anuncia secret scanning nativo como
habilitado. CODEOWNERS documenta la responsabilidad, pero por sí solo no impide un push directo.
El análisis Gitleaks y CI aportan comprobaciones sin modificar la visibilidad privada del proyecto.
Los resultados efectivos de cada ejecución se consultan en Actions; una definición de workflow no
equivale a una ejecución aprobada.

Antes de incorporar colaboradores, revisar permisos y exigir los controles disponibles para el
plan de la cuenta. Las credenciales se rotan en sus proveedores si existe una exposición.
