# GestorPDF 2.0 · Visor avanzado y diseño profesional

Primera evolución de tu aplicación de escritorio BIHOTZ / LOGOPEDIA.

**No se ha incorporado detección automática de CIC, pacientes, nombres, apellidos, clasificación, OCR ni IA.** Los campos siguen rellenándose por una persona. La búsqueda de texto solo se ejecuta si el usuario escribe y pulsa **Buscar**.

## Cambios visibles

- Interfaz moderna, clara y distribuida entre visor y formulario.
- Navegación por todas las páginas: anterior, siguiente e ir a página.
- Miniaturas con selección y paginación en bloques de 10.
- Zoom +/- (y Ctrl + rueda), ajustar ancho y ajustar página.
- Rotación visual 90° sin editar ni guardar cambios en el PDF.
- Búsqueda manual en el texto existente del PDF, con coincidencias resaltadas, resultado siguiente/anterior. **No realiza OCR**: en PDFs escaneados como imagen puede no encontrar texto.
- Barra de estado y atajos Ctrl+O para abrir y Ctrl+F para buscar.
- Se mantienen las acciones: guardar, abrir carpeta, firmados, volantes, crear/abrir/comprimir día BIHOTZ y compresión LOGOPEDIA.

## Configuración conservada

- Unidad T: para documentos: `T:\00IMArrasate\AÑO\BIHOTZ` o `...\LOGOPEDIA` (el año pasa a ser el actual).
- Documentos diarios: `T:\00IMArrasate\AÑO\BIHOTZ POR DIAS\BIHOTZ dd-mm-aaaa`.
- Volantes: `T:\00Archivo_Volantes_Gipuzkoa`.
- Descargas del usuario Windows actual: `Path.home() / "Downloads"`.
- Los PDFs de origen se copian, no se mueven.
- **Las claves de los archivos 7z no se guardan en el código:** la aplicación las solicita al comprimir. Si no recuerdas la contraseña autorizada, consúltala con el responsable correspondiente. No la incluyas en GitHub.
- Para comprimir se requiere instalar [7-Zip](https://www.7-zip.org/) en Windows.

### Precauciones

Esta edición está centrada en el visor y el aspecto visual. Aunque se han añadido confirmaciones antes de sobrescribir, la operación 'Firmado' sigue utilizando la coincidencia de nombres en la carpeta Descargas como en el programa original. **No valida firmas electrónicas.** Comprueba siempre que los archivos propuestos pertenecen al expediente correcto.

No subas a GitHub PDFs reales, datos de pacientes ni contraseñas. Prueba primero con documentos ficticios y un destino local. `Crear carpeta del día` y otras operaciones de la unidad T: escriben en ubicaciones reales.

## Ejecutar en Windows desde el código

Instala Python 3.12 y ejecuta desde la carpeta del proyecto:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

## Crear el .exe con GitHub Actions

1. Crea un repositorio **privado** de GitHub (o utiliza el tuyo).
2. Sube todos los archivos de esta carpeta respetando la estructura oculta `.github/workflows/build-windows.yml`.
3. En la pestaña **Actions**, selecciona **Compilar GestorPDF para Windows**.
4. Pulsa **Run workflow**.
5. Al finalizar, descarga el artefacto **GestorPDF-Windows**. Dentro contiene `GestorPDF-Windows.zip`.
6. Descomprime el paquete en Windows y ejecuta **GestorPDF.exe**, manteniendo los archivos y subcarpetas que acompañan al `.exe`.

Alternativamente, crear un tag de versión `v2.0.0` activa la compilación.

Por fiabilidad con CustomTkinter, se distribuye en modo **onedir**: no es un `.exe` único; es un `.exe` más sus bibliotecas, empaquetados en un ZIP. No se adjunta un `.exe` compilado: lo generará GitHub Actions en Windows.

## Verificaciones

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py pdf_core.py
```

Las pruebas incluidas verifican la apertura de documentos, renderizado, miniaturas, rotación, búsqueda y resaltado. Antes de utilizar el programa en producción hay que validar visualmente la interfaz y los circuitos de archivo en un Windows de pruebas con 7-Zip.

## Estructura

```
app.py                           # Interfaz y operaciones existentes
pdf_core.py                      # Motor PDF en lectura, sin Tkinter
requirements.txt
hooks/hook-tkinterdnd2.py        # Incluye binarios de arrastrar y soltar
.github/workflows/build-windows.yml
.gitignore
tests/test_pdf_core.py
```
