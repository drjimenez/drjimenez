import SwiftUI
import SwiftData

struct VehiculoDetalleView: View {
    @Bindable var vehiculo: Vehiculo

    @State private var editando = false
    @State private var nuevaOrden = false

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 4) {
                    Image(systemName: "car.side.fill")
                        .font(.largeTitle)
                        .foregroundStyle(Color.accentColor)
                    Text(vehiculo.descripcion).font(.title2.bold())
                    if let cliente = vehiculo.cliente {
                        Text(cliente.nombre).foregroundStyle(.secondary)
                    }
                }
                .padding(.vertical, 4)

                Button("Nueva orden de servicio", systemImage: "wrench.and.screwdriver.fill") {
                    nuevaOrden = true
                }
                .buttonStyle(.glassProminent)
                .frame(maxWidth: .infinity)
                .listRowBackground(Color.clear)
            }

            Section("Datos") {
                LabeledContent("Placas", value: vehiculo.placa.isEmpty ? "—" : vehiculo.placa)
                LabeledContent("VIN", value: vehiculo.vin.isEmpty ? "—" : vehiculo.vin)
                LabeledContent("Color", value: vehiculo.color.isEmpty ? "—" : vehiculo.color)
                LabeledContent("Kilometraje", value: "\(vehiculo.kilometraje.formatted()) km")
            }

            Section("Historial de servicio") {
                if vehiculo.ordenes.isEmpty {
                    Text("Este vehículo aún no tiene órdenes.").foregroundStyle(.secondary)
                }
                ForEach(vehiculo.ordenesRecientes) { orden in
                    NavigationLink(value: orden) {
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(orden.folioTexto).font(.headline.monospaced())
                                Spacer()
                                EstadoBadge(estado: orden.estado)
                            }
                            Text(orden.problemaReportado).font(.subheadline).lineLimit(2)
                            Text("\(orden.fechaIngreso.formatted(date: .abbreviated, time: .omitted)) · \(orden.kilometraje.formatted()) km · \(orden.total.comoMoneda)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
        .navigationTitle(vehiculo.descripcionCorta)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            Button("Editar") { editando = true }
        }
        .sheet(isPresented: $editando) { VehiculoFormView(vehiculo: vehiculo) }
        .sheet(isPresented: $nuevaOrden) { NuevaOrdenView(vehiculo: vehiculo) }
    }
}
