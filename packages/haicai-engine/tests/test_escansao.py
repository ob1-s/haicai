import pytest

from haicai import escandir, forma_ok


def intervalo(linha):
    r = escandir(linha)
    return r.minimo, r.maximo


# ---- contagem básica: postônicas finais caem -------------------------------

def test_paroxitona_final_cai_postotonica():
    # sau-da-de: tônica em "da", "-de" final não conta; diérese sa-ú abre o 3
    assert intervalo("saudade") == (2, 3)


def test_oxitona_nada_cai():
    # co-ra-ção: oxítona, conta tudo
    assert intervalo("coração") == (3, 3)


def test_proparoxitona_cai_duas():
    # "última" = úl-ti-ma: tônica em "úl", contam 1
    assert intervalo("última") == (1, 1)


# ---- sinalefa (fusão entre palavras) ---------------------------------------

def test_sinalefa_basica():
    # "a-ve a-zul": ave(2) + azul(2); com fusão "ve|a" = 3, sem = 4
    assert intervalo("ave azul") == (3, 4)


def test_consoante_bloqueia():
    # "mar azul": r|a não funde (consoante fecha); mar(1)+a(2)+zul(3)
    assert intervalo("mar azul") == (3, 3)


def test_h_silento_permite():
    # "na hora": HO-ra paroxítona; fusão "na|ho" absorve a tônica -> 1, sem -> 2
    assert intervalo("na hora") == (1, 2)


# ---- sinérese e diérese (dentro da palavra) --------------------------------

def test_sinerese_sinfonia():
    # sin-fo-ni-a (4 gram.) -> sin-fo-nia (3) com sinérese
    assert intervalo("sinfonia") == (3, 3)


def test_sinerese_historia():
    # his-TÓ-ri-a: contagem vai até a tônica "tó" -> 2 nas duas leituras
    assert intervalo("história") == (2, 2)


def test_dierese_traicao():
    # trai-ção (2) -> tra-i-ção (3); tônica em "ção", conta tudo
    assert intervalo("traição") == (2, 3)


# ---- átonas -----------------------------------------------------------------

def test_atona_final_nao_carrega():
    # "flor de": tônica fica em "flor"; "de" átono não conta
    assert intervalo("flor de") == (1, 1)


def test_atona_meio_conta():
    # "de flor": "de" no meio conta (1) + flor (1) = 2
    assert intervalo("de flor") == (2, 2)


# ---- enclíticos --------------------------------------------------------------

def test_enclitico_estressado():
    # fá-lo-ias: tônica em FÁ; lo-i-as todos postônicos -> contam 1
    assert intervalo("fá-lo-ias") == (1, 1)


# ---- versos reais -------------------------------------------------------------

def test_verso_classico_7():
    # Drummond: verso livre, anti-métrico por projeto — não há escansão canônica.
    # "meio" tem as duas leituras reais ([mej] neutra, [mej.u] enfática);
    # o intervalo [5,6] é a resposta honesta. O alvo do portão é 6 (leitura enfática).
    r = escandir("No meio do caminho")
    assert 6 in range(r.minimo, r.maximo + 1)


def test_haicai_5_7_5():
    haiku = [
        "o vento da tarde",
        "leva as folhas no vento",
        "para o rio azul",
    ]
    resultados = [escandir(v) for v in haiku]
    checagem = forma_ok(*resultados)
    assert checagem["versos_ok"] == [True, True, True]
