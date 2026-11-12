# Taller Mecánico · App para iOS 26+

Aplicación nativa para iPhone y iPad (iOS 26 o posterior) para administrar un taller mecánico.
Está hecha con **SwiftUI** + **SwiftData** y usa el diseño **Liquid Glass** de iOS 26.
Todos los datos se guardan en el dispositivo; no necesita servidor.

**Moneda oficial: colón costarricense (₡).** Los repuestos que se compran en **dólares (US$)** se
registran en dólares y se convierten a colones con el **tipo de cambio del día**, que la app consulta
automáticamente (tipo de cambio de venta de referencia del BCCR, publicado por la API del Ministerio de
Hacienda; respaldo: ExchangeRate-API). Mientras una orden no se factura, sus repuestos en dólares se
recalculan cada día; al emitir la factura se congela el tipo de cambio y se imprime en el documento.

## Funciones

| Sección | Qué hace |
|---|---|
| **Inicio** | Panel con órdenes activas, vehículos listos para entregar, ingresos del mes, citas de hoy y refacciones por reabastecer. |
| **Órdenes** | Órdenes de servicio con folio consecutivo (`OS-00001`), estado (recibido → diagnóstico → autorización → refacciones → reparación → listo → entregado), kilometraje, nivel de combustible, problema reportado, diagnóstico, mano de obra, refacciones, IVA, anticipo y saldo. Genera la orden en **PDF** y la comparte (WhatsApp, correo, AirDrop, imprimir…). |
| **Clientes** | Clientes con sus vehículos (marca, modelo, año, placas, VIN, color, km), historial de servicio por vehículo y botones para llamar, abrir WhatsApp o enviar correo. |
| **Inventario** | Refacciones con código, marca, ubicación, existencia, mínimo, costo, precio y margen, en colones o en dólares (con su equivalente en colones del día). Al agregar una refacción a una orden se descuenta del inventario (y se devuelve si se borra la línea). Alertas de stock bajo. |
| **Facturación** | Desde una orden se genera la factura al cliente (folio `FAC-00001`): detalle de mano de obra con **tiempo** (horas) y tarifa, repuestos/refacciones, subtotal, IVA, **total de la reparación**, **anticipo** descontado y saldo a pagar, días en taller y **garantía de 30 días** en mano de obra con fechas de vigencia. Se exporta a **PDF tamaño carta**, se imprime por AirPrint, se **envía por correo** (PDF adjunto, dirigido al correo del cliente, con resumen del saldo y la garantía) o se comparte. Lista de facturas con total facturado, saldo por cobrar y garantías vigentes (botón 📄 en *Órdenes*). |
| **Agenda** | Calendario de citas con cliente y vehículo; una cita se puede convertir en orden de servicio. |
| **Ajustes** | Datos del taller para el PDF (incluye cédula jurídica), IVA (13 % por omisión), tipo de cambio del dólar (automático o manual), días de garantía, términos y condiciones, datos de ejemplo y borrado. |

## Requisitos

- Mac con **Xcode 26** o posterior
- iPhone/iPad con **iOS/iPadOS 26** o posterior (o el simulador)

## Cómo abrirla y ejecutarla

1. Abre `TallerMecanico/TallerMecanico.xcodeproj` en Xcode.
2. En *Signing & Capabilities* elige tu equipo (Team). Si hace falta, cambia el
   *Bundle Identifier* (`com.drjimenez.TallerMecanico`).
3. Elige un simulador o tu iPhone y pulsa **Run** (⌘R).
4. Ve a **Inicio → ⚙︎ Ajustes → Cargar datos de ejemplo** para probarla con datos de demostración.

## Estructura

```
TallerMecanico/
├── TallerMecanico.xcodeproj
└── TallerMecanico/
    ├── TallerMecanicoApp.swift      # Punto de entrada y contenedor de SwiftData
    ├── Modelos/                     # Cliente, Vehiculo, OrdenServicio, LineaOrden, Refaccion, Cita, estados
    ├── Vistas/
    │   ├── ContentView.swift        # Barra de pestañas
    │   ├── Inicio/  Ordenes/  Clientes/  Inventario/  Agenda/  Ajustes/
    │   └── Componentes/             # Tarjetas, insignias de estado, botones de contacto
    ├── Utilidades/                  # Preferencias, PDF, datos de ejemplo
    └── Assets.xcassets              # Ícono y color de acento
```

El proyecto usa carpetas sincronizadas de Xcode: cualquier archivo `.swift` que agregues dentro
de `TallerMecanico/TallerMecanico/` se incluye automáticamente en la app.

## Compilación automática

El workflow `.github/workflows/ios-taller.yml` compila la app en GitHub Actions (macOS 26)
cada vez que cambia algo dentro de `TallerMecanico/`.

## Ideas para siguientes versiones

- Sincronización entre dispositivos con iCloud (CloudKit)
- Fotos del vehículo al recibirlo (cámara)
- Recordatorios de servicio por kilometraje o fecha (notificaciones)
- Usuarios/técnicos y asignación de órdenes
- Facturación electrónica (CFDI) mediante un proveedor externo
