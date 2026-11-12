import SwiftUI

enum GeneradorPDF {
    /// Tamaño carta en puntos (8.5 × 11 in).
    static let carta = CGSize(width: 612, height: 792)

    static func crear(orden: OrdenServicio) -> URL? {
        crear(OrdenDocumentoView(orden: orden, taller: .actual), nombre: orden.folioTexto)
    }

    static func crear(factura: Factura) -> URL? {
        crear(FacturaDocumentoView(factura: factura, taller: .actual), nombre: factura.folioTexto)
    }

    /// Renderiza una vista en una hoja tamaño carta lista para imprimir.
    /// Si el contenido es más alto que la hoja, se reduce para que quepa completo.
    static func crear<Contenido: View>(_ contenido: Contenido, nombre: String) -> URL? {
        let vista = contenido
            .frame(width: carta.width)
            .environment(\.colorScheme, .light)

        let renderer = ImageRenderer(content: vista)
        renderer.proposedSize = ProposedViewSize(width: carta.width, height: nil)

        let url = URL.temporaryDirectory.appending(path: "\(nombre).pdf")
        var exito = false

        renderer.render { tamano, dibujar in
            var caja = CGRect(origin: .zero, size: carta)
            guard let pdf = CGContext(url as CFURL, mediaBox: &caja, nil) else { return }
            pdf.beginPDFPage(nil)
            let escala = min(1, carta.height / max(tamano.height, 1), carta.width / max(tamano.width, 1))
            // El origen del PDF está abajo a la izquierda: se alinea el contenido arriba.
            pdf.translateBy(x: 0, y: carta.height - tamano.height * escala)
            pdf.scaleBy(x: escala, y: escala)
            dibujar(pdf)
            pdf.endPDFPage()
            pdf.closePDF()
            exito = true
        }
        return exito ? url : nil
    }
}

/// Vista imprimible de la orden de servicio (se usa para el PDF).
struct OrdenDocumentoView: View {
    let orden: OrdenServicio
    let taller: DatosTaller

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            encabezado
            Divider()
            datosClienteVehiculo
            bloque("Problema reportado", orden.problemaReportado)
            if !orden.diagnostico.isEmpty { bloque("Diagnóstico", orden.diagnostico) }
            tabla
            totales
            if !taller.terminos.isEmpty {
                Text(taller.terminos).font(.system(size: 8)).foregroundStyle(.gray)
            }
            firmas
        }
        .padding(36)
        .foregroundStyle(.black)
        .background(.white)
    }

    private var encabezado: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 3) {
                Text(taller.nombre).font(.system(size: 20, weight: .bold))
                if !taller.direccion.isEmpty { Text(taller.direccion) }
                if !taller.telefono.isEmpty { Text("Tel. \(taller.telefono)") }
                if !taller.rfc.isEmpty { Text("RFC \(taller.rfc)") }
            }
            .font(.system(size: 10))
            Spacer()
            VStack(alignment: .trailing, spacing: 3) {
                Text("ORDEN DE SERVICIO").font(.system(size: 11, weight: .semibold)).foregroundStyle(.gray)
                Text(orden.folioTexto).font(.system(size: 18, weight: .bold, design: .monospaced))
                Text(orden.fechaIngreso.formatted(date: .long, time: .shortened)).font(.system(size: 10))
                Text(orden.estado.titulo).font(.system(size: 10, weight: .semibold))
            }
        }
    }

    private var datosClienteVehiculo: some View {
        HStack(alignment: .top, spacing: 24) {
            VStack(alignment: .leading, spacing: 3) {
                etiqueta("CLIENTE")
                Text(orden.vehiculo?.cliente?.nombre ?? "—").bold()
                if let tel = orden.vehiculo?.cliente?.telefono, !tel.isEmpty { Text(tel) }
                if let correo = orden.vehiculo?.cliente?.correo, !correo.isEmpty { Text(correo) }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            VStack(alignment: .leading, spacing: 3) {
                etiqueta("VEHÍCULO")
                Text(orden.vehiculo?.descripcion ?? "—").bold()
                Text("Placas: \(orden.vehiculo?.placa ?? "—")")
                if let vin = orden.vehiculo?.vin, !vin.isEmpty { Text("VIN: \(vin)") }
                Text("Kilometraje: \(orden.kilometraje.formatted()) km · Combustible: \(orden.nivelCombustible.formatted(.percent.precision(.fractionLength(0))))")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .font(.system(size: 10))
    }

    private var tabla: some View {
        Grid(alignment: .leading, horizontalSpacing: 10, verticalSpacing: 6) {
            GridRow {
                etiqueta("CONCEPTO")
                etiqueta("TIPO")
                etiqueta("CANT.").gridColumnAlignment(.trailing)
                etiqueta("P. UNIT.").gridColumnAlignment(.trailing)
                etiqueta("IMPORTE").gridColumnAlignment(.trailing)
            }
            Divider().gridCellUnsizedAxes(.horizontal)
            ForEach(orden.lineasOrdenadas) { linea in
                GridRow {
                    Text(linea.descripcion)
                    Text(linea.tipo.titulo).foregroundStyle(.gray)
                    Text(linea.cantidad.formatted())
                    Text(linea.precioOriginalTexto)
                    Text(linea.importe.comoMoneda)
                }
            }
            if orden.lineas.isEmpty {
                GridRow { Text("Sin conceptos registrados").foregroundStyle(.gray).gridCellColumns(5) }
            }
        }
        .font(.system(size: 10))
    }

    private var totales: some View {
        HStack {
            Spacer()
            Grid(alignment: .trailing, horizontalSpacing: 16, verticalSpacing: 4) {
                filaTotal("Mano de obra", orden.totalManoDeObra)
                filaTotal("Refacciones", orden.totalRefacciones)
                filaTotal("Subtotal", orden.subtotal)
                filaTotal("IVA (\(orden.tasaIVA.formatted(.percent)))", orden.iva)
                filaTotal("Total", orden.total, resaltar: true)
                if orden.anticipo > 0 {
                    filaTotal("Anticipo", orden.anticipo)
                    filaTotal("Saldo", orden.saldo, resaltar: true)
                }
            }
            .font(.system(size: 10))
        }
    }

    private var firmas: some View {
        HStack(spacing: 40) {
            lineaFirma("Recibe (taller)")
            lineaFirma("Autoriza (cliente)")
        }
        .padding(.top, 30)
    }

    private func filaTotal(_ titulo: String, _ valor: Double, resaltar: Bool = false) -> some View {
        GridRow {
            Text(titulo)
            Text(valor.comoMoneda).fontWeight(resaltar ? .bold : .regular)
        }
    }

    private func etiqueta(_ texto: String) -> some View {
        Text(texto).font(.system(size: 8, weight: .semibold)).foregroundStyle(.gray)
    }

    private func bloque(_ titulo: String, _ texto: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            etiqueta(titulo.uppercased())
            Text(texto.isEmpty ? "—" : texto).font(.system(size: 10))
        }
    }

    private func lineaFirma(_ titulo: String) -> some View {
        VStack(spacing: 4) {
            Rectangle().frame(height: 0.5)
            Text(titulo).font(.system(size: 9)).foregroundStyle(.gray)
        }
    }
}
