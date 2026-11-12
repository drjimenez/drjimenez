import Foundation
import Observation
import SwiftData

/// Tipos de cambio a colones de las monedas extranjeras (dólar y euro).
///
/// - Automático: se consulta una vez al día. Dólar: tipo de cambio de **venta** de referencia
///   del BCCR (API pública del Ministerio de Hacienda). Euro: API de Hacienda; respaldo para
///   ambas monedas: ExchangeRate-API.
/// - Manual: el usuario registra el valor que quiere usar (por ejemplo, el de su banco).
///   Mientras el modo manual esté activo para una moneda, se usa ese valor.
/// Cada valor obtenido o registrado queda en el historial.
@Observable
final class TipoCambio {
    static let compartido = TipoCambio()

    struct Registro: Codable, Identifiable, Hashable {
        var id = UUID()
        let moneda: Moneda
        let valor: Double
        let fecha: Date
        let fuente: String
        let manual: Bool
    }

    private(set) var automatico: [Moneda: Double] = [:]
    private(set) var fechaAutomatico: [Moneda: Date] = [:]
    private(set) var fuenteAutomatico: [Moneda: String] = [:]
    private(set) var manual: [Moneda: Double] = [:]
    private(set) var fechaManual: [Moneda: Date] = [:]
    private(set) var usaManual: [Moneda: Bool] = [:]
    private(set) var historial: [Registro] = []
    private(set) var actualizando = false
    private(set) var error: String?

    private static let valoresIniciales: [Moneda: Double] = [.dolar: 505, .euro: 550]
    private static let maxHistorial = 120

    private init() { cargar() }

    // MARK: Consulta

    /// Colones por cada unidad de la moneda (1 para el colón).
    func valor(_ moneda: Moneda) -> Double {
        guard moneda != .colon else { return 1 }
        if usaManual[moneda] == true, let valor = manual[moneda], valor > 0 { return valor }
        return automatico[moneda] ?? Self.valoresIniciales[moneda] ?? 1
    }

    func esManual(_ moneda: Moneda) -> Bool { usaManual[moneda] == true }

    /// Ej.: "₡505,12 por US$1"
    func descripcion(_ moneda: Moneda) -> String {
        "\(valor(moneda).comoMoneda) por \(moneda.simbolo)1"
    }

    func detalleFuente(_ moneda: Moneda) -> String {
        if esManual(moneda) {
            let fecha = fechaManual[moneda].map { " · \($0.formatted(date: .abbreviated, time: .shortened))" } ?? ""
            return "Registrado manualmente\(fecha)"
        }
        guard let fecha = fechaAutomatico[moneda] else { return "Sin actualizar (valor de referencia)" }
        return "\(fuenteAutomatico[moneda] ?? "") · \(fecha.formatted(date: .abbreviated, time: .shortened))"
    }

    /// Fuente para imprimir en documentos (vacía si nunca se actualizó).
    func fuenteParaDocumento(_ moneda: Moneda) -> String {
        if esManual(moneda) { return "registro manual" }
        guard let fecha = fechaAutomatico[moneda] else { return "" }
        return "\(fuenteAutomatico[moneda] ?? ""), \(fecha.formatted(date: .abbreviated, time: .omitted))"
    }

    func historial(de moneda: Moneda) -> [Registro] { historial.filter { $0.moneda == moneda } }

    private var automaticoEsDeHoy: Bool {
        Moneda.extranjeras.allSatisfy { moneda in
            esManual(moneda) || (fechaAutomatico[moneda].map { Calendar.current.isDateInToday($0) } ?? false)
        }
    }

    // MARK: Registro manual

    /// Guarda un tipo de cambio escrito por el usuario y lo empieza a usar para esa moneda.
    func registrarManual(_ valor: Double, para moneda: Moneda, fecha: Date = .now) {
        guard moneda != .colon, valor > 0 else { return }
        manual[moneda] = valor.redondeado
        fechaManual[moneda] = fecha
        usaManual[moneda] = true
        agregarAlHistorial(Registro(moneda: moneda, valor: valor.redondeado, fecha: fecha,
                                    fuente: "Manual", manual: true))
        guardar()
    }

