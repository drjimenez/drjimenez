import Foundation

/// Claves y valores de configuración compartidos (guardados en UserDefaults / @AppStorage).
enum Preferencias {
    static let nombreTallerKey = "nombreTaller"
    static let direccionKey = "direccionTaller"
    static let telefonoKey = "telefonoTaller"
    static let rfcKey = "rfcTaller"
    static let terminosKey = "terminosOrden"
    static let ivaKey = "tasaIVA"
    static let diasGarantiaKey = "diasGarantia"

    /// Moneda oficial de la app: colón costarricense.
    static let moneda = Moneda.colon.rawValue
    static let terminosPredeterminados = """
    El taller no se hace responsable por objetos dejados en el vehículo. \
    Las refacciones cuentan con la garantía del fabricante. \
    Vehículos no recogidos después de 15 días de terminados generarán cargo por pensión.
    """

    static var diasGarantia: Int {
        UserDefaults.standard.object(forKey: diasGarantiaKey) as? Int ?? 30
    }

    static var tasaIVA: Double {
        UserDefaults.standard.object(forKey: ivaKey) as? Double ?? 0.13
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

extension String {
    var limpio: String { trimmingCharacters(in: .whitespacesAndNewlines) }
}
