import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_script(name: str) -> int:
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / name)],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return completed.returncode


def main() -> int:
    print("正在确保 Streamlit 新闻知识库运行...")
    streamlit_code = run_script("start_web.py")
    print("正在确保 Next.js 新闻前端运行...")
    frontend_code = run_script("start_frontend.py")
    if streamlit_code or frontend_code:
        print("至少一个本地站点启动失败，请检查 logs/ 下的日志。")
        return 1
    print("两个本地站点均已启动。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
