import Foundation
import SwiftData

@Model
final class Cita {
    var fecha: Date = Date.now
    var duracionMinutos: Int = 60
    var motivo: String = ""
    var notas: String = ""
    var completada: Bool = false
    var cliente: Cliente?
    var vehiculo: Vehiculo?

    init(fecha: Date, duracionMinutos: Int = 60, motivo: String, notas: String = "") {
        self.fecha = fecha
        self.duracionMinutos = duracionMinutos
        self.motivo = motivo
        self.notas = notas
    }

    var fin: Date { fecha.addingTimeInterval(TimeInterval(duracionMinutos * 60)) }
}
