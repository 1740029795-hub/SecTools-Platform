"""
端口扫描工具 — TCP 端口扫描，内建常用端口库。

特性:
  - 三种扫描模式：常用端口 (Top 50) / Top 1000 / 自定义范围
  - 使用 python-nmap（需安装 nmap）
  - 备选方案：纯 Python socket 扫描（无需 nmap）
  - 服务识别
  - 进度显示
  - 结果过滤（按状态）
"""

from __future__ import annotations

import socket
import concurrent.futures
from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

# 常用端口 (服务名 → 端口)
COMMON_PORTS: dict[int, str] = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPC", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
    1723: "PPTP", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
    5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
    27017: "MongoDB", 27018: "MongoDB", 2222: "SSH-Alt",
    3128: "Squid", 8000: "HTTP-Dev", 8888: "HTTP-Dev",
    9200: "Elasticsearch", 11211: "Memcached", 15672: "RabbitMQ",
    5000: "Docker", 2375: "Docker-TLS", 9090: "Cockpit",
    5060: "SIP", 1521: "Oracle", 1433: "MSSQL", 2049: "NFS",
    1883: "MQTT", 5672: "AMQP", 9092: "Kafka", 6443: "K8s-API",
    8081: "HTTP-Alt", 8880: "HTTP-Alt", 10000: "Webmin",
    25565: "Minecraft", 27015: "Steam", 123: "NTP", 161: "SNMP",
}

# Top 100 常用端口（补充）
TOP_PORTS = sorted(set(
    list(COMMON_PORTS.keys()) +
    [
        7, 13, 19, 37, 49, 67, 68, 69, 70, 79, 88, 102, 113, 118, 119,
        156, 389, 465, 514, 515, 587, 636, 873, 989, 990, 991, 992, 993,
        995, 1025, 1080, 1194, 1434, 1701, 1720, 1812, 1900, 2000, 2082,
        2083, 2086, 2087, 2095, 2096, 2483, 2484, 2967, 3050, 3074, 3260,
        3268, 3269, 3333, 3478, 4000, 4444, 4567, 4664, 4899, 5000, 5104,
        5190, 5222, 5269, 5353, 5555, 5631, 5632, 5800, 5984, 6000, 6379,
        6666, 7000, 7001, 7070, 8008, 8080, 8089, 8443, 8888, 9000, 9090,
        9100, 9999, 10000, 11211, 15672, 27017, 27018, 27019,
    ]
))


