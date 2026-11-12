import SwiftUI
import SwiftData

struct OrdenDetalleView: View {
    @Environment(\.modelContext) private var context
    @Bindable var orden: OrdenServicio

    @State private var agregarLinea: TipoLinea?
    @State private var pdfURL: URL?

    var body: some View {
        Form {
            encabezado
            if let vehiculo = orden.vehiculo { seccionVehiculo(vehiculo) }

            Section("Problema reportado") {
                TextField("Descripción del cliente", text: $orden.problemaReportado, axis: .vertical)
            }
            Section("Diagnóstico") {
                TextField("Hallazgos del técnico", text: $orden.diagnostico, axis: .vertical)
                    .lineLimit(2...10)
            }

            seccionLineas(.manoDeObra)
            seccionLineas(.refaccion)
            totales

            Section("Observaciones internas") {
                TextField("Notas que no aparecen en el documento", text: $orden.observaciones, axis: .vertical)
            }

            Section("Documento") {
                Button("Generar PDF de la orden", systemImage: "doc.richtext") {
                    pdfURL = GeneradorPDF.crear(orden: orden)
                }
                if let pdfURL {
                    ShareLink(item: pdfURL,
                              preview: SharePreview(orden.folioTexto, image: Image(systemName: "doc.fill"))) {
                        Label("Compartir \(orden.folioTexto).pdf", systemImage: "square.and.arrow.up")
                    }
                }
            }
        }
        .navigationTitle(orden.folioTexto)
        .navigationBarTitleDisplayMode(.inline)
        .sheet(item: $agregarLinea) { tipo in
            LineaFormView(orden: orden, tipo: tipo)
        }
        .onChange(of: orden.lineas.count) { pdfURL = nil }
    }

    private var encabezado: some View {
        Section {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(orden.folioTexto).font(.title2.bold().monospaced())
                    Text("Ingreso: \(orden.fechaIngreso.formatted(date: .abbreviated, time: .shortened))")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    if let entrega = orden.fechaEntrega {
                        Text("Entregado: \(entrega.formatted(date: .abbreviated, time: .shortened))")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                EstadoBadge(estado: orden.estado)
            }
            ProgressView(value: orden.estado.progreso)
                .tint(orden.estado.color)
                .animation(.smooth, value: orden.estado)

            Picker("Estado", selection: $orden.estado) {
                ForEach(EstadoOrden.allCases) { estado in
                    Label(estado.titulo, systemImage: estado.icono).tag(estado)
                }
            }

            Toggle("Fecha promesa", isOn: Binding(
                get: { orden.fechaPromesa != nil },
                set: { orden.fechaPromesa = $0 ? (orden.fechaPromesa ?? .now.addingTimeInterval(86_400)) : nil }
            ))
            if let promesa = orden.fechaPromesa {
                DatePicker("Entrega prometida", selection: Binding(
                    get: { promesa },
                    set: { orden.fechaPromesa = $0 }
                ))
                .foregroundStyle(orden.estaRetrasada ? .red : .primary)
            }
        }
    }

    private func seccionVehiculo(_ vehiculo: Vehiculo) -> some View {
        Section("Vehículo y cliente") {
            LabeledContent("Vehículo", value: vehiculo.descripcion)
            LabeledContent("Placas", value: vehiculo.placa.isEmpty ? "—" : vehiculo.placa)
            LabeledContent("Kilometraje", value: "\(orden.kilometraje.formatted()) km")
            LabeledContent("Combustible",
                           value: orden.nivelCombustible.formatted(.percent.precision(.fractionLength(0))))
            if let cliente = vehiculo.cliente {
                LabeledContent("Cliente", value: cliente.nombre)
                BotonesContacto(telefono: cliente.telefono, correo: cliente.correo)
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets())
            }
        }
    }

    private func seccionLineas(_ tipo: TipoLinea) -> some View {
        let lineas = orden.lineas(de: tipo)
        return Section(tipo == .manoDeObra ? "Mano de obra" : "Refacciones") {
            ForEach(lineas) { linea in
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(linea.descripcion)
                        Text("\(linea.cantidad.formatted()) × \(linea.precioUnitario.comoMoneda)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text(linea.importe.comoMoneda).monospacedDigit()
                }
            }
            .onDelete { indices in
                for indice in indices { eliminar(lineas[indice]) }
            }
            Button(tipo == .manoDeObra ? "Agregar mano de obra" : "Agregar refacción",
                   systemImage: "plus.circle.fill") {
                agregarLinea = tipo
            }
        }
    }

    private var totales: some View {
        Section("Totales") {
            LabeledContent("Mano de obra", value: orden.totalManoDeObra.comoMoneda)
            LabeledContent("Refacciones", value: orden.totalRefacciones.comoMoneda)
            LabeledContent("Subtotal", value: orden.subtotal.comoMoneda)
            LabeledContent("IVA (\(orden.tasaIVA.formatted(.percent)))", value: orden.iva.comoMoneda)
            LabeledContent {
                Text(orden.total.comoMoneda).bold()
            } label: {
                Text("Total").bold()
            }
            LabeledContent("Anticipo") {
                TextField("Anticipo", value: $orden.anticipo, format: .currency(code: Preferencias.moneda))
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
            }
            LabeledContent {
                Text(orden.saldo.comoMoneda)
                    .bold()
                    .foregroundStyle(orden.saldo > 0 ? .orange : .green)
            } label: {
                Text("Saldo pendiente")
            }
        }
        .monospacedDigit()
    }

    private func eliminar(_ linea: LineaOrden) {
        // Devuelve las piezas al inventario.
        linea.refaccion?.existencia += linea.unidadesInventario
        orden.lineas.removeAll { $0.persistentModelID == linea.persistentModelID }
        context.delete(linea)
        pdfURL = nil
    }
}
