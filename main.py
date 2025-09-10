# bulk_sms_pro.py

import sys
import csv
import os
import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QFileDialog, QMessageBox, QListWidget, QHBoxLayout,
    QLineEdit, QTabWidget, QProgressBar, QInputDialog
)
from PyQt6.QtGui import QPalette, QColor


class BulkSMSApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bulk SMS Manager (Android)")
        self.setGeometry(300, 100, 900, 600)

        # Tabs
        self.tabs = QTabWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # Data stores
        self.drafts = {}
        self.history = []
        self.contacts = {}
        self.templates = {}

        # Build Tabs
        self.init_send_tab()
        self.init_drafts_tab()
        self.init_history_tab()
        self.init_contacts_tab()
        self.init_templates_tab()

    # ---------------- SEND TAB ----------------
    def init_send_tab(self):
        self.tab_send = QWidget()
        send_layout = QVBoxLayout()

        self.label_csv = QLabel("Selected CSV File: None")
        send_layout.addWidget(self.label_csv)

        self.btn_csv = QPushButton("📂 Select CSV File")
        self.btn_csv.clicked.connect(self.load_csv)
        send_layout.addWidget(self.btn_csv)

        self.label_msg = QLabel("Enter SMS Message:")
        send_layout.addWidget(self.label_msg)

        self.txt_message = QTextEdit()
        send_layout.addWidget(self.txt_message)

        self.btn_insert_template = QPushButton("📝 Insert Template")
        self.btn_insert_template.clicked.connect(self.insert_template)
        send_layout.addWidget(self.btn_insert_template)

        self.btn_save_draft = QPushButton("💾 Save as Draft")
        self.btn_save_draft.clicked.connect(self.save_draft)
        send_layout.addWidget(self.btn_save_draft)

        self.btn_send = QPushButton("📨 Send SMS")
        self.btn_send.clicked.connect(self.send_bulk_sms)
        send_layout.addWidget(self.btn_send)

        self.progress = QProgressBar()
        send_layout.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        send_layout.addWidget(self.log)

        self.tab_send.setLayout(send_layout)
        self.tabs.addTab(self.tab_send, "📤 Send SMS")

        self.csv_file = None

    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.csv_file = file_path
            self.label_csv.setText(f"Selected CSV File: {file_path}")

    def send_sms(self, phone, message):
        try:
            cmd = f'adb shell service call isms 7 i32 0 s16 "com.android.mms.service" ' \
                  f's16 "{phone}" s16 "null" s16 "{message}" s16 "null" s16 "null"'
            os.system(cmd)
            status = "✅ Success"
            self.log.append(f"✅ Sent to {phone}")
        except Exception as e:
            status = f"❌ Failed: {e}"
            self.log.append(f"❌ Failed to {phone}: {e}")

        # Save in history
        self.history.append({
            "phone": phone,
            "message": message,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status
        })
        self.refresh_history()

    def send_bulk_sms(self):
        message = self.txt_message.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Error", "Please enter a message!")
            return

        numbers = []

        # From CSV
        if self.csv_file:
            with open(self.csv_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        numbers.append(row[0].strip())

        # From Contacts
        for phone in self.contacts.values():
            numbers.append(phone)

        if not numbers:
            QMessageBox.warning(self, "Error", "No recipients found (CSV or Contacts).")
            return

        self.progress.setMaximum(len(numbers))
        self.progress.setValue(0)

        for i, phone in enumerate(numbers, start=1):
            self.send_sms(phone, message)
            self.progress.setValue(i)

        QMessageBox.information(self, "Done", "📨 Bulk SMS sending complete!")

    # ---------------- DRAFTS TAB ----------------
    def init_drafts_tab(self):
        self.tab_drafts = QWidget()
        layout = QVBoxLayout()

        self.draft_list = QListWidget()
        layout.addWidget(self.draft_list)

        btns = QHBoxLayout()
        self.btn_edit_draft = QPushButton("✏️ Edit Draft")
        self.btn_edit_draft.clicked.connect(self.edit_draft)
        btns.addWidget(self.btn_edit_draft)

        self.btn_delete_draft = QPushButton("🗑 Delete Draft")
        self.btn_delete_draft.clicked.connect(self.delete_draft)
        btns.addWidget(self.btn_delete_draft)

        layout.addLayout(btns)
        self.tab_drafts.setLayout(layout)
        self.tabs.addTab(self.tab_drafts, "💾 Drafts")

    def save_draft(self):
        message = self.txt_message.toPlainText().strip()
        if message:
            self.drafts[message[:30]] = message
            self.refresh_drafts()
            QMessageBox.information(self, "Saved", "Draft saved successfully!")

    def edit_draft(self):
        selected = self.draft_list.currentItem()
        if selected:
            draft_key = selected.text()
            self.txt_message.setPlainText(self.drafts[draft_key])
            self.tabs.setCurrentWidget(self.tab_send)

    def delete_draft(self):
        selected = self.draft_list.currentItem()
        if selected:
            draft_key = selected.text()
            del self.drafts[draft_key]
            self.refresh_drafts()

    def refresh_drafts(self):
        self.draft_list.clear()
        for k in self.drafts.keys():
            self.draft_list.addItem(k)

    # ---------------- HISTORY TAB ----------------
    def init_history_tab(self):
        self.tab_history = QWidget()
        layout = QVBoxLayout()

        self.history_list = QListWidget()
        layout.addWidget(self.history_list)

        self.btn_export_history = QPushButton("⬇ Export History to CSV")
        self.btn_export_history.clicked.connect(self.export_history)
        layout.addWidget(self.btn_export_history)

        self.tab_history.setLayout(layout)
        self.tabs.addTab(self.tab_history, "📜 History")

    def refresh_history(self):
        self.history_list.clear()
        for item in self.history:
            entry = f"{item['time']} | {item['phone']} | {item['status']} | {item['message']}"
            self.history_list.addItem(entry)

    def export_history(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save History", "", "CSV Files (*.csv)")
        if file_path:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "Phone", "Message", "Status"])
                for item in self.history:
                    writer.writerow([item["time"], item["phone"], item["message"], item["status"]])
            QMessageBox.information(self, "Exported", "History exported successfully!")

    # ---------------- CONTACTS TAB ----------------
    def init_contacts_tab(self):
        self.tab_contacts = QWidget()
        layout = QVBoxLayout()

        self.contact_list = QListWidget()
        layout.addWidget(self.contact_list)

        btns = QHBoxLayout()
        self.btn_add_contact = QPushButton("➕ Add Contact")
        self.btn_add_contact.clicked.connect(self.add_contact)
        btns.addWidget(self.btn_add_contact)

        self.btn_delete_contact = QPushButton("🗑 Delete Contact")
        self.btn_delete_contact.clicked.connect(self.delete_contact)
        btns.addWidget(self.btn_delete_contact)

        layout.addLayout(btns)

        self.tab_contacts.setLayout(layout)
        self.tabs.addTab(self.tab_contacts, "📒 Contacts")

    def add_contact(self):
        name, ok1 = QInputDialog.getText(self, "Add Contact", "Enter contact name:")
        if ok1 and name.strip():
            phone, ok2 = QInputDialog.getText(self, "Add Contact", "Enter phone number:")
            if ok2 and phone.strip():
                self.contacts[name] = phone.strip()
                self.refresh_contacts()

    def delete_contact(self):
        selected = self.contact_list.currentItem()
        if selected:
            name = selected.text().split(" | ")[0]
            del self.contacts[name]
            self.refresh_contacts()

    def refresh_contacts(self):
        self.contact_list.clear()
        for name, phone in self.contacts.items():
            self.contact_list.addItem(f"{name} | {phone}")

    # ---------------- TEMPLATES TAB ----------------
    def init_templates_tab(self):
        self.tab_templates = QWidget()
        layout = QVBoxLayout()

        self.template_list = QListWidget()
        layout.addWidget(self.template_list)

        btns = QHBoxLayout()
        self.btn_add_template = QPushButton("➕ Add Template")
        self.btn_add_template.clicked.connect(self.add_template)
        btns.addWidget(self.btn_add_template)

        self.btn_delete_template = QPushButton("🗑 Delete Template")
        self.btn_delete_template.clicked.connect(self.delete_template)
        btns.addWidget(self.btn_delete_template)

        layout.addLayout(btns)

        self.tab_templates.setLayout(layout)
        self.tabs.addTab(self.tab_templates, "📝 Templates")

    def add_template(self):
        title, ok1 = QInputDialog.getText(self, "Add Template", "Enter template name:")
        if ok1 and title.strip():
            body, ok2 = QInputDialog.getMultiLineText(self, "Add Template", "Enter message body (use {name} if needed):")
            if ok2 and body.strip():
                self.templates[title] = body.strip()
                self.refresh_templates()

    def delete_template(self):
        selected = self.template_list.currentItem()
        if selected:
            title = selected.text()
            del self.templates[title]
            self.refresh_templates()

    def refresh_templates(self):
        self.template_list.clear()
        for title in self.templates.keys():
            self.template_list.addItem(title)

    def insert_template(self):
        selected = self.template_list.currentItem()
        if selected:
            template_title = selected.text()
            self.txt_message.setPlainText(self.templates[template_title])


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Dark theme with green, blue, and gold
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0B1D26"))     # Dark Blue background
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#FFD700")) # Gold text
    palette.setColor(QPalette.ColorRole.Base, QColor("#0F2F1E"))       # Dark Green inputs
    palette.setColor(QPalette.ColorRole.Text, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1B3B4F"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#FFD700"))
    app.setPalette(palette)

    window = BulkSMSApp()
    window.show()
    sys.exit(app.exec())
