import sys
import os
import requests
import logging
import yaml
from yaml import SafeLoader
import time
from datetime import timedelta
from fake_useragent import UserAgent
from pystyle import Colors, Colorate, Center
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QLabel, QPushButton, QMessageBox, QFileDialog
from PyQt5.QtGui import QIcon, QPixmap, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal, QObject
from PIL import ImageTk, Image
import webbrowser
import threading
from threading import Thread
from pyupdater.client import Client
from pyupdater import settings
import tempfile
import shutil
import stat

wersja = "0.1.2"

# Logo.
logo = """
██╗ ██╗███████╗██╗ ██╗ ██████╗ ██████╗ ████████╗
██║ ██╔╝██╔════╝╚██╗ ██╔╝ ██╔══██╗██╔═══██╗╚══██╔══╝
█████╔╝ █████╗ ╚████╔╝█████╗██████╔╝██║ ██║ ██║ 
██╔═██╗ ██╔══╝ ╚██╔╝ ╚════╝██╔══██╗██║ ██║ ██║ 
██║ ██╗███████╗ ██║ ██████╔╝╚██████╔╝ ██║ 
╚═╝ ╚═╝╚══════╝ ╚═╝ ╚═════╝ ╚═════╝ ╚═╝ 
"""

# Default config file.
default_config = """
# Konfig battle bota
bearer_token: ""
sleep_interval: 1
ticket_cost_threshold: 1000
ratelimit_sleep: 15
"""

# Clear the console.
clear = lambda: os.system("cls" if os.name in ("nt", "dos") else "clear")

# Set the console title.
os.system(f"title Key-Bot")


class BattleBot(QObject):
    log_update = pyqtSignal(str)

    def __init__(self, bearer_token, sleep_interval=1, ticket_cost_threshold=1000):
        super().__init__()
        self.session = requests.Session()
        self.user_agent = UserAgent()
        self.session.headers.update({
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Host": "kdrp2.com",
            "Origin": "https://key-drop.com",
            "Referer": "https://key-drop.com/",
            "authorization": f"Bearer {bearer_token}",
            "User-Agent": self.user_agent.random
        })
        self.base_url = "https://kdrp2.com/CaseBattle/"
        self.active_battles_url = f"{self.base_url}battle?type=active&page=0&priceFrom=0&priceTo=0.29&searchText=&sort=priceAscending&players=all&roundsCount=all"
        self.join_battle_url = f"{self.base_url}joinCaseBattle/"
        self.sleep_interval = sleep_interval
        self.ticket_cost_threshold = ticket_cost_threshold

    def load_config(self):
        try:
            with open("config.yaml", "r") as f:
                config = yaml.load(f, Loader=SafeLoader)
                self.bearer_token = config.get("bearer_token", "")
                self.sleep_interval = config.get("sleep_interval", 1)
                self.ticket_cost_threshold = config.get("ticket_cost_threshold", 1000)
                self.ratelimit_sleep = config.get("ratelimit_sleep", 1)
        except FileNotFoundError:
            with open("config.yaml", "w") as f:
                f.write(default_config)
            self.load_config()

    def save_config(self):
        config = {
            "bearer_token": self.bearer_token,
            "sleep_interval": self.sleep_interval,
            "ticket_cost_threshold": self.ticket_cost_threshold,
            "ratelimit_sleep": self.ratelimit_sleep
        }
        with open("config.yaml", "w") as f:
            yaml.dump(config, f)

    def start(self):
        self.log_update.emit("Starting BattleBot")
        if not self.bearer_token:
            self.log_update.emit("Bearer Token cannot be empty!")
            return

        while self.running:
            self.log_update.emit("Checking for battles")
            try:
                headers = {
                    "Host": "kdrp2.com",
                    "Origin": "https://key-drop.com",
                    "Referer": "https://key-drop.com/",
                    "authorization": f"Bearer {self.bearer_token}",
                    "content-type": "application/json"
                }
                with requests.Session() as session:
                    session.headers.update(headers)
                    response = session.get(self.active_battles_url)
                    if response.status_code != 200:
                        self.log_update.emit(f"Received unexpected status code: {response.status_code}")
                        self.log_update.emit(f"Response text: {response.text}")
                    else:
                        data = response.json()
                        self.log_update.emit(f"Received data: {data}")
                        battles = data.get("battles", [])
                        for battle in battles:
                            if battle["cost"] == 0:
                                self.log_update.emit(f"Joining battle: {battle}")
                                response = session.post(f"{self.join_battle_url}/{battle['id']}/join")
                                if response.status_code != 200:
                                    self.log_update.emit(f"Failed to join battle: {response.text}")
                                    continue
                                else:
                                    self.log_update.emit(f"Successfully joined battle: {battle}")
                                    battle_data = response.json()
                                    self.log_update.emit(f"Received battle data: {battle_data}")
                                    battle_id = battle_data.get("battle_id", "")
                                    battle_link = f"https://key-drop.com/battle/{battle_id}"
                                    self.log_update.emit(f"Battle link: {battle_link}")
                                    webbrowser.open(battle_link)
                                    self.log_update.emit("Waiting for the battle to end...")
                                    time.sleep(self.sleep_interval)
                                break
                self.log_update.emit("No battles found. Waiting for the next check...")
                time.sleep(self.sleep_interval)
            except requests.RequestException as e:
                self.log_update.emit(f"An error occurred: {e}")
                time.sleep(self.ratelimit_sleep)

    def stop(self):
        self.log_update.emit("Stopping BattleBot")
        self.running = False

