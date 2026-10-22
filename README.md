# Gestor Documental 2.4 · BIHOTZ / LOGOPEDIA / POLICLINICA

Versión incremental de la interfaz **2.2**, sin cambios en el visor avanzado ni reconocimiento automático.

## Nuevo en v2.4: BIHOTZ · ENVIAR por correo

En el panel **GESTIÓN DIARIA · BIHOTZ** aparece **ENVIAR** a continuación de **Comprimir**; no se añade a LOGOPEDIA ni POLICLINICA. Los cuatro botones permanecen en una sola fila y el formulario sigue sin desplazamiento vertical.

Flujo operativo:

1. Importa los documentos firmados del día o verifica la carpeta diaria BIHOTZ.
2. Pulsa **Comprimir**. Introduce la contraseña que autoriza el servicio. BIHOTZ genera un **7z nuevo** y sustituye el existente solo tras completar y verificar con 7-Zip la compresión correctamente, para que no sobrevivan documentos de compresiones anteriores.
3. Tras comprimir correctamente, se habilita **ENVIAR**. Si se agregan o modifican PDFs del día, el programa solicitará volver a comprimir.
4. Pulsa **ENVIAR**. Se comprobará que el archivo `.7z` pertenece a la carpeta del **día actual**, que no está vacío, que tiene cabecera 7z y que la carpeta diaria no ha cambiado desde la compresión.
5. La aplicación solicita confirmación y **abre un borrador en Outlook clásico**, dirigido a **Info@bihotz.es**, con el asunto **Volantes DD-MM-AAAA**, el mensaje bilingüe y el **BIHOTZ DD-MM-AAAA.7z** adjunto.
6. **Revisa en Outlook la cuenta remitente, el destinatario y el adjunto; pulsa Enviar en Outlook.** La aplicación no envía mensajes automáticamente ni registra un envío como completado.

El texto completo se encuentra en `bihotz_email.py` y conserva literalmente los párrafos de cortesía y confidencialidad proporcionados, con saltos de línea reales (no los códigos `%0D%0A`).

**Requisito:** Microsoft **Outlook clásico para Windows**, instalado y con una cuenta configurada y autorizada para enviar estos documentos. La integración utiliza `pywin32` y COM; **el nuevo Outlook no es compatible con este método**. No se instala ni se configura ninguna cuenta de correo automáticamente.

**Seguridad:** antes de habilitar correo con documentos médicos, la organización debe validar autorización del destinatario, canal, tipo de archivo permitido, política de contraseñas y envío seguro. El `.7z` contiene información sensible; no uses datos reales en GitHub ni en pruebas. El programa no puede verificar por sí mismo que Outlook haya enviado el mensaje.

**Tras reiniciar la aplicación** hay que volver a pulsar **Comprimir** para habilitar **ENVIAR**, aunque exista ya un `.7z`. Esto evita adjuntar sin control comprimidos antiguos. Las pruebas automatizadas usan Outlook ficticio; no abren ni envían correo real.

## Nuevo: POLICLINICA

- En **TIPO DOCUMENTAL** aparece la tercera opción **POLICLINICA**.
- Si se selecciona la unidad T:, la carpeta del expediente es `T:\00IMArrasate\AÑO\POLICLINICA\APELLIDOS, NOMBRE`. Con la fecha de 2026 se utiliza `T:\00IMArrasate\2026\POLICLINICA\...`.
- Si se selecciona **Escritorio**, se utiliza `Escritorio\APELLIDOS, NOMBRE`, igual que en los circuitos anteriores.
- El documento original se guarda como **`POLI CIC <CIC>.pdf`**. Ejemplo ficticio: `POLI CIC 12345.pdf`.
- Tras **GUARDAR DOCUMENTO**, el botón **Firmado** permite buscar en Descargas un archivo cuyo nombre comience por `POLI CIC <CIC>` y tenga extensión `.pdf`. Se pide confirmación de la lista de archivos antes de copiarlos a la carpeta del expediente.
- El botón **Comprimir** toma el **último archivo incorporado mediante Firmado** y genera un `.7z` con su mismo nombre base, en la carpeta del expediente. **No** añade una copia a BIHOTZ POR DÍAS.
- El botón **Volantes** usa la misma nomenclatura **POLI CIC** para localizar el archivo en Descargas, pide confirmación y lo copia a `T:\00Archivo_Volantes_Gipuzkoa`, igual que en las otras opciones.
- POLICLINICA no tiene selector MATIA / ARANSGI: ese selector pertenece únicamente a LOGOPEDIA.

### Contraseña de compresión POLICLINICA

La contraseña de este circuito es la **clave indicada por el servicio para POLICLINICA** (introdúcela manualmente la primera vez).

**Por seguridad no está escrita en el código ni incluida en el .exe ni en GitHub.** La primera vez que se pulse **Comprimir** (o **Configurar clave**), introducir la clave autorizada que ya tienes. La aplicación intentará recordarla en **Administrador de credenciales de Windows**, mediante la biblioteca `keyring`. En operaciones posteriores la recuperará automáticamente para comprimir; **Configurar clave** permite cambiarla si es necesario.

