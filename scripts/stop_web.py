import json
import time

from web_runtime import (
    PROJECT_ROOT,
    STATUS_PATH,
    STOP_REQUEST_PATH,
    SCHEDULER_STATUS_PATH,
    ensure_runtime_directories,
    is_current_project_streamlit,
    is_current_project_scheduler,
    is_current_project_supervisor,
    process_is_alive,
    read_status,
    remove_status,
    terminate_process,
)


def stop() -> int:
    ensure_runtime_directories()
    status = read_status()
    if not status:
        print("当前没有检测到正在运行的网页服务。")
        return 0

    if str(status.get("project_root", "")) != str(PROJECT_ROOT.resolve()):
        print("状态文件不属于当前项目，为避免误停其他程序，已取消操作。")
        return 1

    try:
        pid = int(status.get("pid", 0))
        supervisor_pid = int(status.get("supervisor_pid", 0))
        scheduler_pid = int(status.get("scheduler_pid", 0))
    except (TypeError, ValueError):
        pid = 0
        supervisor_pid = 0
        scheduler_pid = 0

    if not scheduler_pid and SCHEDULER_STATUS_PATH.exists():
        try:
            scheduler_data = json.loads(
                SCHEDULER_STATUS_PATH.read_text(encoding="utf-8")
            )
            scheduler_pid = int(scheduler_data.get("pid", 0))
        except (OSError, TypeError, ValueError):
            scheduler_pid = 0

    if process_is_alive(scheduler_pid) and is_current_project_scheduler(
        scheduler_pid
    ):
        terminate_process(scheduler_pid)
    SCHEDULER_STATUS_PATH.unlink(missing_ok=True)

    if process_is_alive(supervisor_pid) and is_current_project_supervisor(
        supervisor_pid
    ):
        STOP_REQUEST_PATH.write_text("stop\n", encoding="utf-8")
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if not process_is_alive(pid) and not STATUS_PATH.exists():
                print("网页服务已停止。")
                return 0
            time.sleep(0.5)

    # 守护器失效时，只结束命令行明确包含当前 app.py 的进程。
    if process_is_alive(pid):
        if not is_current_project_streamlit(pid):
            print(
                "检测到 PID 已被其他程序使用，为避免误杀，"
                "未执行强制停止。"
            )
            return 1
        if not terminate_process(pid):
            print("网页进程停止失败，请查看任务管理器或重新启动电脑。")
            return 1

    if process_is_alive(supervisor_pid) and is_current_project_supervisor(
        supervisor_pid
    ):
        terminate_process(supervisor_pid)

    STOP_REQUEST_PATH.unlink(missing_ok=True)
    remove_status()
    print("网页服务已停止。")
    return 0


if __name__ == "__main__":
    raise SystemExit(stop())