    /// Vuelve a usar el tipo de cambio automático para la moneda.
    func usarAutomatico(_ moneda: Moneda) {
        usaManual[moneda] = false
        guardar()
    }

    func borrarDelHistorial(_ registro: Registro) {
        historial.removeAll { $0.id == registro.id }
        guardar()
    }

    // MARK: Actualización automática

    @discardableResult
    func actualizarSiHaceFalta() async -> Bool {
        guard !automaticoEsDeHoy, !actualizando else { return false }
        return await actualizar()
    }

    @discardableResult
    func actualizar() async -> Bool {
        actualizando = true
        error = nil
        defer { actualizando = false }

        let dolarHacienda = await consultarDolarHacienda()
        let euroHacienda = await consultarEuroHacienda()
        var respaldo: [String: Double]?
        if dolarHacienda == nil || euroHacienda == nil {
            respaldo = await consultarExchangeRateAPI()
        }

        var faltantes: [Moneda] = []

        if let dolar = dolarHacienda {
            registrarAutomatico(dolar, para: .dolar, fuente: "BCCR · Hacienda")
        } else if let tasas = respaldo, let crc = tasas["CRC"], crc > 0 {
            registrarAutomatico(crc, para: .dolar, fuente: "ExchangeRate-API")
        } else {
            faltantes.append(.dolar)
        }

        if let euro = euroHacienda {
            registrarAutomatico(euro, para: .euro, fuente: "BCCR · Hacienda")
        } else if let tasas = respaldo, let crc = tasas["CRC"], let eur = tasas["EUR"], eur > 0 {
            registrarAutomatico(crc / eur, para: .euro, fuente: "ExchangeRate-API")
        } else {
            faltantes.append(.euro)
        }

        guardar()
        if !faltantes.isEmpty {
            let nombres = faltantes.map(\.nombreSingular).joined(separator: " y ")
            error = "No se pudo obtener el tipo de cambio del \(nombres). Puedes registrarlo manualmente."
        }
        return faltantes.isEmpty
    }

    private func registrarAutomatico(_ valor: Double, para moneda: Moneda, fuente: String) {
        let redondeado = valor.redondeado
        let yaRegistradoHoy = fechaAutomatico[moneda].map { Calendar.current.isDateInToday($0) } ?? false
        automatico[moneda] = redondeado
        fechaAutomatico[moneda] = .now
        fuenteAutomatico[moneda] = fuente
        if !(yaRegistradoHoy && historial.first(where: { $0.moneda == moneda && !$0.manual })?.valor == redondeado) {
            agregarAlHistorial(Registro(moneda: moneda, valor: redondeado, fecha: .now, fuente: fuente, manual: false))
        }
    }

    private func agregarAlHistorial(_ registro: Registro) {
        historial.insert(registro, at: 0)
        if historial.count > Self.maxHistorial { historial.removeLast(historial.count - Self.maxHistorial) }
    }

    // MARK: Fuentes

    private struct RespuestaDolarHacienda: Decodable {
        struct Indicador: Decodable { let valor: Double }
        let venta: Indicador
    }

    private struct RespuestaEuroHacienda: Decodable {
        let colones: Double
    }

    private struct RespuestaExchangeRate: Decodable {
        let rates: [String: Double]
    }

    private func consultarDolarHacienda() async -> Double? {
        guard let datos = await descargar("https://api.hacienda.go.cr/indicadores/tc/dolar"),
              let respuesta = try? JSONDecoder().decode(RespuestaDolarHacienda.self, from: datos),
              respuesta.venta.valor > 0 else { return nil }
        return respuesta.venta.valor
    }

