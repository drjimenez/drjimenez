import Foundation

/// Monedas que maneja el taller. La moneda oficial es el colón costarricense;
/// algunos repuestos se compran en dólares estadounidenses.
enum Moneda: String, CaseIterable, Identifiable, Codable {
    case colon = "CRC"
    case dolar = "USD"

    var id: String { rawValue }

    var simbolo: String {
        switch self {
        case .colon: "₡"
        case .dolar: "US$"
        }
    }

    var nombre: String {
        switch self {
        case .colon: "Colones (₡)"
        case .dolar: "Dólares (US$)"
        }
    }

    private static let localeCR = Locale(identifier: "es_CR")

    /// Ej.: ₡27 376,00 · US$60,00
    func formatear(_ valor: Double) -> String {
        let numero = abs(valor).formatted(.number.precision(.fractionLength(2)).locale(Self.localeCR))
        return (valor < 0 ? "-" : "") + simbolo + numero
    }
}

extension Double {
    /// Monto en la moneda oficial (colones).
    var comoMoneda: String { Moneda.colon.formatear(self) }
    var comoDolares: String { Moneda.dolar.formatear(self) }

    /// Redondeo a céntimos.
    var redondeado: Double { (self * 100).rounded() / 100 }
}
