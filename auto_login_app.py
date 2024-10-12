import sys, os, time, json, requests, winreg as reg, re
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class CustomCheckBox(QCheckBox):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("QCheckBox { color: #333333; spacing: 5px; }")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawText(24, int(self.height() / 2 + 5), self.text())
        checkbox_size = 18
        checkbox_rect = QRect(0, int((self.height() - checkbox_size) / 2), checkbox_size, checkbox_size)
        painter.setBrush(QColor("#4CAF50" if self.isChecked() else "#FFFFFF"))
        painter.setPen(QColor("#CCCCCC"))
        painter.drawRect(checkbox_rect)
        if self.isChecked():
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(checkbox_rect, Qt.AlignCenter, "✓")

    def sizeHint(self): return QSize(100, 30)

class AutoLoginApp(QMainWindow):
    def __init__(self, auto_start=False):
        super().__init__()
        self.auto_start = auto_start
        self.setWindowIcon(QIcon(resource_path('connection.ico')))
        self.auto_login = False
        self.session = requests.Session()
        self.moveFlag = False
        self.movePosition = None
        QTimer.singleShot(0, self.initUI)
        QTimer.singleShot(0, self.loadSettings)
        QTimer.singleShot(100, self.check_login_status)
        QTimer.singleShot(200, self.auto_login_if_needed)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_for_updates)
        self.update_timer.start(3600000)  # 每小时检查一次更新

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        container = QFrame(self)
        container.setObjectName("container")
        container.setStyleSheet("#container { background-color: #4CAF50; border-radius: 10px; }")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setStyleSheet("#titleBar { background-color: #4CAF50; border-top-left-radius: 15px; border-top-right-radius: 15px; }")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 15, 0)
        title_layout.setSpacing(0)
        title_bar.setFixedHeight(50)
        title_label = QLabel('CUMT校园网自动登录工具 by MuQYY')
        title_label.setStyleSheet("color: white; font-weight: bold;")
        title_layout.addWidget(title_label)
        close_button = QPushButton('×')
        close_button.setStyleSheet("QPushButton { background-color: transparent; color: white; font-size: 18px; font-weight: bold; border: none; } QPushButton:hover { background-color: #FF5555; }")
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button, alignment=Qt.AlignRight)
        container_layout.addWidget(title_bar)
        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        content_widget.setStyleSheet("#contentWidget { background-color: white; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; }")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(20, 20, 20, 20)
        for label_text, widget_attr in [('学号:', ('student_id_input', QLineEdit())), ('密码:', ('password_input', QLineEdit())), ('运营商:', ('operator_input', QComboBox()))]:
            layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setStyleSheet("color: #333333;")
            layout.addWidget(label)
            widget = widget_attr[1]
            if isinstance(widget, QLineEdit):
                widget.setStyleSheet("QLineEdit { border: 1px solid #CCCCCC; border-radius: 4px; padding: 5px; background-color: #F5F5F5; } QLineEdit:focus { border-color: #4CAF50; }")
                if label_text == '密码:': widget.setEchoMode(QLineEdit.Password)
            elif isinstance(widget, QComboBox):
                widget.addItems(['校园网', '中国电信', '中国移动', '中国联通'])
                widget.setStyleSheet("QComboBox { border: 1px solid #CCCCCC; border-radius: 4px; padding: 5px; padding-right: 20px; background-color: #F5F5F5; } QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left: 1px solid #CCCCCC; border-top-right-radius: 3px; border-bottom-right-radius: 3px; } QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid #333333; width: 0; height: 0; margin-right: 5px; }")
            layout.addWidget(widget)
            setattr(self, widget_attr[0], widget)
            content_layout.addLayout(layout)
        checkbox_layout = QHBoxLayout()
        for text, attr_name in [('开机自启', 'auto_start_check'), ('自动登录', 'auto_login_check')]:
            checkbox = CustomCheckBox(text)
            checkbox_layout.addWidget(checkbox)
            setattr(self, attr_name, checkbox)
        content_layout.addLayout(checkbox_layout)
        self.login_button = QPushButton('登录')
        self.login_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; border: none; border-radius: 4px; padding: 10px; font-size: 16px; } QPushButton:hover { background-color: #45a049; }")
        self.login_button.clicked.connect(self.login)
        content_layout.addWidget(self.login_button)
        self.logout_button = QPushButton('注销')
        self.logout_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; border: none; border-radius: 4px; padding: 10px; font-size: 16px; } QPushButton:hover { background-color: #d32f2f; }")
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setEnabled(False)
        content_layout.addWidget(self.logout_button)
        container_layout.addWidget(content_widget)
        main_layout.addWidget(container)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self.setFixedSize(400, 400)
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.moveFlag = True
            self.movePosition = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if Qt.LeftButton and self.moveFlag:
            self.move(event.globalPos() - self.movePosition)
            event.accept()

    def mouseReleaseEvent(self, event): self.moveFlag = False

    def loadSettings(self):
        settings = QSettings('AutoLoginApp', 'Settings')
        self.student_id_input.setText(settings.value('username', ''))
        self.password_input.setText(settings.value('password', ''))
        self.operator_input.setCurrentText(settings.value('operator', '校园网'))
        self.auto_start_check.setChecked(settings.value('autostart', False, type=bool))
        self.auto_login_check.setChecked(settings.value('auto_login', False, type=bool))
        self.auto_login = settings.value('auto_login', False, type=bool)
        if self.verify_login(): self.update_ui_after_login()
        else:
            self.login_button.setEnabled(True)
            self.logout_button.setEnabled(False)

    def saveSettings(self):
        settings = QSettings('AutoLoginApp', 'Settings')
        settings.setValue('username', self.student_id_input.text())
        settings.setValue('password', self.password_input.text())
        settings.setValue('operator', self.operator_input.currentText())
        settings.setValue('autostart', self.auto_start_check.isChecked())
        settings.setValue('auto_login', self.auto_login_check.isChecked())
        self.auto_login = self.auto_login_check.isChecked()
        self.setAutoStart(self.auto_start_check.isChecked())

    def setAutoStart(self, enable):
        key = reg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "AutoLoginApp"
        try:
            with reg.OpenKey(key, key_path, 0, reg.KEY_ALL_ACCESS) as registry_key:
                if enable: reg.SetValueEx(registry_key, app_name, 0, reg.REG_SZ, f'"{sys.executable}" "{os.path.abspath(__file__)}" --auto-start')
                else: reg.DeleteValue(registry_key, app_name)
        except WindowsError: print("无法设置开机自启")

    def update_ui_after_login(self):
        self.login_button.setEnabled(False)
        self.logout_button.setEnabled(True)

    def login(self):
        self.session = requests.Session()
        username = self.student_id_input.text()
        password = self.password_input.text()
        operator = self.operator_input.currentText()
        self.saveSettings()
        username += "@xyw" if operator == "校园网" else "@telecom" if operator == "中国电信" else "@cmcc" if operator == "中国移动" else "@unicom"
        ip_attempts = [""]
        headers = {
            "Accept": "*/*", "Accept-Encoding": "gzip, deflate", "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive", "Host": "10.2.5.251:801", "Referer": "http://10.2.5.251/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        }
        for ip in ip_attempts:
            try:
                timestamp = int(time.time() * 1000)
                callback = f"dr{timestamp}"
                login_url = f"http://10.2.5.251:801/eportal/?c=Portal&a=login&callback={callback}&login_method=1&user_account={username}&user_password={password}&wlan_user_ip={ip}&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&jsVersion=3.0&_={timestamp}"
                login_response = self.session.get(login_url, headers=headers, timeout=5)
                login_response.raise_for_status()
                print(f"服务器响应: {login_response.text}")
                response_text = login_response.text
                json_str = response_text[response_text.index('(') + 1 : response_text.rindex(')')]
                response_data = json.loads(json_str)
                result = response_data.get('result')
                ret_code = response_data.get('ret_code', '')
                msg = response_data.get('msg', '')
                if result == '1':
                    if self.verify_login():
                        QMessageBox.information(self, "成功", "登录成功")
                        self.update_ui_after_login()
                        if self.auto_start:
                            self.close()
                            sys.exit(0)
                        return
                    else: print("登录似乎成功，但无法验证网络连接")
                elif result == '0':
                    if ret_code == '1':
                        QMessageBox.warning(self, "错误", "账号或密码错误，请重新登录")
                        return
                    elif ret_code == '2' or "在线数量超过限制" in msg:
                        QMessageBox.information(self, "提示", "您已经登录过了")
                        self.update_ui_after_login()
                        if self.auto_start:
                            self.close()
                            sys.exit(0)
                        return
            except requests.RequestException as e: print(f"尝试登录时发生网络错误: {str(e)}")
            except json.JSONDecodeError as e: print(f"解析响应失败: {str(e)}")
            except Exception as e: print(f"发生未知错误: {str(e)}")
        QMessageBox.warning(self, "错误", "登录失败，请检查网络连接或稍后重试")

    def logout(self):
        try:
            timestamp = int(time.time() * 1000)
            callback = f"dr{timestamp}"
            logout_url = f"http://10.2.5.251:801/eportal/?c=Portal&a=logout&callback={callback}&login_method=1&user_account=drcom&user_password=123&ac_logout=0&wlan_user_ip={self.get_user_ip()}&wlan_user_ipv6=&wlan_vlan_id=1&wlan_user_mac={self.get_user_mac()}&wlan_ac_ip=&wlan_ac_name=&jsVersion=3.0&_={timestamp-22}"
            headers = {
                "Accept": "*/*",                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Host": "10.2.5.251:801",
                "Referer": "http://10.2.5.251/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            }
            response = self.session.get(logout_url, headers=headers, timeout=5)
            response.raise_for_status()
            print(f"注销响应: {response.text}")
            json_str = response.text[response.text.index('(') + 1 : response.text.rindex(')')]
            result = json.loads(json_str)
            if result.get('result') == '1':
                QMessageBox.information(self, "成功", "已成功注销")
                self.clear_login_status()
            else:
                QMessageBox.warning(self, "错误", f"注销失败: {result.get('msg', '未知错误')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "错误", f"注销时发生网络错误: {str(e)}")
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "错误", f"解析响应时发生错误: {str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"注销时发生未知错误: {str(e)}")

    def get_user_ip(self):
        try:
            response = self.session.get("http://10.2.5.251/", timeout=5)
            ip_match = re.search(r'user_ip\s*=\s*[\'"](.+?)[\'"]', response.text)
            if ip_match: return ip_match.group(1)
        except Exception as e: print(f"获取用户 IP 时出错: {str(e)}")
        return ""

    def get_user_mac(self):
        try:
            response = self.session.get("http://10.2.5.251/", timeout=5)
            mac_match = re.search(r'user_mac\s*=\s*[\'"](.+?)[\'"]', response.text)
            if mac_match: return mac_match.group(1)
        except Exception as e: print(f"获取用户 MAC 地址时出错: {str(e)}")
        return ""

    def clear_login_status(self):
        self.session = requests.Session()
        self.login_button.setEnabled(True)
        self.logout_button.setEnabled(False)

    def verify_login(self):
        try:
            response = self.session.get("http://10.2.5.251/", timeout=5)
            print("Login verification response:", response.text)
            return "已登录" in response.text or "注销" in response.text or "在线数量超过限制" in response.text
        except Exception as e:
            print("Login verification error:", str(e))
            return False

    def check_login_status(self):
        if self.verify_login(): self.update_ui_after_login()

    def auto_login_if_needed(self):
        if self.auto_login: self.login()

    def check_for_updates(self):
        try:
            response = requests.get("https://api.github.com/repos/MuQY1818/CUMT_Net_Auto_Login/releases/latest")
            latest_version = response.json()["tag_name"]
            current_version = "v1.0.1"  # 当前版本
            if latest_version > current_version:
                QMessageBox.information(self, "更新可用", f"新版本 {latest_version} 可用。请访问 GitHub 页面下载最新版本。")
        except Exception as e:
            print(f"检查更新时出错: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path('connection.ico')))  
    auto_start = '--auto-start' in sys.argv
    ex = AutoLoginApp(auto_start)
    sys.exit(app.exec_())