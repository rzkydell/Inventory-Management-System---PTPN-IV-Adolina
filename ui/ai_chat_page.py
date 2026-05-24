"""
Halaman AI Chat — Antarmuka percakapan dengan Asisten AI Inventaris.
Desain terinspirasi dari ChatGPT/Gemini dengan tampilan modern dan responsif.
Berjalan di thread terpisah agar UI tidak membeku saat menunggu respons AI.
"""

import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QTextCursor
from utils.ai_assistant import AIAssistant


class AIWorkerThread(QThread):
    """Thread terpisah untuk memanggil API Gemini agar UI tidak membeku."""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, assistant: AIAssistant, question: str):
        super().__init__()
        self.assistant = assistant
        self.question = question

    def run(self):
        try:
            response = self.assistant.ask(self.question)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(f"⚠️ Terjadi kesalahan: {str(e)}")


class ChatBubble(QFrame):
    """Widget gelembung chat individual (user atau AI)."""

    def __init__(self, text: str, is_user: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("userBubble" if is_user else "aiBubble")
        self.is_user = is_user

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Header (icon + nama)
        header = QHBoxLayout()
        header.setSpacing(8)

        if is_user:
            icon_text = "👤"
            name_text = "Anda"
            name_color = "#1e40af"
        else:
            icon_text = "🤖"
            name_text = "Asisten AI Inventaris"
            name_color = "#059669"

        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet("font-size: 18px; background: transparent;")

        name_label = QLabel(name_text)
        name_label.setStyleSheet(f"""
            font-size: 13px; 
            font-weight: 700; 
            color: {name_color}; 
            background: transparent;
        """)

        header.addWidget(icon_label)
        header.addWidget(name_label)
        header.addStretch()
        layout.addLayout(header)

        # Konten pesan
        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setTextFormat(Qt.RichText)
        self.content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.content_label.setOpenExternalLinks(False)

        # Konversi markdown sederhana ke HTML
        html_text = self._markdown_to_html(text)
        self.content_label.setText(html_text)

        self.content_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                line-height: 1.6;
                color: {'#1e293b' if is_user else '#1e293b'};
                background: transparent;
                padding: 4px 0px;
            }}
        """)

        layout.addWidget(self.content_label)

        # Style bubble
        if is_user:
            self.setStyleSheet("""
                QFrame#userBubble {
                    background-color: #eff6ff;
                    border: 1px solid #bfdbfe;
                    border-radius: 16px;
                    margin-left: 60px;
                    margin-right: 8px;
                    margin-top: 4px;
                    margin-bottom: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#aiBubble {
                    background-color: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 16px;
                    margin-left: 8px;
                    margin-right: 60px;
                    margin-top: 4px;
                    margin-bottom: 4px;
                }
            """)

        # Drop shadow untuk kesan premium
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 25))
        self.setGraphicsEffect(shadow)

    def _markdown_to_html(self, text: str) -> str:
        """Konversi markdown dasar ke HTML untuk ditampilkan di QLabel."""
        if not text:
            return ""

        # Escape HTML entities terlebih dahulu
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")

        # Bold: **text** -> <b>text</b>
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

        # Italic: *text* -> <i>text</i>
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)

        # Inline code: `text` -> <code>text</code>
        text = re.sub(r'`([^`]+)`', r'<code style="background:#f1f5f9; padding:2px 6px; border-radius:4px; font-size:13px; color:#e11d48;">\1</code>', text)

        # Headers: ### -> bold larger
        text = re.sub(r'^### (.+)$', r'<br><b style="font-size:15px;">📋 \1</b>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<br><b style="font-size:16px;">\1</b>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<br><b style="font-size:17px;">\1</b>', text, flags=re.MULTILINE)

        # Horizontal rule
        text = re.sub(r'^---+$', r'<hr style="border: 1px solid #e2e8f0; margin: 8px 0;">', text, flags=re.MULTILINE)

        # Bullet list: - item or * item
        text = re.sub(r'^[\-\*] (.+)$', r'&nbsp;&nbsp;• \1', text, flags=re.MULTILINE)
        # Numbered list
        text = re.sub(r'^(\d+)\. (.+)$', r'&nbsp;&nbsp;\1. \2', text, flags=re.MULTILINE)

        # Table detection: lines with | 
        lines = text.split('\n')
        in_table = False
        table_html = []
        result_lines = []

        for line in lines:
            stripped = line.strip()
            if '|' in stripped and stripped.startswith('|') and stripped.endswith('|'):
                # Baris tabel
                cells = [c.strip() for c in stripped.split('|')[1:-1]]

                # Cek apakah separator (---) 
                if all(re.match(r'^[\-:]+$', c) for c in cells):
                    continue  # skip separator

                if not in_table:
                    in_table = True
                    table_html.append('<table style="border-collapse:collapse; margin:8px 0; width:100%;">')
                    # Header row
                    table_html.append('<tr>')
                    for cell in cells:
                        table_html.append(f'<th style="border:1px solid #cbd5e1; padding:6px 10px; background:#f1f5f9; font-weight:600; font-size:13px; text-align:left;">{cell}</th>')
                    table_html.append('</tr>')
                else:
                    # Data row
                    table_html.append('<tr>')
                    for cell in cells:
                        table_html.append(f'<td style="border:1px solid #cbd5e1; padding:5px 10px; font-size:13px;">{cell}</td>')
                    table_html.append('</tr>')
            else:
                if in_table:
                    table_html.append('</table>')
                    result_lines.append(''.join(table_html))
                    table_html = []
                    in_table = False
                result_lines.append(line)

        if in_table:
            table_html.append('</table>')
            result_lines.append(''.join(table_html))

        text = '\n'.join(result_lines)

        # Newline ke <br>
        text = text.replace('\n', '<br>')

        return text


class TypingIndicator(QFrame):
    """Widget animasi 'AI sedang mengetik...'"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("typingIndicator")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(8)

        icon = QLabel("🤖")
        icon.setStyleSheet("font-size: 18px; background: transparent;")

        self.dots_label = QLabel("Asisten AI sedang berpikir")
        self.dots_label.setStyleSheet("""
            font-size: 14px;
            color: #64748b;
            font-style: italic;
            font-weight: 500;
            background: transparent;
        """)

        layout.addWidget(icon)
        layout.addWidget(self.dots_label)
        layout.addStretch()

        self.setStyleSheet("""
            QFrame#typingIndicator {
                background-color: #f8fafc;
                border: 1px dashed #cbd5e1;
                border-radius: 16px;
                margin-left: 8px;
                margin-right: 120px;
                margin-top: 4px;
                margin-bottom: 4px;
            }
        """)

        # Animasi titik-titik
        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_dots)
        self._timer.start(500)

    def _animate_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        self.dots_label.setText(f"Asisten AI sedang berpikir{dots}")

    def stop(self):
        self._timer.stop()


