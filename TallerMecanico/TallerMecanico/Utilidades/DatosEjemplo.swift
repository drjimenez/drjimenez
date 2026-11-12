import Foundation
import SwiftData

enum DatosEjemplo {
    static func cargar(en context: ModelContext) {
        let ahora = Date.now
        let cal = Calendar.current

        // Inventario (precios en colones; las pastillas de freno se compran en dólares)
        let aceite = Refaccion(nombre: "Aceite sintético 5W-30 (L)", codigo: "ACE-530", marca: "Mobil",
                               ubicacion: "Estante A1", existencia: 24, existenciaMinima: 10, costo: 4_200, precioVenta: 6_000)
        let filtroAceite = Refaccion(nombre: "Filtro de aceite", codigo: "FA-1021", marca: "Fram",
                                     ubicacion: "Estante A2", existencia: 8, existenciaMinima: 5, costo: 2_800, precioVenta: 4_500)
        let pastillas = Refaccion(nombre: "Pastillas de freno delanteras cerámicas", codigo: "BD-778", marca: "Brembo",
                                  ubicacion: "Estante B1", existencia: 2, existenciaMinima: 3, costo: 38, precioVenta: 60,
                                  moneda: .dolar)
        let bujia = Refaccion(nombre: "Bujía iridio", codigo: "BJ-IR4", marca: "NGK",
                              ubicacion: "Cajón C3", existencia: 16, existenciaMinima: 8, costo: 3_200, precioVenta: 5_000)
        let anticongelante = Refaccion(nombre: "Refrigerante (galón)", codigo: "ANT-G", marca: "Prestone",
                                       ubicacion: "Estante A3", existencia: 1, existenciaMinima: 4, costo: 7_500, precioVenta: 11_000)
        let sensor = Refaccion(nombre: "Sensor de temperatura", codigo: "ST-2210", marca: "Denso",
                               ubicacion: "Cajón C1", existencia: 3, existenciaMinima: 1, costo: 18, precioVenta: 29,
                               moneda: .dolar)
        let filtroCabina = Refaccion(nombre: "Filtro de cabina con carbón activado", codigo: "FC-0451", marca: "Bosch",
                                     ubicacion: "Estante A4", existencia: 6, existenciaMinima: 2, costo: 14, precioVenta: 22,
                                     moneda: .euro)
        [aceite, filtroAceite, pastillas, bujia, anticongelante, sensor, filtroCabina].forEach { context.insert($0) }

        // Clientes y vehículos
        let ana = Cliente(nombre: "Ana López", telefono: "8812 3456", correo: "ana@example.com")
        let carlos = Cliente(nombre: "Carlos Ramírez", telefono: "7012 9876")
        let flotilla = Cliente(nombre: "Transportes del Norte", telefono: "2222 0101",
                               correo: "flotilla@example.com", notas: "Facturar a nombre de la empresa.")
        [ana, carlos, flotilla].forEach { context.insert($0) }

        let versa = Vehiculo(marca: "Nissan", modelo: "Versa", anio: 2021, placa: "BCD-123", color: "Gris", kilometraje: 48_200)
        let jetta = Vehiculo(marca: "Volkswagen", modelo: "Jetta", anio: 2018, placa: "SJB-456", color: "Blanco", kilometraje: 96_500)
        let hilux = Vehiculo(marca: "Toyota", modelo: "Hilux", anio: 2022, placa: "CL-278812", color: "Rojo", kilometraje: 61_000)
        [versa, jetta, hilux].forEach { context.insert($0) }
        versa.cliente = ana
        jetta.cliente = carlos
        hilux.cliente = flotilla

        // Órdenes
        let tc = TipoCambio.compartido
        func linea(_ tipo: TipoLinea, _ desc: String, _ cant: Double, _ precio: Double,
                   _ orden: OrdenServicio, _ ref: Refaccion? = nil) {
            let l = LineaOrden(tipo: tipo, descripcion: desc, cantidad: cant, precioUnitario: precio)
            if let moneda = ref?.moneda, moneda != .colon {
                l.fijarPrecioExtranjero(precio, en: moneda, tipoCambio: tc.valor(moneda))
            }
            context.insert(l)
            l.orden = orden
            l.refaccion = ref
        }

        let o1 = OrdenServicio(folio: 1, problemaReportado: "Servicio de mantenimiento de 50 000 km.",
                               kilometraje: 48_200, nivelCombustible: 0.75)
        context.insert(o1)
        o1.vehiculo = versa
        o1.estado = .enReparacion
        o1.diagnostico = "Mantenimiento preventivo. Se recomienda revisar pastillas de freno en el siguiente servicio."
        o1.fechaPromesa = cal.date(byAdding: .hour, value: 5, to: ahora)
        linea(.manoDeObra, "Servicio de afinación", 1.5, 15_000, o1)
        linea(.refaccion, aceite.nombre, 4, aceite.precioVenta, o1, aceite)
        linea(.refaccion, filtroAceite.nombre, 1, filtroAceite.precioVenta, o1, filtroAceite)
        linea(.refaccion, bujia.nombre, 4, bujia.precioVenta, o1, bujia)
        linea(.refaccion, filtroCabina.nombre, 1, filtroCabina.precioVenta, o1, filtroCabina)

        let o2 = OrdenServicio(folio: 2, problemaReportado: "Rechinido al frenar.", kilometraje: 96_500,
                               nivelCombustible: 0.25, anticipo: 15_000)
        context.insert(o2)
        o2.vehiculo = jetta
        o2.estado = .esperandoRefacciones
        o2.diagnostico = "Pastillas delanteras al 10 %. Discos dentro de tolerancia."
        linea(.manoDeObra, "Cambio de pastillas de freno delanteras", 1.5, 15_000, o2)
        linea(.refaccion, pastillas.nombre, 1, pastillas.precioVenta, o2, pastillas)

        let o3 = OrdenServicio(folio: 3, problemaReportado: "Sobrecalentamiento en presas.", kilometraje: 60_800,
                               anticipo: 30_000)
        context.insert(o3)
        o3.vehiculo = hilux
        o3.fechaIngreso = cal.date(byAdding: .day, value: -6, to: ahora) ?? ahora
        o3.diagnostico = "Termostato pegado, sensor de temperatura defectuoso y refrigerante degradado."
        linea(.manoDeObra, "Reemplazo de termostato y purga del sistema", 2, 15_000, o3)
        linea(.manoDeObra, "Cambio de sensor de temperatura", 0.5, 15_000, o3)
        linea(.refaccion, "Termostato", 1, 18_500, o3)
        linea(.refaccion, sensor.nombre, 1, sensor.precioVenta, o3, sensor)
        linea(.refaccion, anticongelante.nombre, 2, anticongelante.precioVenta, o3, anticongelante)
        o3.estado = .entregado
        let factura = Factura(folio: 1, diasGarantia: 30, metodoPago: .transferencia)
        factura.fuenteTipoCambio = "US$: \(tc.detalleFuente(.dolar))"
        context.insert(factura)
        factura.orden = o3

        let o4 = OrdenServicio(folio: 4, problemaReportado: "Revisión de luz de check engine.", kilometraje: 61_000)
        context.insert(o4)
        o4.vehiculo = hilux
        o4.estado = .listo
        o4.diagnostico = "Sensor de oxígeno con lectura intermitente; se limpió el conector."
        linea(.manoDeObra, "Escaneo y diagnóstico electrónico", 1, 20_000, o4)

        // Citas
        let inicioHoy = cal.startOfDay(for: ahora)
        let c1 = Cita(fecha: cal.date(byAdding: .hour, value: 10, to: inicioHoy) ?? ahora, motivo: "Alineación y balanceo")
        let c2 = Cita(fecha: cal.date(byAdding: .hour, value: 16, to: inicioHoy) ?? ahora, duracionMinutos: 90,
                      motivo: "Diagnóstico de suspensión")
        let c3 = Cita(fecha: cal.date(byAdding: .hour, value: 33, to: inicioHoy) ?? ahora, motivo: "Revisión de frenos")
        [c1, c2, c3].forEach { context.insert($0) }
        c1.cliente = ana; c1.vehiculo = versa
        c2.cliente = flotilla; c2.vehiculo = hilux
        c3.cliente = carlos; c3.vehiculo = jetta

        try? context.save()
    }

    static func borrarTodo(en context: ModelContext) {
        try? context.delete(model: Factura.self)
        try? context.delete(model: LineaOrden.self)
        try? context.delete(model: OrdenServicio.self)
        try? context.delete(model: Cita.self)
        try? context.delete(model: Vehiculo.self)
        try? context.delete(model: Cliente.self)
        try? context.delete(model: Refaccion.self)
        try? context.save()
    }
}
