"""
子进程管理器 — QProcess 封装，用于运行外部安全工具（nmap、sqlmap 等）。

特性:
  - 异步非阻塞执行（QProcess 事件驱动）
  - 实时 stdout/stderr 输出
  - 超时自动终止
  - 取消支持
  - 线程安全信号
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from PyQt6.QtCore import (
    QObject,
    QProcess,
    pyqtSignal,
    pyqtSlot,
    QTimer,
)


@dataclass
class SubprocessResult:
    """子进程执行结果"""
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    cancelled: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and not self.cancelled


class SubprocessManager(QObject):
    """QProcess 子进程管理器"""

    # 信号
    output_line = pyqtSignal(str)          # 实时输出行
    error_line = pyqtSignal(str)           # 实时错误行
    progress_updated = pyqtSignal(int)      # 进度信号
    finished = pyqtSignal(SubprocessResult) # 执行完成
    state_changed = pyqtSignal(str)         # 状态变化（用于状态栏显示）

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._timer: Optional[QTimer] = None
        self._stdout_buffer: str = ""
        self._stderr_buffer: str = ""
        self._is_running: bool = False
        self._timeout_ms: int = 30000
        self._cancelled: bool = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def execute(
        self,
        program: str,
        args: list[str] = [],
        working_dir: str = "",
        timeout_ms: int = 30000,
        env: Optional[dict[str, str]] = None,
    ) -> None:
        """启动子进程

        Args:
            program: 可执行程序路径
            args: 命令行参数
            working_dir: 工作目录
            timeout_ms: 超时时间（毫秒）
            env: 环境变量
        """
        if self._is_running:
            self.cancel()

        self._timeout_ms = timeout_ms
        self._cancelled = False
        self._stdout_buffer = ""
        self._stderr_buffer = ""

        self._process = QProcess(self)
        self._process.setProcessChannelMode(
            QProcess.ProcessChannelMode.SeparateChannels
        )

        if working_dir:
            self._process.setWorkingDirectory(working_dir)

        if env:
            qprocess_env = self._process.processEnvironment()
            for k, v in env.items():
                qprocess_env.insert(k, v)
            self._process.setProcessEnvironment(qprocess_env)

        # 连接信号
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

        # 超时定时器
        if timeout_ms > 0:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self._on_timeout)
            self._timer.start(timeout_ms)

        self._is_running = True
        self.state_changed.emit(f"正在运行: {program} {' '.join(args)}")
        self._process.start(program, args)

    def cancel(self) -> None:
        """取消正在运行的进程"""
        if self._process and self._is_running:
            self._cancelled = True
            self._process.kill()
            self._cleanup()
            self._is_running = False
            self.state_changed.emit("已取消")

    # ---- 内部槽 ----

    @pyqtSlot()
    def _on_stdout(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="replace")
        self._stdout_buffer += text
        for line in text.splitlines():
            if line.strip():
                self.output_line.emit(line)

    @pyqtSlot()
    def _on_stderr(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="replace")
        self._stderr_buffer += text
        for line in text.splitlines():
            if line.strip():
                self.error_line.emit(line)

    @pyqtSlot(int, QProcess.ExitStatus)
    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if self._cancelled:
            return
        self._cleanup()
        self._is_running = False
        result = SubprocessResult(
            exit_code=exit_code,
            stdout=self._stdout_buffer,
            stderr=self._stderr_buffer,
        )
        self.state_changed.emit(
            f"完成 (退出码: {exit_code})"
        )
        self.finished.emit(result)

    @pyqtSlot(QProcess.ProcessError)
    def _on_error(self, error: QProcess.ProcessError) -> None:
        if self._cancelled:
            return
        error_msg = {
            QProcess.ProcessError.FailedToStart: "无法启动程序",
            QProcess.ProcessError.Crashed: "程序崩溃",
            QProcess.ProcessError.Timedout: "超时",
            QProcess.ProcessError.WriteError: "写入错误",
            QProcess.ProcessError.ReadError: "读取错误",
            QProcess.ProcessError.UnknownError: "未知错误",
        }.get(error, f"错误代码: {error}")

        self._cleanup()
        self._is_running = False
        result = SubprocessResult(
            exit_code=-1,
            stdout=self._stdout_buffer,
            stderr=self._stderr_buffer + f"\n[错误] {error_msg}",
        )
        self.state_changed.emit(f"错误: {error_msg}")
        self.finished.emit(result)

    @pyqtSlot()
    def _on_timeout(self) -> None:
        """超时处理"""
        if self._process and self._is_running:
            self._process.kill()
            self._is_running = False
            result = SubprocessResult(
                exit_code=-1,
                stdout=self._stdout_buffer,
                stderr=self._stderr_buffer,
                timed_out=True,
            )
            self.state_changed.emit("超时已终止")
            self.finished.emit(result)

    def _cleanup(self) -> None:
        """清理定时器"""
        if self._timer and self._timer.isActive():
            self._timer.stop()
        self._timer = None
