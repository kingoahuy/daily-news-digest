import webbrowser

from web_runtime import read_status, status_is_running


def open_web() -> int:
    status = read_status()
    if not status_is_running(status):
        print("网页当前未运行，请先启动：")
        print("python scripts/start_web.py")
        return 1

    url = str(status["url"])
    if webbrowser.open(url, new=2):
        print(f"已用默认浏览器打开：{url}")
        return 0

    print("未能自动打开浏览器，请手动访问：")
    print(url)
    return 1


if __name__ == "__main__":
    raise SystemExit(open_web())
