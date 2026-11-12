import SwiftUI
import SwiftData

struct PanelView: View {
    @Binding var seleccion: SeccionApp

    @Query private var ordenes: [OrdenServicio]
    @Query(sort: \Refaccion.existencia) private var refacciones: [Refaccion]
    @Query(sort: \Cita.fecha) private var citas: [Cita]
    @AppStorage(Preferencias.nombreTallerKey) private var nombreTaller = "Mi Taller"

    @State private var mostrarAjustes = false
    @State private var mostrarNuevaOrden = false

    private var activas: [OrdenServicio] {
        ordenes.filter { $0.estado.esActiva }.sorted { $0.fechaIngreso < $1.fechaIngreso }
    }

    private var listas: [OrdenServicio] { activas.filter { $0.estado == .listo } }

    private var ingresosMes: Double {
        ordenes
            .filter { orden in
                guard orden.estado == .entregado, let entrega = orden.fechaEntrega else { return false }
                return Calendar.current.isDate(entrega, equalTo: .now, toGranularity: .month)
            }
            .reduce(0) { $0 + $1.total }
    }

    private var stockBajo: [Refaccion] { refacciones.filter(\.stockBajo) }

    private var citasHoy: [Cita] {
        citas.filter { Calendar.current.isDateInToday($0.fecha) && !$0.completada }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    metricas
                    porEstado
                    citasDeHoy
                    if !stockBajo.isEmpty { alertasInventario }
                }
                .padding()
            }
            .background(fondo)
            .navigationTitle(nombreTaller)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Ajustes", systemImage: "gearshape") { mostrarAjustes = true }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Nueva orden", systemImage: "plus") { mostrarNuevaOrden = true }
                }
            }
            .sheet(isPresented: $mostrarAjustes) { AjustesView() }
            .sheet(isPresented: $mostrarNuevaOrden) { NuevaOrdenView() }
            .navigationDestination(for: OrdenServicio.self) { OrdenDetalleView(orden: $0) }
            .navigationDestination(for: Factura.self) { FacturaDetalleView(factura: $0) }
            .task {
                switch ArranqueDemo.abrir {
                case "ajustes": mostrarAjustes = true
                case "nuevaOrden": mostrarNuevaOrden = true
                default: break
                }
            }
        }
    }

    private var fondo: some View {
        LinearGradient(colors: [Color.accentColor.opacity(0.28), Color(.systemBackground)],
                       startPoint: .top, endPoint: .center)
            .ignoresSafeArea()
    }

    private var metricas: some View {
        GlassEffectContainer(spacing: 16) {
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 16), GridItem(.flexible(), spacing: 16)],
                      spacing: 16) {
                TarjetaMetrica(titulo: "Órdenes activas", valor: "\(activas.count)",
                               icono: "wrench.and.screwdriver.fill", tinte: .blue)
                TarjetaMetrica(titulo: "Listas para entregar", valor: "\(listas.count)",
                               icono: "checkmark.seal.fill", tinte: .green)
                TarjetaMetrica(titulo: "Ingresos del mes", valor: ingresosMes.comoMoneda,
                               icono: "banknote.fill", tinte: .teal)
                TarjetaMetrica(titulo: "Refacciones con stock bajo", valor: "\(stockBajo.count)",
                               icono: "exclamationmark.triangle.fill",
                               tinte: stockBajo.isEmpty ? .gray : .orange)
            }
        }
    }

    private var porEstado: some View {
        PanelSeccion(titulo: "Vehículos en el taller", icono: "car.2.fill") {
            if activas.isEmpty {
                Text("No hay vehículos en el taller.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(activas.prefix(6)) { orden in
                    NavigationLink(value: orden) {
                        FilaOrden(orden: orden)
                    }
                    .buttonStyle(.plain)
                }
                if activas.count > 6 {
                    Button("Ver las \(activas.count) órdenes activas") { seleccion = .ordenes }
                        .font(.subheadline)
                }
            }
        }
    }

    private var citasDeHoy: some View {
        PanelSeccion(titulo: "Citas de hoy", icono: "calendar") {
            if citasHoy.isEmpty {
                Text("Sin citas pendientes para hoy.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(citasHoy) { cita in
                    HStack {
                        Text(cita.fecha, format: .dateTime.hour().minute())
                            .font(.subheadline.monospacedDigit().bold())
                            .fixedSize()
                            .frame(minWidth: 64, alignment: .leading)
                        VStack(alignment: .leading) {
                            Text(cita.motivo)
                            Text(cita.cliente?.nombre ?? "Sin cliente")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            Button("Abrir agenda") { seleccion = .agenda }
                .font(.subheadline)
        }
    }

    private var alertasInventario: some View {
        PanelSeccion(titulo: "Reabastecer", icono: "shippingbox.fill") {
            ForEach(stockBajo.prefix(5)) { refaccion in
                HStack {
                    Text(refaccion.nombre).lineLimit(1)
                    Spacer()
                    Text("\(refaccion.existencia) / mín. \(refaccion.existenciaMinima)")
                        .font(.subheadline.monospacedDigit())
                        .foregroundStyle(refaccion.existencia == 0 ? .red : .orange)
                }
            }
            Button("Ir a inventario") { seleccion = .inventario }
                .font(.subheadline)
        }
    }
}