    private func consultarEuroHacienda() async -> Double? {
        guard let datos = await descargar("https://api.hacienda.go.cr/indicadores/tc/euro"),
              let respuesta = try? JSONDecoder().decode(RespuestaEuroHacienda.self, from: datos),
              respuesta.colones > 0 else { return nil }
        return respuesta.colones
    }

    private func consultarExchangeRateAPI() async -> [String: Double]? {
        guard let datos = await descargar("https://open.er-api.com/v6/latest/USD"),
              let respuesta = try? JSONDecoder().decode(RespuestaExchangeRate.self, from: datos) else { return nil }
        return respuesta.rates
    }

    private func descargar(_ direccion: String) async -> Data? {
        guard let url = URL(string: direccion) else { return nil }
        var solicitud = URLRequest(url: url, timeoutInterval: 12)
        solicitud.setValue("application/json", forHTTPHeaderField: "Accept")
        guard let (datos, respuesta) = try? await URLSession.shared.data(for: solicitud),
              (respuesta as? HTTPURLResponse)?.statusCode == 200 else { return nil }
        return datos
    }

    // MARK: Persistencia

    private struct Estado: Codable {
        var automatico: [String: Double] = [:]
        var fechaAutomatico: [String: Date] = [:]
        var fuenteAutomatico: [String: String] = [:]
        var manual: [String: Double] = [:]
        var fechaManual: [String: Date] = [:]
        var usaManual: [String: Bool] = [:]
        var historial: [Registro] = []
    }

    private static let clave = "tiposDeCambio.v2"

    private func guardar() {
        func porCodigo<V>(_ d: [Moneda: V]) -> [String: V] {
            Dictionary(uniqueKeysWithValues: d.map { ($0.key.rawValue, $0.value) })
        }
        let estado = Estado(automatico: porCodigo(automatico), fechaAutomatico: porCodigo(fechaAutomatico),
                            fuenteAutomatico: porCodigo(fuenteAutomatico), manual: porCodigo(manual),
                            fechaManual: porCodigo(fechaManual), usaManual: porCodigo(usaManual),
                            historial: historial)
        if let datos = try? JSONEncoder().encode(estado) {
            UserDefaults.standard.set(datos, forKey: Self.clave)
        }
    }

    private func cargar() {
        guard let datos = UserDefaults.standard.data(forKey: Self.clave),
              let estado = try? JSONDecoder().decode(Estado.self, from: datos) else { return }
        func porMoneda<V>(_ d: [String: V]) -> [Moneda: V] {
            Dictionary(uniqueKeysWithValues: d.compactMap { k, v in Moneda(rawValue: k).map { ($0, v) } })
        }
        automatico = porMoneda(estado.automatico)
        fechaAutomatico = porMoneda(estado.fechaAutomatico)
        fuenteAutomatico = porMoneda(estado.fuenteAutomatico)
        manual = porMoneda(estado.manual)
        fechaManual = porMoneda(estado.fechaManual)
        usaManual = porMoneda(estado.usaManual)
        historial = estado.historial
    }
}

/// Recalcula en colones los repuestos en moneda extranjera de las órdenes abiertas con el tipo
/// de cambio vigente. Las órdenes ya facturadas conservan el tipo de cambio con que se emitieron.
enum RevalorizacionMonedas {
    static func aplicar(en context: ModelContext, tipoCambio: TipoCambio = .compartido) {
        guard let lineas = try? context.fetch(FetchDescriptor<LineaOrden>()) else { return }
        for linea in lineas {
            guard let precio = linea.precioExtranjero,
                  linea.monedaOrigen != .colon,
                  let orden = linea.orden,
                  orden.factura == nil,
                  orden.estado.esActiva else { continue }
            let tc = tipoCambio.valor(linea.monedaOrigen)
            let nuevoPrecio = (precio * tc).redondeado
            if linea.precioUnitario != nuevoPrecio || linea.tipoCambio != tc {
                linea.precioUnitario = nuevoPrecio
                linea.tipoCambio = tc
            }
        }
    }
}
