# Novedades 2.4 · ENVIAR BIHOTZ

- Botón **ENVIAR** solo en BIHOTZ, junto a Crear día, Abrir día y Comprimir.
- Correo de Outlook clásico con destinatario `Info@bihotz.es`, asunto `Volantes DD-MM-AAAA` y cuerpo bilingüe literal.
- Se adjunta el 7z correspondiente a la carpeta diaria `BIHOTZ DD-MM-AAAA`, de la unidad T:.
- El correo **solo se prepara**: requiere pulsar Enviar en Outlook; nunca se envía automáticamente.
- ENVIAR se habilita tras comprimir correctamente en la sesión y se bloquea si la carpeta del día o el comprimido cambian.
- Comprimir BIHOTZ crea un 7z nuevo temporal y reemplaza el anterior tras comprobar firma 7z y superar la comprobación de integridad de 7-Zip.
- `bihotz_email.py` separa textos, preparación del borrador y comprobaciones.
- Se añade `pywin32` (Windows) y el import oculto `win32timezone` al workflow de PyInstaller.
- Ni LOGOPEDIA ni POLICLINICA ni el visor cambian su funcionalidad.
- No se realiza detección automática de datos.
