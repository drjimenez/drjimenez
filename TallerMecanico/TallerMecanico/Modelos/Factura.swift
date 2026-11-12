import Foundation
import SwiftData

enum MetodoPago: String, CaseIterable, Identifiable, Codable {
    case efectivo, tarjeta, transferencia, otro

    var id: String { rawValue }

    var titulo: String {
        switch self {
        case .efectivo: "Efectivo"
        case .tarjeta: "Tarjeta"
        case .transferencia: "Transferencia"
        case .otro: "Otro"
        }
    }
}

@Model
final class Factura {
    var folio: Int = 0
    var fechaEmision: Date = Date.now
    /// Días de garantía sobre la mano de obra (30 por omisión).
    var diasGarantia: Int = 30
    var metodoPagoRaw: String = MetodoPago.efectivo.rawValue
    var notas: String = ""
    var orden: OrdenServicio?
    /// Origen de los tipos de cambio congelados al emitir la factura (cada línea guarda el suyo).
    var fuenteTipoCambio: String = ""

    init(folio: Int, diasGarantia: Int = 30, metodoPago: MetodoPago = .efectivo, notas: String = "") {
        self.folio = folio
        self.fechaEmision = .now
        self.diasGarantia = diasGarantia
        self.metodoPagoRaw = metodoPago.rawValue
        self.notas = notas
    }

    var metodoPago: MetodoPago {
        get { MetodoPago(rawValue: metodoPagoRaw) ?? .efectivo }
        set { metodoPagoRaw = newValue.rawValue }
    }

    var folioTexto: String { String(format: "FAC-%05d", folio) }

    /// La garantía corre desde la entrega del vehículo (o la emisión si aún no se entrega).
    var inicioGarantia: Date { orden?.fechaEntrega ?? fechaEmision }

    var finGarantia: Date {
        Calendar.current.date(byAdding: .day, value: diasGarantia, to: inicioGarantia) ?? inicioGarantia
    }

    var garantiaVigente: Bool { Date.now <= finGarantia }

    var diasRestantesGarantia: Int {
        let cal = Calendar.current
        let dias = cal.dateComponents([.day], from: cal.startOfDay(for: .now),
                                      to: cal.startOfDay(for: finGarantia)).day ?? 0
        return max(0, dias)
    }

    var textoBusqueda: String {
        [folioTexto, orden?.folioTexto ?? "", orden?.vehiculo?.cliente?.nombre ?? "",
         orden?.vehiculo?.placa ?? ""].joined(separator: " ")
    }
}
