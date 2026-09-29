# launcher.py — build entry point, never used in normal dev
import os, sys, threading
from pathlib import Path


def main():
    data_dir = (
        Path(sys.executable).parent
        if getattr(sys, "frozen", False)
        else Path(__file__).parent
    ) / "data"
    os.environ.update(
        {
            "APP_ROLE": "terminal",
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJPOS_DATA_DIR": str(data_dir),
        }
    )

    import django

    django.setup()
    from django.core.management import call_command

    call_command("migrate", "--noinput")

    from sync.engine import worker

    threading.Thread(target=worker, daemon=True).start()

    from config.wsgi import application
    from waitress import serve

    threading.Thread(
        target=serve,
        args=(application,),
        kwargs={"host": "127.0.0.1", "port": 8001},
        daemon=True,
    ).start()
    import webview

    webview.create_window("DJPOS", "http://127.0.0.1:8001", width=1280, height=800)
    webview.start()  # blocks; closing the window closes the till app — nice kiosk behavior


if __name__ == "__main__":
    main()
