import Foundation
import SwiftData

@Model
final class LineaOrden {
    var tipoRaw: String = TipoLinea.manoDeObra.rawValue
    var descripcion: String = ""
    var cantidad: Double = 1
    var precioUnitario: Double = 0
    var creada: Date = Date.now
    var orden: OrdenServicio?
    /// Refacción del inventario de la que se descontó existencia (si aplica).
    var refaccion: Refaccion?
    /// Precio unitario en dólares cuando el repuesto se compró en US$.
    /// `precioUnitario` guarda su equivalente en colones con `tipoCambio`.
    var precioUSD: Double?
    var tipoCambio: Double?

    init(tipo: TipoLinea, descripcion: String, cantidad: Double, precioUnitario: Double) {
        self.tipoRaw = tipo.rawValue
        self.descripcion = descripcion
        self.cantidad = cantidad
        self.precioUnitario = precioUnitario
        self.creada = .now
    }

    var tipo: TipoLinea {
        get { TipoLinea(rawValue: tipoRaw) ?? .manoDeObra }
        set { tipoRaw = newValue.rawValue }
    }

    var importe: Double { (cantidad * precioUnitario).redondeado }

    var esEnDolares: Bool { precioUSD != nil }

    /// Ej.: "2 × ₡6 000,00" o "2 × US$60,00 (TC ₡505,12)"
    var detallePrecio: String {
        let cantidadTexto = tipo == .manoDeObra ? "\(cantidad.formatted()) h" : cantidad.formatted()
        if let precioUSD {
            let tc = tipoCambio.map { " (TC \($0.comoMoneda))" } ?? ""
            return "\(cantidadTexto) × \(precioUSD.comoDolares)\(tc)"
        }
        return "\(cantidadTexto) × \(precioUnitario.comoMoneda)"
    }

    /// Unidades que esta línea descuenta del inventario.
    var unidadesInventario: Int { Int(cantidad.rounded()) }
}
