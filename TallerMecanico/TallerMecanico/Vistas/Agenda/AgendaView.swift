import SwiftUI
import SwiftData

struct AgendaView: View {
    @Environment(\.modelContext) private var context
    @Query(sort: \Cita.fecha) private var citas: [Cita]

    @State private var dia = Date.now
    @State private var mostrarNuevaCita = false
    @State private var citaParaOrden: Cita?

    private var citasDelDia: [Cita] {
        citas.filter { Calendar.current.isDate($0.fecha, inSameDayAs: dia) }
    }

    private var proximas: [Cita] {
        let finDelDia = Calendar.current.startOfDay(for: dia).addingTimeInterval(86_400)
        return citas.filter { $0.fecha >= finDelDia && !$0.completada }.prefix(5).map { $0 }
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    DatePicker("Día", selection: $dia, displayedComponents: .date)
                        .datePickerStyle(.graphical)
                }

                Section(dia.formatted(date: .complete, time: .omitted).capitalized) {
                    if citasDelDia.isEmpty {
                        Text("Sin citas para este día.").foregroundStyle(.secondary)
                    }
                    ForEach(citasDelDia) { cita in
                        FilaCita(cita: cita)
                            .swipeActions(edge: .leading) {
                                Button(cita.completada ? "Pendiente" : "Completada",
                                       systemImage: cita.completada ? "arrow.uturn.backward" : "checkmark") {
                                    cita.completada.toggle()
                                }
                                .tint(.green)
                                if cita.vehiculo != nil {
                                    Button("Crear orden", systemImage: "wrench.and.screwdriver") {
                                        citaParaOrden = cita
                                    }
                                    .tint(.blue)
                                }
                            }
                            .swipeActions(edge: .trailing) {
                                Button("Eliminar", systemImage: "trash", role: .destructive) {
                                    context.delete(cita)
                                }
                            }
                    }
                }

                if !proximas.isEmpty {
                    Section("Próximas") {
                        ForEach(proximas) { cita in
                            Button { dia = cita.fecha } label: {
                                LabeledContent(cita.motivo,
                                               value: cita.fecha.formatted(.dateTime.weekday().day().month().hour().minute()))
                            }
                            .foregroundStyle(.primary)
                        }
                    }
                }
            }
            .navigationTitle("Agenda")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Hoy") { withAnimation { dia = .now } }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Nueva cita", systemImage: "plus") { mostrarNuevaCita = true }
                }
            }
            .sheet(isPresented: $mostrarNuevaCita) { CitaFormView(fecha: dia) }
            .sheet(item: $citaParaOrden) { cita in
                NuevaOrdenView(vehiculo: cita.vehiculo, problema: cita.motivo)
            }
        }
    }
}

struct FilaCita: View {
    let cita: Cita

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .trailing) {
                Text(cita.fecha, format: .dateTime.hour().minute())
                    .font(.subheadline.bold().monospacedDigit())
                Text("\(cita.duracionMinutos) min")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            .fixedSize()
            .frame(minWidth: 64, alignment: .trailing)

            RoundedRectangle(cornerRadius: 2)
                .fill(cita.completada ? Color.green : Color.accentColor)
                .frame(width: 4)

            VStack(alignment: .leading, spacing: 2) {
                Text(cita.motivo)
                    .font(.headline)
                    .strikethrough(cita.completada)
                Text(cita.cliente?.nombre ?? "Sin cliente")
                    .font(.subheadline)
                if let vehiculo = cita.vehiculo {
                    Text(vehiculo.descripcionCorta)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .opacity(cita.completada ? 0.6 : 1)
    }
}