class MainWindow(QMainWindow):
    def __init__(self):
        self.running = True
        super().__init__()

        self.setWindowTitle("Key-Bot")
        self.setWindowIcon(QIcon("icon.png"))

        # Logo Label
        self.logo_label = QLabel(self)
        self.logo_label.setGeometry(290, 20, 220, 100)
        pixmap = QPixmap("logo.png")
        self.logo_label.setPixmap(pixmap.scaled(220, 100, Qt.KeepAspectRatio))
        self.logo_label.setAlignment(Qt.AlignCenter)

        # Log Text Edit
        self.log_text_edit = QTextEdit(self)
        self.log_text_edit.setGeometry(20, 140, 760, 350)
        self.log_text_edit.setReadOnly(True)

        # Bearer Token Label
        self.bearer_token_label = QLabel(self)
        self.bearer_token_label.setGeometry(20, 510, 150, 30)
        self.bearer_token_label.setText("Bearer Token:")

        # Bearer Token Text Edit
        self.bearer_token_text_edit = QTextEdit(self)
        self.bearer_token_text_edit.setGeometry(20, 540, 550, 30)

        # Battle-bot Button
        self.battle_bot_button = QPushButton("Battle-bot", self)
        self.battle_bot_button.setGeometry(20, 580, 150, 30)
        self.battle_bot_button.clicked.connect(self.start_battle_bot)

        # Wkrótce Button
        self.wkrotce_button = QPushButton("Wkrótce", self)
        self.wkrotce_button.setGeometry(190, 580, 150, 30)
        self.wkrotce_button.setDisabled(True)

        # Edytuj Konfigurację Button
        self.edytuj_konfiguracje_button = QPushButton("Edytuj Konfigurację", self)
        self.edytuj_konfiguracje_button.setGeometry(360, 580, 150, 30)
        self.edytuj_konfiguracje_button.clicked.connect(self.edit_config)

        # Aktualizacja Button
        self.aktualizacja_button = QPushButton("Aktualizacja", self)
        self.aktualizacja_button.setGeometry(530, 580, 150, 30)
        self.aktualizacja_button.clicked.connect(self.update_application)

        # Wyjście Button
        self.wyjscie_button = QPushButton("Wyjście", self)
        self.wyjscie_button.setGeometry(700, 580, 80, 30)
        self.wyjscie_button.clicked.connect(self.close)

        # Github Link Label
        self.github_link_label = QLabel(self)
        self.github_link_label.setGeometry(20, 560, 150, 20)
        self.github_link_label.setText("<a href='https://github.com/legolasek/Key-Bot.git'>Github</a>")
        self.github_link_label.setOpenExternalLinks(True)

    def start_battle_bot(self):
        bearer_token = self.bearer_token_text_edit.toPlainText()

        if not bearer_token:
            QMessageBox.warning(self, "Error", "Bearer token is missing!")
            return

        bot = BattleBot()
        bot.bearer_token = bearer_token
        bot.log_update.connect(self.update_log)

        thread = threading.Thread(target=bot.start)
        thread.start()

    def update_log(self, message):
        print(f"Received log message: {message}")
        self.log_text_edit.append(message)

    def edit_config(self):
        config_file,_=QFileDialog.getOpenFileName(self,"Select Config File","","YAML Files (*.yaml)")
        if config_file:
            os.system(f'notepad "{config_file}"') 

    def update_application(self):
        self.aktualizacja_button.setDisabled(True) 
        threading.Thread(target=self.update_thread).start() 

    def update_thread(self):
        temp_dir=tempfile.mkdtemp() 
        client=Client(settings) 

        try:
            client.refresh() 
            app_update=client.update_check("Key-Bot",wersja) 

            if app_update:
                self.log_text_edit.append(f"{QColor(Qt.green).name()}Updating application...") 
                client.download_update(app_update,temp_dir) 

                self.log_text_edit.append(f"{QColor(Qt.green).name()}Installing update...") 
                client.extract_update(app_update,temp_dir) 

                self.log_text_edit.append(f"{QColor(Qt.green).name()}Restarting application...") 
                sleep(2) 

                self.log_text_edit.clear() 
                shutil.rmtree(temp_dir,onerror=self.remove_readonly) 

                python=sys.executable 
                os.execl(python,
                python,*sys.argv) 
            else:
                self.log_text_edit.append(f"{QColor(Qt.yellow).name()}No updates available.") 
        except Exception as e:
            self.log_text_edit.append(f"{QColor(Qt.red).name()}Error occurred during update: {str(e)}") 

            self.aktualizacja_button.setEnabled(True) 

    def remove_readonly(self,
        func,path,
        excinfo): 
        os.chmod(path,
        stat.S_IWRITE) 
        func(path) 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
