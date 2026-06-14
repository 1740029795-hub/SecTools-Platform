"""
工具工作线程 — QThread 封装，用于在后台执行耗时工具逻辑。

特性:
  - 非阻塞执行，UI 保持响应
  - 通过信号回传输出、进度、结果
  - 支持取消
  - 异常安全
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from PyQt6.QtCore import QThread, pyqtSignal


class ToolWorker(QThread):
    """后台工具执行线程"""

    # 信号
    output_line = pyqtSignal(str)       # 实时输出行
    progress = pyqtSignal(int)          # 进度 (0-100)
    finished = pyqtSignal(object)       # 执行结果
    error = pyqtSignal(str)             # 错误信息
    status_update = pyqtSignal(str)     # 状态更新

    def __init__(
        self,
        execute_fn: Callable[[dict], Any],
        params: dict[str, Any],
        parent: Optional[QThread] = None,
    ) -> None:
        super().__init__(parent)
        self._execute_fn = execute_fn
        self._params = params
        self._cancelled = False

    def run(self) -> None:
        """在线程中执行工具逻辑"""
        try:
            self.status_update.emit("运行中...")
            result = self._execute_fn(self._params)
            if not self._cancelled:
                self.finished.emit(result)
                self.status_update.emit("完成")
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))
                self.status_update.emit(f"错误: {e}")

    def cancel(self) -> None:
        """请求取消"""
        self._cancelled = True
        self.status_update.emit("正在取消...")
        if self.isRunning():
            self.terminate()
            self.wait(2000)


class ThreadedToolRunner:
    """工具线程运行器 — 管理工具执行的生命周期

    用法:
        runner = ThreadedToolRunner(tool_instance)
        runner.output_line.connect(console.append)
        runner.progress.connect(status_bar.set_progress)
        runner.finished.connect(handle_result)
        runner.run(params)
    """

    def __init__(self, tool: Any) -> None:
        """
        Args:
            tool: BaseTool 实例
        """
        self._tool = tool
        self._worker: Optional[ToolWorker] = None

        # 将工具的 output_ready 信号连接到 runner
        if hasattr(tool, 'output_ready'):
            self.output_line = tool.output_ready
        else:
            self.output_line = pyqtSignal(str)

        if hasattr(tool, 'progress_updated'):
            self.progress = tool.progress_updated
        else:
            self.progress = pyqtSignal(int)

        if hasattr(tool, 'finished'):
            self.finished = tool.finished
        else:
            self.finished = pyqtSignal(object)

    def run(self, params: dict[str, Any]) -> ToolWorker:
        """启动后台执行

        Returns:
            ToolWorker: 工作线程实例
        """
        # 创建闭包，在线程中执行时能访问工具信号
        def _execute(p: dict) -> Any:
            # 将工具的 progress_updated 连接到 worker 的 progress
            return self._tool.execute(p)

        self._worker = ToolWorker(_execute, params)
        self._worker.progress.connect(self.progress.emit)
        self._worker.status_update.connect(
            lambda s: self.output_line.emit(f"[状态] {s}")
        )
        self._worker.finished.connect(self.finished.emit)
        self._worker.error.connect(
            lambda e: self.output_line.emit(f"[错误] {e}")
        )
        self._worker.start()
        return self._worker

    def cancel(self) -> None:
        """取消执行"""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()

    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()
