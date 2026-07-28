# Política de seguridad

## Versiones mantenidas

Mientras MatchLab permanezca en desarrollo privado, solo la rama `main` y la última versión
publicada reciben correcciones de seguridad.

## Comunicación responsable

No publiques vulnerabilidades, credenciales, datos personales ni detalles de explotación en una
incidencia normal.

1. Si GitHub muestra **Private vulnerability reporting**, úsalo. En caso contrario, contacta de
   forma privada al propietario `@AlexRS97` desde GitHub y solicita un canal seguro.
2. Incluye componente afectado, impacto, versión o commit, pasos mínimos de reproducción y una
   propuesta de mitigación si la conoces.
3. No accedas a datos que no sean tuyos, no mantengas persistencia y detén la prueba cuando hayas
   demostrado el impacto.

El propietario intentará confirmar la recepción en un máximo de 5 días laborables. Los plazos de
corrección dependen de la gravedad y de la disponibilidad de una solución segura.

## Secretos expuestos

Si una clave aparece en un commit, un log o una captura:

1. revócala en el proveedor inmediatamente;
2. crea una credencial nueva;
3. revisa accesos y consumo desde la última fecha conocida como segura;
4. elimina el secreto del historial cuando sea necesario;
5. documenta el incidente sin copiar el valor comprometido.

Eliminar únicamente el texto del último commit no invalida una credencial ya expuesta.

## Alcance actual

La configuración incluida está preparada para uso local enlazado a `127.0.0.1`. Antes de exponer
MatchLab a Internet son obligatorios, como mínimo: autenticación centralizada, autorización por
roles, protección CSRF donde corresponda, rate limiting distribuido, gestor externo de secretos,
TLS terminado en un proxy confiable, observabilidad, copias de seguridad cifradas y una revisión de
seguridad independiente.
