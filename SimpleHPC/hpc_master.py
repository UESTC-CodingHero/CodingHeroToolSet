from core.net import ProgressServer
from core.helper import run_cmd


def update_progress(jid, progress, info):
    run_cmd(f"job modify {jid} /progress:{int(progress)} /progressmsg:{info}")


if __name__ == '__main__':
    ProgressServer(callback=update_progress).start()
