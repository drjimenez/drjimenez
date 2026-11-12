import SwiftUI
import SwiftData

enum SeccionApp: String, Hashable {
    case inicio, ordenes, clientes, inventario, agenda
}

/// Argumentos de arranque para demostraciones y capturas de pantalla, p. ej.:
/// `-demo YES -tab ordenes -abrir orden`
enum ArranqueDemo {
    static var activo: Bool { UserDefaults.standard.bool(forKey: "demo") }
    static var pestana: SeccionApp {
        SeccionApp(rawValue: UserDefaults.standard.string(forKey: "tab") ?? "") ?? .inicio
    }
    static var abrir: String { UserDefaults.standard.string(forKey: "abrir") ?? "" }
}

struct ContentView: View {
    @Environment(\.modelContext) private var context
    @Environment(\.scenePhase) private var fase
    @State private var seleccion: SeccionApp = ArranqueDemo.pestana

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
        .onAppear(perform: cargarDemoSiHaceFalta)
        .task(id: fase) {
            guard fase == .active else { return }
            await TipoCambio.compartido.actualizarSiHaceFalta()
            RevalorizacionMonedas.aplicar(en: context)
        }
    }

    private func cargarDemoSiHaceFalta() {
        guard ArranqueDemo.activo,
              (try? context.fetchCount(FetchDescriptor<Cliente>())) == 0 else { return }
        DatosEjemplo.cargar(en: context)
    }
}

#Preview {
    ContentView()
        .modelContainer(for: [Cliente.self, Vehiculo.self, OrdenServicio.self,
                              LineaOrden.self, Refaccion.self, Cita.self, Factura.self], inMemory: true)
}
