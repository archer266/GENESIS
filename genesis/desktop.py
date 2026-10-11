"""Shared source/frozen entry point with per-user error reporting."""
import logging
import os
import sys


def main():
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from .user_files import configure_logging, user_directory
    try:
        root = user_directory()
        logger = configure_logging(root)
        from . import __version__
        logger.info("Starting GENESIS %s; frozen=%s", __version__, bool(getattr(sys, "frozen", False)))
        if len(sys.argv) >= 2 and sys.argv[1] == "--release-check":
            from .release_check import main as check
            check(sys.argv[2:])
        else:
            from .app import main as application
            application()
    except Exception as error:
        logging.getLogger("genesis").exception("Unexpected desktop failure")
        message = f"GENESIS could not continue: {error}\n\nLog location (if writable): {locals().get('root', 'per-user GENESIS folder')}\\genesis.log"
        if "--release-check" in sys.argv:
            raise SystemExit(1)
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, "GENESIS — Error", 0x10)
        else:
            print(message, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
