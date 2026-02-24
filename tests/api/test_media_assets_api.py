"""API tests for media asset upload/list/delete endpoints."""

from __future__ import annotations

import io


def test_upload_and_list_media_asset(api_client, user_token):
    upload = api_client.post(
        "/api/media-assets",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("replacement.jpg", io.BytesIO(b"fake-image"), "image/jpeg")},
        data={"name": "Brand image"},
    )
    assert upload.status_code == 201
    created = upload.json()
    assert created["name"] == "Brand image"
    assert created["media_kind"] == "photo"
    assert created["size_bytes"] == len(b"fake-image")

    listed = api_client.get(
        "/api/media-assets",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert listed.status_code == 200
    items = listed.json()
    assert any(it["id"] == created["id"] for it in items)


def test_upload_media_asset_empty_file_400(api_client, user_token):
    upload = api_client.post(
        "/api/media-assets",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("empty.bin", io.BytesIO(b""), "application/octet-stream")},
    )
    assert upload.status_code == 400
    assert "empty" in upload.json()["detail"].lower()


def test_delete_media_asset_409_when_in_use(api_client, user_token):
    upload = api_client.post(
        "/api/media-assets",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("replacement.mp4", io.BytesIO(b"fake-video"), "video/mp4")},
    )
    assert upload.status_code == 201
    asset_id = upload.json()["id"]

    create_rule = api_client.post(
        "/api/mappings/1/transforms",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "rule_type": "media",
            "replacement_media_asset_id": asset_id,
            "apply_to_media_types": "photo,video",
        },
    )
    assert create_rule.status_code == 201

    delete_resp = api_client.delete(
        f"/api/media-assets/{asset_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert delete_resp.status_code == 409
    assert "in use" in delete_resp.json()["detail"].lower()


def test_delete_media_asset_200_when_unused(api_client, user_token):
    upload = api_client.post(
        "/api/media-assets",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("voice.ogg", io.BytesIO(b"fake-audio"), "audio/ogg")},
    )
    assert upload.status_code == 201
    asset_id = upload.json()["id"]

    delete_resp = api_client.delete(
        f"/api/media-assets/{asset_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "ok"
