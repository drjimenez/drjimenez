import Foundation

/// Monedas que maneja el taller. La moneda oficial es el colón costarricense;
/// algunos repuestos se compran en dólares estadounidenses o en euros.
enum Moneda: String, CaseIterable, Identifiable, Codable {
    case colon = "CRC"
    case dolar = "USD"
    case euro = "EUR"

    var id: String { rawValue }

    var simbolo: String {
        switch self {
        case .colon: "₡"
        case .dolar: "US$"
        case .euro: "€"
        }
    }

    var nombre: String {
        switch self {
        case .colon: "Colones (₡)"
        case .dolar: "Dólares (US$)"
        case .euro: "Euros (€)"
        }
    }

    var nombreCorto: String {
        switch self {
        case .colon: "₡"
        case .dolar: "US$"
        case .euro: "€"
        }
    }

    var nombreSingular: String {
        switch self {
        case .colon: "colón"
        case .dolar: "dólar"
        case .euro: "euro"
        }
    }

    var icono: String {
        switch self {
        case .colon: "coloncurrencysign.circle.fill"
        case .dolar: "dollarsign.circle.fill"
        case .euro: "eurosign.circle.fill"
        }
    }

    /// Monedas extranjeras que requieren tipo de cambio.
    static var extranjeras: [Moneda] { [.dolar, .euro] }

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
    func como(_ moneda: Moneda) -> String { moneda.formatear(self) }

    /// Redondeo a céntimos.
    var redondeado: Double { (self * 100).rounded() / 100 }
}
