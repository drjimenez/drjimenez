import SwiftUI

/// Hoja tamaño carta de la factura al cliente (se usa para el PDF y la impresión).
struct FacturaDocumentoView: View {
    let factura: Factura
    let taller: DatosTaller

    private var orden: OrdenServicio? { factura.orden }
    private let tinta = Color(red: 0.10, green: 0.10, blue: 0.12)
    private let acento = Color(red: 0.86, green: 0.38, blue: 0.10)
    private let gris = Color(red: 0.45, green: 0.45, blue: 0.48)
    private let fondoSuave = Color(red: 0.96, green: 0.96, blue: 0.97)

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            encabezado
            Rectangle().fill(acento).frame(height: 2)
            datosClienteVehiculo
            if let orden {
                tablaManoDeObra(orden)
                tablaRefacciones(orden)
                HStack(alignment: .top, spacing: 18) {
                    resumenTiempo(orden)
                    totales(orden)
                }
            }
            garantia
            if !factura.notas.isEmpty {
                VStack(alignment: .leading, spacing: 2) {
                    etiqueta("NOTAS")
                    Text(factura.notas).font(.system(size: 9))
                }
            }
            Spacer(minLength: 0)
            firmas
            pie
        }
        .padding(.horizontal, 40)
        .padding(.vertical, 34)
        .frame(width: GeneradorPDF.carta.width, alignment: .top)
        .frame(minHeight: GeneradorPDF.carta.height, alignment: .top)
        .foregroundStyle(tinta)
        .background(.white)
    }

    // MARK: Secciones

    private var encabezado: some View {
        HStack(alignment: .top) {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "wrench.and.screwdriver.fill")
                    .font(.system(size: 20))
                    .foregroundStyle(.white)
                    .frame(width: 38, height: 38)
                    .background(acento, in: .rect(cornerRadius: 8))
                VStack(alignment: .leading, spacing: 2) {
                    Text(taller.nombre).font(.system(size: 17, weight: .bold))
                    if !taller.direccion.isEmpty { Text(taller.direccion) }
                    if !taller.telefono.isEmpty { Text("Tel. \(taller.telefono)") }
                    if !taller.rfc.isEmpty { Text("RFC \(taller.rfc)") }
                }
                .font(.system(size: 9))
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text("FACTURA").font(.system(size: 20, weight: .heavy)).foregroundStyle(acento)
                Text(factura.folioTexto).font(.system(size: 12, weight: .semibold, design: .monospaced))
                Text("Fecha: \(factura.fechaEmision.formatted(date: .long, time: .omitted))")
                if let orden { Text("Orden de servicio: \(orden.folioTexto)") }
                Text("Forma de pago: \(factura.metodoPago.titulo)")
            }
            .font(.system(size: 9))
        }
    }

    private var datosClienteVehiculo: some View {
        let vehiculo = orden?.vehiculo
        let cliente = vehiculo?.cliente
        return HStack(alignment: .top, spacing: 12) {
            caja {
                etiqueta("CLIENTE")
                Text(cliente?.nombre ?? "—").font(.system(size: 11, weight: .semibold))
                if let tel = cliente?.telefono, !tel.isEmpty { Text("Tel. \(tel)") }
                if let correo = cliente?.correo, !correo.isEmpty { Text(correo) }
            }
            caja {
                etiqueta("VEHÍCULO")
                Text(vehiculo?.descripcion ?? "—").font(.system(size: 11, weight: .semibold))
                Text("Placas: " + ((vehiculo?.placa).flatMap { $0.isEmpty ? nil : $0 } ?? "—"))
                if let vin = vehiculo?.vin, !vin.isEmpty { Text("VIN: \(vin)") }
                if let orden { Text("Kilometraje: \(orden.kilometraje.formatted()) km") }
            }
        }
        .font(.system(size: 9))
    }

    private func tablaManoDeObra(_ orden: OrdenServicio) -> some View {
        let lineas = orden.lineas(de: .manoDeObra)
        return VStack(alignment: .leading, spacing: 4) {
            tituloSeccion("MANO DE OBRA")
            Grid(alignment: .leading, horizontalSpacing: 8, verticalSpacing: 5) {
                GridRow {
                    etiqueta("DESCRIPCIÓN DEL TRABAJO")
                    etiqueta("TIEMPO").gridColumnAlignment(.trailing)
                    etiqueta("TARIFA").gridColumnAlignment(.trailing)
                    etiqueta("IMPORTE").gridColumnAlignment(.trailing)
                }
                separador
                ForEach(lineas) { linea in
                    GridRow {
                        Text(linea.descripcion).frame(maxWidth: .infinity, alignment: .leading)
                        Text(horas(linea.cantidad))
                        Text(linea.precioUnitario.comoMoneda)
                        Text(linea.importe.comoMoneda)
                    }
                }
                if lineas.isEmpty {
                    GridRow { Text("Sin mano de obra registrada").foregroundStyle(gris).gridCellColumns(4) }
                }
                separador
                GridRow {
                    Text("Subtotal mano de obra").bold()
                    Text(horas(orden.horasManoDeObra)).bold()
                    Text("")
                    Text(orden.totalManoDeObra.comoMoneda).bold()
                }
            }
            .font(.system(size: 9))
        }
    }

    private func tablaRefacciones(_ orden: OrdenServicio) -> some View {
        let lineas = orden.lineas(de: .refaccion)
        return VStack(alignment: .leading, spacing: 4) {
            tituloSeccion("REPUESTOS Y REFACCIONES")
            Grid(alignment: .leading, horizontalSpacing: 8, verticalSpacing: 5) {
                GridRow {
                    etiqueta("DESCRIPCIÓN")
                    etiqueta("CANT.").gridColumnAlignment(.trailing)
                    etiqueta("P. UNITARIO").gridColumnAlignment(.trailing)
                    etiqueta("IMPORTE").gridColumnAlignment(.trailing)
                }
                separador
                ForEach(lineas) { linea in
                    GridRow {
                        VStack(alignment: .leading, spacing: 0) {
                            Text(linea.descripcion)
                            if let codigo = linea.refaccion?.codigo, !codigo.isEmpty {
                                Text(codigo).font(.system(size: 7)).foregroundStyle(gris)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        Text(linea.cantidad.formatted())
                        Text(linea.precioUnitario.comoMoneda)
                        Text(linea.importe.comoMoneda)
                    }
                }
                if lineas.isEmpty {
                    GridRow { Text("Sin refacciones").foregroundStyle(gris).gridCellColumns(4) }
                }
                separador
                GridRow {
                    Text("Subtotal refacciones").bold()
                    Text("")
                    Text("")
                    Text(orden.totalRefacciones.comoMoneda).bold()
                }
            }
            .font(.system(size: 9))
        }
    }

    private func resumenTiempo(_ orden: OrdenServicio) -> some View {
        caja {
            etiqueta("TIEMPO DE LA REPARACIÓN")
            fila("Ingreso", orden.fechaIngreso.formatted(date: .abbreviated, time: .shortened))
            fila("Entrega", (orden.fechaEntrega ?? factura.fechaEmision).formatted(date: .abbreviated, time: .shortened))
            fila("Días en taller", orden.diasEnTaller == 0 ? "Mismo día" : "\(orden.diasEnTaller)")
            fila("Horas de mano de obra", horas(orden.horasManoDeObra))
        }
        .font(.system(size: 9))
    }

    private func totales(_ orden: OrdenServicio) -> some View {
        VStack(spacing: 4) {
            fila("Mano de obra", orden.totalManoDeObra.comoMoneda)
            fila("Refacciones", orden.totalRefacciones.comoMoneda)
            fila("Subtotal", orden.subtotal.comoMoneda)
            fila("IVA (\(orden.tasaIVA.formatted(.percent)))", orden.iva.comoMoneda)
            Rectangle().fill(tinta).frame(height: 0.8)
            HStack {
                Text("TOTAL DE LA REPARACIÓN").font(.system(size: 10, weight: .bold))
                Spacer()
                Text(orden.total.comoMoneda).font(.system(size: 12, weight: .bold))
            }
            if orden.anticipo > 0 {
                fila("Anticipo recibido", "− \(orden.anticipo.comoMoneda)")
            }
            HStack {
                Text(orden.saldo > 0 ? "SALDO A PAGAR" : "PAGADO")
                    .font(.system(size: 11, weight: .heavy))
                Spacer()
                Text(orden.saldo.comoMoneda).font(.system(size: 14, weight: .heavy))
            }
            .foregroundStyle(.white)
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .background(orden.saldo > 0 ? acento : Color(red: 0.2, green: 0.6, blue: 0.35),
                        in: .rect(cornerRadius: 6))
        }
        .font(.system(size: 9))
        .frame(width: 230)
    }

    private var garantia: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "checkmark.shield.fill")
                .font(.system(size: 22))
                .foregroundStyle(acento)
            VStack(alignment: .leading, spacing: 3) {
                Text("GARANTÍA DE \(factura.diasGarantia) DÍAS EN MANO DE OBRA")
                    .font(.system(size: 10, weight: .bold))
                Text("Vigente del \(factura.inicioGarantia.formatted(date: .long, time: .omitted)) al \(factura.finGarantia.formatted(date: .long, time: .omitted)).")
                    .font(.system(size: 9, weight: .semibold))
                Text("Cubre defectos en los trabajos realizados por el taller. No cubre desgaste normal, mal uso, accidentes ni intervenciones de terceros. Las refacciones cuentan con la garantía de su fabricante. Para hacer válida la garantía presente este documento.")
                    .font(.system(size: 8))
                    .foregroundStyle(gris)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(acento, lineWidth: 1))
    }

    private var firmas: some View {
        HStack(spacing: 50) {
            lineaFirma("Entrega (taller)")
            lineaFirma("Recibe de conformidad (cliente)")
        }
    }

    private var pie: some View {
        VStack(alignment: .leading, spacing: 2) {
            if !taller.terminos.isEmpty {
                Text(taller.terminos)
            }
            Text("Comprobante de servicio. Este documento no sustituye un comprobante fiscal digital.")
        }
        .font(.system(size: 7))
        .foregroundStyle(gris)
    }

    // MARK: Auxiliares

    private var separador: some View {
        Rectangle().fill(gris.opacity(0.4)).frame(height: 0.5).gridCellUnsizedAxes(.horizontal)
    }

    private func horas(_ valor: Double) -> String {
        "\(valor.formatted(.number.precision(.fractionLength(0...1)))) h"
    }

    private func caja<C: View>(@ViewBuilder _ contenido: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 3, content: contenido)
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(fondoSuave, in: .rect(cornerRadius: 8))
    }

    private func tituloSeccion(_ texto: String) -> some View {
        Text(texto)
            .font(.system(size: 9, weight: .bold))
            .foregroundStyle(acento)
    }

    private func etiqueta(_ texto: String) -> some View {
        Text(texto).font(.system(size: 7, weight: .semibold)).foregroundStyle(gris)
    }

    private func fila(_ titulo: String, _ valor: String) -> some View {
        HStack {
            Text(titulo)
            Spacer()
            Text(valor)
        }
    }

    private func lineaFirma(_ titulo: String) -> some View {
        VStack(spacing: 4) {
            Rectangle()
                .fill(tinta)
                .frame(maxWidth: .infinity, minHeight: 0.8, maxHeight: 0.8)
            Text(titulo).font(.system(size: 8)).foregroundStyle(gris)
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 34)
    }
}
