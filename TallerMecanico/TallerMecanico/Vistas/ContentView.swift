import SwiftUI

enum SeccionApp: Hashable {
    case inicio, ordenes, clientes, inventario, agenda
}

struct ContentView: View {
    @State private var seleccion: SeccionApp = .inicio

    var body: some View {
        TabView(selection: $seleccion) {
            Tab("Inicio", systemImage: "gauge.with.dots.needle.67percent", value: SeccionApp.inicio) {
                PanelView(seleccion: $seleccion)
            }
            Tab("Órdenes", systemImage: "wrench.and.screwdriver", value: SeccionApp.ordenes) {
                OrdenesListView()
            }
            Tab("Clientes", systemImage: "person.2", value: SeccionApp.clientes) {
                ClientesListView()
            }
            Tab("Inventario", systemImage: "shippingbox", value: SeccionApp.inventario) {
                InventarioView()
            }
            Tab("Agenda", systemImage: "calendar", value: SeccionApp.agenda) {
                AgendaView()
            }
        }
        .tabBarMinimizeBehavior(.onScrollDown)
    }
}

#Preview {
    ContentView()
        .modelContainer(for: [Cliente.self, Vehiculo.self, OrdenServicio.self,
                              LineaOrden.self, Refaccion.self, Cita.self], inMemory: true)
}