Si Windows no permite acceder a su almacén de credenciales, se pedirá la clave manualmente. Este mecanismo almacena la clave por cuenta de Windows, no por expediente; debe usarse solo en equipos gestionados y autorizados.

**Nota de seguridad:** las contraseñas compartidas y especialmente cortas ofrecen una protección limitada. Es recomendable que el servicio revise su política de cifrado y claves. 7-Zip recibe la clave como argumento de su proceso, por lo que podría quedar expuesta a usuarios con suficientes privilegios en el equipo. No debe subirse nunca información clínica real a GitHub.

### Qué permanece igual

- BIHOTZ: ruta, nomenclatura `BIHOTZ CIC`, carpeta diaria y compresión del día.
- LOGOPEDIA (opción **LOGO**): ruta `LOGOPEDIA`, nomenclatura `LOGO CIC`, elección MATIA/ARANSGI y compresión del documento firmado.
- Vista PDF multipágina, buscar texto manualmente, rotación, zoom y miniaturas opcionales.
- Arrastrar el PDF sobre el visor, campos rellenados manualmente, formulario sin scroll.
- Guardado en unidad T: o en Escritorio y volantes.
- Confirmación de sobrescrituras y validación del circuito activo antes de incorporar firmados.

**No se ha introducido OCR, lectura automática de CIC, nombres, apellidos ni detección automática.** El programa solo hace búsquedas por nombre de archivo a petición del operador.

La búsqueda en Descargas ahora exige la nomenclatura completa seguida de un separador o la extensión; esto impide que el CIC ficticio `12345` coincida con `123456`. Se aceptan sufijos como `_Firmado`, `(1)` o `-signed`.

## Nuevo en v2.3: formato único de carpetas por persona

Los tres circuitos (BIHOTZ, LOGO y POLICLINICA) guardan siempre el PDF original en una **subcarpeta identificada por apellidos y nombre**, tanto en la unidad T: como en el Escritorio. Se añade **un espacio tras la coma**:

- `CONCEPCIÓN URIARTE, MARKEL`
- Ejemplo en red: `T:\00IMArrasate\2026\POLICLINICA\CONCEPCIÓN URIARTE, MARKEL\POLI CIC 12345.pdf`
- Ejemplo en Escritorio: `Escritorio\CONCEPCIÓN URIARTE, MARKEL\POLI CIC 12345.pdf`

En BIHOTZ y LOGOPEDIA se aplica exactamente la misma convención; no cambia la nomenclatura de los PDF ni los demás flujos. **No se renombran ni trasladan automáticamente las carpetas anteriores** sin espacio, para evitar mover expedientes existentes sin autorización. Si una carpeta antigua tiene documentos, conviene revisarla antes de utilizar la nueva ruta.

## Instalar y ejecutar en Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Se necesita 7-Zip instalado en `C:\Program Files\7-Zip\7z.exe` o `C:\Program Files (x86)\7-Zip\7z.exe`.

## Generar GestorPDF.exe con GitHub

Sube el contenido del ZIP directamente a la raíz del repositorio (no la carpeta que los contiene). El flujo `.github/workflows/build-windows.yml` compila en Windows mediante PyInstaller y publica el artefacto `GestorPDF-Windows`.

- Si **ya usas `.github/workflows/main.yml`**, puedes conservarlo. Asegúrate de que instala el `requirements.txt` actualizado, de que ``document_routes.py` y `bihotz_email.py` están en la raíz y de añadir `--collect-all keyring` al comando PyInstaller para la recuperación de la clave.
- **No crees dos workflows de compilación** innecesarios: el archivo `build-windows.yml` del ZIP es una alternativa a tu `main.yml` actual.
- En GitHub entra en **Actions → Compilar GestorPDF para Windows → Run workflow**. Descarga el artefacto al completar la ejecución y extrae el ZIP interior antes de abrir `GestorPDF.exe`.
- PyInstaller usa `--onedir`: mantén el `.exe` junto con sus bibliotecas.

## Pruebas

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py pdf_core.py document_routes.py bihotz_email.py
```

Las pruebas verifican el motor PDF y las reglas de ruta, nomenclatura y coincidencia de los tres circuitos. **No constituyen una prueba de integración Windows**. Antes de trabajar con documentos reales, utilizar PDFs ficticios para probar guardado, Descargas, compresión real con 7-Zip, recuperación de contraseña y volantes, además de comprobar el diseño sin scroll a la escala de pantalla utilizada.

## Archivos

```
app.py
pdf_core.py
document_routes.py
bihotz_email.py
requirements.txt
.github/workflows/build-windows.yml
hooks/hook-tkinterdnd2.py
tests/test_pdf_core.py
tests/test_document_routes.py
tests/test_bihotz_email.py
README.md
CAMBIOS_2_2.md
```

Si usas `.github/workflows/main.yml` en lugar del workflow incluido, además de las dependencias actuales añade `pywin32` desde `requirements.txt` y `--hidden-import win32timezone` a PyInstaller.
