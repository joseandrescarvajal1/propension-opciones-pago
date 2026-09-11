
from tests.conftest import filas_sinteticas


def _peticion(modelo, n=1, semilla=1):
    df = filas_sinteticas(modelo, n=n, semilla=semilla)
    return {"obligaciones": [{"ID": f"1#2#{i}", "variables": {k: (None if v != v else v) for k, v in fila.items()}} for i, fila in enumerate(df.to_dict("records"))]}


def test_health(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_version(cliente, cabecera):
    r = cliente.get("/version", headers=cabecera)
    assert r.status_code == 200
    d = r.json(); assert d["version_modelo"] == "v4" and d["n_features"] == 100 and 0 < d["umbral"] < 1


def test_predict_una(cliente, cabecera, modelo):
    r = cliente.post("/predict", json=_peticion(modelo, 1), headers=cabecera)
    assert r.status_code == 200
    d = r.json(); assert d["n"] == 1 and d["version_modelo"] == "v4"
    p = d["predicciones"][0]; assert p["ID"] == "1#2#0" and 0 <= p["prob_uno"] <= 1 and p["var_rpta_alt"] in (0, 1)


def test_predict_lote_mantiene_orden(cliente, cabecera, modelo):
    r = cliente.post("/predict", json=_peticion(modelo, 5), headers=cabecera)
    assert r.status_code == 200
    ids = [p["ID"] for p in r.json()["predicciones"]]
    assert ids == [f"1#2#{i}" for i in range(5)]


def test_predict_umbral_personalizado(cliente, cabecera, modelo):
    pet = _peticion(modelo, 6); pet["umbral"] = 0.99
    r = cliente.post("/predict", json=pet, headers=cabecera)
    assert r.status_code == 200 and r.json()["umbral"] == 0.99
    assert all(p["var_rpta_alt"] == 0 or p["prob_uno"] >= 0.99 for p in r.json()["predicciones"])


def test_predict_faltan_variables(cliente, cabecera, modelo):
    pet = _peticion(modelo, 1); pet["obligaciones"][0]["variables"].pop(modelo.features[0])
    r = cliente.post("/predict", json=pet, headers=cabecera)
    assert r.status_code == 422 and "faltan" in r.json()["detail"]


def test_predict_cuerpo_invalido(cliente, cabecera):
    r = cliente.post("/predict", json={"obligaciones": []}, headers=cabecera)
    assert r.status_code == 422


def test_sin_api_key(cliente, modelo):
    r = cliente.post("/predict", json=_peticion(modelo, 1))
    assert r.status_code == 401


def test_api_key_incorrecta(cliente, modelo):
    r = cliente.post("/predict", json=_peticion(modelo, 1), headers={"X-API-Key": "otra"})
    assert r.status_code == 401


def test_sin_api_key_configurada(cliente, modelo, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    r = cliente.post("/predict", json=_peticion(modelo, 1), headers={"X-API-Key": "x"})
    assert r.status_code == 503
    monkeypatch.setenv("API_KEY", "clave-de-prueba")


def test_limite_de_filas(cliente, cabecera, modelo, monkeypatch):
    import api.main as m
    monkeypatch.setattr(m, "MAX_FILAS", 2)
    r = cliente.post("/predict", json=_peticion(modelo, 3), headers=cabecera)
    assert r.status_code == 413


def test_explain(cliente, cabecera, modelo):
    r = cliente.post("/explain?k=3", json=_peticion(modelo, 2), headers=cabecera)
    assert r.status_code == 200
    d = r.json(); assert d["n"] == 2 and d["k"] == 3 and d["version_modelo"] == "v4"
    e = d["explicaciones"][0]; assert e["ID"] == "1#2#0" and len(e["factores"]) == 3 and e["var_rpta_alt"] in (0, 1)
    assert set(e["factores"][0]) == {"variable", "valor", "contribucion", "sentido"}


def test_explain_coincide_con_predict(cliente, cabecera, modelo):
    pet = _peticion(modelo, 3)
    p = cliente.post("/predict", json=pet, headers=cabecera).json()["predicciones"]
    e = cliente.post("/explain", json=pet, headers=cabecera).json()["explicaciones"]
    assert [round(x["prob_uno"], 5) for x in p] == [round(x["prob_uno"], 5) for x in e]


def test_explain_sin_api_key(cliente, modelo):
    assert cliente.post("/explain", json=_peticion(modelo, 1)).status_code == 401
