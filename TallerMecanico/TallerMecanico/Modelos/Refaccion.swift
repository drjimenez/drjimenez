import Foundation
import SwiftData

@Model
final class Refaccion {
    var nombre: String = ""
    var codigo: String = ""
    var marca: String = ""
    var ubicacion: String = ""
    var existencia: Int = 0
    var existenciaMinima: Int = 1
    var costo: Double = 0
    var precioVenta: Double = 0
    /// Moneda en que se compra y se cotiza el repuesto (colones o dólares).
    var monedaRaw: String = Moneda.colon.rawValue

    @Relationship(deleteRule: .nullify, inverse: \LineaOrden.refaccion)
    var usos: [LineaOrden] = []

    init(nombre: String, codigo: String = "", marca: String = "", ubicacion: String = "",
         existencia: Int = 0, existenciaMinima: Int = 1, costo: Double = 0, precioVenta: Double = 0,
         moneda: Moneda = .colon) {
        self.monedaRaw = moneda.rawValue
        self.nombre = nombre
        self.codigo = codigo
        self.marca = marca
        self.ubicacion = ubicacion
        self.existencia = existencia
        self.existenciaMinima = existenciaMinima
        self.costo = costo
        self.precioVenta = precioVenta
    }

    var stockBajo: Bool { existencia <= existenciaMinima }

    var margen: Double {
        guard precioVenta > 0 else { return 0 }
        return (precioVenta - costo) / precioVenta
    }

    var moneda: Moneda {
        get { Moneda(rawValue: monedaRaw) ?? .colon }
        set { monedaRaw = newValue.rawValue }
    }

    func enColones(_ monto: Double, con tipoCambio: TipoCambio) -> Double {
        (monto * tipoCambio.valor(moneda)).redondeado
    }

    /// Valor del inventario en colones (a costo).
    func valorInventario(con tipoCambio: TipoCambio) -> Double {
        Double(max(0, existencia)) * enColones(costo, con: tipoCambio)
    }

    var textoBusqueda: String { "\(nombre) \(codigo) \(marca) \(ubicacion)" }
}
