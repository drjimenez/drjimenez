import SwiftUI
import SwiftData

struct LineaFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context

    let orden: OrdenServicio
    let tipo: TipoLinea

    @Query(sort: \Refaccion.nombre) private var inventario: [Refaccion]

    @State private var refaccion: Refaccion?
    @State private var descripcion = ""
    @State private var cantidad: Double = 1
    @State private var precio: Double = 0

    private var faltaExistencia: Bool {
        guard let refaccion else { return false }
        return Int(cantidad.rounded()) > refaccion.existencia
    }

    var body: some View {
        NavigationStack {
            Form {
                if tipo == .refaccion && !inventario.isEmpty {
                    Section {
                        Picker("Refacción", selection: $refaccion) {
                            Text("Captura manual").tag(Refaccion?.none)
                            ForEach(inventario) { r in
                                Text("\(r.nombre) · \(r.existencia) disp.").tag(Optional(r))
                            }
                        }
                        .pickerStyle(.navigationLink)
                        if faltaExistencia, let refaccion {
                            Label("Solo hay \(refaccion.existencia) en existencia", systemImage: "exclamationmark.triangle.fill")
                                .foregroundStyle(.orange)
                        }
                    } header: {
                        Text("Desde inventario")
                    } footer: {
                        Text("Al guardar se descuenta la cantidad del inventario.")
                    }
                }

                Section("Detalle") {
                    TextField(tipo == .manoDeObra ? "Ej. Cambio de balatas" : "Ej. Filtro de aire",
                              text: $descripcion, axis: .vertical)
                    Stepper(value: $cantidad, in: (tipo == .manoDeObra ? 0.5 : 1)...999,
                            step: tipo == .manoDeObra ? 0.5 : 1) {
                        LabeledContent(tipo == .manoDeObra ? "Horas / servicios" : "Cantidad",
                                       value: cantidad.formatted())
                    }
                    LabeledContent("Precio unitario") {
                        TextField("Precio", value: $precio, format: .currency(code: Preferencias.moneda))
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                    }
                }

                Section {
                    LabeledContent {
                        Text((cantidad * precio).comoMoneda).bold()
                    } label: {
                        Text("Importe")
                    }
                }
            }
            .navigationTitle(tipo == .manoDeObra ? "Mano de obra" : "Refacción")
            .navigationBarTitleDisplayMode(.inline)
            .onChange(of: refaccion) { _, nueva in
                if let nueva {
                    descripcion = nueva.nombre
                    precio = nueva.precioVenta
                }
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Agregar", systemImage: "checkmark", role: .confirm, action: guardar)
                        .disabled(descripcion.limpio.isEmpty)
                }
            }
        }
    }

    private func guardar() {
        let linea = LineaOrden(tipo: tipo, descripcion: descripcion.limpio,
                               cantidad: cantidad, precioUnitario: precio)
        context.insert(linea)
        linea.orden = orden
        if tipo == .refaccion, let refaccion {
            linea.refaccion = refaccion
            // Puede quedar negativa: indica piezas que faltan por surtir.
            refaccion.existencia -= linea.unidadesInventario
        }
        dismiss()
    }
}
