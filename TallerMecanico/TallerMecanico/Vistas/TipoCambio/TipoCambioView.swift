import SwiftUI
import SwiftData

/// Consulta y registro manual de los tipos de cambio del dólar y del euro.
struct TipoCambioView: View {
    @Environment(\.modelContext) private var context
    private let tipoCambio = TipoCambio.compartido

    @State private var registrando: Moneda?

    var body: some View {
        List {
            ForEach(Moneda.extranjeras) { moneda in
                Section {
                    tarjeta(moneda)
                    Button("Registrar tipo de cambio manual", systemImage: "square.and.pencil") {
                        registrando = moneda
                    }
                    if tipoCambio.esManual(moneda) {
                        Button("Volver al tipo de cambio automático", systemImage: "arrow.triangle.2.circlepath") {
                            tipoCambio.usarAutomatico(moneda)
                            RevalorizacionMonedas.aplicar(en: context)
                        }
                    }
                } header: {
                    Text(moneda == .dolar ? "Dólar estadounidense" : "Euro")
                }
            }

            Section {
                Button {
                    Task {
                        await tipoCambio.actualizar()
                        RevalorizacionMonedas.aplicar(en: context)
                    }
                } label: {
                    HStack {
                        Label("Consultar tipo de cambio de hoy", systemImage: "arrow.clockwise")
                        if tipoCambio.actualizando {
                            Spacer()
                            ProgressView()
                        }
                    }
                }
                .disabled(tipoCambio.actualizando)
                if let error = tipoCambio.error {
                    Label(error, systemImage: "exclamationmark.triangle.fill")
                        .font(.footnote)
                        .foregroundStyle(.orange)
                }
            } footer: {
                Text("Automático: tipo de cambio de venta de referencia del BCCR (API de Hacienda), consultado una vez al día. Si registras un valor manual, la app usa ese valor para esa moneda hasta que vuelvas al automático. Los repuestos en moneda extranjera de las órdenes abiertas se recalculan; las facturas emitidas conservan su tipo de cambio.")
            }

            Section("Historial") {
                if tipoCambio.historial.isEmpty {
                    Text("Sin registros todavía.").foregroundStyle(.secondary)
                }
                ForEach(tipoCambio.historial.prefix(40)) { registro in
                    HStack {
                        Image(systemName: registro.moneda.icono)
                            .foregroundStyle(registro.manual ? Color.orange : Color.green)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("\(registro.valor.comoMoneda) por \(registro.moneda.simbolo)1")
                                .monospacedDigit()
                            Text("\(registro.fuente) · \(registro.fecha.formatted(date: .abbreviated, time: .shortened))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .swipeActions {
                        Button("Borrar", systemImage: "trash", role: .destructive) {
                            tipoCambio.borrarDelHistorial(registro)
                        }
                    }
                }
            }
        }
        .navigationTitle("Tipo de cambio")
        .sheet(item: $registrando) { moneda in
            RegistroTipoCambioView(moneda: moneda)
        }
        .task {
            if ArranqueDemo.abrir == "registroTC" {
                try? await Task.sleep(for: .milliseconds(600))
                registrando = .euro
            }
        }
    }

    private func tarjeta(_ moneda: Moneda) -> some View {
        HStack(spacing: 14) {
            Image(systemName: moneda.icono)
                .font(.largeTitle)
                .foregroundStyle(moneda == .dolar ? Color.green : Color.blue)
            VStack(alignment: .leading, spacing: 4) {
                Text(tipoCambio.valor(moneda).comoMoneda)
                    .font(.title2.bold().monospacedDigit())
                    .contentTransition(.numericText())
                Text("por cada \(moneda.simbolo)1")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Label(tipoCambio.detalleFuente(moneda),
                      systemImage: tipoCambio.esManual(moneda) ? "hand.raised.fill" : "antenna.radiowaves.left.and.right")
                    .font(.caption)
                    .foregroundStyle(tipoCambio.esManual(moneda) ? Color.orange : Color.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

/// Formulario para grabar manualmente el tipo de cambio de una moneda.
struct RegistroTipoCambioView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context
    let moneda: Moneda

    private let tipoCambio = TipoCambio.compartido
    @State private var valor: Double
    @State private var fecha = Date.now

    init(moneda: Moneda) {
        self.moneda = moneda
        _valor = State(initialValue: TipoCambio.compartido.valor(moneda))
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    LabeledContent("₡ por \(moneda.simbolo)1") {
                        TextField("Tipo de cambio", value: $valor, format: .number.precision(.fractionLength(2)))
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                            .font(.title3.monospacedDigit())
                    }
                    DatePicker("Fecha", selection: $fecha, in: ...Date.now)
                } header: {
                    Text(moneda.nombre)
                } footer: {
                    Text("Valor actual: \(tipoCambio.descripcion(moneda)) — \(tipoCambio.detalleFuente(moneda)).")
                }

                Section("Ejemplo") {
                    LabeledContent("\(moneda.formatear(100)) equivalen a", value: (100 * valor).redondeado.comoMoneda)
                }
            }
            .navigationTitle("Tipo de cambio manual")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Guardar", systemImage: "checkmark", role: .confirm) {
                        tipoCambio.registrarManual(valor, para: moneda, fecha: fecha)
                        RevalorizacionMonedas.aplicar(en: context)
                        dismiss()
                    }
                    .disabled(valor <= 0)
                }
            }
        }
    }
}
