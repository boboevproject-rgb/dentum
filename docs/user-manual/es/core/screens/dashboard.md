---
module: core
screen: dashboard
route: /
last_verified_commit: 63bb9557
---

# Panel

El panel es la pantalla inicial después de iniciar sesión. El saludo y las
tarjetas resumen el trabajo de la clínica. Las tarjetas dependen de los
módulos instalados y de tu rol, por lo que dos personas pueden ver secciones
distintas.

## Antes de iniciar sesión

Si nadie ha iniciado sesión, la misma ruta `/` muestra la página pública de
Dentum. Elige **Iniciar sesión** para continuar. En una instalación nueva se
abre la configuración inicial; después de iniciar sesión, Dentum muestra el
panel.

## Buscar una tarea

1. Usa la navegación principal para abrir pacientes, citas, presupuestos,
   informes y las demás áreas disponibles para tu cuenta.
2. Abre una tarjeta del panel para continuar con el registro o flujo de trabajo
   relacionado.
3. Si el panel está vacío, completa la configuración de la clínica y añade
   los primeros pacientes o citas. El panel de bienvenida aparece hasta que
   haya contenido de los módulos.

## Si falta una opción

Pide a una persona administradora que compruebe si el módulo correspondiente
está instalado y si tu cuenta tiene permiso para ver sus datos. Las tarjetas
se ocultan cuando el módulo o el permiso no están disponibles.
