from web_runtime import (
    LOG_PATH,
    SCHEDULER_LOG_PATH,
    display_relative_path,
    is_current_project_scheduler,
    process_is_alive,
    read_status,
    status_is_running,
)


def show_status() -> int:
    status = read_status()
    if status_is_running(status):
        print("网页正在运行")
        print(f"访问地址：{status['url']}")
        print(f"进程 PID：{status['pid']}")
        print(f"日志文件：{display_relative_path(LOG_PATH)}")
        scheduler_pid = int(status.get("scheduler_pid", 0))
        if process_is_alive(scheduler_pid) and is_current_project_scheduler(
            scheduler_pid
        ):
            print(f"本地邮件调度器 PID：{scheduler_pid}")
            print(
                "调度器日志："
                f"{display_relative_path(SCHEDULER_LOG_PATH)}"
            )
        else:
            print("本地邮件调度器：未运行")
        return 0

    print("网页当前未运行")
    if status and status.get("last_error"):
        print(f"最近错误：{status['last_error']}")
        print(f"日志文件：{display_relative_path(LOG_PATH)}")
    print("启动命令：python scripts/start_web.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(show_status())
