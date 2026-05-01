"""Valeteck v7 backend tests — Rankings, Checklist PDF, Inventory transfer."""
import os
import pytest
import requests

BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL") or "https://installer-track-1.preview.emergentagent.com").rstrip("/")
TECH_EMAIL = "tecnico@valeteck.com"
TECH_PASSWORD = "tecnico123"


@pytest.fixture(scope="module")
def auth_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": TECH_EMAIL, "password": TECH_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# --- Rankings ---
class TestRankings:
    def test_weekly_ranking_structure(self, headers):
        r = requests.get(f"{BASE_URL}/api/rankings/weekly", headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "top_earners" in data and "top_fast" in data
        assert "me_earners_pos" in data and "me_fast_pos" in data
        assert isinstance(data["top_earners"], list) and len(data["top_earners"]) <= 5
        assert isinstance(data["top_fast"], list) and len(data["top_fast"]) <= 5

    def test_top_earners_sorted_desc(self, headers):
        r = requests.get(f"{BASE_URL}/api/rankings/weekly", headers=headers, timeout=15)
        data = r.json()
        nets = [e["total_net"] for e in data["top_earners"]]
        assert nets == sorted(nets, reverse=True), f"top_earners not desc: {nets}"

    def test_badges_gold_silver_bronze(self, headers):
        r = requests.get(f"{BASE_URL}/api/rankings/weekly", headers=headers, timeout=15)
        data = r.json()
        for arr in (data["top_earners"], data["top_fast"]):
            expected = ["gold", "silver", "bronze"]
            for i, badge in enumerate(expected):
                if i < len(arr):
                    assert arr[i]["badge"] == badge, f"pos {i} badge={arr[i]['badge']} expected {badge}"

    def test_me_position_present(self, headers):
        r = requests.get(f"{BASE_URL}/api/rankings/weekly", headers=headers, timeout=15)
        data = r.json()
        # tecnico has at least one entry → me position should resolve to 1+
        assert data["me_earners_pos"] is not None
        assert data["me_fast_pos"] is not None


# --- Checklist PDF ---
class TestChecklistPDF:
    def _get_a_checklist_id(self, headers):
        r = requests.get(f"{BASE_URL}/api/checklists", headers=headers, timeout=15)
        assert r.status_code == 200
        items = r.json()
        if not items:
            pytest.skip("no checklists for tecnico")
        return items[0]["id"]

    def test_pdf_returns_bytes_with_pdf_header(self, headers):
        cid = self._get_a_checklist_id(headers)
        r = requests.get(f"{BASE_URL}/api/checklists/{cid}/pdf", headers=headers, timeout=30)
        assert r.status_code == 200, r.text[:500]
        assert "application/pdf" in r.headers.get("content-type", "").lower()
        assert r.content[:5] == b"%PDF-", f"not a PDF, head={r.content[:20]!r}"
        assert len(r.content) > 500

    def test_pdf_404_for_unknown_id(self, headers):
        r = requests.get(f"{BASE_URL}/api/checklists/non-existent-id-xyz/pdf", headers=headers, timeout=15)
        assert r.status_code == 404

    def test_pdf_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/checklists/anyid/pdf", timeout=15)
        assert r.status_code == 401


# --- Inventory ---
class TestInventory:
    def test_inventory_me_seeded_six(self, headers):
        r = requests.get(f"{BASE_URL}/api/inventory/me", headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        items = r.json()
        assert len(items) >= 6, f"expected >=6 items, got {len(items)}"
        statuses = {it["status"] for it in items}
        # at least 1 of each requested status
        for required in ("with_tech", "in_transit_to_tech", "installed", "pending_reverse"):
            assert required in statuses, f"missing status {required} in {statuses}"

    def test_transfer_valid_status_updates_item(self, headers):
        # Pick a 'pending_reverse' item to move to in_transit_to_hq, then revert
        r = requests.get(f"{BASE_URL}/api/inventory/me", headers=headers, timeout=15)
        items = r.json()
        candidates = [i for i in items if i["status"] == "pending_reverse"]
        if not candidates:
            pytest.skip("no pending_reverse item to test transfer")
        item = candidates[0]
        item_id = item["id"]
        original_status = item["status"]
        try:
            r2 = requests.post(
                f"{BASE_URL}/api/inventory/{item_id}/transfer",
                headers=headers,
                json={"new_status": "in_transit_to_hq", "tracking_code": "TEST_BR999BR"},
                timeout=15,
            )
            assert r2.status_code == 200, r2.text
            updated = r2.json()
            assert updated["status"] == "in_transit_to_hq"
            assert updated["tracking_code"] == "TEST_BR999BR"
            assert updated["id"] == item_id
            # GET to verify persistence
            r3 = requests.get(f"{BASE_URL}/api/inventory/me", headers=headers, timeout=15)
            updated_in_list = next(i for i in r3.json() if i["id"] == item_id)
            assert updated_in_list["status"] == "in_transit_to_hq"
        finally:
            # restore
            requests.post(
                f"{BASE_URL}/api/inventory/{item_id}/transfer",
                headers=headers,
                json={"new_status": original_status, "tracking_code": ""},
                timeout=15,
            )

    def test_transfer_invalid_status_400(self, headers):
        r = requests.get(f"{BASE_URL}/api/inventory/me", headers=headers, timeout=15)
        item_id = r.json()[0]["id"]
        r2 = requests.post(
            f"{BASE_URL}/api/inventory/{item_id}/transfer",
            headers=headers,
            json={"new_status": "bogus_status"},
            timeout=15,
        )
        assert r2.status_code == 400

    def test_transfer_unknown_id_404(self, headers):
        r = requests.post(
            f"{BASE_URL}/api/inventory/non-existent-id/transfer",
            headers=headers,
            json={"new_status": "with_tech"},
            timeout=15,
        )
        assert r.status_code == 404
