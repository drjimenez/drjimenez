import SwiftUI

struct EstadoBadge: View {
    let estado: EstadoOrden

    var body: some View {
        Label(estado.titulo, systemImage: estado.icono)
            .font(.caption.weight(.semibold))
            .lineLimit(1)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .foregroundStyle(estado.color)
            .background(estado.color.opacity(0.15), in: .capsule)
    }
}

struct TarjetaMetrica: View {
    let titulo: String
    let valor: String
    let icono: String
    let tinte: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Image(systemName: icono)
                .font(.title2)
                .foregroundStyle(tinte)
            Text(valor)
                .font(.title.bold())
                .lineLimit(1)
                .minimumScaleFactor(0.5)
                .contentTransition(.numericText())
            Text(titulo)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .glassEffect(.regular.tint(tinte.opacity(0.12)), in: .rect(cornerRadius: 24))
    }
}

/// Contenedor con efecto Liquid Glass para secciones del panel.
struct PanelSeccion<Contenido: View>: View {
    let titulo: String
    let icono: String
    @ViewBuilder var contenido: Contenido

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(titulo, systemImage: icono)
                .font(.headline)
            contenido
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .glassEffect(.regular, in: .rect(cornerRadius: 24))
    }
}

struct BotonesContacto: View {
    let telefono: String
    let correo: String
    @Environment(\.openURL) private var openURL

    private var digitos: String { telefono.filter(\.isNumber) }

    var body: some View {
        HStack(spacing: 12) {
            if !digitos.isEmpty {
                boton("Llamar", icono: "phone.fill", url: "tel:\(digitos)")
                boton("WhatsApp", icono: "message.fill",
                      url: "https://wa.me/\(digitos.count == 8 ? "506" + digitos : digitos)")
            }
            if !correo.isEmpty {
                boton("Correo", icono: "envelope.fill", url: "mailto:\(correo)")
            }
        }
        .frame(maxWidth: .infinity)
    }

    private func boton(_ titulo: String, icono: String, url: String) -> some View {
        Button {
            if let destino = URL(string: url) { openURL(destino) }
        } label: {
            VStack(spacing: 4) {
                Image(systemName: icono).font(.title3)
                Text(titulo).font(.caption)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.glass)
    }
}

struct FilaOrden: View {
    let orden: OrdenServicio

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: orden.estado.icono)
                .font(.title3)
                .foregroundStyle(orden.estado.color)
                .frame(width: 44, height: 44)
                .background(orden.estado.color.opacity(0.15), in: .circle)

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(orden.folioTexto).font(.headline.monospaced())
                    if orden.estaRetrasada {
                        Image(systemName: "clock.badge.exclamationmark.fill")
                            .foregroundStyle(.red)
                            .accessibilityLabel("Retrasada")
                    }
                }
                Text(orden.vehiculo?.descripcionCorta ?? "Sin vehículo")
                    .font(.subheadline)
                Text(orden.vehiculo?.cliente?.nombre ?? "")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer(minLength: 8)

            VStack(alignment: .trailing, spacing: 4) {
                Text(orden.total.comoMoneda).font(.subheadline.bold())
                Text(orden.estado.titulo)
                    .font(.caption2)
                    .foregroundStyle(orden.estado.color)
                    .lineLimit(1)
            }
        }
        .padding(.vertical, 2)
    }
}

struct Avatar: View {
    let texto: String
    var tamano: CGFloat = 40

    var body: some View {
        Text(texto)
            .font(.system(size: tamano * 0.4, weight: .semibold))
            .foregroundStyle(.white)
            .frame(width: tamano, height: tamano)
            .background(Color.accentColor.gradient, in: .circle)
    }
}
