"""线程池任务调度：所有网络请求走后台线程，UI 线程永不阻塞。

回调统一在主线程执行（信号跨线程排队），因此回调里可以安全操作控件。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _Job(QRunnable):
    def __init__(self, job_id: int, fn: Callable[[], Any], emitter) -> None:
        super().__init__()
        self.job_id = job_id
        self.fn = fn
        self.emitter = emitter
        self.setAutoDelete(True)

    def run(self) -> None:  # 后台线程
        try:
            result = self.fn()
        except Exception as exc:  # 统一收敛，交由主线程分类处理
            self.emitter(self.job_id, None, exc)
        else:
            self.emitter(self.job_id, result, None)


class TaskRunner(QObject):
    _finished = Signal(int, object, object)

    def __init__(self, parent: Optional[QObject] = None, max_threads: int = 4) -> None:
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max_threads)
        self._callbacks: Dict[int, Tuple[Optional[Callable], Optional[Callable]]] = {}
        self._seq = 0
        self._finished.connect(self._dispatch)

    def submit(
        self,
        fn: Callable[[], Any],
        on_ok: Optional[Callable[[Any], None]] = None,
        on_err: Optional[Callable[[Exception], None]] = None,
    ) -> int:
        self._seq += 1
        job_id = self._seq
        self._callbacks[job_id] = (on_ok, on_err)
        self._pool.start(_Job(job_id, fn, self._finished.emit))
        return job_id

    def _dispatch(self, job_id: int, result: Any, error: object) -> None:
        callbacks = self._callbacks.pop(job_id, None)
        if not callbacks:
            return
        on_ok, on_err = callbacks
        try:
            if error is not None:
                if on_err:
                    on_err(error)  # type: ignore[arg-type]
            elif on_ok:
                on_ok(result)
        except RuntimeError:
            # 控件已被销毁（例如窗口已关闭），静默丢弃
            pass

    def shutdown(self) -> None:
        self._callbacks.clear()
        self._pool.clear()
        self._pool.waitForDone(1500)
