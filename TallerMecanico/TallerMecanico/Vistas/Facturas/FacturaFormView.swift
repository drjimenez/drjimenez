import SwiftUI
import SwiftData

/// Genera la factura de una orden de servicio.
struct FacturaFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context

    let orden: OrdenServicio
    var alGuardar: ((Factura) -> Void)?

    @Query(sort: \Factura.folio, order: .reverse) private var facturas: [Factura]

    @State private var diasGarantia = Preferencias.diasGarantia
    @State private var metodoPago: MetodoPago = .efectivo
    @State private var notas = ""
    @State private var marcarEntregado = true

    private var siguienteFolio: Int { (facturas.first?.folio ?? 0) + 1 }

    var body: some View {
        NavigationStack {
            Form {
                Section("Resumen de la reparación") {
                    LabeledContent("Orden", value: orden.folioTexto)
                    LabeledContent("Cliente", value: orden.vehiculo?.cliente?.nombre ?? "—")
                    LabeledContent("Mano de obra",
                                   value: "\(orden.horasManoDeObra.formatted()) h · \(orden.totalManoDeObra.comoMoneda)")
                    LabeledContent("Refacciones", value: orden.totalRefacciones.comoMoneda)
                    LabeledContent("IVA", value: orden.iva.comoMoneda)
                    LabeledContent {
                        Text(orden.total.comoMoneda).bold()
                    } label: {
                        Text("Total").bold()
                    }
                    if orden.anticipo > 0 {
                        LabeledContent("Anticipo", value: "− \(orden.anticipo.comoMoneda)")
                    }
                    LabeledContent {
                        Text(orden.saldo.comoMoneda).bold().foregroundStyle(orden.saldo > 0 ? .orange : .green)
                    } label: {
                        Text("Saldo a pagar")
                    }
                }
                .monospacedDigit()

                Section {
                    Stepper("Garantía: \(diasGarantia) días", value: $diasGarantia, in: 0...365, step: 15)
                    Picker("Forma de pago", selection: $metodoPago) {
                        ForEach(MetodoPago.allCases) { Text($0.titulo).tag($0) }
                    }
                    if orden.estado != .entregado {
                        Toggle("Marcar vehículo como entregado", isOn: $marcarEntregado)
                    }
                } header: {
                    Text("Factura")
                } footer: {
                    Text("La garantía cubre la mano de obra y corre a partir de la entrega del vehículo.")
                }

                Section("Notas para el cliente") {
                    TextField("Recomendaciones, próximos servicios…", text: $notas, axis: .vertical)
                        .lineLimit(2...6)
                }
            }
            .navigationTitle("Factura \(String(format: "FAC-%05d", siguienteFolio))")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Generar", systemImage: "checkmark", role: .confirm, action: guardar)
                        .disabled(orden.lineas.isEmpty)
                }
            }
        }
    }

    private func guardar() {
        if marcarEntregado && orden.estado != .entregado {
            orden.estado = .entregado
        }
        let factura = Factura(folio: siguienteFolio, diasGarantia: diasGarantia,
                              metodoPago: metodoPago, notas: notas.limpio)
        context.insert(factura)
        factura.orden = orden
        alGuardar?(factura)
        dismiss()
    }
}
