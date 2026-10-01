"""三千思创无线画布 Windows 桌面入口。"""

import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn
import webview


APP_TITLE = "三千思创无线画布"
HOST = "127.0.0.1"
PORT = 3000
APP_URL = f"http://{HOST}:{PORT}/"


def application_dir() -> Path:
    """返回资源目录；兼容源码运行和 PyInstaller onedir 打包。"""
    if getattr(sys, "frozen", False):
        internal = Path(sys.executable).resolve().parent / "_internal"
        if (internal / "main.py").is_file():
            return internal
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
    return Path(__file__).resolve().parent


def configure_storage(app_dir: Path) -> None:
    """沿用现有 D 盘目录；首次使用时再在桌面版目录旁创建数据目录。"""
    if not getattr(sys, "frozen", False):
        install_dir = app_dir
    else:
        exe_dir = Path(sys.executable).resolve().parent
        # 当前仓库的发行目录是 <根目录>/代码仓库/dist/<应用名>；
        # 优先复用根目录已有的用户数据/API 密钥，更新 exe 时不会丢设置。
        roots = [exe_dir]
        if len(exe_dir.parents) >= 3:
            roots.append(exe_dir.parents[2])
        if len(exe_dir.parents) >= 2:
            roots.append(exe_dir.parents[1])
        install_dir = next(
            (root for root in roots if (root / "用户数据").exists() or (root / "API密钥").exists()),
            exe_dir,
        )
    os.environ.setdefault("SQSC_USER_DATA_DIR", str(install_dir / "用户数据"))
    os.environ.setdefault("SQSC_API_KEY_DIR", str(install_dir / "API密钥"))


def port_is_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(0.4)
        return client.connect_ex((HOST, PORT)) == 0


def wait_until_ready(timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(APP_URL, timeout=1) as response:
                if response.status < 500:
                    return
        except Exception:
            time.sleep(0.15)
    raise RuntimeError("服务启动超时，请检查 3000 端口是否被其他程序占用。")


class DesktopRuntime:
    def __init__(self) -> None:
        self.server = None
        self.thread = None
        self.owns_server = False

    def start_server(self) -> None:
        if port_is_open():
            return

        from main import app

        config = uvicorn.Config(
            app,
            host=HOST,
            port=PORT,
            log_level="warning",
            ws_ping_interval=None,
            ws_ping_timeout=None,
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, name="sqsc-server", daemon=True)
        self.thread.start()
        self.owns_server = True

    def stop_server(self) -> None:
        if self.owns_server and self.server is not None:
            self.server.should_exit = True
            if self.thread is not None:
                self.thread.join(timeout=5)


def main() -> int:
    app_dir = application_dir()
    os.chdir(app_dir)
    sys.path.insert(0, str(app_dir))
    configure_storage(app_dir)

    runtime = DesktopRuntime()
    try:
        runtime.start_server()
        wait_until_ready()
        window = webview.create_window(
            APP_TITLE,
            APP_URL,
            width=1440,
            height=900,
            min_size=(1024, 700),
            text_select=True,
        )
        window.events.closed += runtime.stop_server
        webview.start(debug=False, private_mode=False)
        return 0
    except Exception as exc:
        runtime.stop_server()
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, str(exc), f"{APP_TITLE}启动失败", 0x10)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
