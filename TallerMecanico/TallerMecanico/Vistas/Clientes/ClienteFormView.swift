import SwiftUI
import SwiftData

struct ClienteFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context

    private let cliente: Cliente?
    private let onGuardar: ((Cliente, Vehiculo?) -> Void)?

    @State private var nombre: String
    @State private var telefono: String
    @State private var correo: String
    @State private var notas: String

    // Primer vehículo (solo al dar de alta)
    @State private var agregarVehiculo = true
    @State private var marca = ""
    @State private var modelo = ""
    @State private var anio = Calendar.current.component(.year, from: .now)
    @State private var placa = ""

    init(cliente: Cliente? = nil, onGuardar: ((Cliente, Vehiculo?) -> Void)? = nil) {
        self.cliente = cliente
        self.onGuardar = onGuardar
        _nombre = State(initialValue: cliente?.nombre ?? "")
        _telefono = State(initialValue: cliente?.telefono ?? "")
        _correo = State(initialValue: cliente?.correo ?? "")
        _notas = State(initialValue: cliente?.notas ?? "")
    }

    private var esNuevo: Bool { cliente == nil }

    private var puedeGuardar: Bool {
        guard !nombre.limpio.isEmpty else { return false }
        if esNuevo && agregarVehiculo { return !marca.limpio.isEmpty && !modelo.limpio.isEmpty }
        return true
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Datos de contacto") {
                    TextField("Nombre o razón social", text: $nombre)
                        .textContentType(.name)
                    TextField("Teléfono", text: $telefono)
                        .keyboardType(.phonePad)
                        .textContentType(.telephoneNumber)
                    TextField("Correo electrónico", text: $correo)
                        .keyboardType(.emailAddress)
                        .textContentType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }
                Section("Notas") {
                    TextField("Preferencias, datos de facturación…", text: $notas, axis: .vertical)
                }
                if esNuevo {
                    Section {
                        Toggle("Registrar vehículo", isOn: $agregarVehiculo.animation())
                        if agregarVehiculo {
                            TextField("Marca", text: $marca)
                            TextField("Modelo", text: $modelo)
                            LabeledContent("Año") {
                                TextField("Año", value: $anio, format: .number.grouping(.never))
                                    .keyboardType(.numberPad)
                                    .multilineTextAlignment(.trailing)
                            }
                            TextField("Placas", text: $placa)
                                .textInputAutocapitalization(.characters)
                        }
                    } header: {
                        Text("Vehículo")
                    } footer: {
                        Text("Podrás agregar más vehículos desde la ficha del cliente.")
                    }
                }
            }
            .navigationTitle(esNuevo ? "Nuevo cliente" : "Editar cliente")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Guardar", systemImage: "checkmark", role: .confirm, action: guardar)
                        .disabled(!puedeGuardar)
                }
            }
        }
    }

    private func guardar() {
        let destino: Cliente
        if let cliente {
            destino = cliente
        } else {
            destino = Cliente(nombre: nombre.limpio)
            context.insert(destino)
        }
        destino.nombre = nombre.limpio
        destino.telefono = telefono.limpio
        destino.correo = correo.limpio
        destino.notas = notas.limpio

        var vehiculoNuevo: Vehiculo?
        if esNuevo && agregarVehiculo {
            let vehiculo = Vehiculo(marca: marca.limpio, modelo: modelo.limpio, anio: anio,
                                    placa: placa.limpio.uppercased())
            context.insert(vehiculo)
            vehiculo.cliente = destino
            vehiculoNuevo = vehiculo
        }
        onGuardar?(destino, vehiculoNuevo)
        dismiss()
    }
}
