import subprocess
import sys
from pathlib import Path

from api_runtime import read_status as read_api_status
from frontend_runtime import read_status as read_frontend_status
from scheduler_runtime import launch_scheduler_if_enabled


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_script(name: str) -> int:
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / name)],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return completed.returncode


def main() -> int:
    print("正在确保 FastAPI 后端运行...")
    api_code = run_script("start_api.py")
    print("正在确保 Next.js 主界面运行...")
    frontend_code = run_script("start_frontend.py")
    print("正在检查本地邮件调度器...")
    scheduler_pid, scheduler_reason = launch_scheduler_if_enabled()
    if api_code or frontend_code:
        print("至少一个服务启动失败，请检查 logs/ 下的日志。")
        return 1
    api_status = read_api_status() or {}
    frontend_status = read_frontend_status() or {}
    print("====================================")
    print("Daily News Digest 已启动")
    print(
        "唯一网页入口："
        f"{frontend_status.get('url', 'http://localhost:3000')}"
    )
    print(
        "后端接口："
        f"{api_status.get('url', 'http://localhost:8000')}"
    )
    if scheduler_pid:
        print(f"本地邮件调度器 PID：{scheduler_pid}")
        print("调度器日志：logs/local_mail_scheduler.log")
    else:
        print(f"本地邮件调度器：未启用或未启动，原因：{scheduler_reason}")
    print("====================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
