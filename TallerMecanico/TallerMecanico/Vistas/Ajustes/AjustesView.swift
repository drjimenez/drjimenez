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
    @AppStorage(Preferencias.ivaKey) private var tasaIVA = 0.16
    @AppStorage(Preferencias.monedaKey) private var moneda = Preferencias.monedaPredeterminada
    @AppStorage(Preferencias.diasGarantiaKey) private var diasGarantia = 30

    @State private var confirmarBorrado = false

    private let monedas = ["MXN", "USD", "EUR", "COP", "ARS", "CLP", "PEN", "GTQ", "CRC", "DOP"]

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
                    TextField("RFC / Identificación fiscal", text: $rfc)
                        .textInputAutocapitalization(.characters)
                } header: {
                    Text("Datos del taller")
                } footer: {
                    Text("Aparecen en el encabezado de las órdenes en PDF.")
                }

                Section {
                    Stepper(value: $tasaIVA, in: 0...0.30, step: 0.01) {
                        LabeledContent("IVA", value: tasaIVA.formatted(.percent))
                    }
                    Picker("Moneda", selection: $moneda) {
                        ForEach(monedas, id: \.self) { Text($0).tag($0) }
                        if !monedas.contains(moneda) { Text(moneda).tag(moneda) }
                    }
                } header: {
                    Text("Impuestos y moneda")
                } footer: {
                    Text("El IVA se aplica a las órdenes nuevas; las existentes conservan su tasa.")
                }

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
