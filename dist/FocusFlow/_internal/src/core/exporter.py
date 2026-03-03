"""
exporter.py — Export notes to PDF, Markdown, Plain Text, and Clipboard.
"""
import os
import re
import tempfile
import subprocess
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication
from PyQt5.QtWebEngineWidgets import QWebEnginePage   # used for PDF printing
from PyQt5.QtCore import QUrl


def html_to_markdown(html: str) -> str:
    """Very lightweight HTML → Markdown conversion."""
    text = html
    text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', text, flags=re.S)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', text, flags=re.S)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', text, flags=re.S)
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.S)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.S)
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.S)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.S)
    text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.S)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.S)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)   # strip remaining tags
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def html_to_plain(html: str) -> str:
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
    text = re.sub(r'</p>', '\n\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class Exporter:
    def __init__(self, editor_view, title: str):
        """
        editor_view: the Editor widget (has .web_view and .get_content())
        title:       page title string
        """
        self.editor = editor_view
        self.title = title

    # ── Public export methods ───────────────────────────────────────────────

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(None, "Export as PDF", f"{self.title}.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        # QWebEnginePage.printToPdf prints the current web page
        self.editor.web_view.page().printToPdf(path)
        QMessageBox.information(None, "Export Complete", f"PDF saved to:\n{path}")

    def export_markdown(self):
        path, _ = QFileDialog.getSaveFileName(None, "Export as Markdown", f"{self.title}.md", "Markdown (*.md)")
        if not path:
            return
        self.editor.get_content(lambda html: self._write_text(path, html_to_markdown(html)))

    def export_plain(self):
        path, _ = QFileDialog.getSaveFileName(None, "Export as Plain Text", f"{self.title}.txt", "Text files (*.txt)")
        if not path:
            return
        self.editor.get_content(lambda html: self._write_text(path, html_to_plain(html)))

    def copy_to_clipboard(self):
        self.editor.get_content(lambda html: QApplication.clipboard().setText(html_to_plain(html)))
        QMessageBox.information(None, "Copied", "Note content copied to clipboard.")

    def send_email(self):
        """Export as PDF then open default mail client with attachment."""
        tmp = os.path.join(tempfile.gettempdir(), f"{self.title}.pdf")
        self.editor.web_view.page().printToPdf(tmp)
        # Give the PDF a moment to write, then open mail client
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: subprocess.Popen(
            f'start "" mailto:?subject={self.title}&attachment="{tmp}"',
            shell=True
        ))

    # ── Internal ────────────────────────────────────────────────────────────
    @staticmethod
    def _write_text(path: str, content: str):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            QMessageBox.information(None, "Export Complete", f"File saved to:\n{path}")
        except Exception as e:
            QMessageBox.warning(None, "Export Failed", str(e))
