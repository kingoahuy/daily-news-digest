from api_runtime import LOG_PATH, read_status, status_is_running


def show_status() -> int:
    status = read_status()
    if status_is_running(status):
        print("FastAPI 后端正在运行")
        print(f"接口地址：{status['url']}")
        print(f"进程 PID：{status['pid']}")
        print(f"日志文件：{LOG_PATH}")
        return 0
    print("FastAPI 后端当前未运行")
    if status and status.get("last_error"):
        print(f"最近错误：{status['last_error']}")
    print("启动命令：python scripts/start_api.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(show_status())
