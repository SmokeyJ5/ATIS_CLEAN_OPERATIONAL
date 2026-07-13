from atis_clean.core.logging import log_event, log_error
from atis_clean.core.qt_runtime import configure_qt_runtime
from atis_clean.release.manifest import write_manifest_file

try:
    configure_qt_runtime()
    write_manifest_file()
    log_event("ATIS startup requested.")
    from atis_clean.app import main
    if __name__ == "__main__":
        main()
except Exception as exc:
    log_error("Fatal startup error", exc)
    raise
