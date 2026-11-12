import SwiftUI
import UIKit
import PDFKit
import MessageUI

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

// MARK: - Correo electrónico

/// Datos para enviar un documento por correo.
struct CorreoDocumento: Identifiable {
    let id = UUID()
    let destinatarios: [String]
    let asunto: String
    let cuerpo: String
    let adjunto: URL
}

enum Correo {
    /// `true` si el dispositivo tiene una cuenta configurada en la app Mail.
    static var disponible: Bool { MFMailComposeViewController.canSendMail() }
}

/// Redactor de correo de iOS con el PDF adjunto.
struct RedactorCorreo: UIViewControllerRepresentable {
    let correo: CorreoDocumento
    var alTerminar: (MFMailComposeResult) -> Void

    func makeCoordinator() -> Coordinador { Coordinador(alTerminar: alTerminar) }

    func makeUIViewController(context: Context) -> MFMailComposeViewController {
        let redactor = MFMailComposeViewController()
        redactor.mailComposeDelegate = context.coordinator
        redactor.setToRecipients(correo.destinatarios)
        redactor.setSubject(correo.asunto)
        redactor.setMessageBody(correo.cuerpo, isHTML: false)
        if let datos = try? Data(contentsOf: correo.adjunto) {
            redactor.addAttachmentData(datos, mimeType: "application/pdf",
                                       fileName: correo.adjunto.lastPathComponent)
        }
        return redactor
    }

    func updateUIViewController(_ controlador: MFMailComposeViewController, context: Context) {}

    final class Coordinador: NSObject, MFMailComposeViewControllerDelegate {
        let alTerminar: (MFMailComposeResult) -> Void

        init(alTerminar: @escaping (MFMailComposeResult) -> Void) {
            self.alTerminar = alTerminar
        }

        func mailComposeController(_ controller: MFMailComposeViewController,
                                   didFinishWith result: MFMailComposeResult, error: Error?) {
            alTerminar(result)
        }
    }
}
