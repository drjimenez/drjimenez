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

    var importe: Double { cantidad * precioUnitario }

    /// Unidades que esta línea descuenta del inventario.
    var unidadesInventario: Int { Int(cantidad.rounded()) }
}
