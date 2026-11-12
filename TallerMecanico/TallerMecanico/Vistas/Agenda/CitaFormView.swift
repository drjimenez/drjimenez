import SwiftUI
import SwiftData

struct CitaFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context

    @Query(sort: \Cliente.nombre) private var clientes: [Cliente]

    @State private var fecha: Date
    @State private var duracion = 60
    @State private var motivo = ""
    @State private var notas = ""
    @State private var cliente: Cliente?
    @State private var vehiculo: Vehiculo?

    private let duraciones = [30, 60, 90, 120, 180, 240, 480]

    init(fecha: Date) {
        // Propone la siguiente hora en punto del día elegido.
        let cal = Calendar.current
        let hora = max(9, min(18, cal.component(.hour, from: .now) + 1))
        let propuesta = cal.date(bySettingHour: hora, minute: 0, second: 0, of: fecha) ?? fecha
        _fecha = State(initialValue: propuesta)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Cita") {
                    TextField("Motivo (ej. afinación, frenos…)", text: $motivo)
                    DatePicker("Fecha y hora", selection: $fecha)
                    Picker("Duración", selection: $duracion) {
                        ForEach(duraciones, id: \.self) { minutos in
                            Text(minutos < 60 ? "\(minutos) min" : "\((Double(minutos) / 60).formatted()) h")
                                .tag(minutos)
                        }
                    }
                }
                Section("Cliente") {
                    Picker("Cliente", selection: $cliente) {
                        Text("Sin cliente").tag(Cliente?.none)
                        ForEach(clientes) { c in Text(c.nombre).tag(Optional(c)) }
                    }
                    if let cliente, !cliente.vehiculos.isEmpty {
                        Picker("Vehículo", selection: $vehiculo) {
                            Text("Sin vehículo").tag(Vehiculo?.none)
                            ForEach(cliente.vehiculosOrdenados) { v in Text(v.descripcionCorta).tag(Optional(v)) }
                        }
                    }
                }
                Section("Notas") {
                    TextField("Notas", text: $notas, axis: .vertical)
                }
            }
            .navigationTitle("Nueva cita")
            .navigationBarTitleDisplayMode(.inline)
            .onChange(of: cliente) { _, nuevo in
                vehiculo = nuevo?.vehiculosOrdenados.first
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Guardar", systemImage: "checkmark", role: .confirm, action: guardar)
                        .disabled(motivo.limpio.isEmpty)
                }
            }
        }
    }

    private func guardar() {
        let cita = Cita(fecha: fecha, duracionMinutos: duracion, motivo: motivo.limpio, notas: notas.limpio)
        context.insert(cita)
        cita.cliente = cliente
        cita.vehiculo = vehiculo
        dismiss()
    }
}
