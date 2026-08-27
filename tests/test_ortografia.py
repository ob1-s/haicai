"""Testes do gate ortográfico (precisam do sidecar LanguageTool no ar)."""
from unittest.mock import patch

import pytest

from haicai import ortografia
from haicai.ortografia import (
    Problema,
    bloqueantes,
    gate_rapido,
    ortografia_ok,
    tokens_desconhecidos,
    verificar,
)

try:
    verificar("fumaça")
except ConnectionError:
    pytest.skip("LanguageTool sidecar não está rodando", allow_module_level=True)


def test_frase_correta_passa():
    assert ortografia_ok("O gato dorme ao sol.")


def test_haiku_correto_passa():
    haiku = "No lago parado\na lua inteira cabe\numa pedra cai."
    assert ortografia_ok(haiku)


def test_erro_ortografico_bloqueia():
    texto = "Uma excessao a regra do jogo."
    assert not ortografia_ok(texto)
    problemas = bloqueantes(texto)
    assert any(p.regra == "MORFOLOGIK_RULE_PT_BR" for p in problemas)
    excessao = next(p for p in problemas if p.trecho == "excessao")
    assert "exceção" in excessao.sugestoes


def test_acento_faltante_bloqueia():
    assert not ortografia_ok("Avo materna mora na fazenda.")


def test_bloqueantes_filtra_por_tipo():
    falsos = [
        Problema("ESTILO_X", "style", "m", 0, 4, "algo", ()),
        Problema("GRAMATICA_Y", "grammar", "m", 5, 4, "coisa", ()),
        Problema("MORFOLOGIK_RULE_PT_BR", "misspelling", "m", 9, 3, "err", ()),
    ]
    with patch.object(ortografia, "verificar", return_value=falsos):
        sobram = bloqueantes("qualquer coisa errada aqui")
    assert [p.tipo for p in sobram] == ["misspelling"]


def test_offset_e_trecho_consistentes():
    texto = "O menino brinca no quintal."
    for p in verificar(texto):
        if p.tamanho:
            assert texto[p.offset:p.offset + p.tamanho] == p.trecho


def test_gate_rapido_passa_vocabulario_conhecido():
    ok, problemas = gate_rapido("no lago parado a lua inteira cabe")
    assert ok and problemas == []


def test_gate_rapido_bloqueia_erro_conhecido():
    ok, problemas = gate_rapido("uma excessao a regra do jogo")
    assert not ok
    assert any(p.trecho.lower() == "excessao" for p in problemas)


def test_gate_rapido_bloqueia_pre_ao90():
    assert not gate_rapido("a idéia velha da boa velha")[0]


def test_nome_proprio_passa_via_fallback():
    # Capitalizada com minúscula fora do vocabulário audita no LT ao vivo:
    # 'Brasil' é aceito pelo oráculo, 'Amazena' (grafia errada) é bloqueada.
    assert tokens_desconhecidos("Brasil é o nome do país") == ["Brasil"]
    assert gate_rapido("Brasil é o nome do país")[0]
    assert not gate_rapido("Amazena o vento na colina")[0]


def test_tokens_desconhecidos_aponta_palavra_nova():
    assert "excessao" in tokens_desconhecidos("uma excessao comum")
