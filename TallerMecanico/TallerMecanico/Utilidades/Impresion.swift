import SwiftUI
import UIKit
import PDFKit

enum Impresion {
    /// Abre el diálogo de impresión de iOS (AirPrint) con el PDF indicado.
    static func imprimir(_ url: URL, nombre: String) {
        let info = UIPrintInfo(dictionary: nil)
        info.outputType = .general
        info.jobName = nombre
        let controlador = UIPrintInteractionController.shared
        controlador.printInfo = info
        controlador.printingItem = url
        controlador.present(animated: true)
    }
}

/// Documento PDF listo para mostrarse en una hoja.
struct DocumentoPDF: Identifiable {
    let id = UUID()
    let url: URL
    let titulo: String
}

struct VistaPreviaPDF: View {
    let documento: DocumentoPDF
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VisorPDF(url: documento.url)
                .ignoresSafeArea(edges: .bottom)
                .navigationTitle(documento.titulo)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cerrar", systemImage: "xmark", role: .close) { dismiss() }
                    }
                    ToolbarItemGroup(placement: .primaryAction) {
                        ShareLink(item: documento.url) {
                            Label("Compartir", systemImage: "square.and.arrow.up")
                        }
                        Button("Imprimir", systemImage: "printer") {
                            Impresion.imprimir(documento.url, nombre: documento.titulo)
                        }
                    }
                }
        }
    }
}

struct VisorPDF: UIViewRepresentable {
    let url: URL

    func makeUIView(context: Context) -> PDFView {
        let vista = PDFView()
        vista.autoScales = true
        vista.displayMode = .singlePageContinuous
        vista.backgroundColor = .secondarySystemBackground
        vista.document = PDFDocument(url: url)
        return vista
    }

    func updateUIView(_ vista: PDFView, context: Context) {
        if vista.document?.documentURL != url {
            vista.document = PDFDocument(url: url)
        }
    }
}
