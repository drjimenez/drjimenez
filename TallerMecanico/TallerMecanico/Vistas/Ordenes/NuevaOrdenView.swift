import SwiftUI
import SwiftData

struct NuevaOrdenView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context

    @Query(sort: \Vehiculo.marca) private var vehiculos: [Vehiculo]
    @Query(sort: \OrdenServicio.folio, order: .reverse) private var ordenes: [OrdenServicio]

    @State private var vehiculo: Vehiculo?
    @State private var kilometraje: Int
    @State private var nivelCombustible = 0.5
    @State private var problema: String
    @State private var anticipo: Double = 0
    @State private var conFechaPromesa = false
    @State private var fechaPromesa = Date.now.addingTimeInterval(60 * 60 * 24)
    @State private var mostrarNuevoCliente = false

    init(vehiculo: Vehiculo? = nil, problema: String = "") {
        _vehiculo = State(initialValue: vehiculo)
        _kilometraje = State(initialValue: vehiculo?.kilometraje ?? 0)
        _problema = State(initialValue: problema)
    }

    private var siguienteFolio: Int { (ordenes.first?.folio ?? 0) + 1 }

    private var puedeGuardar: Bool { vehiculo != nil && !problema.limpio.isEmpty }

    var body: some View {
        NavigationStack {
            Form {
                Section("Vehículo") {
                    if !vehiculos.isEmpty {
                        Picker("Vehículo", selection: $vehiculo) {
                            Text("Seleccionar…").tag(Vehiculo?.none)
                            ForEach(vehiculos) { v in
                                Text("\(v.descripcionCorta) · \(v.cliente?.nombre ?? "")")
                                    .tag(Optional(v))
                            }
                        }
                        .pickerStyle(.navigationLink)
                    }
                    Button("Registrar cliente nuevo", systemImage: "person.badge.plus") {
                        mostrarNuevoCliente = true
                    }
                }

                Section("Recepción") {
                    LabeledContent("Kilometraje") {
                        TextField("km", value: $kilometraje, format: .number)
                            .keyboardType(.numberPad)
                            .multilineTextAlignment(.trailing)
                    }
                    VStack(alignment: .leading) {
                        LabeledContent("Combustible",
                                       value: nivelCombustible.formatted(.percent.precision(.fractionLength(0))))
                        Slider(value: $nivelCombustible, in: 0...1, step: 0.125) {
                            Text("Combustible")
                        } minimumValueLabel: {
                            Image(systemName: "fuelpump")
                        } maximumValueLabel: {
                            Image(systemName: "fuelpump.fill")
                        }
                    }
                    Toggle("Fecha promesa de entrega", isOn: $conFechaPromesa)
                    if conFechaPromesa {
                        DatePicker("Entrega", selection: $fechaPromesa, in: Date.now...)
                    }
                }

                Section("Problema reportado por el cliente") {
                    TextField("Describe la falla o el servicio solicitado", text: $problema, axis: .vertical)
                        .lineLimit(3...8)
                }

                Section("Anticipo") {
                    TextField("Anticipo", value: $anticipo, format: .currency(code: Preferencias.moneda))
                        .keyboardType(.decimalPad)
                }
            }
            .navigationTitle("Orden \(String(format: "OS-%05d", siguienteFolio))")
            .navigationBarTitleDisplayMode(.inline)
            .onChange(of: vehiculo) { _, nuevo in
                if let nuevo { kilometraje = max(kilometraje, nuevo.kilometraje) }
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Crear", systemImage: "checkmark", role: .confirm, action: guardar)
                        .disabled(!puedeGuardar)
                }
            }
            .sheet(isPresented: $mostrarNuevoCliente) {
                ClienteFormView { _, vehiculoNuevo in
                    if let vehiculoNuevo { vehiculo = vehiculoNuevo }
                }
            }
        }
    }

    private func guardar() {
        guard let vehiculo else { return }
        let orden = OrdenServicio(folio: siguienteFolio,
                                  problemaReportado: problema.limpio,
                                  kilometraje: kilometraje,
                                  nivelCombustible: nivelCombustible,
                                  tasaIVA: Preferencias.tasaIVA,
                                  anticipo: anticipo)
        orden.fechaPromesa = conFechaPromesa ? fechaPromesa : nil
        context.insert(orden)
        orden.vehiculo = vehiculo
        if kilometraje > vehiculo.kilometraje { vehiculo.kilometraje = kilometraje }
        dismiss()
    }
}
