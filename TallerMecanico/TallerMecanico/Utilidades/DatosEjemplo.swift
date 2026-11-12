import Foundation
import SwiftData

enum DatosEjemplo {
    static func cargar(en context: ModelContext) {
        let ahora = Date.now
        let cal = Calendar.current

        // Inventario
        let aceite = Refaccion(nombre: "Aceite sintético 5W-30 (L)", codigo: "ACE-530", marca: "Mobil",
                               ubicacion: "Estante A1", existencia: 24, existenciaMinima: 10, costo: 145, precioVenta: 210)
        let filtroAceite = Refaccion(nombre: "Filtro de aceite", codigo: "FA-1021", marca: "Fram",
                                     ubicacion: "Estante A2", existencia: 8, existenciaMinima: 5, costo: 90, precioVenta: 160)
        let balatas = Refaccion(nombre: "Balatas delanteras cerámicas", codigo: "BD-778", marca: "Brembo",
                                ubicacion: "Estante B1", existencia: 2, existenciaMinima: 3, costo: 620, precioVenta: 980)
        let bujia = Refaccion(nombre: "Bujía iridio", codigo: "BJ-IR4", marca: "NGK",
                              ubicacion: "Cajón C3", existencia: 16, existenciaMinima: 8, costo: 115, precioVenta: 190)
        let anticongelante = Refaccion(nombre: "Anticongelante (galón)", codigo: "ANT-G", marca: "Prestone",
                                       ubicacion: "Estante A3", existencia: 1, existenciaMinima: 4, costo: 260, precioVenta: 390)
        [aceite, filtroAceite, balatas, bujia, anticongelante].forEach { context.insert($0) }

        // Clientes y vehículos
        let ana = Cliente(nombre: "Ana López", telefono: "55 1234 5678", correo: "ana@example.com")
        let carlos = Cliente(nombre: "Carlos Ramírez", telefono: "33 9876 5432")
        let flotilla = Cliente(nombre: "Transportes del Norte", telefono: "81 5555 0101",
                               correo: "flotilla@example.com", notas: "Facturar a nombre de la empresa.")
        [ana, carlos, flotilla].forEach { context.insert($0) }

        let versa = Vehiculo(marca: "Nissan", modelo: "Versa", anio: 2021, placa: "ABC-123-D", color: "Gris", kilometraje: 48_200)
        let jetta = Vehiculo(marca: "Volkswagen", modelo: "Jetta", anio: 2018, placa: "JKL-456-M", color: "Blanco", kilometraje: 96_500)
        let hilux = Vehiculo(marca: "Toyota", modelo: "Hilux", anio: 2022, placa: "NL-7788-X", color: "Rojo", kilometraje: 61_000)
        [versa, jetta, hilux].forEach { context.insert($0) }
        versa.cliente = ana
        jetta.cliente = carlos
        hilux.cliente = flotilla

        // Órdenes
        func linea(_ tipo: TipoLinea, _ desc: String, _ cant: Double, _ precio: Double,
                   _ orden: OrdenServicio, _ ref: Refaccion? = nil) {
            let l = LineaOrden(tipo: tipo, descripcion: desc, cantidad: cant, precioUnitario: precio)
            context.insert(l)
            l.orden = orden
            l.refaccion = ref
        }

        let o1 = OrdenServicio(folio: 1, problemaReportado: "Servicio de mantenimiento de 50,000 km.",
                               kilometraje: 48_200, nivelCombustible: 0.75)
        context.insert(o1)
        o1.vehiculo = versa
        o1.estado = .enReparacion
        o1.diagnostico = "Mantenimiento preventivo. Se recomienda revisar balatas en el siguiente servicio."
        o1.fechaPromesa = cal.date(byAdding: .hour, value: 5, to: ahora)
        linea(.manoDeObra, "Servicio de afinación", 1, 850, o1)
        linea(.refaccion, aceite.nombre, 4, aceite.precioVenta, o1, aceite)
        linea(.refaccion, filtroAceite.nombre, 1, filtroAceite.precioVenta, o1, filtroAceite)
        linea(.refaccion, bujia.nombre, 4, bujia.precioVenta, o1, bujia)

        let o2 = OrdenServicio(folio: 2, problemaReportado: "Rechinido al frenar.", kilometraje: 96_500,
                               nivelCombustible: 0.25, anticipo: 500)
        context.insert(o2)
        o2.vehiculo = jetta
        o2.estado = .esperandoRefacciones
        o2.diagnostico = "Balatas delanteras al 10%. Discos dentro de tolerancia."
        linea(.manoDeObra, "Cambio de balatas delanteras", 1.5, 450, o2)

        let o3 = OrdenServicio(folio: 3, problemaReportado: "Sobrecalentamiento en tráfico.", kilometraje: 60_800)
        context.insert(o3)
        o3.vehiculo = hilux
        o3.fechaIngreso = cal.date(byAdding: .day, value: -6, to: ahora) ?? ahora
        o3.diagnostico = "Termostato pegado y anticongelante degradado."
        linea(.manoDeObra, "Reemplazo de termostato y purga del sistema", 2, 450, o3)
        linea(.refaccion, "Termostato", 1, 680, o3)
        linea(.refaccion, anticongelante.nombre, 2, anticongelante.precioVenta, o3, anticongelante)
        o3.estado = .entregado

        let o4 = OrdenServicio(folio: 4, problemaReportado: "Revisión de luz de check engine.", kilometraje: 61_000)
        context.insert(o4)
        o4.vehiculo = hilux
        o4.estado = .listo
        o4.diagnostico = "Sensor de oxígeno con lectura intermitente; se limpió conector."
        linea(.manoDeObra, "Escaneo y diagnóstico electrónico", 1, 600, o4)

        // Citas
        let inicioHoy = cal.startOfDay(for: ahora)
        let c1 = Cita(fecha: cal.date(byAdding: .hour, value: 10, to: inicioHoy) ?? ahora, motivo: "Alineación y balanceo")
        let c2 = Cita(fecha: cal.date(byAdding: .hour, value: 16, to: inicioHoy) ?? ahora, duracionMinutos: 90,
                      motivo: "Diagnóstico de suspensión")
        let c3 = Cita(fecha: cal.date(byAdding: .hour, value: 33, to: inicioHoy) ?? ahora, motivo: "Servicio de frenos")
        [c1, c2, c3].forEach { context.insert($0) }
        c1.cliente = ana; c1.vehiculo = versa
        c2.cliente = flotilla; c2.vehiculo = hilux
        c3.cliente = carlos; c3.vehiculo = jetta

        try? context.save()
    }

    static func borrarTodo(en context: ModelContext) {
        try? context.delete(model: LineaOrden.self)
        try? context.delete(model: OrdenServicio.self)
        try? context.delete(model: Cita.self)
        try? context.delete(model: Vehiculo.self)
        try? context.delete(model: Cliente.self)
        try? context.delete(model: Refaccion.self)
        try? context.save()
    }
}
