import SwiftUI
import SwiftData

struct RefaccionFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context

    private let refaccion: Refaccion?

    @State private var nombre: String
    @State private var codigo: String
    @State private var marca: String
    @State private var ubicacion: String
    @State private var existencia: Int
    @State private var existenciaMinima: Int
    @State private var costo: Double
    @State private var precioVenta: Double

    init(refaccion: Refaccion? = nil) {
        self.refaccion = refaccion
        _nombre = State(initialValue: refaccion?.nombre ?? "")
        _codigo = State(initialValue: refaccion?.codigo ?? "")
        _marca = State(initialValue: refaccion?.marca ?? "")
        _ubicacion = State(initialValue: refaccion?.ubicacion ?? "")
        _existencia = State(initialValue: refaccion?.existencia ?? 0)
        _existenciaMinima = State(initialValue: refaccion?.existenciaMinima ?? 1)
        _costo = State(initialValue: refaccion?.costo ?? 0)
        _precioVenta = State(initialValue: refaccion?.precioVenta ?? 0)
    }

    private var margen: Double {
        precioVenta > 0 ? (precioVenta - costo) / precioVenta : 0
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Artículo") {
                    TextField("Nombre", text: $nombre)
                    TextField("Código / número de parte", text: $codigo)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                    TextField("Marca", text: $marca)
                    TextField("Ubicación en almacén", text: $ubicacion)
                }
                Section("Existencias") {
                    Stepper("Existencia: \(existencia)", value: $existencia, in: -999...99_999)
                    Stepper("Mínimo: \(existenciaMinima)", value: $existenciaMinima, in: 0...9_999)
                }
                Section {
                    LabeledContent("Costo") {
                        TextField("Costo", value: $costo, format: .currency(code: Preferencias.moneda))
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                    }
                    LabeledContent("Precio de venta") {
                        TextField("Precio", value: $precioVenta, format: .currency(code: Preferencias.moneda))
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                    }
                    LabeledContent("Margen", value: margen.formatted(.percent.precision(.fractionLength(0))))
                        .foregroundStyle(margen < 0 ? .red : .secondary)
                } header: {
                    Text("Precios")
                }
            }
            .navigationTitle(refaccion == nil ? "Nueva refacción" : "Editar refacción")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Guardar", systemImage: "checkmark", role: .confirm, action: guardar)
                        .disabled(nombre.limpio.isEmpty)
                }
            }
        }
    }

    private func guardar() {
        let destino: Refaccion
        if let refaccion {
            destino = refaccion
        } else {
            destino = Refaccion(nombre: nombre.limpio)
            context.insert(destino)
        }
        destino.nombre = nombre.limpio
        destino.codigo = codigo.limpio.uppercased()
        destino.marca = marca.limpio
        destino.ubicacion = ubicacion.limpio
        destino.existencia = existencia
        destino.existenciaMinima = existenciaMinima
        destino.costo = costo
        destino.precioVenta = precioVenta
        dismiss()
    }
}
