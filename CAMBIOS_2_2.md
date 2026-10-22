# Cambios v2.2 — POLICLINICA

1. Nueva opción **POLICLINICA** en TIPO DOCUMENTAL (junto a BIHOTZ y LOGO).
2. Ruta en red `T:\00IMArrasate\AÑO\POLICLINICA` o Escritorio; subcarpeta del expediente con apellidos y nombre.
3. Nomenclatura de fichero `POLI CIC <CIC>.pdf`.
4. Importación manual de firmado desde Descargas mediante patrón `POLI CIC <CIC>`, con confirmación de archivos.
5. Compresión del último PDF firmado en su misma carpeta, con la clave definida para ese circuito, almacenada mediante el administrador de credenciales de Windows tras la primera entrada. No queda incrustada en GitHub ni en el ejecutable.
6. Opción **Volantes** disponible usando el mismo patrón `POLI CIC <CIC>` y la carpeta de volantes ya existente.
7. El selector MATIA/ARANSGI sigue siendo exclusivo de LOGO.
8. Se conservan el visor avanzado y el formulario fijo sin scroll de la v2.1. No se incluye OCR ni detección automática.
9. Si se cambia el tipo documental, se invalida el expediente guardado en memoria para evitar copiar firmados a carpetas de otro circuito. Si cambian los datos o el destino, se exige guardar nuevamente antes de incorporar firmados.
10. Búsqueda en Descargas: coincidencia exacta de CIC y solo archivos PDF completos.
11. Nuevo módulo `document_routes.py`, tests para los tres circuitos, dependencia `keyring` y actualización de GitHub Actions.
