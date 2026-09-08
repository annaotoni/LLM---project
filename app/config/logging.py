import json
import logging
import sys

_CAMPOS_PADRAO = set(
    logging.LogRecord(
        name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
    ).__dict__
)


class FormatadorJSON(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
        }
        payload.update(
            {chave: valor for chave, valor in record.__dict__.items() if chave not in _CAMPOS_PADRAO}
        )
        return json.dumps(payload, ensure_ascii=False, default=str)


def configurar_logging(nivel: int = logging.INFO) -> None:
    # Fora do Docker, o Windows abre stdout no codepage do console (cp1252, não UTF-8) — sem
    # isso, acento sai como byte errado (silencioso) em vez de erro, e corrompe o log em disco.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatadorJSON())
    logging.basicConfig(level=nivel, handlers=[handler], force=True)
