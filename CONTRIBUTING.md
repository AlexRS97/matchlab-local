# Política de contribuciones

MatchLab es un proyecto propietario y privado. No se aceptan contribuciones externas salvo
autorización previa y escrita del propietario.

## Requisitos de una contribución autorizada

- Crea una rama desde `main` y abre un pull request.
- No hagas push directo a `main`.
- Explica el problema, el enfoque, los riesgos y cómo se ha verificado.
- Añade o actualiza pruebas para cualquier cambio de comportamiento.
- No incluyas secretos, datos reales de usuarios, respuestas privadas de proveedores ni material
  de terceros sin licencia compatible.
- Mantén los commits pequeños, descriptivos y, cuando la cuenta lo permita, firmados.
- Resuelve todos los controles de CI y las conversaciones de revisión antes de fusionar.

## Propiedad intelectual

Al enviar una contribución autorizada, declaras que tienes derecho a aportar el contenido y que no
incorpora código confidencial de terceros. La integración de una contribución requiere un acuerdo
escrito que defina expresamente su licencia o cesión; la mera apertura de un pull request no obliga
al propietario a aceptarla.

## Estilo de documentación

Se documenta el **porqué**, los invariantes, límites, efectos laterales y decisiones difíciles. No
se comentan operaciones evidentes línea por línea. Una modificación de arquitectura, seguridad,
datos o predicción debe actualizar el documento técnico correspondiente.

## Comprobaciones locales

```powershell
.\scripts\check.ps1
.\scripts\security-check.ps1
```