class AIChatPage(QWidget):
    """Halaman utama AI Chat yang terintegrasi ke dalam Dashboard."""

    # Style constants
    SEND_BTN_NORMAL_STYLE = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
        }
    """

    SEND_BTN_LOADING_STYLE = """
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c1}, stop:1 {c2});
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_assistant = AIAssistant()
        self.worker_thread = None
        self.typing_indicator = None
        self._is_loading = False
        self._loading_frame = 0
        self._loading_timer = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== AREA CHAT (Scrollable) ==========
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f8fafc;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f1f5f9;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #cbd5e1;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94a3b8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: #f8fafc;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(20, 20, 20, 20)
        self.chat_layout.setSpacing(8)
        self.chat_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.chat_container)
        main_layout.addWidget(self.scroll_area, 1)

        # ========== SUGGESTED QUESTIONS ==========
        self.suggestion_frame = QFrame()
        self.suggestion_frame.setObjectName("suggestionFrame")
        self.suggestion_frame.setStyleSheet("""
            QFrame#suggestionFrame {
                background-color: #ffffff;
                border-top: 1px solid #e2e8f0;
                padding: 6px;
            }
        """)

        suggestion_layout = QHBoxLayout(self.suggestion_frame)
        suggestion_layout.setContentsMargins(20, 8, 20, 4)
        suggestion_layout.setSpacing(8)

        suggestion_label = QLabel("💡 Coba tanyakan:")
        suggestion_label.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 600;")
        suggestion_layout.addWidget(suggestion_label)

        suggestions = [
            "Barang apa yang stoknya kritis?",
            "Total transaksi bulan ini?",
            "Barang paling banyak keluar?",
        ]

        for s_text in suggestions:
            btn = QPushButton(s_text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f1f5f9;
                    color: #475569;
                    border: 1px solid #e2e8f0;
                    border-radius: 14px;
                    padding: 5px 14px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #e0e7ff;
                    border-color: #818cf8;
                    color: #4338ca;
                }
            """)
            btn.clicked.connect(lambda checked=False, text=s_text: self._use_suggestion(text))
            suggestion_layout.addWidget(btn)

        suggestion_layout.addStretch()
        main_layout.addWidget(self.suggestion_frame)

        # ========== INPUT AREA ==========
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_frame.setStyleSheet("""
            QFrame#inputFrame {
                background-color: #ffffff;
                border-top: 1px solid #e2e8f0;
            }
        """)

        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 12, 20, 16)
        input_layout.setSpacing(12)

        # Tombol Clear History
        self.btn_clear = QPushButton("🗑️")
        self.btn_clear.setToolTip("Bersihkan riwayat percakapan")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setFixedSize(44, 44)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 12px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #fee2e2;
                border-color: #f87171;
            }
        """)
        self.btn_clear.clicked.connect(self.clear_chat)
        input_layout.addWidget(self.btn_clear)

        # Text Input
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Tanyakan sesuatu tentang inventaris... (Enter untuk kirim, Shift+Enter untuk baris baru)")
        self.text_input.setFixedHeight(48)
        self.text_input.setStyleSheet("""
            QTextEdit {
                background-color: #f8fafc;
                border: 2px solid #e2e8f0;
                border-radius: 14px;
                padding: 10px 16px;
                font-size: 14px;
                color: #1e293b;
            }
            QTextEdit:focus {
                border-color: #818cf8;
                background-color: #ffffff;
            }
        """)
        self.text_input.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        input_layout.addWidget(self.text_input, 1)

        # Send Button
        self.btn_send = QPushButton("  Kirim  ➤")
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.setFixedHeight(44)
        self.btn_send.setFixedWidth(120)
        self.btn_send.setStyleSheet(self.SEND_BTN_NORMAL_STYLE)
        self.btn_send.clicked.connect(self.send_message)
        input_layout.addWidget(self.btn_send)

        main_layout.addWidget(input_frame)

        # ========== WELCOME MESSAGE ==========
        self._show_welcome()

    def _show_welcome(self):
        """Tampilkan pesan sambutan dari AI dengan statistik database."""
        welcome_text = (
            "Halo! 👋 Saya adalah **Asisten AI Inventaris PTPN IV Kebun Adolina**.\n\n"
            "Saya bisa membantu Anda menganalisis data gudang dengan cepat, seperti:\n"
            "- 📦 Mencari data barang berdasarkan nama, kategori, atau lokasi\n"
            "- ⚠️ Mengecek barang yang stoknya kritis\n"
            "- 📊 Menganalisis tren transaksi masuk/keluar\n"
            "- 🔍 Mencari riwayat transaksi spesifik\n"
            "- 📈 Memberikan insight dan ringkasan data\n\n"
            "Cukup ketik pertanyaan Anda dalam **Bahasa Indonesia** biasa, saya yang akan carikan datanya dari database! 🚀"
        )
        self._add_bubble(welcome_text, is_user=False)

        # Tampilkan statistik cepat
        try:
            stats = self.ai_assistant.get_quick_stats()
            self._add_bubble(stats, is_user=False)
        except Exception:
            pass

    def keyPressEvent(self, event):
        """Override untuk menangkap Enter pada text input."""
        super().keyPressEvent(event)

    def _install_enter_handler(self):
        """Install event filter untuk Enter key."""
        self.text_input.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Tangkap Enter key pada text input."""
        if obj == self.text_input and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        """Saat halaman ditampilkan, install event filter."""
        super().showEvent(event)
        self._install_enter_handler()

    def _use_suggestion(self, text: str):
        """Isi text input dengan pertanyaan yang disarankan lalu kirim."""
        self.text_input.setPlainText(text)
        self.send_message()

    def send_message(self):
        """Kirim pesan pengguna ke AI dan tampilkan hasilnya."""
        if self._is_loading:
            return

        question = self.text_input.toPlainText().strip()
        if not question:
            return

        # Masuk ke mode loading
        self._start_loading()
        self.text_input.clear()

        # Tampilkan bubble user
        self._add_bubble(question, is_user=True)

        # Tampilkan indikator typing
        self.typing_indicator = TypingIndicator()
        self.chat_layout.addWidget(self.typing_indicator)
        self._scroll_to_bottom()

        # Jalankan AI di thread terpisah
        self.worker_thread = AIWorkerThread(self.ai_assistant, question)
        self.worker_thread.finished.connect(self._on_ai_response)
        self.worker_thread.error.connect(self._on_ai_error)
        self.worker_thread.start()

    def _on_ai_response(self, response: str):
        """Callback saat AI memberikan respons."""
        self._remove_typing_indicator()
        self._add_bubble(response, is_user=False)
        self._enable_input()

    def _on_ai_error(self, error_msg: str):
        """Callback saat terjadi error."""
        self._remove_typing_indicator()
        self._add_bubble(error_msg, is_user=False)
        self._enable_input()

    def _remove_typing_indicator(self):
        """Hapus widget indikator typing."""
        if self.typing_indicator:
            self.typing_indicator.stop()
            self.chat_layout.removeWidget(self.typing_indicator)
            self.typing_indicator.deleteLater()
            self.typing_indicator = None

    def _start_loading(self):
        """Aktifkan mode loading — tombol kirim berubah jadi animasi spinner."""
        self._is_loading = True
        self._loading_frame = 0

        # Disable semua input
        self.text_input.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.suggestion_frame.setVisible(False)

        # Mulai animasi tombol
        self._loading_timer = QTimer(self)
        self._loading_timer.timeout.connect(self._animate_send_button)
        self._loading_timer.start(150)
        self._animate_send_button()  # tampilkan frame pertama langsung

    def _animate_send_button(self):
        """Animasi spinner pada tombol kirim saat AI sedang berpikir."""
        spinner_chars = ["◐", "◓", "◑", "◒"]
        labels = [
            "Menganalisis..",
            "Berpikir..",
            "Memproses..",
            "Mencari data..",
        ]

        idx = self._loading_frame % len(spinner_chars)
        cycle = (self._loading_frame // 8) % len(labels)
        spinner = spinner_chars[idx]
        label = labels[cycle]

        self.btn_send.setText(f" {spinner} {label}")

        # Gradien warna yang berubah perlahan untuk efek "hidup"
        color_pairs = [
            ("#6366f1", "#8b5cf6"),
            ("#7c3aed", "#a78bfa"),
            ("#8b5cf6", "#c084fc"),
            ("#7c3aed", "#a78bfa"),
        ]
        c1, c2 = color_pairs[idx]
        self.btn_send.setStyleSheet(self.SEND_BTN_LOADING_STYLE.format(c1=c1, c2=c2))

        self._loading_frame += 1

    def _stop_loading(self):
        """Hentikan mode loading — kembalikan tombol kirim ke semula."""
        self._is_loading = False

        # Hentikan timer animasi
        if self._loading_timer:
            self._loading_timer.stop()
            self._loading_timer.deleteLater()
            self._loading_timer = None

        # Kembalikan tombol ke kondisi awal
        self.btn_send.setText("  Kirim  ➤")
        self.btn_send.setStyleSheet(self.SEND_BTN_NORMAL_STYLE)

        # Aktifkan kembali semua input
        self.text_input.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.suggestion_frame.setVisible(True)
        self.text_input.setFocus()

    def _enable_input(self):
        """Aktifkan kembali input setelah AI selesai merespons."""
        self._stop_loading()

    def _add_bubble(self, text: str, is_user: bool):
        """Tambahkan gelembung chat baru ke area percakapan."""
        bubble = ChatBubble(text, is_user=is_user)
        self.chat_layout.addWidget(bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        """Scroll otomatis ke bawah."""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_chat(self):
        """Bersihkan seluruh riwayat percakapan."""
        # Hapus semua widget chat
        while self.chat_layout.count():
            child = self.chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Reset AI history
        self.ai_assistant.clear_history()

        # Tampilkan welcome lagi
        self._show_welcome()
