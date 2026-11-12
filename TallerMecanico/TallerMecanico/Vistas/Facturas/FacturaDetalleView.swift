import SwiftUI
import SwiftData

struct GarantiaBadge: View {
    let factura: Factura

    var body: some View {
        let vigente = factura.garantiaVigente
        Label(vigente ? "Garantía: \(factura.diasRestantesGarantia) días" : "Garantía vencida",
              systemImage: vigente ? "checkmark.shield.fill" : "shield.slash")
            .font(.caption.weight(.semibold))
            .lineLimit(1)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .foregroundStyle(vigente ? Color.green : Color.secondary)
            .background((vigente ? Color.green : Color.gray).opacity(0.15), in: .capsule)
    }
}

struct FacturaDetalleView: View {
    @Bindable var factura: Factura
    @State private var documento: DocumentoPDF?

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(factura.folioTexto).font(.title2.bold().monospaced())
                        Spacer()
                        GarantiaBadge(factura: factura)
                    }
                    Text(factura.fechaEmision.formatted(date: .long, time: .shortened))
                        .foregroundStyle(.secondary)
                    if let orden = factura.orden {
                        Text("\(orden.vehiculo?.cliente?.nombre ?? "—") · \(orden.vehiculo?.descripcionCorta ?? "")")
                            .font(.subheadline)
                    }
                }
                HStack(spacing: 12) {
                    Button("Ver PDF", systemImage: "doc.richtext", action: abrirPDF)
                        .buttonStyle(.glass)
                    Button("Imprimir", systemImage: "printer", action: imprimir)
                        .buttonStyle(.glassProminent)
                }
                .frame(maxWidth: .infinity)
                .listRowBackground(Color.clear)
            }

            if let orden = factura.orden {
                Section("Mano de obra · \(orden.horasManoDeObra.formatted()) h") {
                    ForEach(orden.lineas(de: .manoDeObra)) { linea in
                        filaLinea(linea, detalle: "\(linea.cantidad.formatted()) h × \(linea.precioUnitario.comoMoneda)")
                    }
                }
                Section("Repuestos y refacciones") {
                    if orden.lineas(de: .refaccion).isEmpty {
                        Text("Sin refacciones").foregroundStyle(.secondary)
                    }
                    ForEach(orden.lineas(de: .refaccion)) { linea in
                        filaLinea(linea, detalle: "\(linea.cantidad.formatted()) × \(linea.precioUnitario.comoMoneda)")
                    }
                }
                Section("Totales") {
                    LabeledContent("Subtotal", value: orden.subtotal.comoMoneda)
                    LabeledContent("IVA (\(orden.tasaIVA.formatted(.percent)))", value: orden.iva.comoMoneda)
                    LabeledContent {
                        Text(orden.total.comoMoneda).bold()
                    } label: {
                        Text("Total de la reparación").bold()
                    }
                    if orden.anticipo > 0 {
                        LabeledContent("Anticipo recibido", value: "− \(orden.anticipo.comoMoneda)")
                    }
                    LabeledContent {
                        Text(orden.saldo.comoMoneda).bold().foregroundStyle(orden.saldo > 0 ? .orange : .green)
                    } label: {
                        Text(orden.saldo > 0 ? "Saldo a pagar" : "Pagado")
                    }
                }
                .monospacedDigit()

                Section("Tiempo de la reparación") {
                    LabeledContent("Ingreso", value: orden.fechaIngreso.formatted(date: .abbreviated, time: .shortened))
                    if let entrega = orden.fechaEntrega {
                        LabeledContent("Entrega", value: entrega.formatted(date: .abbreviated, time: .shortened))
                    }
                    LabeledContent("Días en taller", value: orden.diasEnTaller == 0 ? "Mismo día" : "\(orden.diasEnTaller)")
                    LabeledContent("Horas de mano de obra", value: "\(orden.horasManoDeObra.formatted()) h")
                }

                Section("Orden de servicio") {
                    NavigationLink(value: orden) {
                        Label(orden.folioTexto, systemImage: "wrench.and.screwdriver")
                    }
                }
            }

            Section {
                Stepper("\(factura.diasGarantia) días", value: $factura.diasGarantia, in: 0...365, step: 15)
                LabeledContent("Desde", value: factura.inicioGarantia.formatted(date: .long, time: .omitted))
                LabeledContent("Hasta", value: factura.finGarantia.formatted(date: .long, time: .omitted))
            } header: {
                Text("Garantía de mano de obra")
            }

            Section("Pago y notas") {
                Picker("Forma de pago", selection: $factura.metodoPago) {
                    ForEach(MetodoPago.allCases) { Text($0.titulo).tag($0) }
                }
                TextField("Notas para el cliente", text: $factura.notas, axis: .vertical)
            }
        }
        .navigationTitle(factura.folioTexto)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            Button("Ver PDF", systemImage: "doc.richtext", action: abrirPDF)
        }
        .sheet(item: $documento) { VistaPreviaPDF(documento: $0) }
        .task {
            if ArranqueDemo.abrir == "facturaPDF" {
                try? await Task.sleep(for: .milliseconds(600))
                abrirPDF()
            }
        }
    }

    private func filaLinea(_ linea: LineaOrden, detalle: String) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(linea.descripcion)
                Text(detalle).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            Text(linea.importe.comoMoneda).monospacedDigit()
        }
    }

    private func abrirPDF() {
        if let url = GeneradorPDF.crear(factura: factura) {
            documento = DocumentoPDF(url: url, titulo: factura.folioTexto)
        }
    }

    private func imprimir() {
        if let url = GeneradorPDF.crear(factura: factura) {
            Impresion.imprimir(url, nombre: factura.folioTexto)
        }
    }
}
