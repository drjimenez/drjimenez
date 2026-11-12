import Foundation
import SwiftData

@Model
final class Cliente {
    var nombre: String = ""
    var telefono: String = ""
    var correo: String = ""
    var notas: String = ""
    var fechaAlta: Date = Date.now

    @Relationship(deleteRule: .cascade, inverse: \Vehiculo.cliente)
    var vehiculos: [Vehiculo] = []

    @Relationship(deleteRule: .nullify, inverse: \Cita.cliente)
    var citas: [Cita] = []

    init(nombre: String, telefono: String = "", correo: String = "", notas: String = "") {
        self.nombre = nombre
        self.telefono = telefono
        self.correo = correo
        self.notas = notas
        self.fechaAlta = .now
    }

    var vehiculosOrdenados: [Vehiculo] {
        vehiculos.sorted { $0.descripcion < $1.descripcion }
    }

    var resumenVehiculos: String {
        if vehiculos.isEmpty { return "Sin vehículos registrados" }
        return vehiculosOrdenados.map(\.descripcionCorta).joined(separator: ", ")
    }

    var iniciales: String {
        let partes = nombre.split(separator: " ").prefix(2)
        let letras = partes.compactMap(\.first).map(String.init).joined()
        return letras.isEmpty ? "?" : letras.uppercased()
    }

    var textoBusqueda: String {
        ([nombre, telefono, correo] + vehiculos.flatMap { [$0.placa, $0.marca, $0.modelo] })
            .joined(separator: " ")
    }
}
