"""
editor.py — Polished rich-text editor with split-screen PDF viewer,
            inline attachment chips, and full note edit/delete support.
"""
import os
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFileDialog, QSplitter, QMenu,
                             QLineEdit, QSizePolicy, QWidget, QToolButton,
                             QMessageBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QFont

# ── Intercepting page ────────────────────────────────────────────────────────
class EditorPage(QWebEnginePage):
    pdf_view_requested = pyqtSignal(str)

    def javaScriptConsoleMessage(self, level, message, line, source):
        if message.startswith("FOCUSFLOW:VIEW_PDF:"):
            path = message[len("FOCUSFLOW:VIEW_PDF:"):]
            self.pdf_view_requested.emit(path)

# ── Editor HTML ──────────────────────────────────────────────────────────────
EDITOR_HTML = r"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{
  background:transparent;
  color:#F0F4F8;
  font-family:'Segoe UI Variable Text','Segoe UI',system-ui,sans-serif;
  font-size:16px;line-height:1.8;height:100%;
}
#editor{
  padding:32px 52px 140px 52px;
  min-height:100vh;
  outline:none;
  caret-color:#6366F1;
}
#editor:empty::before{
  content:"Start writing your note…";
  color:#2D3748;pointer-events:none;display:block;
}
h1{font-size:2.1em;font-weight:800;color:#F8FAFC;margin:28px 0 12px;line-height:1.2}
h2{font-size:1.5em;font-weight:700;color:#E2E8F0;margin:22px 0 10px}
h3{font-size:1.2em;font-weight:700;color:#CBD5E1;margin:18px 0 8px}
p{margin:6px 0}
ul,ol{padding-left:28px;margin:8px 0}li{margin:4px 0}
strong{color:#F8FAFC}em{color:#E2E8F0}
code{
  background:rgba(99,102,241,0.15);
  border:1px solid rgba(99,102,241,0.25);
  color:#A5B4FC;padding:2px 8px;border-radius:6px;
  font-family:'Cascadia Code','Consolas',monospace;font-size:.87em;
}
pre{
  background:rgba(0,0,0,0.35);
  border:1px solid rgba(255,255,255,0.07);
  border-left:3px solid #6366F1;
  padding:16px 20px;border-radius:10px;
  margin:14px 0;overflow-x:auto;
  font-family:'Cascadia Code',monospace;font-size:14px;line-height:1.6;
}
blockquote{
  border-left:3px solid #6366F1;
  padding:8px 0 8px 20px;margin:14px 0;
  color:#94A3B8;font-style:italic;
}
hr{border:none;border-top:1px solid rgba(255,255,255,0.08);margin:22px 0}
.task-row{display:flex;align-items:flex-start;gap:10px;margin:5px 0;}
.task-row input[type=checkbox]{
  margin-top:4px;width:16px;height:16px;accent-color:#6366F1;cursor:pointer;flex-shrink:0;
}
.task-row.done span{text-decoration:line-through;color:#475569}

/* PDF chip */
.pdf-chip{
  display:flex;align-items:center;gap:10px;
  background:rgba(99,102,241,0.10);
  border:1px solid rgba(99,102,241,0.30);
  border-radius:12px;padding:12px 16px;
  margin:16px 0;max-width:480px;
  user-select:none;cursor:default;
  transition:border-color .2s,background .2s;
}
.pdf-chip:hover{
  background:rgba(99,102,241,0.16);
  border-color:rgba(99,102,241,0.55);
}
.pdf-icon{font-size:28px;flex-shrink:0}
.pdf-info{flex:1;min-width:0}
.pdf-name{
  color:#A5B4FC;font-size:14px;font-weight:600;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.pdf-meta{color:#475569;font-size:11px;margin-top:2px}
.btn-view{
  background:rgba(99,102,241,0.25);
  border:1px solid rgba(99,102,241,0.5);
  border-radius:8px;color:#A5B4FC;
  padding:6px 16px;cursor:pointer;font-size:12px;font-weight:600;
  white-space:nowrap;transition:all .15s;
}
.btn-view:hover{background:rgba(99,102,241,0.55);color:white}
.btn-remove{
  background:transparent;border:none;
  color:#334155;cursor:pointer;font-size:18px;
  padding:0 4px;transition:color .15s;flex-shrink:0;line-height:1;
}
.btn-remove:hover{color:#EF4444}
::selection{background:rgba(99,102,241,0.30);color:#F8FAFC}
</style></head>
<body>
<div id="editor" contenteditable="true"></div>
<script>
const ed = document.getElementById('editor');
function fmt(cmd){ ed.focus(); document.execCommand(cmd,false,null); }
function block(tag){ ed.focus(); document.execCommand('formatBlock',false,tag); }

function insertCode(){
  ed.focus();
  const sel=window.getSelection();
  if(sel&&sel.rangeCount>0&&!sel.isCollapsed){
    document.execCommand('insertHTML',false,`<code>${sel.toString()}</code>`);
  } else {
    document.execCommand('insertHTML',false,
      '<pre style="background:rgba(0,0,0,.35);border-left:3px solid #6366F1;padding:14px 18px;border-radius:10px;font-family:monospace;margin:14px 0">// code here</pre>');
  }
}
function insertQuote(){
  ed.focus();
  document.execCommand('insertHTML',false,
    '<blockquote style="border-left:3px solid #6366F1;padding:8px 0 8px 20px;color:#94A3B8;font-style:italic;margin:14px 0">Quote text here…</blockquote>');
}
function insertChecklist(){
  ed.focus();
  document.execCommand('insertHTML',false,
    '<div class="task-row"><input type="checkbox"><span>New task</span></div>');
}
function insertHR(){
  ed.focus();
  document.execCommand('insertHorizontalRule',false,null);
}

document.addEventListener('click',function(e){
  if(e.target.classList.contains('btn-view')){
    const chip=e.target.closest('.pdf-chip');
    if(chip) console.log('FOCUSFLOW:VIEW_PDF:'+chip.dataset.path);
    return;
  }
  if(e.target.classList.contains('btn-remove')){
    const chip=e.target.closest('.pdf-chip');
    if(chip) chip.remove();
    return;
  }
  if(e.target.type==='checkbox'){
    const row=e.target.closest('.task-row');
    if(row) row.classList.toggle('done',e.target.checked);
  }
});

ed.addEventListener('keydown',function(e){
  if(e.key==='Tab'){e.preventDefault();
    document.execCommand('insertText',false,'    ');}
});

ed.addEventListener('input',function(){
  const txt=ed.innerText.trim();
  const wc=txt?txt.split(/\s+/).length:0;
  console.log('FOCUSFLOW:WORDCOUNT:'+wc);
});
</script></body></html>"""


# ── Toolbar button factory ───────────────────────────────────────────────────
def _tb_btn(label, tooltip="", colored=False, danger=False):
    btn = QPushButton(label)
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.PointingHandCursor)
    if danger:
        style = """
            QPushButton {
                background: rgba(239,68,68,0.15);
                border: 1px solid rgba(239,68,68,0.35);
                border-radius: 7px; color: #FCA5A5;
                font-size: 13px; font-weight: 600; padding: 4px 10px;
            }
            QPushButton:hover { background: rgba(239,68,68,0.35); color: white; }
        """
    elif colored:
        style = """
            QPushButton {
                background: rgba(99,102,241,0.2);
                border: 1px solid rgba(99,102,241,0.4);
                border-radius: 7px; color: #A5B4FC;
                font-size: 13px; font-weight: 600; padding: 4px 10px;
            }
            QPushButton:hover { background: rgba(99,102,241,0.45); color: white; }
        """
    else:
        style = """
            QPushButton {
                background: transparent; border: none;
                border-radius: 7px; color: #64748B;
                font-size: 13px; font-weight: 600; padding: 4px 9px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.08); color: #F8FAFC; }
        """
    btn.setStyleSheet(style)
    return btn


def _sep():
    s = QFrame()
    s.setFixedSize(1, 20)
    s.setStyleSheet("background: rgba(255,255,255,0.08); margin: 0 4px;")
    return s


# ── Main Editor widget ───────────────────────────────────────────────────────
class Editor(QFrame):
    content_changed  = pyqtSignal(str)
    attachment_added = pyqtSignal(str)
    export_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(int)   # page_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self.setObjectName("Editor")
        self.setStyleSheet("QFrame#Editor { background: transparent; }")
        self._current_file = None
        self._page_id      = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Chrome ────────────────────────────────────────────────────────
        chrome = QFrame()
        chrome.setObjectName("EditorChrome")
        chrome.setStyleSheet("""
            QFrame#EditorChrome {
                background: rgba(8,8,22,0.90);
                border-bottom: 1px solid rgba(255,255,255,0.07);
            }
        """)
        chrome_lay = QVBoxLayout(chrome)
        chrome_lay.setContentsMargins(32, 16, 28, 10)
        chrome_lay.setSpacing(6)

        # Title row
        title_row = QHBoxLayout()
        self.title_edit = QLineEdit("Untitled Page")
        self.title_edit.setStyleSheet("""
            QLineEdit {
                background: transparent; border: none;
                color: #F8FAFC; font-size: 24px; font-weight: 800; padding: 0;
            }
            QLineEdit:focus { color: white; }
        """)
        self.title_edit.setPlaceholderText("Page title…")
        title_row.addWidget(self.title_edit)
        title_row.addStretch()

        self.wc_label = QLabel("0 words")
        self.wc_label.setStyleSheet("color: #334155; font-size: 11px; background: transparent;")
        title_row.addWidget(self.wc_label)

        # Note actions (edit title is inline, these are delete + more)
        self.delete_btn = _tb_btn("🗑 Delete", "Delete this note", danger=True)
        self.delete_btn.clicked.connect(self._confirm_delete)
        title_row.addSpacing(10)
        title_row.addWidget(self.delete_btn)

        chrome_lay.addLayout(title_row)

        # Toolbar
        tb = QHBoxLayout()
        tb.setSpacing(1)

        fmt_groups = [
            [("B",  "bold",          "Bold (Ctrl+B)"),
             ("I",  "italic",        "Italic (Ctrl+I)"),
             ("U",  "underline",     "Underline (Ctrl+U)"),
             ("S̶", "strikeThrough", "Strikethrough")],
            [("H1", "h1", "Heading 1"),
             ("H2", "h2", "Heading 2"),
             ("H3", "h3", "Heading 3")],
            [("•",  "ul",    "Bullet list"),
             ("1.", "ol",    "Numbered list"),
             ("</> ", "code", "Code block"),
             ("❝",  "quote", "Blockquote"),
             ("☑",  "check", "Checklist"),
             ("—",  "hr",    "Divider")],
        ]

        for group in fmt_groups:
            for label, cmd, tip in group:
                btn = _tb_btn(label, tip)
                self._wire_fmt(btn, cmd)
                tb.addWidget(btn)
            tb.addWidget(_sep())

        tb.addStretch()

        self.pdf_toggle_btn = _tb_btn("📄 View PDF ▸", "Toggle PDF panel", colored=True)
        self.pdf_toggle_btn.setVisible(False)
        self.pdf_toggle_btn.clicked.connect(self._toggle_pdf_panel)
        tb.addWidget(self.pdf_toggle_btn)

        attach_btn = _tb_btn("📎 Attach", "Attach a file")
        attach_btn.clicked.connect(self._pick_attachment)
        tb.addWidget(attach_btn)

        export_btn = _tb_btn("↑ Export ▾", "Export note")
        export_btn.clicked.connect(self._show_export_menu)
        tb.addWidget(export_btn)

        timer_btn = _tb_btn("⏱ Focus", "Start Pomodoro timer", colored=True)
        timer_btn.clicked.connect(lambda: self.export_requested.emit("timer"))
        tb.addWidget(timer_btn)

        chrome_lay.addLayout(tb)
        root.addWidget(chrome)

        # ── Splitter ──────────────────────────────────────────────────────
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter::handle { background: rgba(255,255,255,0.05); width: 4px; }
            QSplitter::handle:hover { background: rgba(99,102,241,0.4); }
        """)

        # Web editor
        self._page = EditorPage(self)
        self._page.pdf_view_requested.connect(self.set_file_to_view)

        _orig = self._page.javaScriptConsoleMessage
        def _js_cb(level, msg, line, src):
            if msg.startswith("FOCUSFLOW:WORDCOUNT:"):
                try:
                    n = int(msg.split(":")[-1])
                    self.wc_label.setText(f"{n} word{'s' if n!=1 else ''}")
                except Exception:
                    pass
            else:
                _orig(level, msg, line, src)
        self._page.javaScriptConsoleMessage = _js_cb

        self.web_view = QWebEngineView()
        self.web_view.setPage(self._page)
        self.web_view.setHtml(EDITOR_HTML)
        self.splitter.addWidget(self.web_view)

        # PDF panel
        self.attach_panel = self._build_pdf_panel()
        self.attach_panel.hide()
        self.splitter.addWidget(self.attach_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)

        root.addWidget(self.splitter)

    # ── PDF panel builder ─────────────────────────────────────────────────────
    def _build_pdf_panel(self):
        panel = QFrame()
        panel.setObjectName("AttachPanel")
        panel.setMinimumWidth(320)
        panel.setStyleSheet("""
            QFrame#AttachPanel {
                background: rgba(6,6,18,0.92);
                border-left: 1px solid rgba(255,255,255,0.07);
            }
        """)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet("""
            QFrame {
                background: rgba(10,10,26,0.97);
                border-bottom: 1px solid rgba(255,255,255,0.07);
            }
        """)
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 10, 14, 10)

        self.pdf_name_lbl = QLabel("No file loaded")
        self.pdf_name_lbl.setStyleSheet(
            "color: #64748B; font-size: 12px; background: transparent;"
        )
        hdr_lay.addWidget(self.pdf_name_lbl, 1)

        close_btn = QPushButton("✕  Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px; color: #64748B;
                font-size: 12px; padding: 4px 14px;
            }
            QPushButton:hover {
                background: rgba(239,68,68,0.18);
                border-color: rgba(239,68,68,0.4);
                color: #FCA5A5;
            }
        """)
        close_btn.clicked.connect(self._close_pdf_panel)
        hdr_lay.addWidget(close_btn)
        lay.addWidget(hdr)

        # File-not-found banner (hidden by default)
        self._missing_banner = QLabel("⚠️  File not found — it may have been moved or deleted.")
        self._missing_banner.setAlignment(Qt.AlignCenter)
        self._missing_banner.setStyleSheet("""
            QLabel {
                background: rgba(239,68,68,0.12);
                border-bottom: 1px solid rgba(239,68,68,0.3);
                color: #FCA5A5; font-size: 13px; padding: 10px;
            }
        """)
        self._missing_banner.hide()
        lay.addWidget(self._missing_banner)

        self.attach_viewer = QWebEngineView()
        self.attach_viewer.setStyleSheet("background: transparent;")
        lay.addWidget(self.attach_viewer, 1)

        return panel

    # ── Public API ────────────────────────────────────────────────────────────
    def set_page_id(self, page_id):
        self._page_id = page_id

    def set_content(self, title: str, content: str):
        self.title_edit.setText(title or "Untitled Page")
        safe = (content or "").replace("\\", "\\\\").replace("`", "\\`")
        self.web_view.page().runJavaScript(
            f"document.getElementById('editor').innerHTML = `{safe}`;"
        )

    def get_content(self, callback):
        self.web_view.page().runJavaScript(
            "document.getElementById('editor').innerHTML", callback
        )

    def get_title(self):
        return self.title_edit.text().strip() or "Untitled Page"

    def insert_attachment_chip(self, path: str, filename: str):
        safe_path = path.replace("\\", "\\\\").replace("'", "\\'")
        safe_name = filename.replace("'", "\\'")
        ext = os.path.splitext(filename)[1].upper().lstrip(".")
        icon = {"PDF": "📄", "PPTX": "📊", "PPT": "📊",
                "DOCX": "📝", "DOC": "📝",
                "PNG": "🖼", "JPG": "🖼", "JPEG": "🖼"}.get(ext, "📎")
        js = f"""
        (function(){{
            const chip = document.createElement('div');
            chip.className = 'pdf-chip';
            chip.dataset.path = '{safe_path}';
            chip.contentEditable = 'false';
            chip.innerHTML = `
                <span class='pdf-icon'>{icon}</span>
                <div class='pdf-info'>
                    <div class='pdf-name'>{safe_name}</div>
                    <div class='pdf-meta'>Click View to open in side panel</div>
                </div>
                <button class='btn-view'>View →</button>
                <button class='btn-remove' title='Remove attachment'>✕</button>
            `;
            const ed = document.getElementById('editor');
            const sel = window.getSelection();
            if(sel && sel.rangeCount > 0){{
                const r = sel.getRangeAt(0);
                r.collapse(false);
                r.insertNode(chip);
                const br = document.createElement('p');
                br.innerHTML = '<br>';
                chip.parentNode.insertBefore(br, chip.nextSibling);
                r.setStartAfter(br);
                r.collapse(true);
                sel.removeAllRanges();
                sel.addRange(r);
            }} else {{
                ed.appendChild(chip);
            }}
        }})();
        """
        self.web_view.page().runJavaScript(js)
        self._current_file = path
        self.pdf_toggle_btn.setVisible(True)
        self.pdf_name_lbl.setText(filename)

    def set_file_to_view(self, path: str):
        if path and os.path.exists(path):
            self._missing_banner.hide()
            self.attach_viewer.load(QUrl.fromLocalFile(path))
            self.attach_panel.show()
            self.splitter.setSizes([620, 460])
            self.pdf_toggle_btn.setText("📄 Hide PDF ◂")
            self.pdf_name_lbl.setText(os.path.basename(path))
            self._current_file = path
        elif path:
            self._missing_banner.show()
            self.attach_panel.show()
            self.splitter.setSizes([620, 360])
            self.pdf_name_lbl.setText("File missing")
            self.pdf_toggle_btn.setText("📄 Hide PDF ◂")

    # ── Internal helpers ──────────────────────────────────────────────────────
    def _wire_fmt(self, btn, cmd):
        cmd_map = {
            "bold":          lambda: self._js("fmt('bold')"),
            "italic":        lambda: self._js("fmt('italic')"),
            "underline":     lambda: self._js("fmt('underline')"),
            "strikeThrough": lambda: self._js("fmt('strikeThrough')"),
            "h1":            lambda: self._js("block('H1')"),
            "h2":            lambda: self._js("block('H2')"),
            "h3":            lambda: self._js("block('H3')"),
            "ul":            lambda: self._js("fmt('insertUnorderedList')"),
            "ol":            lambda: self._js("fmt('insertOrderedList')"),
            "code":          lambda: self._js("insertCode()"),
            "quote":         lambda: self._js("insertQuote()"),
            "check":         lambda: self._js("insertChecklist()"),
            "hr":            lambda: self._js("insertHR()"),
        }
        if cmd in cmd_map:
            btn.clicked.connect(cmd_map[cmd])

    def _js(self, script: str):
        self.web_view.page().runJavaScript(script)

    def _pick_attachment(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Attach File", "",
            "Supported Files (*.pdf *.png *.jpg *.jpeg *.docx *.pptx)"
        )
        if path:
            self.attachment_added.emit(path)

    def _toggle_pdf_panel(self):
        if self.attach_panel.isHidden():
            if self._current_file:
                self.set_file_to_view(self._current_file)
        else:
            self._close_pdf_panel()

    def _close_pdf_panel(self):
        self.attach_panel.hide()
        self.pdf_toggle_btn.setText("📄 View PDF ▸")

    def _confirm_delete(self):
        if not self._page_id or self._page_id < 0:
            return
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Note")
        dlg.setText(f"Move <b>{self.get_title()}</b> to archive?")
        dlg.setInformativeText("You can restore it from the archive later.")
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        dlg.setDefaultButton(QMessageBox.Cancel)
        dlg.setStyleSheet("""
            QMessageBox {
                background: #0D0D22;
                color: white;
            }
            QLabel { color: #F8FAFC; background: transparent; }
            QPushButton {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px; color: white;
                padding: 6px 20px; font-size: 13px;
            }
            QPushButton:hover { background: rgba(239,68,68,0.3); }
        """)
        if dlg.exec_() == QMessageBox.Yes:
            self.delete_requested.emit(self._page_id)

    def _show_export_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(12,14,32,0.98);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 12px; color: white; padding: 6px;
            }
            QMenu::item { padding: 9px 20px; border-radius: 8px; font-size: 13px; }
            QMenu::item:selected { background: rgba(99,102,241,0.35); }
            QMenu::separator { height: 1px; background: rgba(255,255,255,0.07); margin: 4px 0; }
        """)
        menu.addAction("📄  Export as PDF",       lambda: self.export_requested.emit("pdf"))
        menu.addAction("✏️  Export as Markdown",  lambda: self.export_requested.emit("md"))
        menu.addAction("📝  Export as Plain Text", lambda: self.export_requested.emit("txt"))
        menu.addSeparator()
        menu.addAction("📋  Copy to Clipboard",   lambda: self.export_requested.emit("copy"))
        menu.addAction("📧  Send via Email",      lambda: self.export_requested.emit("email"))
        sender = self.sender()
        if sender:
            menu.exec_(sender.mapToGlobal(sender.rect().bottomLeft()))