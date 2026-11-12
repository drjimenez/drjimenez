import Foundation
import Observation
import SwiftData

/// Tipo de cambio colón/dólar del día.
/// Fuente principal: API pública del Ministerio de Hacienda, que publica el tipo de
/// cambio de referencia del Banco Central de Costa Rica (BCCR). Respaldo: ExchangeRate-API.
/// Se usa el tipo de cambio de **venta**, que es lo que paga el taller para comprar dólares.
@Observable
final class TipoCambio {
    static let compartido = TipoCambio()

    private enum Clave {
        static let valor = "tcValor"
        static let fecha = "tcFecha"
        static let fuente = "tcFuente"
        static let manual = "tcManual"
        static let valorManual = "tcValorManual"
    }

    private(set) var valorAutomatico: Double
    private(set) var fecha: Date?
    private(set) var fuente: String
    private(set) var actualizando = false
    private(set) var error: String?

    var usarManual: Bool {
        didSet { UserDefaults.standard.set(usarManual, forKey: Clave.manual) }
    }

    var valorManual: Double {
        didSet { UserDefaults.standard.set(valorManual, forKey: Clave.valorManual) }
    }

    /// Colones por cada dólar que usa la app en este momento.
    var valor: Double { usarManual ? valorManual : valorAutomatico }

    var esDeHoy: Bool { fecha.map { Calendar.current.isDateInToday($0) } ?? false }

    var descripcion: String { "\(valor.comoMoneda) por US$1" }

    var detalleFuente: String {
        if usarManual { return "Tipo de cambio manual" }
        guard let fecha else { return "Sin actualizar (valor de referencia)" }
        return "\(fuente) · \(fecha.formatted(date: .abbreviated, time: .shortened))"
    }

    private init() {
        let d = UserDefaults.standard
        let guardado = d.double(forKey: Clave.valor)
        valorAutomatico = guardado > 0 ? guardado : 505
        fecha = d.object(forKey: Clave.fecha) as? Date
        fuente = d.string(forKey: Clave.fuente) ?? ""
        usarManual = d.bool(forKey: Clave.manual)
        let manual = d.double(forKey: Clave.valorManual)
        valorManual = manual > 0 ? manual : (guardado > 0 ? guardado : 505)
    }

    /// Consulta el tipo de cambio si todavía no se ha obtenido el de hoy.
    @discardableResult
    func actualizarSiHaceFalta() async -> Bool {
        guard !usarManual, !esDeHoy, !actualizando else { return false }
        return await actualizar()
    }

    @discardableResult
    func actualizar() async -> Bool {
        actualizando = true
        error = nil
        defer { actualizando = false }

        if let venta = await consultarHacienda() {
            guardar(venta, fuente: "BCCR · Hacienda")
            return true
        }
        if let tasa = await consultarExchangeRateAPI() {
            guardar(tasa, fuente: "ExchangeRate-API")
            return true
        }
        error = "No se pudo obtener el tipo de cambio de hoy. Se usa el último disponible."
        return false
    }

    private func guardar(_ nuevo: Double, fuente nuevaFuente: String) {
        valorAutomatico = nuevo.redondeado
        fecha = .now
        fuente = nuevaFuente
        let d = UserDefaults.standard
        d.set(valorAutomatico, forKey: Clave.valor)
        d.set(fecha, forKey: Clave.fecha)
        d.set(fuente, forKey: Clave.fuente)
    }

    // MARK: Fuentes

    private struct RespuestaHacienda: Decodable {
        struct Indicador: Decodable { let valor: Double }
        let venta: Indicador
    }

    private struct RespuestaExchangeRate: Decodable {
        let rates: [String: Double]
    }

    private func consultarHacienda() async -> Double? {
        guard let url = URL(string: "https://api.hacienda.go.cr/indicadores/tc/dolar"),
              let datos = await descargar(url),
              let respuesta = try? JSONDecoder().decode(RespuestaHacienda.self, from: datos),
              respuesta.venta.valor > 0 else { return nil }
        return respuesta.venta.valor
    }

    private func consultarExchangeRateAPI() async -> Double? {
        guard let url = URL(string: "https://open.er-api.com/v6/latest/USD"),
              let datos = await descargar(url),
              let respuesta = try? JSONDecoder().decode(RespuestaExchangeRate.self, from: datos),
              let crc = respuesta.rates["CRC"], crc > 0 else { return nil }
        return crc
    }

    private func descargar(_ url: URL) async -> Data? {
        var solicitud = URLRequest(url: url, timeoutInterval: 12)
        solicitud.setValue("application/json", forHTTPHeaderField: "Accept")
        guard let (datos, respuesta) = try? await URLSession.shared.data(for: solicitud),
              (respuesta as? HTTPURLResponse)?.statusCode == 200 else { return nil }
        return datos
    }
}

/// Recalcula en colones los repuestos comprados en dólares de las órdenes abiertas
/// con el tipo de cambio vigente. Las órdenes ya facturadas conservan su tipo de cambio.
enum RevalorizacionDolares {
    static func aplicar(en context: ModelContext, tipoCambio: Double = TipoCambio.compartido.valor) {
        guard tipoCambio > 0, let lineas = try? context.fetch(FetchDescriptor<LineaOrden>()) else { return }
        for linea in lineas {
            guard let usd = linea.precioUSD,
                  let orden = linea.orden,
                  orden.factura == nil,
                  orden.estado.esActiva else { continue }
            let nuevoPrecio = (usd * tipoCambio).redondeado
            if linea.precioUnitario != nuevoPrecio || linea.tipoCambio != tipoCambio {
                linea.precioUnitario = nuevoPrecio
                linea.tipoCambio = tipoCambio
            }
        }
    }
}
