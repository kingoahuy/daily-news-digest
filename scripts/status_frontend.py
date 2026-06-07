from frontend_runtime import LOG_PATH, read_status, status_is_running


def show_status() -> int:
    status = read_status()
    if status_is_running(status):
        print("Next.js 前端正在运行")
        print(f"访问地址：{status['url']}")
        print(f"进程 PID：{status['pid']}")
        print(f"日志文件：{LOG_PATH}")
        return 0
    print("Next.js 前端当前未运行")
    if status and status.get("last_error"):
        print(f"最近错误：{status['last_error']}")
    print("启动命令：python scripts/start_frontend.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(show_status())
