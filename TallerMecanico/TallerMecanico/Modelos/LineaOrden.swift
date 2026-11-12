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
    /// Precio unitario en la moneda extranjera (US$ o €) cuando el repuesto se compró en ella.
    /// `precioUnitario` guarda su equivalente en colones calculado con `tipoCambio`.
    var precioExtranjero: Double?
    var monedaExtranjeraRaw: String?
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

    var monedaOrigen: Moneda {
        monedaExtranjeraRaw.flatMap(Moneda.init(rawValue:)) ?? .colon
    }

    var esEnMonedaExtranjera: Bool { precioExtranjero != nil && monedaOrigen != .colon }

    func fijarPrecioExtranjero(_ precio: Double, en moneda: Moneda, tipoCambio tc: Double) {
        precioExtranjero = precio
        monedaExtranjeraRaw = moneda.rawValue
        tipoCambio = tc
        precioUnitario = (precio * tc).redondeado
    }

    /// Precio unitario en su moneda original (ej. "US$60,00", "€45,00" o "₡6 000,00").
    var precioOriginalTexto: String {
        if esEnMonedaExtranjera, let precioExtranjero { return precioExtranjero.como(monedaOrigen) }
        return precioUnitario.comoMoneda
    }

    /// Ej.: "2 × ₡6 000,00" o "2 × US$60,00 (TC ₡505,12)"
    var detallePrecio: String {
        let cantidadTexto = tipo == .manoDeObra ? "\(cantidad.formatted()) h" : cantidad.formatted()
        if esEnMonedaExtranjera {
            let tc = tipoCambio.map { " (TC \($0.comoMoneda))" } ?? ""
            return "\(cantidadTexto) × \(precioOriginalTexto)\(tc)"
        }
        return "\(cantidadTexto) × \(precioUnitario.comoMoneda)"
    }

    /// Unidades que esta línea descuenta del inventario.
    var unidadesInventario: Int { Int(cantidad.rounded()) }
}
