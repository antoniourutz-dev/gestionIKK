# Cambios v2.3 — Carpeta «APELLIDOS, NOMBRE»

1. El PDF de **POLICLINICA** se guarda dentro de su propia carpeta personal, tanto en unidad T: como en Escritorio.
2. En los tres circuitos, la convención pasa a ser `APELLIDOS, NOMBRE` (un espacio después de la coma), por ejemplo `CONCEPCIÓN URIARTE, MARKEL`.
3. La ruta del expediente se construye en un único módulo (`document_routes.py`) para evitar diferencias entre BIHOTZ, LOGO y POLICLINICA.
4. Se añaden pruebas de ruta completa para los tres servicios y ambos destinos, sin cambiar los prefijos PDF ni el visor.
5. Los archivos se guardan por la carpeta de nuevo formato a partir de esta versión; las carpetas antiguas se dejan intactas (sin renombrado ni movimiento automático).

**Sin detección automática ni OCR.** El nombre y apellidos siguen siendo campos manuales.
