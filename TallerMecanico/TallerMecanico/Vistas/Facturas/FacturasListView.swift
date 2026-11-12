import SwiftUI
import SwiftData

struct FacturasListView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Factura.folio, order: .reverse) private var facturas: [Factura]
    @State private var busqueda = ""

    private var filtradas: [Factura] {
        busqueda.isEmpty ? facturas : facturas.filter { $0.textoBusqueda.localizedStandardContains(busqueda) }
    }

    private var totalFacturado: Double {
        facturas.reduce(0) { $0 + ($1.orden?.total ?? 0) }
    }

    private var porCobrar: Double {
        facturas.reduce(0) { $0 + ($1.orden?.saldo ?? 0) }
    }

    var body: some View {
        List {
            if !facturas.isEmpty && busqueda.isEmpty {
                Section {
                    LabeledContent("Total facturado", value: totalFacturado.comoMoneda)
                    LabeledContent("Por cobrar", value: porCobrar.comoMoneda)
                    LabeledContent("Garantías vigentes", value: "\(facturas.filter(\.garantiaVigente).count)")
                }
                .monospacedDigit()
            }
            ForEach(filtradas) { factura in
                NavigationLink(value: factura) {
                    FilaFactura(factura: factura)
                }
            }
            .onDelete { indices in
                for indice in indices { context.delete(filtradas[indice]) }
            }
        }
        .overlay {
            if filtradas.isEmpty {
                if busqueda.isEmpty {
                    ContentUnavailableView("Sin facturas", systemImage: "doc.text",
                                           description: Text("Genera una factura desde el detalle de una orden de servicio."))
                } else {
                    ContentUnavailableView.search(text: busqueda)
                }
            }
        }
        .navigationTitle("Facturas")
        .searchable(text: $busqueda, prompt: "Folio, cliente o placa")
    }
}

struct FilaFactura: View {
    let factura: Factura

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "doc.text.fill")
                .font(.title3)
                .foregroundStyle(Color.accentColor)
                .frame(width: 44, height: 44)
                .background(Color.accentColor.opacity(0.15), in: .circle)
            VStack(alignment: .leading, spacing: 2) {
                Text(factura.folioTexto).font(.headline.monospaced())
                Text(factura.orden?.vehiculo?.cliente?.nombre ?? "—").font(.subheadline)
                Text(factura.fechaEmision.formatted(date: .abbreviated, time: .omitted))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 8)
            VStack(alignment: .trailing, spacing: 4) {
                Text((factura.orden?.total ?? 0).comoMoneda).font(.subheadline.bold())
                GarantiaBadge(factura: factura, compacto: true)
            }
        }
    }
}
