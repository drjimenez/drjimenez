import SwiftUI
import SwiftData

struct LineaFormView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context

    let orden: OrdenServicio
    let tipo: TipoLinea

    @Query(sort: \Refaccion.nombre) private var inventario: [Refaccion]
    private let tipoCambio = TipoCambio.compartido

    @State private var refaccion: Refaccion?
    @State private var descripcion = ""
    @State private var cantidad: Double = 1
    @State private var moneda: Moneda = .colon
    @State private var precio: Double = 0

    init(orden: OrdenServicio, tipo: TipoLinea) {
        self.orden = orden
        self.tipo = tipo
    }

    private var faltaExistencia: Bool {
        guard let refaccion else { return false }
        return Int(cantidad.rounded()) > refaccion.existencia
    }

    /// Precio unitario en colones (moneda oficial).
    private var precioEnColones: Double {
        moneda == .dolar ? (precio * tipoCambio.valor).redondeado : precio
    }

    var body: some View {
        NavigationStack {
            Form {
                if tipo == .refaccion && !inventario.isEmpty {
                    Section {
                        Picker("Refacción", selection: $refaccion) {
                            Text("Captura manual").tag(Refaccion?.none)
                            ForEach(inventario) { r in
                                Text("\(r.nombre) · \(r.existencia) disp.").tag(Optional(r))
                            }
                        }
                        .pickerStyle(.navigationLink)
                        if faltaExistencia, let refaccion {
                            Label("Solo hay \(refaccion.existencia) en existencia", systemImage: "exclamationmark.triangle.fill")
                                .foregroundStyle(.orange)
                        }
                    } header: {
                        Text("Desde inventario")
                    } footer: {
                        Text("Al guardar se descuenta la cantidad del inventario.")
                    }
                }

                Section("Detalle") {
                    TextField(tipo == .manoDeObra ? "Ej. Cambio de pastillas de freno" : "Ej. Filtro de aire",
                              text: $descripcion, axis: .vertical)
                    Stepper(value: $cantidad, in: (tipo == .manoDeObra ? 0.5 : 1)...999,
                            step: tipo == .manoDeObra ? 0.5 : 1) {
                        LabeledContent(tipo == .manoDeObra ? "Tiempo (horas)" : "Cantidad",
                                       value: cantidad.formatted())
                    }
                    if tipo == .refaccion {
                        Picker("Moneda", selection: $moneda) {
                            ForEach(Moneda.allCases) { Text($0.nombre).tag($0) }
                        }
                        .pickerStyle(.segmented)
                    }
                    LabeledContent(tipo == .manoDeObra ? "Tarifa por hora" : "Precio unitario") {
                        TextField("Precio", value: $precio, format: .currency(code: moneda.rawValue))
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                    }
                }

                Section {
                    if moneda == .dolar {
                        LabeledContent("Tipo de cambio", value: tipoCambio.descripcion)
                        LabeledContent("Precio unitario en colones", value: precioEnColones.comoMoneda)
                    }
                    LabeledContent {
                        Text((cantidad * precioEnColones).redondeado.comoMoneda).bold()
                    } label: {
                        Text("Importe")
                    }
                } footer: {
                    if moneda == .dolar {
                        Text("Mientras la orden no se facture, el precio en colones se actualiza cada día con el tipo de cambio vigente (\(tipoCambio.detalleFuente)).")
                    }
                }
            }
            .navigationTitle(tipo == .manoDeObra ? "Mano de obra" : "Refacción")
            .navigationBarTitleDisplayMode(.inline)
            .onChange(of: refaccion) { _, nueva in
                if let nueva {
                    descripcion = nueva.nombre
                    moneda = nueva.moneda
                    precio = nueva.precioVenta
                }
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancelar", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Agregar", systemImage: "checkmark", role: .confirm, action: guardar)
                        .disabled(descripcion.limpio.isEmpty)
                }
            }
        }
    }

    private func guardar() {
        let linea = LineaOrden(tipo: tipo, descripcion: descripcion.limpio,
                               cantidad: cantidad, precioUnitario: precioEnColones)
        if moneda == .dolar {
            linea.precioUSD = precio
            linea.tipoCambio = tipoCambio.valor
        }
        context.insert(linea)
        linea.orden = orden
        if tipo == .refaccion, let refaccion {
            linea.refaccion = refaccion
            // Puede quedar negativa: indica piezas que faltan por surtir.
            refaccion.existencia -= linea.unidadesInventario
        }
        dismiss()
    }
}
