import Foundation
import SwiftData

@Model
final class Vehiculo {
    var marca: String = ""
    var modelo: String = ""
    var anio: Int = 2020
    var placa: String = ""
    var vin: String = ""
    var color: String = ""
    var kilometraje: Int = 0
    var cliente: Cliente?

    @Relationship(deleteRule: .cascade, inverse: \OrdenServicio.vehiculo)
    var ordenes: [OrdenServicio] = []

    @Relationship(deleteRule: .nullify, inverse: \Cita.vehiculo)
    var citas: [Cita] = []

    init(marca: String, modelo: String, anio: Int, placa: String,
         vin: String = "", color: String = "", kilometraje: Int = 0) {
        self.marca = marca
        self.modelo = modelo
        self.anio = anio
        self.placa = placa
        self.vin = vin
        self.color = color
        self.kilometraje = kilometraje
    }

    var descripcion: String { "\(marca) \(modelo) \(String(anio))" }

    var descripcionCorta: String {
        placa.isEmpty ? "\(marca) \(modelo)" : "\(marca) \(modelo) (\(placa))"
    }

    var ordenesRecientes: [OrdenServicio] {
        ordenes.sorted { $0.fechaIngreso > $1.fechaIngreso }
    }
}
