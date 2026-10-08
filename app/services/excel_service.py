from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment


def _player(players, idx, field):
    for p in players:
        if p.player_index == idx:
            return getattr(p, field, "")
    return ""


def generate_registrations_export(registrations):
    wb = Workbook()
    ws = wb.active
    ws.title = "Registrations"
    headers = [
        "Registration ID",
        "Tournament",
        "Team Name",
        "Captain Name",
        "Captain Phone",
        "Player 1 Name",
        "Player 1 UID",
        "Player 1 Level",
        "Player 2 Name",
        "Player 2 UID",
        "Player 2 Level",
        "Player 3 Name",
        "Player 3 UID",
        "Player 3 Level",
        "Player 4 Name",
        "Player 4 UID",
        "Player 4 Level",
        "Transaction ID",
        "Payment Status",
        "Registration Status",
        "Rejection Reason",
        "Registration Date",
        "Confirmation Date",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    widths = {
        "A": 18, "B": 22, "C": 20, "D": 18, "E": 16, "W": 22, "V": 22
    }
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    for r in registrations:
        tname = r.tournament.name if r.tournament else ""
        players = list(r.players) if hasattr(r, "players") else []
        row = [
            r.registration_id or "",
            tname,
            r.team_name or "",
            r.captain_name or "",
            r.captain_phone or "",
            _player(players, 1, "name"),
            _player(players, 1, "ff_uid"),
            _player(players, 1, "ff_level") or "",
            _player(players, 2, "name"),
            _player(players, 2, "ff_uid"),
            _player(players, 2, "ff_level") or "",
            _player(players, 3, "name"),
            _player(players, 3, "ff_uid"),
            _player(players, 3, "ff_level") or "",
            _player(players, 4, "name"),
            _player(players, 4, "ff_uid"),
            _player(players, 4, "ff_level") or "",
            r.payment_transaction_id or "",
            (r.payment_status or "").replace("_", " ").title(),
            (r.registration_status or "").replace("_", " ").title(),
            r.rejection_reason or "",
            r.created_at.isoformat() if r.created_at else "",
            r.confirmation_date.isoformat() if r.confirmation_date else "",
        ]
        ws.append(row)
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio
