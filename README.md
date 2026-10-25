# Titan Medicación Alertas

Flujo de Mistral Workflows que revisa diariamente la base de datos
"Tratamiento de TITAN | Notificaciones" en Notion y, cuando la columna
"¿Cuantas pastillas se le ha proporcionado?" de la fila SIDENAFILO llega a
un múltiplo de 10 (dos días antes, un día antes y el mismo día), envía un
correo de recordatorio a Gmail.

Ejecución programada: todos los días a las 08:00 (America/Lima).
