"""
SP500 Session Guardian — Time-boxing tool with DST awareness
Uses America/New_York timezone to dynamically calculate killzones.
No need to manually update UTC offsets when clocks change.

NY Market Hours (local time, fixed year-round):
- Pre-market: 08:00 - 09:30 ET
- AM Killzone: 09:30 - 11:30 ET (first 2 hours = highest volume)
- Lunch: 11:30 - 14:00 ET (low volume chop)
- PM Killzone: 14:00 - 16:00 ET (end-of-day positioning)
- Regular session: 09:30 - 16:00 ET

DST impact on UTC:
- Summer (Mar-Nov): ET = UTC-4 → AM KZ = 13:30-15:30 UTC
- Winter (Nov-Mar): ET = UTC-5 → AM KZ = 14:30-16:30 UTC
"""
import json
from datetime import datetime, time
import pytz

NY_TZ = pytz.timezone("America/New_York")

# Fixed NY local times (these never change)
PREMARKET_START = time(8, 0)
AM_KZ_START = time(9, 30)
AM_KZ_END = time(11, 30)
LUNCH_START = time(11, 30)
LUNCH_END = time(14, 0)
PM_KZ_START = time(14, 0)
PM_KZ_END = time(16, 0)
REGULAR_END = time(16, 0)


def register_session_tools(mcp):

    @mcp.tool()
    async def sp500_session_guardian() -> str:
        """
        Validates if the current time is within SP500 tradeable killzones.
        Uses America/New_York timezone — automatically handles DST transitions.
        SP500 only trades during NY AM Killzone (09:30-11:30 ET) and PM Killzone (14:00-16:00 ET).
        Returns session state, active killzone, and whether trading is allowed.
        """
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
                "next_session": "Monday 09:30 ET (AM Killzone)"
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
            note = "Low volume chop zone 11:30-14:00 ET. Wait for PM Killzone. Only manage existing positions."
        elif in_premarket:
            session = "PREMARKET"
            can_trade = False
            note = "Pre-market 08:00-09:30 ET. Calculate reference levels (Asia/London H/L). No entries."
        elif in_regular:
            session = "REGULAR_SESSION"
            can_trade = False
            note = "Between killzones. Monitor only. Can manage existing positions."
        else:
            session = "OFF_HOURS"
            can_trade = False
            note = f"Market closed. Next AM Killzone: 09:30 ET ({('13:30' if is_dst else '14:30')} UTC)"

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
                "am_killzone": "09:30-11:30 ET (dynamic UTC)",
                "pm_killzone": "14:00-16:00 ET (dynamic UTC)",
                "regular_session": "09:30-16:00 ET",
                "dst_status": "EDT (UTC-4)" if is_dst else "EST (UTC-5)"
            }
        })
