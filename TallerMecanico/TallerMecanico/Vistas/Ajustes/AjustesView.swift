import SwiftUI
import SwiftData

struct AjustesView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.modelContext) private var context

    @AppStorage(Preferencias.nombreTallerKey) private var nombreTaller = "Mi Taller"
    @AppStorage(Preferencias.direccionKey) private var direccion = ""
    @AppStorage(Preferencias.telefonoKey) private var telefono = ""
    @AppStorage(Preferencias.rfcKey) private var rfc = ""
    @AppStorage(Preferencias.terminosKey) private var terminos = Preferencias.terminosPredeterminados
    @AppStorage(Preferencias.ivaKey) private var tasaIVA = 0.13
    @AppStorage(Preferencias.diasGarantiaKey) private var diasGarantia = 30

    @State private var confirmarBorrado = false

    @Bindable private var tipoCambio = TipoCambio.compartido

    private var version: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Nombre del taller", text: $nombreTaller)
                    TextField("Dirección", text: $direccion, axis: .vertical)
                    TextField("Teléfono", text: $telefono)
                        .keyboardType(.phonePad)
                    TextField("Cédula jurídica", text: $rfc)
                        .textInputAutocapitalization(.characters)
                } header: {
                    Text("Datos del taller")
                } footer: {
                    Text("Aparecen en el encabezado de las órdenes y facturas en PDF.")
                }

                Section {
                    Stepper(value: $tasaIVA, in: 0...0.30, step: 0.01) {
                        LabeledContent("IVA", value: tasaIVA.formatted(.percent))
                    }
                    LabeledContent("Moneda oficial", value: "Colón costarricense (₡)")
                } header: {
                    Text("Impuestos y moneda")
                } footer: {
                    Text("El IVA se aplica a las órdenes nuevas; las existentes conservan su tasa.")
                }

                Section {
                    LabeledContent("Dólar hoy", value: tipoCambio.descripcion)
                    LabeledContent("Fuente", value: tipoCambio.detalleFuente)
                    Button {
                        Task {
                            await tipoCambio.actualizar()
                            RevalorizacionDolares.aplicar(en: context)
                        }
                    } label: {
                        HStack {
                            Label("Actualizar ahora", systemImage: "arrow.clockwise")
                            if tipoCambio.actualizando {
                                Spacer()
                                ProgressView()
                            }
                        }
                    }
                    .disabled(tipoCambio.actualizando || tipoCambio.usarManual)
                    if let error = tipoCambio.error {
                        Text(error).font(.footnote).foregroundStyle(.orange)
                    }
                    Toggle("Usar tipo de cambio manual", isOn: $tipoCambio.usarManual)
                    if tipoCambio.usarManual {
                        LabeledContent("₡ por US$1") {
                            TextField("Tipo de cambio", value: $tipoCambio.valorManual,
                                      format: .number.precision(.fractionLength(2)))
                                .keyboardType(.decimalPad)
                                .multilineTextAlignment(.trailing)
                        }
                    }
                } header: {
                    Text("Tipo de cambio del dólar")
                } footer: {
                    Text("Se consulta automáticamente cada día el tipo de cambio de venta de referencia del BCCR. Los repuestos comprados en dólares se recalculan en colones en las órdenes abiertas; las facturas conservan el tipo de cambio con que se emitieron.")
                }
                .onChange(of: tipoCambio.valor) { RevalorizacionDolares.aplicar(en: context) }

                Section {
                    Stepper("Garantía: \(diasGarantia) días", value: $diasGarantia, in: 0...365, step: 15)
                } header: {
                    Text("Garantía")
                } footer: {
                    Text("Plazo de garantía sobre la mano de obra que se propone al generar cada factura.")
                }

                Section("Términos y condiciones") {
                    TextField("Texto al pie de la orden", text: $terminos, axis: .vertical)
                        .lineLimit(3...10)
                }

                Section("Datos") {
                    Button("Cargar datos de ejemplo", systemImage: "wand.and.stars") {
                        DatosEjemplo.cargar(en: context)
                    }
                    Button("Borrar todos los datos", systemImage: "trash", role: .destructive) {
                        confirmarBorrado = true
                    }
                    .confirmationDialog("¿Borrar todos los clientes, vehículos, órdenes, citas e inventario?",
                                        isPresented: $confirmarBorrado, titleVisibility: .visible) {
                        Button("Borrar todo", role: .destructive) { DatosEjemplo.borrarTodo(en: context) }
                    }
                }

                Section {
                    LabeledContent("Versión", value: version)
                }
            }
            .navigationTitle("Ajustes")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Listo", systemImage: "checkmark", role: .confirm) { dismiss() }
                }
            }
        }
    }
}
