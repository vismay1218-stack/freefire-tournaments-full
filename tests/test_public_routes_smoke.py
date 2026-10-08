from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app import db
from app.models.tournament import Tournament
from app.models.winner_proof import WinnerProof


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_tournament(name, status, days_from_now_deadline=7):
    deadline = _utcnow() + timedelta(days=days_from_now_deadline)
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


def test_home_page_has_tournaments_and_winners(app, client):
    with app.app_context():
        t1 = _make_tournament("Open Cup #1", "OPEN", days_from_now_deadline=7)
        t2 = _make_tournament("Draft Cup", "DRAFT", days_from_now_deadline=14)
        t3 = _make_tournament("Closed Cup", "CLOSED", days_from_now_deadline=-1)
        t4 = _make_tournament("Completed Cup", "COMPLETED", days_from_now_deadline=-30)
        t5 = _make_tournament("Open Cup #2", "OPEN", days_from_now_deadline=5)
        t6 = _make_tournament("Open Cup #3", "OPEN", days_from_now_deadline=3)

        db.session.add_all([t1, t2, t3, t4, t5, t6])
        db.session.flush()

        w1 = WinnerProof(
            tournament_id=t4.id,
            title="Champions of Fall Cup",
            description="Team Alpha takes the crown!",
            image_path="fall_champs.jpg",
            published=True,
        )
        w2 = WinnerProof(
            tournament_id=None,
            title="Unpublished - Should not show",
            description="Draft proof",
            image_path="draft.jpg",
            published=False,
        )
        w3 = WinnerProof(
            tournament_id=None,
            title="Squad Showdown Winners",
            description="Team Bravo dominates.",
            image_path="squad.jpg",
            published=True,
        )
        w4 = WinnerProof(
            tournament_id=None,
            title="Weekly Scrimmage #3",
            description="Charlie wins close match.",
            image_path="scrim3.jpg",
            published=True,
        )
        w5 = WinnerProof(
            tournament_id=None,
            title="Home Latest Winner",
            description="Most recent, should be 1st on home.",
            image_path="latest.jpg",
            published=True,
        )

        db.session.add_all([w1, w2, w3, w4, w5])
        db.session.commit()

    resp = client.get("/")
    assert resp.status_code == 200, f"Home page expected 200, got {resp.status_code}"
    html = resp.get_data(as_text=True)
    assert "Upcoming Tournaments" in html, "Home page missing tournaments section"
    assert "Open Cup #1" in html
    assert "Open Cup #2" in html
    assert "Open Cup #3" in html
    assert "Draft Cup" in html
    assert "Closed Cup" in html
    assert "Completed Cup" in html
    pos_open1 = html.index("Open Cup #1")
    pos_draft = html.index("Draft Cup")
    pos_closed = html.index("Closed Cup")
    pos_completed = html.index("Completed Cup")
    assert pos_open1 < pos_draft < pos_closed < pos_completed, (
        "Home tourneys not sorted OPEN -> DRAFT -> CLOSED -> COMPLETED"
    )
    assert "Unpublished" not in html, "Home page shows unpublished winner"
    assert "Home Latest Winner" in html
    assert "Weekly Scrimmage #3" in html
    assert "Squad Showdown Winners" in html
    assert "Champions of Fall Cup" not in html, "Home page shows more than 3 winners (w1 oldest excluded)"
    print("SMOKE [GET /] -> 200: 6 tourneys (OPEN first, then DRAFT/CLOSED/COMPLETED), 3 newest published winners")


def test_tournaments_page_sorts_by_status(app, client):
    with app.app_context():
        closed = _make_tournament("Z-Closed", "CLOSED", days_from_now_deadline=-1)
        completed = _make_tournament("Y-Completed", "COMPLETED", days_from_now_deadline=-60)
        draft = _make_tournament("X-Draft", "DRAFT", days_from_now_deadline=20)
        open_t = _make_tournament("A-Open", "OPEN", days_from_now_deadline=5)
        db.session.add_all([closed, completed, draft, open_t])
        db.session.commit()

    resp = client.get("/tournaments")
    assert resp.status_code == 200, f"Tournaments page expected 200, got {resp.status_code}"
    html = resp.get_data(as_text=True)
    assert "All Tournaments" in html
    assert "A-Open" in html
    assert "X-Draft" in html
    assert "Z-Closed" in html
    assert "Y-Completed" in html

    pos_open = html.index("A-Open")
    pos_draft = html.index("X-Draft")
    pos_closed = html.index("Z-Closed")
    pos_completed = html.index("Y-Completed")
    assert pos_open < pos_draft < pos_closed < pos_completed, (
        f"Tournament sort order wrong: open@{pos_open} draft@{pos_draft} closed@{pos_closed} completed@{pos_completed}"
    )
    print("SMOKE [GET /tournaments] -> 200: correct OPEN->DRAFT->CLOSED->COMPLETED order")


def test_tournament_detail_404_and_data(app, client):
    with app.app_context():
        t = _make_tournament("Detail Cup", "OPEN", days_from_now_deadline=7)
        db.session.add(t)
        db.session.commit()
        t_id = t.id

    resp_missing = client.get(f"/tournaments/99999")
    assert resp_missing.status_code == 404, f"Missing tournament expected 404, got {resp_missing.status_code}"
    print("SMOKE [GET /tournaments/99999] -> 404 correctly")

    resp_ok = client.get(f"/tournaments/{t_id}")
    assert resp_ok.status_code == 200, f"Detail page expected 200, got {resp_ok.status_code}"
    html = resp_ok.get_data(as_text=True)
    assert "Detail Cup" in html
    assert "REGISTER NOW" in html, "Open tournament should show REGISTER NOW button"
    assert "Registration Deadline" in html
    print(f"SMOKE [GET /tournaments/{t_id}] -> 200: cup name + REGISTER NOW + deadline present")


