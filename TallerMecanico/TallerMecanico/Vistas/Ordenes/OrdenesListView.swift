import SwiftUI
import SwiftData

enum RutaOrdenes: Hashable {
    case facturas
}

struct OrdenesListView: View {
    enum Filtro: String, CaseIterable, Identifiable {
        case activas = "Activas"
        case entregadas = "Entregadas"
        case todas = "Todas"
        var id: Self { self }
    }

    @Environment(\.modelContext) private var context
    @Query(sort: \OrdenServicio.fechaIngreso, order: .reverse) private var ordenes: [OrdenServicio]

    @State private var filtro: Filtro = .activas
    @State private var busqueda = ""
    @State private var mostrarNuevaOrden = false
    @State private var ruta = NavigationPath()

    private var filtradas: [OrdenServicio] {
        ordenes.filter { orden in
            let coincideFiltro: Bool
            switch filtro {
            case .activas: coincideFiltro = orden.estado.esActiva
            case .entregadas: coincideFiltro = orden.estado == .entregado
            case .todas: coincideFiltro = true
            }
            guard coincideFiltro else { return false }
            return busqueda.isEmpty || orden.textoBusqueda.localizedStandardContains(busqueda)
        }
    }

    var body: some View {
        NavigationStack(path: $ruta) {
            List {
                ForEach(filtradas) { orden in
                    NavigationLink(value: orden) {
                        FilaOrden(orden: orden)
                    }
                }
                .onDelete(perform: eliminar)
            }
            .overlay {
                if filtradas.isEmpty {
                    if busqueda.isEmpty {
                        ContentUnavailableView("Sin órdenes", systemImage: "wrench.and.screwdriver",
                                               description: Text("Crea una orden de servicio con el botón +."))
                    } else {
                        ContentUnavailableView.search(text: busqueda)
                    }
                }
            }
            .safeAreaBar(edge: .top) {
                Picker("Filtro", selection: $filtro) {
                    ForEach(Filtro.allCases) { Text($0.rawValue).tag($0) }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.bottom, 8)
            }
            .navigationTitle("Órdenes")
            .searchable(text: $busqueda, prompt: "Folio, placa, cliente…")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Facturas", systemImage: "doc.text") { ruta.append(RutaOrdenes.facturas) }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Nueva orden", systemImage: "plus") { mostrarNuevaOrden = true }
                }
            }
            .sheet(isPresented: $mostrarNuevaOrden) { NuevaOrdenView() }
            .navigationDestination(for: OrdenServicio.self) { OrdenDetalleView(orden: $0) }
            .navigationDestination(for: Factura.self) { FacturaDetalleView(factura: $0) }
            .navigationDestination(for: RutaOrdenes.self) { _ in FacturasListView() }
            .task { await abrirParaDemo() }
        }
    }

    private func abrirParaDemo() async {
        let destino = ArranqueDemo.abrir
        guard ["orden", "facturas", "factura", "facturaPDF"].contains(destino) else { return }
        try? await Task.sleep(for: .seconds(3))
        if destino == "orden" {
            if let primera = ordenes.min(by: { $0.folio < $1.folio }) { ruta.append(primera) }
            return
        }
        ruta.append(RutaOrdenes.facturas)
        if destino != "facturas", let factura = ordenes.compactMap(\.factura).first {
            ruta.append(factura)
        }
    }

    private func eliminar(_ indices: IndexSet) {
        for indice in indices {
            let orden = filtradas[indice]
            // Si la orden no se entregó, se devuelven las refacciones al inventario.
            if orden.estado != .entregado {
                for linea in orden.lineas {
                    linea.refaccion?.existencia += linea.unidadesInventario
                }
            }
            context.delete(orden)
        }
    }
}
