import SwiftUI
import SwiftData

struct InventarioView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Refaccion.nombre) private var refacciones: [Refaccion]

    @State private var busqueda = ""
    @State private var soloStockBajo = false
    @State private var editando: Refaccion?
    @State private var mostrarNueva = false
    private let tipoCambio = TipoCambio.compartido

    private var filtradas: [Refaccion] {
        refacciones.filter { r in
            (!soloStockBajo || r.stockBajo)
                && (busqueda.isEmpty || r.textoBusqueda.localizedStandardContains(busqueda))
        }
    }

    private var valorTotal: Double {
        refacciones.reduce(0) { $0 + $1.valorInventario(con: tipoCambio) }
    }

    var body: some View {
        NavigationStack {
            List {
                if !refacciones.isEmpty && busqueda.isEmpty {
                    Section {
                        LabeledContent("Artículos", value: "\(refacciones.count)")
                        LabeledContent("Valor del inventario (costo)", value: valorTotal.comoMoneda)
                    } footer: {
                        let monedas = Moneda.extranjeras.filter { m in refacciones.contains { $0.moneda == m } }
                        if !monedas.isEmpty {
                            Text("Repuestos en moneda extranjera convertidos a " +
                                 monedas.map { tipoCambio.descripcion($0) }.joined(separator: " y ") + ".")
                        }
                    }
                }
                Section {
                    ForEach(filtradas) { refaccion in
                        Button { editando = refaccion } label: {
                            FilaRefaccion(refaccion: refaccion, tipoCambio: tipoCambio)
                        }
                        .foregroundStyle(.primary)
                        .swipeActions(edge: .leading) {
                            Button("Entrada", systemImage: "plus") { refaccion.existencia += 1 }
                                .tint(.green)
                        }
                        .swipeActions(edge: .trailing) {
                            Button("Eliminar", systemImage: "trash", role: .destructive) {
                                context.delete(refaccion)
                            }
                            Button("Salida", systemImage: "minus") {
                                refaccion.existencia = max(0, refaccion.existencia - 1)
                            }
                            .tint(.orange)
                        }
                    }
                }
            }
            .overlay {
                if filtradas.isEmpty {
                    if !busqueda.isEmpty {
                        ContentUnavailableView.search(text: busqueda)
                    } else if soloStockBajo {
                        ContentUnavailableView("Todo en orden", systemImage: "checkmark.circle",
                                               description: Text("No hay refacciones con stock bajo."))
                    } else {
                        ContentUnavailableView("Inventario vacío", systemImage: "shippingbox",
                                               description: Text("Agrega refacciones con el botón +."))
                    }
                }
            }
            .navigationTitle("Inventario")
            .searchable(text: $busqueda, prompt: "Nombre, código, marca…")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Toggle(isOn: $soloStockBajo.animation()) {
                        Label("Stock bajo", systemImage: "exclamationmark.triangle")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Nueva refacción", systemImage: "plus") { mostrarNueva = true }
                }
            }
            .sheet(item: $editando) { RefaccionFormView(refaccion: $0) }
            .sheet(isPresented: $mostrarNueva) { RefaccionFormView() }
        }
    }
}

struct FilaRefaccion: View {
    let refaccion: Refaccion
    let tipoCambio: TipoCambio

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(refaccion.nombre).font(.headline)
                Text([refaccion.codigo, refaccion.marca, refaccion.ubicacion]
                        .filter { !$0.isEmpty }
                        .joined(separator: " · "))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if refaccion.moneda != .colon {
                    HStack(spacing: 4) {
                        Text(refaccion.precioVenta.como(refaccion.moneda)).font(.subheadline.bold())
                        Text("≈ \(refaccion.enColones(refaccion.precioVenta, con: tipoCambio).comoMoneda)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Text(refaccion.precioVenta.comoMoneda)
                        .font(.subheadline)
                }
            }
            Spacer()
            VStack(spacing: 0) {
                Text("\(refaccion.existencia)")
                    .font(.title2.bold().monospacedDigit())
                    .contentTransition(.numericText())
                Text("en stock").font(.caption2)
            }
            .foregroundStyle(refaccion.existencia <= 0 ? .red : (refaccion.stockBajo ? .orange : .primary))
            .frame(minWidth: 56)
        }
        .animation(.snappy, value: refaccion.existencia)
    }
}
