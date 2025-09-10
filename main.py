# bulk_sms_campaigns.py

import sys
import csv
import os
import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QFileDialog, QMessageBox, QListWidget, QHBoxLayout,
    QInputDialog, QTabWidget, QProgressBar, QDateTimeEdit
)
from PyQt6.QtCore import QTimer, QDateTime
from PyQt6.QtGui import QPalette, QColor


class BulkSMSApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bulk SMS Manager (Android)")
        self.setGeometry(200, 80, 1100, 650)

        # Main tabs
        self.tabs = QTabWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # Data stores
        self.drafts = {}
        self.history = []
        self.contacts = {}   # {name: phone}
        self.templates = {}
        self.scheduled = []
        self.campaigns = {}  # {month: [campaigns]}

        # Timer for scheduled tasks
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_scheduled)
        self.timer.start(10000)  # check every 10 seconds

        # Build tabs
        self.init_send_tab()
        self.init_drafts_tab()
        self.init_history_tab()
        self.init_contacts_tab()
        self.init_templates_tab()
        self.init_campaigns_tab()

    # ---------------- SEND TAB ----------------
    def init_send_tab(self):
        self.tab_send = QWidget()
        send_layout = QVBoxLayout()

        self.label_csv = QLabel("Selected CSV File: None")
        send_layout.addWidget(self.label_csv)

        self.btn_csv = QPushButton("📂 Select CSV File")
        self.btn_csv.clicked.connect(self.load_csv)
        send_layout.addWidget(self.btn_csv)

        self.label_msg = QLabel("Enter SMS Message (use {name} for personalization):")
        send_layout.addWidget(self.label_msg)

        self.txt_message = QTextEdit()
        send_layout.addWidget(self.txt_message)

        self.btn_insert_template = QPushButton("📝 Insert Template")
        self.btn_insert_template.clicked.connect(self.insert_template)
        send_layout.addWidget(self.btn_insert_template)

        self.datetime_picker = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_picker.setCalendarPopup(True)
        send_layout.addWidget(QLabel("Schedule (optional):"))
        send_layout.addWidget(self.datetime_picker)

        self.btn_save_draft = QPushButton("💾 Save as Draft")
        self.btn_save_draft.clicked.connect(self.save_draft)
        send_layout.addWidget(self.btn_save_draft)

        self.btn_send = QPushButton("📨 Send Now / Schedule")
        self.btn_send.clicked.connect(self.prepare_bulk_sms)
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

    def personalize_message(self, name, message):
        return message.replace("{name}", name if name else "")

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

        self.history.append({
            "phone": phone,
            "message": message,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status
        })
        self.refresh_history()

    def prepare_bulk_sms(self):
        """Send now or schedule"""
        message = self.txt_message.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Error", "Please enter a message!")
            return

        recipients = []

        # CSV contacts
        if self.csv_file:
            with open(self.csv_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        phone = row[0].strip()
                        name = row[1].strip() if len(row) > 1 else ""
                        recipients.append((name, phone))

        # Stored contacts
        for name, phone in self.contacts.items():
            recipients.append((name, phone))

        if not recipients:
            QMessageBox.warning(self, "Error", "No recipients found.")
            return

        # Campaign
        now = datetime.datetime.now()
        default_campaign = f"{now.strftime('%B %Y')} Campaign"
        campaign_name, ok = QInputDialog.getText(self, "Campaign Name", "Enter campaign name:", text=default_campaign)
        if not ok or not campaign_name.strip():
            campaign_name = default_campaign

        # Schedule or send
        chosen_time = self.datetime_picker.dateTime().toPyDateTime()
        if chosen_time > datetime.datetime.now():
            self.scheduled.append({"time": chosen_time, "recipients": recipients, "message": message, "campaign": campaign_name})
            self.log.append(f"⏰ Scheduled {len(recipients)} SMS for {chosen_time}")
            self.save_campaign(campaign_name, message, recipients, "Scheduled")
            QMessageBox.information(self, "Scheduled", f"SMS scheduled for {chosen_time}")
        else:
            self.send_bulk_sms(recipients, message, campaign_name)

    def send_bulk_sms(self, recipients, message, campaign_name):
        self.progress.setMaximum(len(recipients))
        self.progress.setValue(0)

        for i, (name, phone) in enumerate(recipients, start=1):
            personalized = self.personalize_message(name, message)
            self.send_sms(phone, personalized)
            self.progress.setValue(i)

        QMessageBox.information(self, "Done", f"📨 Campaign '{campaign_name}' complete!")
        self.save_campaign(campaign_name, message, recipients, "Completed")

    def check_scheduled(self):
        now = datetime.datetime.now()
        due = [job for job in self.scheduled if job["time"] <= now]
        for job in due:
            self.send_bulk_sms(job["recipients"], job["message"], job["campaign"])
            self.scheduled.remove(job)

    # ---------------- DRAFTS TAB ----------------
    def init_drafts_tab(self):
        self.tab_drafts = QWidget()
        layout = QVBoxLayout()
        self.draft_list = QListWidget()
        layout.addWidget(self.draft_list)

        btns = QHBoxLayout()
        btn_edit = QPushButton("✏️ Edit")
        btn_edit.clicked.connect(self.edit_draft)
        btns.addWidget(btn_edit)

        btn_delete = QPushButton("🗑 Delete")
        btn_delete.clicked.connect(self.delete_draft)
        btns.addWidget(btn_delete)

        layout.addLayout(btns)
        self.tab_drafts.setLayout(layout)
        self.tabs.addTab(self.tab_drafts, "💾 Drafts")

    def save_draft(self):
        message = self.txt_message.toPlainText().strip()
        if message:
            self.drafts[message[:30]] = message
            self.refresh_drafts()
            QMessageBox.information(self, "Saved", "Draft saved!")

    def edit_draft(self):
        selected = self.draft_list.currentItem()
        if selected:
            self.txt_message.setPlainText(self.drafts[selected.text()])
            self.tabs.setCurrentWidget(self.tab_send)

    def delete_draft(self):
        selected = self.draft_list.currentItem()
        if selected:
            del self.drafts[selected.text()]
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
        self.tab_history.setLayout(layout)
        self.tabs.addTab(self.tab_history, "📜 History")

    def refresh_history(self):
        self.history_list.clear()
        for item in self.history:
            entry = f"{item['time']} | {item['phone']} | {item['status']} | {item['message']}"
            self.history_list.addItem(entry)

    # ---------------- CONTACTS TAB ----------------
    def init_contacts_tab(self):
        self.tab_contacts = QWidget()
        layout = QVBoxLayout()
        self.contact_list = QListWidget()
        layout.addWidget(self.contact_list)

        btns = QHBoxLayout()
        btn_add = QPushButton("➕ Add")
        btn_add.clicked.connect(self.add_contact)
        btns.addWidget(btn_add)

        btn_del = QPushButton("🗑 Delete")
        btn_del.clicked.connect(self.delete_contact)
        btns.addWidget(btn_del)

        layout.addLayout(btns)
        self.tab_contacts.setLayout(layout)
        self.tabs.addTab(self.tab_contacts, "📒 Contacts")

    def add_contact(self):
        name, ok1 = QInputDialog.getText(self, "Add Contact", "Name:")
        if ok1 and name.strip():
            phone, ok2 = QInputDialog.getText(self, "Add Contact", "Phone:")
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
        btn_add = QPushButton("➕ Add")
        btn_add.clicked.connect(self.add_template)
        btns.addWidget(btn_add)

        btn_del = QPushButton("🗑 Delete")
        btn_del.clicked.connect(self.delete_template)
        btns.addWidget(btn_del)

        layout.addLayout(btns)
        self.tab_templates.setLayout(layout)
        self.tabs.addTab(self.tab_templates, "📝 Templates")

    def add_template(self):
        title, ok1 = QInputDialog.getText(self, "Template", "Name:")
        if ok1 and title.strip():
            body, ok2 = QInputDialog.getMultiLineText(self, "Template", "Message:")
            if ok2 and body.strip():
                self.templates[title] = body.strip()
                self.refresh_templates()

    def delete_template(self):
        selected = self.template_list.currentItem()
        if selected:
            del self.templates[selected.text()]
            self.refresh_templates()

    def refresh_templates(self):
        self.template_list.clear()
        for title in self.templates.keys():
            self.template_list.addItem(title)

    def insert_template(self):
        selected = self.template_list.currentItem()
        if selected:
            self.txt_message.setPlainText(self.templates[selected.text()])

    # ---------------- CAMPAIGNS TAB ----------------
    def init_campaigns_tab(self):
        self.tab_campaigns = QWidget()
        layout = QVBoxLayout()

        self.month_tabs = QTabWidget()
        layout.addWidget(self.month_tabs)

        self.tab_campaigns.setLayout(layout)
        self.tabs.addTab(self.tab_campaigns, "📊 Campaigns")

    def save_campaign(self, name, message, recipients, status):
        month = datetime.datetime.now().strftime("%B %Y")
        if month not in self.campaigns:
            self.campaigns[month] = []

        self.campaigns[month].append({
            "name": name,
            "message": message,
            "recipients": recipients,
            "status": status,
            "created": datetime.datetime.now()
        })
        self.refresh_campaigns()

    def refresh_campaigns(self):
        self.month_tabs.clear()
        for month, campaigns in self.campaigns.items():
            tab = QWidget()
            vbox = QVBoxLayout()
            lst = QListWidget()

            # Sort campaigns newest → oldest
            sorted_camps = sorted(campaigns, key=lambda x: x["created"], reverse=True)
            for camp in sorted_camps:
                created_str = camp["created"].strftime("%Y-%m-%d %H:%M")
                lst.addItem(f"{camp['name']} ({camp['status']})    ➝ {created_str}")

            vbox.addWidget(lst)
            tab.setLayout(vbox)
            self.month_tabs.addTab(tab, f"📅 {month}")


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0B1D26"))     # Dark Blue
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#FFD700")) # Gold
    palette.setColor(QPalette.ColorRole.Base, QColor("#0F2F1E"))       # Dark Green
    palette.setColor(QPalette.ColorRole.Text, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1B3B4F"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#FFD700"))
    app.setPalette(palette)

    window = BulkSMSApp()
    window.show()
    sys.exit(app.exec())
