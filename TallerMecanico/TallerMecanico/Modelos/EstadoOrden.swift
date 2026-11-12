import SwiftUI

enum EstadoOrden: String, CaseIterable, Identifiable, Codable {
    case recibido
    case diagnostico
    case esperandoAutorizacion
    case esperandoRefacciones
    case enReparacion
    case listo
    case entregado
    case cancelado

    var id: String { rawValue }

    var titulo: String {
        switch self {
        case .recibido: "Recibido"
        case .diagnostico: "En diagnóstico"
        case .esperandoAutorizacion: "Esperando autorización"
        case .esperandoRefacciones: "Esperando refacciones"
        case .enReparacion: "En reparación"
        case .listo: "Listo para entregar"
        case .entregado: "Entregado"
        case .cancelado: "Cancelado"
        }
    }

    var icono: String {
        switch self {
        case .recibido: "tray.and.arrow.down.fill"
        case .diagnostico: "stethoscope"
        case .esperandoAutorizacion: "hand.raised.fill"
        case .esperandoRefacciones: "shippingbox.fill"
        case .enReparacion: "wrench.and.screwdriver.fill"
        case .listo: "checkmark.seal.fill"
        case .entregado: "car.side.fill"
        case .cancelado: "xmark.circle.fill"
        }
    }

    var color: Color {
        switch self {
        case .recibido: .gray
        case .diagnostico: .purple
        case .esperandoAutorizacion: .orange
        case .esperandoRefacciones: .yellow
        case .enReparacion: .blue
        case .listo: .green
        case .entregado: .teal
        case .cancelado: .red
        }
    }

    var progreso: Double {
        switch self {
        case .recibido: 0.1
        case .diagnostico: 0.25
        case .esperandoAutorizacion: 0.4
        case .esperandoRefacciones: 0.5
        case .enReparacion: 0.7
        case .listo: 0.9
        case .entregado: 1
        case .cancelado: 0
        }
    }

    /// Una orden activa es la que todavía ocupa lugar en el taller.
    var esActiva: Bool { self != .entregado && self != .cancelado }

    static var activos: [EstadoOrden] { allCases.filter(\.esActiva) }
}

enum TipoLinea: String, CaseIterable, Identifiable, Codable {
    case manoDeObra
    case refaccion

    var id: String { rawValue }

    var titulo: String {
        switch self {
        case .manoDeObra: "Mano de obra"
        case .refaccion: "Refacción"
        }
    }

    var icono: String {
        switch self {
        case .manoDeObra: "person.badge.clock.fill"
        case .refaccion: "gearshape.2.fill"
        }
    }
}
