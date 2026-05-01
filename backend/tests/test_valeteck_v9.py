# Valeteck v9 — OCR de placa (Gemini), adapter Rastremix, webhook IN parceiros, e regressão
import base64
import io
import os
import pytest
import requests

BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL") or "").rstrip("/")
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL must be set"

TECH = {"email": "tecnico@valeteck.com", "password": "tecnico123"}
PARTNER_SECRET = os.environ.get("PARTNER_WEBHOOK_SECRET", "valeteck-partner-dev-secret")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=TECH, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture
def auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _make_plate_image(text: str = "BRA2E19") -> str:
    """Cria JPEG base64 de 600x200 com a placa escrita — textura suficiente para Gemini Vision."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (640, 220), (240, 240, 240))
    d = ImageDraw.Draw(img)
    # fundo placa Mercosul
    d.rectangle([30, 30, 610, 190], fill=(255, 255, 255), outline=(0, 0, 0), width=6)
    d.rectangle([30, 30, 610, 70], fill=(0, 70, 160))  # faixa azul superior
    d.text((250, 40), "BRASIL", fill=(255, 255, 255))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
    except Exception:
        font = ImageFont.load_default()
    d.text((80, 80), text, fill=(0, 0, 0), font=font)
    # Um pouco de "ruído"/sombra para não ser uniforme
    d.line([(30, 190), (610, 190)], fill=(80, 80, 80), width=3)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _make_blank_image() -> str:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (400, 300), (200, 200, 200))
    d = ImageDraw.Draw(img)
    # add some texture but NO plate text
    for i in range(0, 400, 40):
        d.line([(i, 0), (i, 300)], fill=(180, 180, 180), width=1)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode()


# ---------------- OCR /api/ocr/plate ----------------
class TestOcrPlate:
    def test_unauthorized(self):
        r = requests.post(f"{BASE_URL}/api/ocr/plate", json={"base64": "x"}, timeout=10)
        assert r.status_code == 401

    def test_empty_base64_returns_400(self, auth):
        r = requests.post(f"{BASE_URL}/api/ocr/plate", headers=auth, json={"base64": ""}, timeout=15)
        assert r.status_code == 400

    def test_detect_mercosul_plate(self, auth):
        b64 = _make_plate_image("BRA2E19")
        r = requests.post(f"{BASE_URL}/api/ocr/plate", headers=auth, json={"base64": b64}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "plate" in data and "confidence" in data and "detected" in data
        # Accept any valid Mercosul plate detection; main agent reported BRA2E19 @ 1.0
        if data["detected"]:
            assert data["plate"] == "BRA2E19", f"expected BRA2E19, got {data}"
            assert data["confidence"] >= 0.5
        else:
            pytest.fail(f"plate not detected; raw={data.get('raw','')[:200]}")

    def test_no_plate_image(self, auth):
        b64 = _make_blank_image()
        r = requests.post(f"{BASE_URL}/api/ocr/plate", headers=auth, json={"base64": b64}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        # Should not detect OR very low confidence
        assert data["detected"] is False or data["plate"] is None


# ---------------- Device test adapter ----------------
class TestDeviceTestAdapter:
    def test_mock_source_when_imei_not_linked(self, auth):
        # IMEI aleatório não presente em nenhum checklist → fallback mock
        r = requests.post(f"{BASE_URL}/api/device/test", headers=auth,
                          json={"imei": "999888777666555"}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("source") == "mock"

    def test_partner_rastremix_source(self, auth):
        # Cria checklist vinculando IMEI à empresa Rastremix
        imei = "771122334455667"
        payload = {
            "vehicle_type": "carro", "nome": "TEST_v9", "sobrenome": "Src",
            "placa": "ABC1D23", "empresa": "Rastremix", "equipamento": "Rastreador GPS XT-2000",
            "tipo_atendimento": "Instalação", "imei": imei,
            "photos": [], "problems_client": [], "problems_technician": [],
            "acessorios": [], "status": "rascunho",
        }
        c = requests.post(f"{BASE_URL}/api/checklists", headers=auth, json=payload, timeout=15)
        assert c.status_code in (200, 201), c.text
        cid = c.json()["id"]
        try:
            r = requests.post(f"{BASE_URL}/api/device/test", headers=auth,
                              json={"imei": imei}, timeout=20)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data.get("source") == "partner:rastremix", f"got {data}"
            assert "online" in data and "latency_ms" in data
        finally:
            requests.delete(f"{BASE_URL}/api/checklists/{cid}", headers=auth, timeout=10)


# ---------------- Webhook IN parceiros ----------------
class TestPartnerWebhook:
    URL = f"{BASE_URL}/api/partners/webhook/appointments"

    def _payload(self, **over):
        base = {
            "partner": "rastremix",
            "user_email": TECH["email"],
            "numero_os": "TEST_OS_V9_0001",
            "cliente_nome": "TEST_Joao",
            "cliente_sobrenome": "Webhook",
            "placa": "BRA2E19",
            "endereco": "Av. Teste 123, São Paulo/SP",
            "scheduled_at": "2026-02-15T10:00:00+00:00",
            "telefone": "(11) 90000-0000",
            "vehicle_type": "carro",
            "prioridade": "normal",
            "tempo_estimado_min": 60,
            "secret": PARTNER_SECRET,
        }
        base.update(over)
        return base

    def test_invalid_secret(self):
        r = requests.post(self.URL, json=self._payload(secret="wrong"), timeout=10)
        assert r.status_code == 401

    def test_unknown_partner(self):
        r = requests.post(self.URL, json=self._payload(partner="unknownxyz"), timeout=10)
        assert r.status_code == 400

    def test_valid_creates_appointment(self, auth):
        p = self._payload(numero_os="TEST_OS_V9_VALID")
        r = requests.post(self.URL, json=p, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert "appointment_id" in data
        assert data.get("empresa") == "Rastremix"
        aid = data["appointment_id"]
        # Técnico deve ver a OS via GET /appointments
        lst = requests.get(f"{BASE_URL}/api/appointments", headers=auth, timeout=15)
        assert lst.status_code == 200
        found = [a for a in lst.json() if a.get("id") == aid]
        assert found, "appointment not visible to tech"
        assert found[0]["empresa"] == "Rastremix"
        assert found[0]["numero_os"] == "TEST_OS_V9_VALID"


# ---------------- Regression ----------------
class TestRegression:
    def test_login_and_me(self, auth):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth, timeout=10)
        assert r.status_code == 200
        assert r.json().get("email") == TECH["email"]

    def test_appointments_list(self, auth):
        r = requests.get(f"{BASE_URL}/api/appointments", headers=auth, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_inventory_list(self, auth):
        r = requests.get(f"{BASE_URL}/api/inventory/me", headers=auth, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_earnings(self, auth):
        r = requests.get(f"{BASE_URL}/api/earnings/me?period=month", headers=auth, timeout=10)
        assert r.status_code == 200
        assert "total_net" in r.json()

    def test_checklist_create_rascunho(self, auth):
        payload = {
            "vehicle_type": "carro", "nome": "TEST_v9", "sobrenome": "Reg",
            "placa": "ABC1D23", "empresa": "Rastremix", "equipamento": "Rastreador GPS XT-2000",
            "tipo_atendimento": "Instalação", "photos": [],
            "problems_client": [], "problems_technician": [],
            "acessorios": [], "status": "rascunho",
        }
        c = requests.post(f"{BASE_URL}/api/checklists", headers=auth, json=payload, timeout=15)
        assert c.status_code in (200, 201), c.text
        cid = c.json()["id"]
        requests.delete(f"{BASE_URL}/api/checklists/{cid}", headers=auth, timeout=10)
