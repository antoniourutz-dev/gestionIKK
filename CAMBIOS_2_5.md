# Gestor Documental 2.5 · HISTORIAL DE TRABAJOS

## Qué incluye

La pantalla principal incorpora un botón **Historial** junto a **Abrir PDF**, sin quitar espacio al visor ni incluir desplazamiento vertical en el formulario. Atajo: **Ctrl+H**.

La ventana de historial tiene:

- Fecha en formato **DD-MM-AAAA**, flechas para día anterior/siguiente y botón **Hoy**.
- Opción **Todas las fechas** (muestra hasta los 2.000 registros más recientes) y filtro de circuito: TODOS, BIHOTZ, LOGO o POLICLINICA.
- Tabla ordenada con **fecha y hora, circuito, operación, carpeta y archivo**.
- Panel que muestra la ubicación completa de la operación, los archivos PDF/7z actualmente existentes en su carpeta y botones **Abrir archivo**, **Abrir carpeta** y **Abrir archivo seleccionado**. Doble clic para abrir un PDF/7z en su aplicación asociada de Windows.
- Accesos **Ver carpeta BIHOTZ de la fecha** y **Mostrar sus archivos**, incluso para fechas anteriores a instalar esta versión. Este último muestra el ZIP/7z diario en su carpeta contenedora si existe.

## Qué operaciones quedan registradas

- Guardar el documento original en su carpeta de expediente.
- Incorporar documentos desde Descargas (registro separado para expediente y para carpeta BIHOTZ del día cuando corresponde).
- Archivar documentos en Volantes.
- Preparar/abrir la carpeta BIHOTZ del día.
- Generar el 7z diario BIHOTZ.
- Preparar el borrador de Outlook BIHOTZ (registrado explícitamente como **borrador preparado, no enviado**).
- Comprimir documento firmado de LOGOPEDIA o POLICLINICA.

Solo se registran operaciones efectuadas: no se anotan copias rechazadas ni intentos de compresión fallidos. Si una copia al expediente se completa pero falla una segunda copia al día, permanece registrado el primer resultado correcto. Las entradas no certifican que un archivo continúe en su ruta: al abrirlo se comprueba la existencia.

## Persistencia, privacidad y límites

- Se guarda en una base **SQLite local** del perfil de Windows: `%LOCALAPPDATA%\GestorPDF\historial.sqlite3`.
- El historial sobrevive al cierre/reinicio de la aplicación y a nuevas compilaciones .exe **si se utiliza la misma cuenta de Windows y no se borra AppData**.
- **No se guarda en GitHub ni dentro del .exe**, y no almacena PDF, contenido extraído, contraseñas ni cuerpos de mensajes. **Sí almacena las rutas de documentos, que pueden contener nombres o identificadores personales:** utilízalo solo en equipos y perfiles autorizados, con las políticas de privacidad y copias de seguridad pertinentes. SQLite no añade cifrado automático.
- Es un historial **por usuario/perfil Windows, no compartido entre todos los ordenadores**. No colocar esta SQLite directamente en una unidad de red compartida sin diseñar una solución multiusuario.
- La fecha consultada filtra la **fecha en la que se registró la operación**, no la de creación interna del PDF.
- El historial **no conserva versiones antiguas**: si un PDF fue sobrescrito o trasladado más tarde, su fila conserva la ruta y al abrirla se muestra el archivo actual, si existe.
- No se crea retrospectivamente un registro completo de operaciones de versiones anteriores; sin embargo, el acceso por fecha a carpetas históricas BIHOTZ permite consultar los PDFs y 7z existentes en la unidad T:.
- Abrir un archivo depende de que siga existiendo y se tenga acceso a la ubicación y al programa asociado. Los archivos en Descargas que nunca llegaron a guardarse no quedan registrados.
- Por seguridad, la lista solo permite abrir archivos `.pdf` y `.7z`, nunca ejecutables.
- Si el disco o el perfil local no permiten escribir, se informa del fallo de registro sin cancelar una operación de copia que haya concluido con éxito.

## Actualizar GitHub y compilar

Sube `app.py`, **`history_store.py` (nuevo)**, **`history_window.py` (nuevo)** y **`tests/test_history_store.py` (nuevo)**, junto al resto del proyecto. Si ya tienes `.github/workflows/main.yml`, **conserva uno solo** e incluye los dos módulos en las comprobaciones de sintaxis opcionales. PyInstaller incorpora módulos importados por `app.py` sin opciones extras para SQLite (biblioteca estándar). Mantén las opciones `--collect-all keyring` y `--hidden-import win32timezone` de v2.4.

Para el trabajo clínico real, primero compila y verifica en Windows con **documentos ficticios**: guardado, firmado, Volantes, compresión, historial, apertura de carpeta y acceso a días pasados. Las pruebas unitarias ejecutadas no sustituyen estas pruebas manuales.