def test_winners_page_lists_all_published(app, client):
    with app.app_context():
        t = _make_tournament("Old Cup", "COMPLETED", days_from_now_deadline=-100)
        db.session.add(t)
        db.session.flush()
        wpub1 = WinnerProof(title="Pub1", description="d1", image_path="p1.jpg", published=True, tournament_id=t.id)
        wpub2 = WinnerProof(title="Pub2", description="d2", image_path="p2.jpg", published=True)
        wpriv = WinnerProof(title="Priv", description="d3", image_path="pr.jpg", published=False)
        db.session.add_all([wpub1, wpub2, wpriv])
        db.session.commit()

    resp = client.get("/winners")
    assert resp.status_code == 200, f"Winners page expected 200, got {resp.status_code}"
    html = resp.get_data(as_text=True)
    winners_title = "Winners & Tournament Proofs"
    winners_title_esc = "Winners &amp; Tournament Proofs"
    assert winners_title in html or winners_title_esc in html, "Winners page title missing"
    assert "Pub1" in html
    assert "Pub2" in html
    assert "Priv" not in html
    print("SMOKE [GET /winners] -> 200: all published shown, unpublished hidden")


def test_status_lookup_get_and_post(app, client):
    from app.models.registration import Registration

    resp_get = client.get("/status")
    assert resp_get.status_code == 200
    html_get = resp_get.get_data(as_text=True)
    assert "Check Registration Status" in html_get
    assert 'name="registration_id"' in html_get
    assert 'name="captain_phone"' in html_get
    print("SMOKE [GET /status] -> 200: lookup form renders")

    with app.app_context():
        t = _make_tournament("Status Cup", "OPEN", days_from_now_deadline=7)
        db.session.add(t)
        db.session.flush()
        reg = Registration(
            tournament_id=t.id,
            registration_id="PV-TEST01",
            team_name="Test Team",
            captain_name="Captain Bob",
            captain_phone="9876543210",
            payment_transaction_id="TXN123",
            registration_status="CONFIRMED",
            confirmation_date=_utcnow(),
        )
        db.session.add(reg)
        db.session.commit()

    resp_bad = client.post("/status", data={
        "registration_id": "PV-WRONG",
        "captain_phone": "9876543210",
    })
    assert resp_bad.status_code == 200
    html_bad = resp_bad.get_data(as_text=True)
    assert "Registration not found" in html_bad
    print("SMOKE [POST /status wrong id] -> 200: not_found shown")

    resp_bad_phone = client.post("/status", data={
        "registration_id": "PV-TEST01",
        "captain_phone": "1111111111",
    })
    html_bad_phone = resp_bad_phone.get_data(as_text=True)
    assert "Registration not found" in html_bad_phone
    print("SMOKE [POST /status wrong phone] -> 200: not_found shown")

    resp_short_phone = client.post("/status", data={
        "registration_id": "PV-TEST01",
        "captain_phone": "12345",
    })
    html_short = resp_short_phone.get_data(as_text=True)
    assert "Registration not found" in html_short
    print("SMOKE [POST /status short/non-digit phone] -> 200: not_found shown")

    resp_case = client.post("/status", data={
        "registration_id": "  pv-test01  ",
        "captain_phone": "9876543210",
    })
    assert resp_case.status_code == 200
    html_case = resp_case.get_data(as_text=True)
    assert "Test Team" in html_case, f"Case-insensitive reg id should match. Snippet: {html_case[:500]}"
    assert "Captain Bob" in html_case
    assert "Status Cup" in html_case
    assert "Confirmed" in html_case or "CONFIRMED" in html_case
    assert "PV-TEST01" in html_case
    print("SMOKE [POST /status case-insensitive match] -> 200: team/captain/tournament/status displayed")


def test_register_start_validates_open(app, client):
    with app.app_context():
        open_t = _make_tournament("Reg Open Cup", "OPEN", days_from_now_deadline=7)
        closed_t = _make_tournament("Reg Closed Cup", "CLOSED", days_from_now_deadline=7)
        db.session.add_all([open_t, closed_t])
        db.session.commit()
        open_id = open_t.id
        closed_id = closed_t.id

    resp_missing = client.get("/tournaments/77777/register")
    assert resp_missing.status_code == 404
    print("SMOKE [GET /tournaments/77777/register] -> 404")

    resp_closed = client.get(f"/tournaments/{closed_id}/register", follow_redirects=False)
    assert resp_closed.status_code in (301, 302), (
        f"Closed tournament should redirect, got {resp_closed.status_code}"
    )
    print(f"SMOKE [GET /tournaments/{closed_id}/register] -> redirect (not open for registration)")

    resp_ok = client.get(f"/tournaments/{open_id}/register")
    assert resp_ok.status_code == 200
    html_ok = resp_ok.get_data(as_text=True)
    assert "Register Your Team" in html_ok
    assert str(open_id) in html_ok
    assert "captain_phone" in html_ok
    print(f"SMOKE [GET /tournaments/{open_id}/register] -> 200: register step1 form renders")
