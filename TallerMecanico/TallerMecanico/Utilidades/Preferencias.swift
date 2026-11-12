import Foundation

/// Claves y valores de configuración compartidos (guardados en UserDefaults / @AppStorage).
enum Preferencias {
    static let nombreTallerKey = "nombreTaller"
    static let direccionKey = "direccionTaller"
    static let telefonoKey = "telefonoTaller"
    static let rfcKey = "rfcTaller"
    static let terminosKey = "terminosOrden"
    static let ivaKey = "tasaIVA"
    static let monedaKey = "moneda"
    static let diasGarantiaKey = "diasGarantia"

    static let monedaPredeterminada = Locale.current.currency?.identifier ?? "MXN"
    static let terminosPredeterminados = """
    El taller no se hace responsable por objetos dejados en el vehículo. \
    Las refacciones cuentan con la garantía del fabricante. \
    Vehículos no recogidos después de 15 días de terminados generarán cargo por pensión.
    """

    static var moneda: String {
        UserDefaults.standard.string(forKey: monedaKey) ?? monedaPredeterminada
    }

    static var diasGarantia: Int {
        UserDefaults.standard.object(forKey: diasGarantiaKey) as? Int ?? 30
    }

    static var tasaIVA: Double {
        UserDefaults.standard.object(forKey: ivaKey) as? Double ?? 0.16
    }
}

struct DatosTaller {
    var nombre: String
    var direccion: String
    var telefono: String
    var rfc: String
    var terminos: String

    static var actual: DatosTaller {
        let d = UserDefaults.standard
        return DatosTaller(
            nombre: d.string(forKey: Preferencias.nombreTallerKey) ?? "Mi Taller",
            direccion: d.string(forKey: Preferencias.direccionKey) ?? "",
            telefono: d.string(forKey: Preferencias.telefonoKey) ?? "",
            rfc: d.string(forKey: Preferencias.rfcKey) ?? "",
            terminos: d.string(forKey: Preferencias.terminosKey) ?? Preferencias.terminosPredeterminados
        )
    }
}

extension Double {
    var comoMoneda: String { formatted(.currency(code: Preferencias.moneda)) }
}

extension String {
    var limpio: String { trimmingCharacters(in: .whitespacesAndNewlines) }
}
