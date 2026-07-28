# Arquitectura de seguridad

## Principios

1. **Privado por defecto.** El código y los datos operativos no se publican.
2. **Mínimo privilegio.** Procesos, tokens y flujos CI reciben solo los permisos necesarios.
3. **Secretos fuera de Git.** `.env` y credenciales reales nunca se versionan.
4. **Defensa en profundidad.** Validación, aislamiento de contenedores, auditoría de dependencias y
   controles del repositorio se complementan; ninguno se considera suficiente por sí solo.
5. **Trazabilidad.** Cambios por pull request, commits identificables y comprobaciones reproducibles.
6. **Fallo seguro.** En producción una configuración insegura debe impedir el arranque, no degradar
   silenciosamente la protección.

## Activos

- Código fuente, modelos probabilísticos y reglas de recomendación.
- Clave de API-Football, credenciales de base de datos y futuros tokens de despliegue.
- Histórico de partidos, snapshots de features, predicciones y cuotas.
- Identidad visual, documentación técnica y decisiones de arquitectura.
- Integridad de imágenes de contenedor y dependencias.

## Fronteras de confianza

```text
Internet / proveedor
        |
        v
API-Football client -- validación y presupuesto de llamadas
        |
        v
worker / beat ---- Redis interno
        |
        v
PostgreSQL interno
        |
        v
FastAPI (127.0.0.1:8000) <----> Next.js (127.0.0.1:3000)
```

PostgreSQL y Redis no publican puertos al host. API y web solo se enlazan a loopback en el perfil
local. Los contenedores de aplicación usan usuarios sin privilegios y `no-new-privileges`.

## Controles del repositorio

- repositorio privado y acceso explícito;
- licencia propietaria y avisos de terceros;
- `CODEOWNERS` para exigir revisión del propietario;
- CI con permisos de solo lectura;
- acciones externas fijadas por SHA completo;
- pruebas, Ruff, mypy, compilación de Next.js y auditorías de dependencias;
- Gitleaks sobre el historial;
- Dependabot semanal con límite de pull requests;
- política de divulgación privada;
- reglas de rama/ruleset para `main`, cuando el plan de GitHub lo permita.

## Gestión de secretos

Desarrollo local usa `.env`, ignorado por Git. Producción no debe utilizar archivos persistentes con
credenciales: debe inyectarlas desde un gestor como AWS Secrets Manager, Azure Key Vault, Google
Secret Manager, Doppler o el mecanismo equivalente del proveedor elegido.

Las credenciales deben ser distintas por entorno, rotables, de alcance mínimo y sin exposición en
variables `NEXT_PUBLIC_*`. Una variable con ese prefijo puede terminar en el navegador y nunca debe
contener un secreto.

## Riesgos pendientes antes de Internet

El producto actual no incorpora cuentas de usuario. Por tanto, los endpoints administrativos solo
son aceptables porque la API se expone en loopback. Antes de un despliegue público se debe:

1. separar API pública y plano administrativo;
2. autenticar mediante OIDC y autorizar por roles;
3. añadir rate limiting por identidad y dirección;
4. proteger tareas costosas contra repetición e idempotencia incorrecta;
5. aplicar TLS, HSTS y cabeceras desde un proxy de confianza;
6. cifrar copias de seguridad y probar restauraciones;
7. centralizar logs sin secretos y crear alertas;
8. realizar SAST/DAST y pentest independiente;
9. definir retención y borrado de datos;
10. revisar términos del proveedor, privacidad y normativa de juego aplicable.

## Respuesta a incidentes

La secuencia mínima es contener, revocar, preservar evidencias, corregir, recuperar, verificar y
documentar. Nunca se debe reutilizar una clave expuesta aunque se haya eliminado del repositorio.
