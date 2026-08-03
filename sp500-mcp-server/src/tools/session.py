"""
SP500 Session Guardian — Time-boxing tool with DST awareness
Uses America/New_York timezone to dynamically calculate killzones.
No need to manually update UTC offsets when clocks change.

Killzone boundaries come from sp500_settings (am_killzone_start/end,
pm_killzone_start/end, premarket_start, regular_session_start/end) as
ET-local "HH:MM" strings — the DST conversion to UTC below is always
applied on top of them, so the DB never needs to store a UTC offset.

NY Market Hours (local time, fixed year-round, DB defaults):
- Pre-market: 08:00 - 09:30 ET
- AM Killzone: 09:30 - 11:30 ET (first 2 hours = highest volume)
- Lunch: 11:30 - 14:00 ET (low volume chop)
- PM Killzone: 14:00 - 16:00 ET (end-of-day positioning)
- Regular session: 09:30 - 16:00 ET
"""
import json
from datetime import datetime, time
import pytz
from src.clients.database import get_settings

NY_TZ = pytz.timezone("America/New_York")


def _parse_hhmm(value: str, fallback: time) -> time:
    """Parse a DB 'HH:MM' string (ET-local) into a time object."""
    try:
        h, m = str(value).split(":")
        return time(int(h), int(m))
    except (ValueError, AttributeError):
        return fallback


def register_session_tools(mcp):

    @mcp.tool()
    async def sp500_session_guardian() -> str:
        """
        Validates if the current time is within SP500 tradeable killzones.
        Uses America/New_York timezone — automatically handles DST transitions.
        Killzone windows come from sp500_settings (DB), not hardcoded values.
        Returns session state, active killzone, and whether trading is allowed.
        """
        settings = get_settings(force_refresh=True)
        PREMARKET_START = _parse_hhmm(settings.get("premarket_start"), time(8, 0))
        AM_KZ_START = _parse_hhmm(settings.get("am_killzone_start"), time(9, 30))
        AM_KZ_END = _parse_hhmm(settings.get("am_killzone_end"), time(11, 30))
        PM_KZ_START = _parse_hhmm(settings.get("pm_killzone_start"), time(14, 0))
        PM_KZ_END = _parse_hhmm(settings.get("pm_killzone_end"), time(16, 0))
        REGULAR_END = _parse_hhmm(settings.get("regular_session_end"), time(16, 0))
        LUNCH_START, LUNCH_END = AM_KZ_END, PM_KZ_START

        now_utc = datetime.now(pytz.utc)
        now_ny = now_utc.astimezone(NY_TZ)
        ny_time = now_ny.time()
        weekday = now_ny.weekday()  # 0=Monday, 6=Sunday

        # DST info for transparency
        is_dst = bool(now_ny.dst())
        utc_offset = now_ny.strftime("%z")

        # Weekend check
        if weekday >= 5:
            return json.dumps({
                "can_trade": False,
                "reason": "Weekend - market closed",
                "current_ny": now_ny.strftime("%H:%M ET"),
                "current_utc": now_utc.strftime("%H:%M UTC"),
                "day": now_ny.strftime("%A"),
                "session": "CLOSED",
                "killzone": None,
                "is_dst": is_dst,
                "utc_offset": utc_offset,
                "next_session": f"Monday {AM_KZ_START.strftime('%H:%M')} ET (AM Killzone)"
            })

        # Determine session state
        in_am_kz = AM_KZ_START <= ny_time < AM_KZ_END
        in_pm_kz = PM_KZ_START <= ny_time < PM_KZ_END
        in_lunch = LUNCH_START <= ny_time < LUNCH_END and not in_am_kz and not in_pm_kz
        in_premarket = PREMARKET_START <= ny_time < AM_KZ_START
        in_regular = AM_KZ_START <= ny_time < REGULAR_END

        if in_am_kz:
            session = "AM_KILLZONE"
            can_trade = True
            note = "Prime execution window. Post-open liquidity sweeps active. Look for PDH/PDL/London sweeps."
        elif in_pm_kz:
            session = "PM_KILLZONE"
            can_trade = True
            note = "Afternoon continuation or reversal. End-of-day positioning. Watch for MOC flows."
        elif in_lunch:
            session = "LUNCH_HOUR"
            can_trade = False
            note = f"Low volume chop zone {LUNCH_START.strftime('%H:%M')}-{LUNCH_END.strftime('%H:%M')} ET. Wait for PM Killzone. Only manage existing positions."
        elif in_premarket:
            session = "PREMARKET"
            can_trade = False
            note = f"Pre-market {PREMARKET_START.strftime('%H:%M')}-{AM_KZ_START.strftime('%H:%M')} ET. Calculate reference levels (Asia/London H/L). No entries."
        elif in_regular:
            session = "REGULAR_SESSION"
            can_trade = False
            note = "Between killzones. Monitor only. Can manage existing positions."
        else:
            session = "OFF_HOURS"
            can_trade = False
            am_kz_utc = NY_TZ.localize(datetime.combine(now_ny.date(), AM_KZ_START)).astimezone(pytz.utc)
            note = f"Market closed. Next AM Killzone: {AM_KZ_START.strftime('%H:%M')} ET ({am_kz_utc.strftime('%H:%M')} UTC)"

        return json.dumps({
            "can_trade": can_trade,
            "session": session,
            "killzone": "AM" if in_am_kz else "PM" if in_pm_kz else None,
            "current_ny": now_ny.strftime("%H:%M ET"),
            "current_utc": now_utc.strftime("%H:%M UTC"),
            "day": now_ny.strftime("%A"),
            "note": note,
            "is_dst": is_dst,
            "utc_offset": utc_offset,
            "in_premarket": in_premarket,
            "regular_session_active": in_regular,
            "time_config": {
                "am_killzone": f"{AM_KZ_START.strftime('%H:%M')}-{AM_KZ_END.strftime('%H:%M')} ET (dynamic UTC)",
                "pm_killzone": f"{PM_KZ_START.strftime('%H:%M')}-{PM_KZ_END.strftime('%H:%M')} ET (dynamic UTC)",
                "regular_session": f"{AM_KZ_START.strftime('%H:%M')}-{REGULAR_END.strftime('%H:%M')} ET",
                "dst_status": "EDT (UTC-4)" if is_dst else "EST (UTC-5)"
            }
        })
