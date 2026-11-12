import SwiftUI
import SwiftData

struct ClientesListView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Cliente.nombre) private var clientes: [Cliente]

    @State private var busqueda = ""
    @State private var mostrarNuevo = false

    private var filtrados: [Cliente] {
        busqueda.isEmpty ? clientes : clientes.filter { $0.textoBusqueda.localizedStandardContains(busqueda) }
    }

    var body: some View {
        NavigationStack {
            List {
                ForEach(filtrados) { cliente in
                    NavigationLink(value: cliente) {
                        HStack(spacing: 12) {
                            Avatar(texto: cliente.iniciales)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(cliente.nombre).font(.headline)
                                Text(cliente.resumenVehiculos)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                        }
                    }
                }
                .onDelete { indices in
                    for indice in indices { context.delete(filtrados[indice]) }
                }
            }
            .overlay {
                if filtrados.isEmpty {
                    if busqueda.isEmpty {
                        ContentUnavailableView("Sin clientes", systemImage: "person.2",
                                               description: Text("Agrega tu primer cliente con el botón +."))
                    } else {
                        ContentUnavailableView.search(text: busqueda)
                    }
                }
            }
            .navigationTitle("Clientes")
            .searchable(text: $busqueda, prompt: "Nombre, teléfono o placa")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Nuevo cliente", systemImage: "person.badge.plus") { mostrarNuevo = true }
                }
            }
            .sheet(isPresented: $mostrarNuevo) { ClienteFormView() }
            .navigationDestination(for: Cliente.self) { ClienteDetalleView(cliente: $0) }
            .navigationDestination(for: Vehiculo.self) { VehiculoDetalleView(vehiculo: $0) }
            .navigationDestination(for: OrdenServicio.self) { OrdenDetalleView(orden: $0) }
        }
    }
}
