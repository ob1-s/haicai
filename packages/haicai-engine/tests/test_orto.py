from haicai import coverage


def test_texto_vazio_zero():
    assert coverage("") == 0.0


def test_haiku_comum_alta_cobertura():
    texto = "Vento frio na rua\nFolhas secas no chão\nNoite cai sem lua"
    assert coverage(texto) > 0.8


def test_erro_ortografico_derruba():
    bom = coverage("uma exceção à regra do jogo")
    ruim = coverage("uma excessao a regra do jogo")
    assert bom >= ruim
    assert ruim < 1.0


def test_outra_lingua_derruba():
    assert coverage("the quick brown fox jumps") < 0.5
