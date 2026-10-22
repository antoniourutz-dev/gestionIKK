# Gestor Documental 2.6.1 — claves asignadas a cada servicio

Se mantiene el visor PDF, BIHOTZ, LOGOPEDIA, POLICLINICA, historial y el
borrador de correo BIHOTZ. No hay detección automática de información de pacientes.

## Compresión por servicio

La compresión usa automáticamente la contraseña fija correspondiente:
BIHOTZ, MATIA, ARANSGI, ASPACE o POLICLINICA. En LOGOPEDIA hay tres centros
seleccionables. No se solicita ni configura una clave al comprimir.

* El contenido `.7z` se cifra y solo se puede abrir o extraer con contraseña.
* Los nombres de los archivos se pueden ver en 7-Zip sin contraseña.
* Si el `.7z` ya existe, se sigue solicitando confirmación de sustitución.
* La aplicación verifica el comprimido antes de sustituirlo y conserva el
  histórico de las operaciones, cuando corresponde.

**Advertencia de seguridad:** por la exigencia de funcionar sin configuración ni
preguntas, las claves compartidas están integradas en `archive_security.py` y
pueden extraerse del ejecutable. No equivale a custodia secreta: el repositorio
y la distribución deben estar restringidos y la organización debe autorizar
este método antes de trabajar con información de salud. Los nombres visibles
en el comprimido también pueden revelar datos personales.

El botón «Claves» se retira de la interfaz porque las claves ya están asignadas.
ASPACE aparece como tercer centro de LOGOPEDIA; el correo de ASPACE mostrado
por el usuario no implica envío de correo automático.

## Compilar con GitHub Actions

Subir todos los archivos del proyecto a la raíz de `gestionIKK`, usando un único
workflow (`.github/workflows/main.yml` existente o el `build-windows.yml`
incluido). Para generar el paquete: Actions → Run workflow → Artifacts.

Se conserva `keyring` en `requirements.txt` por compatibilidad con workflows
previos que tienen `--collect-all keyring`, aunque ya no se usa para las claves.
No se deben subir PDF reales ni datos de pacientes a GitHub.

## Pruebas

`python -m unittest discover -s tests -v`

Pruebas estáticas y unitarias no equivalen a verificar 7-Zip y el ejecutable en
un PC Windows conectado a la unidad T:. Verificar con expedientes ficticios.

