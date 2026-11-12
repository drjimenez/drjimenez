import SwiftUI
import SwiftData

struct VehiculoFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context

    private let cliente: Cliente?
    private let vehiculo: Vehiculo?

    @State private var marca: String
    @State private var modelo: String
    @State private var anio: Int
    @State private var placa: String
    @State private var vin: String
    @State private var color: String
    @State private var kilometraje: Int

    init(cliente: Cliente? = nil, vehiculo: Vehiculo? = nil) {
        self.cliente = cliente
        self.vehiculo = vehiculo
        _marca = State(initialValue: vehiculo?.marca ?? "")
        _modelo = State(initialValue: vehiculo?.modelo ?? "")
        _anio = State(initialValue: vehiculo?.anio ?? Calendar.current.component(.year, from: .now))
        _placa = State(initialValue: vehiculo?.placa ?? "")
        _vin = State(initialValue: vehiculo?.vin ?? "")
        _color = State(initialValue: vehiculo?.color ?? "")
        _kilometraje = State(initialValue: vehiculo?.kilometraje ?? 0)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Vehículo") {
                    TextField("Marca", text: $marca)
                    TextField("Modelo", text: $modelo)
                    LabeledContent("Año") {
                        TextField("Año", value: $anio, format: .number.grouping(.never))
                            .keyboardType(.numberPad)
                            .multilineTextAlignment(.trailing)
                    }
                    TextField("Color", text: $color)
                }
                Section("Identificación") {
                    TextField("Placas", text: $placa)
                        .textInputAutocapitalization(.characters)
                    TextField("Número de serie (VIN)", text: $vin)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled()
                    LabeledContent("Kilometraje") {
                        TextField("km", value: $kilometraje, format: .number)
                            .keyboardType(.numberPad)
                            .multilineTextAlignment(.trailing)
                    }
                }
            }
            .navigationTitle(vehiculo == nil ? "Nuevo vehículo" : "Editar vehículo")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Guardar", systemImage: "checkmark", role: .confirm, action: guardar)
                        .disabled(marca.limpio.isEmpty || modelo.limpio.isEmpty)
                }
            }
        }
    }

    private func guardar() {
        let destino: Vehiculo
        if let vehiculo {
            destino = vehiculo
        } else {
            destino = Vehiculo(marca: marca.limpio, modelo: modelo.limpio, anio: anio, placa: "")
            context.insert(destino)
            destino.cliente = cliente
        }
        destino.marca = marca.limpio
        destino.modelo = modelo.limpio
        destino.anio = anio
        destino.placa = placa.limpio.uppercased()
        destino.vin = vin.limpio.uppercased()
        destino.color = color.limpio
        destino.kilometraje = kilometraje
        dismiss()
    }
}
