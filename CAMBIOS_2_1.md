# Gestor PDF 2.1 — Ajustes visuales

## Qué se ha modificado

- La columna lateral de miniaturas ya no ocupa espacio: desaparece en PDFs de una página y puede mostrarse en una tira horizontal para PDFs multipágina mediante **Ver miniaturas**.
- El formulario de datos es fijo: **no utiliza desplazamiento vertical**. Nombre y apellidos se presentan en dos columnas; se han compactado los botones de las acciones para mostrar BIHOTZ/LOGO.
- El área principal de visualización es también el área de arrastrar archivos. Con el visor vacío aparece la instrucción de arrastrar o hacer clic. No existe una segunda zona de arrastre en el formulario.
- El visor continúa siendo de solo lectura, con zoom, navegación, giro visual y búsqueda manual.
- No se han añadido reconocimiento de documentos, lectura automática de CIC, IA ni OCR.

## Actualizar GitHub

**Opción sencilla:** sustituye el archivo `app.py` del repositorio por el de este paquete. Si ya tienes la anterior entrega, `pdf_core.py`, `requirements.txt`, los tests y el workflow siguen siendo compatibles.

**Opción completa:** sube todo el contenido de este ZIP a la raíz del repositorio, manteniendo la carpeta oculta `.github/workflows/`.

Si ya creaste `.github/workflows/main.yml` para compilar, puedes mantenerlo y no subir además `build-windows.yml`; así evitas dos workflows de compilación. En GitHub, pulsa **Actions** > tu workflow > **Run workflow** y descarga el ZIP generado en **Artifacts**.

## Comprobación previa al uso real

1. Abre un PDF de 1 página: no debe verse el botón de miniaturas.
2. Abre un PDF multipágina: botón **Ver miniaturas** > tira horizontal > **Ocultar miniaturas**.
3. Arrastra un PDF al gran visor (con y sin otro documento abierto).
4. Alterna BIHOTZ / LOGO y comprueba que las acciones siguen accesibles sin desplazamiento vertical.
5. Prueba el guardado en Escritorio con archivos ficticios; comprueba con tu servicio los destinos de la unidad T: antes de operar con documentos reales.

La interfaz modificada no se ha validado en una sesión real de Windows desde este entorno. Las pruebas del motor PDF pasan y el código supera la verificación de sintaxis.
