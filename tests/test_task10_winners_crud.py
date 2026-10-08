import io
import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from werkzeug.security import generate_password_hash
from werkzeug.datastructures import FileStorage
from app import db
from app.models.tournament import Tournament
from app.models.winner_proof import WinnerProof
from app.models.admin import Admin


def _make_tournament(name, status, days_from_now_deadline=7):
    deadline = datetime.utcnow() + timedelta(days=days_from_now_deadline)
    t = Tournament(
        name=name,
        description=f"Description for {name}",
        entry_fee=Decimal("100.00"),
        prize_pool=Decimal("10000.00"),
        date="2026-12-25",
        time="20:00",
        map_name="Bermuda",
        max_teams=48,
        registration_deadline=deadline,
        rules="No hacks. Be on time.",
        status=status,
    )
    return t


def _make_png_bytes():
    import struct
    import zlib

    def chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\x00\x00\x00"
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _login_admin(client, email, password):
    return client.post(
        "/admin/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def test_task10_smoke_winner_crud_public_visibility(app, client):
    """
    Task 10 smoke test:
    1. Create 1 winner via db session + 1 via client POST form (with dummy 1x1 PNG)
    2. Confirm GET /winners page renders published ones
    3. Unpublish via admin toggle-publish
    4. Confirm it disappears from public pages
    """
    print("\n===== TASK 10 SMOKE TEST =====")

    # --- Setup: admin + tournaments ---
    with app.app_context():
        admin = Admin(
            email="admin@test.com",
            password_hash=generate_password_hash("admin123"),
        )
        t1 = _make_tournament("Smoke Cup #1", "COMPLETED", days_from_now_deadline=-10)
        t2 = _make_tournament("Smoke Cup #2", "OPEN", days_from_now_deadline=5)
        db.session.add_all([admin, t1, t2])
        db.session.commit()
        t1_id = t1.id
        t2_id = t2.id

    # --- Step A: Create 1 winner via DB session (published=True) ---
    print("\n[Step A] Creating winner via DB session...")
    with app.app_context():
        w_db = WinnerProof(
            tournament_id=t1_id,
            title="DB-Created Winner",
            description="Inserted directly via db.session",
            image_path="db_created.png",
            published=True,
        )
        db.session.add(w_db)
        db.session.commit()
        w_db_id = w_db.id
        print(f"  -> Created WinnerProof id={w_db_id}, title='{w_db.title}', published=True")

        # Create placeholder file on disk so the media route doesn't 404 in templates
        placeholder = Path(app.config["WINNERS_PUBLIC_DIR"]) / "db_created.png"
        placeholder.write_bytes(_make_png_bytes())
        assert placeholder.is_file(), "Placeholder DB image not written"
        print(f"  -> Placeholder image at {placeholder} exists")

    # --- Step B: Create 1 winner via client POST form (with real 1x1 PNG file) ---
    print("\n[Step B] Creating winner via admin POST form (requires login)...")
    login_resp = _login_admin(client, "admin@test.com", "admin123")
    assert login_resp.status_code in (301, 302), f"Login failed: {login_resp.status_code}"
    print("  -> Admin login OK (redirected to dashboard)")

    png_data = _make_png_bytes()
    image_file = FileStorage(
        stream=io.BytesIO(png_data),
        filename="team_alpha_champs.png",
        content_type="image/png",
    )

    form_data = {
        "title": "POST-Created Winner: Team Alpha",
        "description": "Winner from smoke test via form upload",
        "tournament_id": str(t2_id),
        "published": "on",
        "image": image_file,
    }

    create_resp = client.post(
        "/admin/winners/new",
        data=form_data,
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert create_resp.status_code in (301, 302), (
        f"Expected redirect after create, got {create_resp.status_code}. "
        f"Body snippet: {create_resp.get_data(as_text=True)[:500]}"
    )
    print(f"  -> POST /admin/winners/new -> {create_resp.status_code} (redirect to list)")

    with app.app_context():
        w_post = WinnerProof.query.filter_by(title="POST-Created Winner: Team Alpha").first()
        assert w_post is not None, "POST winner not found in DB"
        w_post_id = w_post.id
        print(f"  -> DB row found: id={w_post_id}, tournament_id={w_post.tournament_id}")
        print(f"  -> image_path={w_post.image_path}, published={w_post.published}")
        assert w_post.tournament_id == t2_id, f"tournament_id mismatch: {w_post.tournament_id} vs {t2_id}"
        assert w_post.published is True, "POST winner should be published"
        assert w_post.image_path and w_post.image_path.endswith(".png"), (
            f"image_path should be a uuid.png, got: {w_post.image_path}"
        )

        saved_image = Path(app.config["WINNERS_PUBLIC_DIR"]) / w_post.image_path
        assert saved_image.is_file(), f"Saved image not found on disk: {saved_image}"
        assert saved_image.stat().st_size > 0, "Saved image is empty"
        print(f"  -> Image saved on disk: {saved_image} ({saved_image.stat().st_size} bytes)")

    # --- Step C: Confirm GET /winners page renders published winners ---
    print("\n[Step C] Verifying public /winners page renders both published winners...")
    winners_resp = client.get("/winners")
    assert winners_resp.status_code == 200, f"GET /winners expected 200, got {winners_resp.status_code}"
    winners_html = winners_resp.get_data(as_text=True)
    assert "DB-Created Winner" in winners_html, "DB winner missing from /winners page"
    assert "POST-Created Winner: Team Alpha" in winners_html, "POST winner missing from /winners page"
    print("  -> Both published winners appear on /winners")

    # Also check home page has them (since both are published and home limits to 3)
    home_resp = client.get("/")
    assert home_resp.status_code == 200
    home_html = home_resp.get_data(as_text=True)
    assert "DB-Created Winner" in home_html, "DB winner missing from / home page"
    assert "POST-Created Winner: Team Alpha" in home_html, "POST winner missing from / home page"
    print("  -> Both published winners appear on / (home)")

    # --- Step D: Admin list page shows them with correct image URLs ---
    print("\n[Step D] Verifying admin winners list...")
    list_resp = client.get("/admin/winners")
    assert list_resp.status_code == 200, f"GET /admin/winners expected 200, got {list_resp.status_code}"
    list_html = list_resp.get_data(as_text=True)
    assert "DB-Created Winner" in list_html, "DB winner missing from admin list"
    assert "POST-Created Winner: Team Alpha" in list_html, "POST winner missing from admin list"
    # Check image URLs use the right route
    assert "/media/winners/" in list_html, "admin list should use /media/winners/<filename> URLs"
    assert "public_media.winner_image" not in list_html, "template should render URL not string literal"
    print("  -> Admin list renders both winners, uses /media/winners/ URLs")

    # Check tournament name appears for the linked one
    assert "Smoke Cup #2" in list_html, "Tournament name should appear for POST-Created winner"
    print("  -> Tournament name 'Smoke Cup #2' shown for linked winner")

    # --- Step E: Unpublish POST winner via admin toggle-publish ---
    print(f"\n[Step E] Unpublishing winner id={w_post_id} via toggle-publish...")
    toggle_resp = client.post(
        f"/admin/winners/{w_post_id}/toggle-publish",
        follow_redirects=False,
    )
    assert toggle_resp.status_code in (301, 302), (
        f"toggle-publish expected redirect, got {toggle_resp.status_code}"
    )
    with app.app_context():
        w_after = db.session.get(WinnerProof, w_post_id)
        assert w_after.published is False, f"published should be False after toggle, got {w_after.published}"
        print(f"  -> DB flag flipped: published={w_after.published}")

    # --- Step F: Confirm unpublished winner disappears from public pages ---
    print("\n[Step F] Verifying unpublished winner disappears from public pages...")
    winners_after = client.get("/winners")
    winners_after_html = winners_after.get_data(as_text=True)
    assert "DB-Created Winner" in winners_after_html, "Still-published DB winner should remain"
    assert "POST-Created Winner: Team Alpha" not in winners_after_html, (
        "Unpublished POST winner should be removed from /winners"
    )
    print("  -> /winners: DB winner still visible, POST winner hidden ✓")

    home_after = client.get("/")
    home_after_html = home_after.get_data(as_text=True)
    assert "POST-Created Winner: Team Alpha" not in home_after_html, (
        "Unpublished POST winner should be removed from /home"
    )
    print("  -> / (home): POST winner hidden ✓")

    # --- Step G: Admin edit page updates fields ---
    print("\n[Step G] Testing admin edit updates fields...")
    edit_get_resp = client.get(f"/admin/winners/{w_db_id}/edit")
    assert edit_get_resp.status_code == 200, f"GET edit page expected 200, got {edit_get_resp.status_code}"
    edit_html = edit_get_resp.get_data(as_text=True)
    assert 'value="DB-Created Winner"' in edit_html, "Edit form should pre-fill title"
    # Check tournament dropdown populated
    assert "Smoke Cup #1" in edit_html, "Tournament dropdown should have Smoke Cup #1"
    assert "Smoke Cup #2" in edit_html, "Tournament dropdown should have Smoke Cup #2"
    print("  -> GET /admin/winners/<id>/edit renders with form values + tournament dropdown")

    edit_post_resp = client.post(
        f"/admin/winners/{w_db_id}/edit",
        data={
            "title": "DB-Created Winner (EDITED)",
            "description": "Updated description",
            "tournament_id": str(t2_id),
            "published": "on",
        },
        follow_redirects=False,
    )
    assert edit_post_resp.status_code in (301, 302), (
        f"edit POST expected redirect, got {edit_post_resp.status_code}"
    )
    with app.app_context():
        w_edited = db.session.get(WinnerProof, w_db_id)
        assert w_edited.title == "DB-Created Winner (EDITED)", f"Title not updated: {w_edited.title}"
        assert w_edited.description == "Updated description"
        assert w_edited.tournament_id == t2_id
        assert w_edited.published is True
        # image_path should NOT have changed
        assert w_edited.image_path == "db_created.png", (
            f"image_path changed unexpectedly: {w_edited.image_path}"
        )
        print("  -> Fields updated, image_path unchanged (no new file uploaded)")

    # --- Step H: Delete winner via admin ---
    print(f"\n[Step H] Deleting winner id={w_db_id} via admin delete...")
    delete_resp = client.post(
        f"/admin/winners/{w_db_id}/delete",
        follow_redirects=False,
    )
    assert delete_resp.status_code in (301, 302), (
        f"delete expected redirect, got {delete_resp.status_code}"
    )
    with app.app_context():
        w_deleted = db.session.get(WinnerProof, w_db_id)
        assert w_deleted is None, "Winner not deleted from DB"
        print("  -> DB row removed")

    print("\n===== TASK 10 SMOKE TEST: ALL PASSED =====")
