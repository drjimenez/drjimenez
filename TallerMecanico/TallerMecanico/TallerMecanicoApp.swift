import SwiftUI
import SwiftData

@main
struct TallerMecanicoApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: [
            Cliente.self,
            Vehiculo.self,
            OrdenServicio.self,
            LineaOrden.self,
            Refaccion.self,
            Cita.self
        ])
    }
}
