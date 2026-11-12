import SwiftUI
import SwiftData

struct ClienteDetalleView: View {
    @Environment(\.modelContext) private var context
    @Bindable var cliente: Cliente

    @State private var editando = false
    @State private var agregandoVehiculo = false

    private var totalHistorico: Double {
        cliente.vehiculos
            .flatMap(\.ordenes)
            .filter { $0.estado == .entregado }
            .reduce(0) { $0 + $1.total }
    }

    var body: some View {
        List {
            Section {
                HStack(spacing: 16) {
                    Avatar(texto: cliente.iniciales, tamano: 64)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(cliente.nombre).font(.title2.bold())
                        Text("Cliente desde \(cliente.fechaAlta.formatted(.dateTime.month(.wide).year()))")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
                BotonesContacto(telefono: cliente.telefono, correo: cliente.correo)
                    .listRowBackground(Color.clear)
                    .listRowInsets(EdgeInsets())
            }

            Section("Contacto") {
                LabeledContent("Teléfono", value: cliente.telefono.isEmpty ? "—" : cliente.telefono)
                LabeledContent("Correo", value: cliente.correo.isEmpty ? "—" : cliente.correo)
                LabeledContent("Total facturado", value: totalHistorico.comoMoneda)
            }

            Section("Vehículos") {
                ForEach(cliente.vehiculosOrdenados) { vehiculo in
                    NavigationLink(value: vehiculo) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(vehiculo.descripcion).font(.headline)
                            Text("\(vehiculo.placa) · \(vehiculo.kilometraje.formatted()) km")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .onDelete { indices in
                    let lista = cliente.vehiculosOrdenados
                    for indice in indices { context.delete(lista[indice]) }
                }
                Button("Agregar vehículo", systemImage: "car.badge.gearshape") { agregandoVehiculo = true }
            }

            if !cliente.notas.isEmpty {
                Section("Notas") { Text(cliente.notas) }
            }
        }
        .navigationTitle(cliente.nombre)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            Button("Editar") { editando = true }
        }
        .sheet(isPresented: $editando) { ClienteFormView(cliente: cliente) }
        .sheet(isPresented: $agregandoVehiculo) { VehiculoFormView(cliente: cliente) }
    }
}
