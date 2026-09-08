import json
import logging
from unittest.mock import MagicMock, patch

from app.config.logging import FormatadorJSON, configurar_logging


def test_formatador_json_inclui_campos_padrao_e_extras() -> None:
    registro = logging.LogRecord(
        name="api.chat", level=logging.INFO, pathname="", lineno=0,
        msg="interacao_chat concluída", args=(), exc_info=None,
    )
    registro.tenant_id = "loja-azul"

    payload = json.loads(FormatadorJSON().format(registro))

    assert payload["nivel"] == "INFO"
    assert payload["logger"] == "api.chat"
    assert payload["mensagem"] == "interacao_chat concluída"
    assert payload["tenant_id"] == "loja-azul"


def test_formatador_json_nao_escapa_acentos() -> None:
    registro = logging.LogRecord(
        name="api.chat", level=logging.INFO, pathname="", lineno=0,
        msg="concluída", args=(), exc_info=None,
    )

    saida = FormatadorJSON().format(registro)

    # ensure_ascii=False: o acento aparece como caractere de verdade, não \uXXXX.
    assert "concluída" in saida
    assert "\\u00ed" not in saida


def test_configurar_logging_forca_utf8_no_stdout_quando_suportado() -> None:
    stdout_falso = MagicMock()

    with patch("app.config.logging.sys.stdout", stdout_falso):
        configurar_logging()

    stdout_falso.reconfigure.assert_called_once_with(encoding="utf-8")


def test_configurar_logging_nao_quebra_sem_reconfigure() -> None:
    stdout_falso = MagicMock(spec=[])  # sem o método reconfigure

    with patch("app.config.logging.sys.stdout", stdout_falso):
        configurar_logging()  # não deve levantar exceção
