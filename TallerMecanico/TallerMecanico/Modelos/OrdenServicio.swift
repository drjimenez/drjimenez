import Foundation
import SwiftData

@Model
final class OrdenServicio {
    var folio: Int = 0
    var fechaIngreso: Date = Date.now
    var fechaPromesa: Date?
    var fechaEntrega: Date?
    var estadoRaw: String = EstadoOrden.recibido.rawValue
    var problemaReportado: String = ""
    var diagnostico: String = ""
    var observaciones: String = ""
    var kilometraje: Int = 0
    /// Nivel de combustible al recibir el vehículo (0 = vacío, 1 = lleno).
    var nivelCombustible: Double = 0.5
    var tasaIVA: Double = 0.13
    var anticipo: Double = 0
    var vehiculo: Vehiculo?

    @Relationship(deleteRule: .cascade, inverse: \LineaOrden.orden)
    var lineas: [LineaOrden] = []

    @Relationship(deleteRule: .cascade, inverse: \Factura.orden)
    var factura: Factura?

    init(folio: Int, problemaReportado: String, kilometraje: Int,
         nivelCombustible: Double = 0.5, tasaIVA: Double = 0.13, anticipo: Double = 0) {
        self.folio = folio
        self.fechaIngreso = .now
        self.problemaReportado = problemaReportado
        self.kilometraje = kilometraje
        self.nivelCombustible = nivelCombustible
        self.tasaIVA = tasaIVA
        self.anticipo = anticipo
    }

    var estado: EstadoOrden {
        get { EstadoOrden(rawValue: estadoRaw) ?? .recibido }
        set {
            estadoRaw = newValue.rawValue
            if newValue == .entregado {
                if fechaEntrega == nil { fechaEntrega = .now }
            } else {
                fechaEntrega = nil
            }
        }
    }

    var folioTexto: String { String(format: "OS-%05d", folio) }

    var lineasOrdenadas: [LineaOrden] { lineas.sorted { $0.creada < $1.creada } }

    func lineas(de tipo: TipoLinea) -> [LineaOrden] {
        lineasOrdenadas.filter { $0.tipo == tipo }
    }

    var totalManoDeObra: Double { lineas(de: .manoDeObra).reduce(0) { $0 + $1.importe } }
    var totalRefacciones: Double { lineas(de: .refaccion).reduce(0) { $0 + $1.importe } }
    /// Tiempo total de mano de obra (la cantidad de cada línea de mano de obra se captura en horas).
    var horasManoDeObra: Double { lineas(de: .manoDeObra).reduce(0) { $0 + $1.cantidad } }

    /// Días naturales que el vehículo estuvo en el taller.
    var diasEnTaller: Int {
        let cal = Calendar.current
        let fin = fechaEntrega ?? .now
        return max(0, cal.dateComponents([.day], from: cal.startOfDay(for: fechaIngreso),
                                         to: cal.startOfDay(for: fin)).day ?? 0)
    }

    var tieneLineasEnMonedaExtranjera: Bool { lineas.contains { $0.esEnMonedaExtranjera } }

    /// Tipos de cambio aplicados en la orden, por moneda (ej. US$ → 505,12; € → 550,20).
    var tiposDeCambioAplicados: [TipoCambioAplicado] {
        Moneda.extranjeras.compactMap { moneda in
            let valores = lineas.filter { $0.esEnMonedaExtranjera && $0.monedaOrigen == moneda }.compactMap(\.tipoCambio)
            guard let valor = valores.first else { return nil }
            return TipoCambioAplicado(moneda: moneda, valor: valor)
        }
    }

    var subtotal: Double { totalManoDeObra + totalRefacciones }
    var iva: Double { (subtotal * tasaIVA * 100).rounded() / 100 }
    var total: Double { subtotal + iva }
    var saldo: Double { max(0, total - anticipo) }

    var estaRetrasada: Bool {
        guard estado.esActiva, let fechaPromesa else { return false }
        return fechaPromesa < .now
    }

    var textoBusqueda: String {
        [folioTexto, vehiculo?.placa ?? "", vehiculo?.descripcion ?? "",
         vehiculo?.cliente?.nombre ?? "", problemaReportado]
            .joined(separator: " ")
    }
}

struct TipoCambioAplicado: Identifiable, Hashable {
    let moneda: Moneda
    let valor: Double
    var id: Moneda { moneda }
}