class PortScanWidget(QWidget):
    """端口扫描 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 输入 ----
        input_group = QGroupBox("扫描目标")
        input_group.setStyleSheet(_group_style())
        igrid = QGridLayout(input_group)
        igrid.setSpacing(8)

        host_label = QLabel("目标主机:")
        host_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        self._host_input = QLineEdit()
        self._host_input.setPlaceholderText("例如: 192.168.1.1 或 example.com")
        self._host_input.setStyleSheet(_input_style())
        self._host_input.returnPressed.connect(self._emit_execute)
        igrid.addWidget(host_label, 0, 0)
        igrid.addWidget(self._host_input, 0, 1)

        layout.addWidget(input_group)

        # ---- 扫描模式 ----
        mode_group = QGroupBox("扫描模式")
        mode_group.setStyleSheet(_group_style())
        mode_layout = QHBoxLayout(mode_group)

        self._mode_common = QRadioButton("常用端口 (Top 50)")
        self._mode_common.setChecked(True)
        self._mode_common.setStyleSheet(_radio_style())
        mode_layout.addWidget(self._mode_common)

        self._mode_top = QRadioButton("扩展端口 (Top 150)")
        self._mode_top.setStyleSheet(_radio_style())
        mode_layout.addWidget(self._mode_top)

        self._mode_custom = QRadioButton("自定义:")
        self._mode_custom.setStyleSheet(_radio_style())
        mode_layout.addWidget(self._mode_custom)

        self._custom_ports = QLineEdit()
        self._custom_ports.setPlaceholderText("80,443,8080 或 1-1024")
        self._custom_ports.setMaximumWidth(200)
        self._custom_ports.setStyleSheet(_input_style())
        self._custom_ports.setEnabled(False)
        self._mode_custom.toggled.connect(
            lambda checked: self._custom_ports.setEnabled(checked)
        )
        mode_layout.addWidget(self._custom_ports)
        mode_layout.addStretch()

        layout.addWidget(mode_group)

        # ---- 参数 ----
        param_group = QGroupBox("扫描参数")
        param_group.setStyleSheet(_group_style())
        param_layout = QHBoxLayout(param_group)

        self._thread_cb = QComboBox()
        self._thread_cb.addItems(["10", "20", "50", "100", "200"])
        self._thread_cb.setCurrentText("50")
        self._thread_cb.setStyleSheet(_combo_style())
        param_layout.addWidget(QLabel("并发数:"))
        param_layout.addWidget(self._thread_cb)

        self._timeout_cb = QComboBox()
        self._timeout_cb.addItems(["1s", "2s", "3s", "5s", "10s"])
        self._timeout_cb.setCurrentText("2s")
        self._timeout_cb.setStyleSheet(_combo_style())
        param_layout.addWidget(QLabel("超时:"))
        param_layout.addWidget(self._timeout_cb)

        param_layout.addStretch()
        layout.addWidget(param_group)

        # ---- 按钮 ----
        btn_layout = QHBoxLayout()
        self._run_btn = QPushButton("🔍 开始扫描")
        self._run_btn.setStyleSheet(_btn_primary_style())
        self._run_btn.clicked.connect(self._emit_execute)
        btn_layout.addWidget(self._run_btn)

        self._stop_btn = QPushButton("⏹ 停止")
        self._stop_btn.setStyleSheet(_btn_danger_style())
        self._stop_btn.setVisible(False)
        btn_layout.addWidget(self._stop_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ---- 进度条 ----
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMaximumHeight(6)
        self._progress.setStyleSheet("""
            QProgressBar {
                background-color: #313244; border: none; border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #89b4fa; border-radius: 3px;
            }
        """)
        layout.addWidget(self._progress)

        # ---- 结果表格 ----
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["端口", "状态", "服务", "Banner"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setStyleSheet(_table_style())
        layout.addWidget(self._table, stretch=1)

        # 统计
        self._stat_label = QLabel("")
        self._stat_label.setStyleSheet("color: #6c7086; font-size: 12px; padding: 4px;")
        layout.addWidget(self._stat_label)

    def get_params(self) -> dict:
        if self._mode_custom.isChecked():
            ports_text = self._custom_ports.text().strip()
        elif self._mode_top.isChecked():
            ports_text = ",".join(str(p) for p in sorted(TOP_PORTS))
        else:
            ports_text = ",".join(str(p) for p in sorted(COMMON_PORTS.keys()))

        return {
            "host": self._host_input.text().strip(),
            "ports": ports_text,
            "threads": int(self._thread_cb.currentText()),
            "timeout": float(self._timeout_cb.currentText().replace("s", "")),
        }

    def add_result(self, port: int, status: str, service: str, banner: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        port_item = QTableWidgetItem(str(port))
        self._table.setItem(row, 0, port_item)

        status_item = QTableWidgetItem(status)
        if status == "开放":
            status_item.setForeground(Qt.GlobalColor.green)
        elif status == "过滤":
            status_item.setForeground(Qt.GlobalColor.yellow)
        else:
            status_item.setForeground(Qt.GlobalColor.gray)
        self._table.setItem(row, 1, status_item)

        self._table.setItem(row, 2, QTableWidgetItem(service))
        self._table.setItem(row, 3, QTableWidgetItem(banner))

    def set_progress(self, value: int) -> None:
        self._progress.setVisible(True)
        self._progress.setValue(value)
        if value >= 100:
            self._progress.setVisible(False)

    def set_stat(self, text: str) -> None:
        self._stat_label.setText(text)

    def clear_results(self) -> None:
        self._table.setRowCount(0)
        self._stat_label.clear()

    def set_running(self, running: bool) -> None:
        self._run_btn.setVisible(not running)
        self._stop_btn.setVisible(running)

    def _emit_execute(self) -> None:
        params = self.get_params()
        if params["host"]:
            self.execute_requested.emit(params)


@register_tool
class PortScanTool(BaseTool):
    """端口扫描工具"""

    meta = ToolMeta(
        name="port_scanner",
        display_name="端口扫描",
        category=ToolCategory.INFO_GATHERING,
        description="TCP 端口扫描，支持常用端口/扩展端口/自定义范围，含服务识别",
        icon="🔌",
        version="1.0.0",
        keywords=["端口", "port", "扫描", "scan", "nmap", "服务"],
        requires_external=["nmap"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[PortScanWidget] = None
        self._cancelled = False

    def create_widget(self) -> QWidget:
        self._widget = PortScanWidget()
        self._widget.execute_requested.connect(self._on_widget_execute)
        if self._widget._stop_btn:
            self._widget._stop_btn.clicked.connect(self.cancel)
        return self._widget

    def execute(self, params: dict[str, Any]) -> list[dict]:
        host = params["host"]
        ports_text = params["ports"]
        threads = params.get("threads", 50)
        timeout = params.get("timeout", 2.0)

        self._cancelled = False

        # 解析端口列表
        ports = self._parse_ports(ports_text)
        if not ports:
            self.output_ready.emit("[错误] 无法解析端口范围")
            return []

        self.output_ready.emit(f"🔍 扫描 {host}，共 {len(ports)} 个端口...")
        if self._widget:
            self._widget.set_running(True)
            self._widget.clear_results()

        # 尝试 python-nmap，失败则用 socket
        results: list[dict] = []
        try:
            import nmap
            results = self._scan_with_nmap(host, ports, timeout)
        except ImportError:
            self.output_ready.emit("python-nmap 未安装，使用 socket 扫描...")
            results = self._scan_with_socket(host, ports, threads, timeout)
        except Exception as e:
            self.output_ready.emit(f"nmap 扫描失败: {e}, 回退到 socket 扫描...")
            results = self._scan_with_socket(host, ports, threads, timeout)

        # 统计
        open_ports = [r for r in results if r["status"] == "开放"]
        stat = (
            f"扫描完成: {len(ports)} 个端口, "
            f"{len(open_ports)} 个开放"
        )
        if self._widget:
            self._widget.set_stat(stat)
            self._widget.set_progress(100)
            self._widget.set_running(False)

        self.output_ready.emit(f"✓ {stat}")
        self.progress_updated.emit(100)
        return results

    def cancel(self) -> None:
        self._cancelled = True
        self.output_ready.emit("⏹ 扫描已取消")
        if self._widget:
            self._widget.set_running(False)

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        host = params.get("host", "").strip()
        if not host:
            errors.append("请输入目标主机")
        return errors

    def _on_widget_execute(self, params: dict) -> None:
        if self._widget:
            self._widget.clear_results()
        self.execute(params)

    # ---- 内部 ----

    @staticmethod
    def _parse_ports(ports_text: str) -> list[int]:
        """解析端口字符串: "80,443,8080-8090" """
        ports: list[int] = []
        for part in ports_text.replace(" ", "").split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    ports.extend(range(int(a), int(b) + 1))
                except ValueError:
                    continue
            else:
                try:
                    ports.append(int(part))
                except ValueError:
                    continue
        return sorted(set(ports))

    def _scan_with_socket(
        self, host: str, ports: list[int], threads: int, timeout: float
    ) -> list[dict]:
        """纯 Python socket 扫描"""
        results: list[dict] = []
        total = len(ports)

        def _scan_one(port: int) -> dict:
            if self._cancelled:
                return {"port": port, "status": "跳过", "service": "", "banner": ""}
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result_code = sock.connect_ex((host, port))
                sock.close()

                if result_code == 0:
                    service = COMMON_PORTS.get(port, "unknown")
                    banner = self._grab_banner(host, port, timeout)
                    return {
                        "port": port,
                        "status": "开放",
                        "service": service,
                        "banner": banner,
                    }
                else:
                    return {
                        "port": port,
                        "status": "关闭",
                        "service": "",
                        "banner": "",
                    }
            except Exception:
                return {"port": port, "status": "错误", "service": "", "banner": ""}

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=threads
        ) as executor:
            futures = {
                executor.submit(_scan_one, p): p for p in ports
            }
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                if self._cancelled:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                completed += 1
                result = future.result()
                results.append(result)

                # 实时更新
                if result["status"] == "开放":
                    self.output_ready.emit(
                        f"  ✓ {result['port']}/tcp 开放 - {result['service']}"
                    )
                    if self._widget:
                        self._widget.add_result(
                            result["port"],
                            result["status"],
                            result["service"],
                            result["banner"],
                        )
                elif result["status"] == "过滤":
                    if self._widget:
                        self._widget.add_result(
                            result["port"], result["status"], "", ""
                        )

                progress = int(completed / total * 100)
                self.progress_updated.emit(progress)
                if self._widget:
                    self._widget.set_progress(progress)

        return sorted(results, key=lambda r: r["port"])

    def _scan_with_nmap(
        self, host: str, ports: list[int], timeout: float
    ) -> list[dict]:
        """使用 python-nmap 扫描"""
        import nmap
        nm = nmap.PortScanner()
        port_range = ",".join(str(p) for p in ports)

        self.output_ready.emit(f"nmap -sS -p {port_range} {host} ...")
        nm.scan(host, port_range, arguments=f"-sS -T4 --host-timeout {timeout}s")

        results: list[dict] = []
        if host in nm.all_hosts():
            for proto in nm[host].all_protocols():
                for port in nm[host][proto].keys():
                    port_info = nm[host][proto][port]
                    status = "开放" if port_info["state"] == "open" else port_info["state"]
                    results.append({
                        "port": port,
                        "status": status,
                        "service": port_info.get("name", ""),
                        "banner": port_info.get("product", ""),
                    })
                    if status == "开放" and self._widget:
                        self._widget.add_result(
                            port, status,
                            port_info.get("name", ""),
                            port_info.get("product", ""),
                        )
                    self.output_ready.emit(
                        f"  {port}/tcp {status} - {port_info.get('name', '')}"
                    )
        return results

    @staticmethod
    def _grab_banner(host: str, port: int, timeout: float) -> str:
        """尝试获取服务 Banner"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
            banner = sock.recv(256)
            sock.close()
            return banner.decode("utf-8", errors="replace").split("\r\n")[0][:100]
        except Exception:
            return ""


