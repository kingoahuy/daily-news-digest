import time

from frontend_runtime import (
    STATUS_PATH,
    STOP_REQUEST_PATH,
    ensure_directories,
    is_current_frontend,
    is_current_supervisor,
    process_is_alive,
    read_status,
    remove_status,
    stop_process,
    terminate_process,
)


def stop() -> int:
    ensure_directories()
    status = read_status()
    if not status:
        print("Next.js 前端当前未运行。")
        return 0

    pid = int(status.get("pid", 0))
    supervisor_pid = int(status.get("supervisor_pid", 0))
    if process_is_alive(supervisor_pid) and is_current_supervisor(supervisor_pid):
        STOP_REQUEST_PATH.write_text("stop\n", encoding="utf-8")
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if not process_is_alive(pid) and not STATUS_PATH.exists():
                print("Next.js 前端已停止。")
                return 0
            time.sleep(0.5)

    if process_is_alive(pid) and is_current_frontend(pid):
        stop_process(pid)
    if process_is_alive(supervisor_pid) and is_current_supervisor(supervisor_pid):
        terminate_process(supervisor_pid)
    STOP_REQUEST_PATH.unlink(missing_ok=True)
    remove_status()
    print("Next.js 前端已停止。")
    return 0


if __name__ == "__main__":
    raise SystemExit(stop())