# ---- 样式 ----

def _group_style() -> str:
    return """
        QGroupBox {
            color: #cdd6f4; font-size: 14px; font-weight: bold;
            border: 1px solid #313244; border-radius: 8px;
            margin-top: 8px; padding-top: 20px;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; }
    """


def _input_style() -> str:
    return """
        QLineEdit {
            background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 10px 12px; font-size: 14px;
        }
        QLineEdit:focus { border-color: #89b4fa; }
    """


def _radio_style() -> str:
    return """
        QRadioButton { color: #cdd6f4; spacing: 6px; font-size: 13px; }
        QRadioButton::indicator { width: 16px; height: 16px; }
    """


def _combo_style() -> str:
    return """
        QComboBox {
            background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 4px;
            padding: 4px 8px; font-size: 12px; min-width: 60px;
        }
    """


def _btn_primary_style() -> str:
    return """
        QPushButton {
            background-color: #89b4fa; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; font-weight: bold;
        }
        QPushButton:hover { background-color: #74c7ec; }
    """


def _btn_danger_style() -> str:
    return """
        QPushButton {
            background-color: #f38ba8; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; font-weight: bold;
        }
        QPushButton:hover { background-color: #eba0ac; }
    """


def _btn_secondary_style() -> str:
    return """
        QPushButton {
            background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 10px 24px; font-size: 13px;
        }
        QPushButton:hover { background-color: #45475a; }
    """


def _table_style() -> str:
    return """
        QTableWidget {
            background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            gridline-color: #313244; font-size: 12px;
            alternate-background-color: #181825;
        }
        QTableWidget::item:selected { background-color: #45475a; }
        QHeaderView::section {
            background-color: #1e1e2e; color: #cdd6f4;
            border: 1px solid #313244;
            padding: 6px 8px; font-weight: bold; font-size: 12px;
        }
    """
