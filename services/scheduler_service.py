from datetime import date

SEND_DAYS: set[int] = {
    6,  # Sunday  (weekday() == 6)
    2,  # Wednesday (weekday() == 2)
    4,  # Friday  (weekday() == 4)
}


def should_send_emails(reference_date: date | None = None) -> bool:
    """
    Return True if emails should be sent today.
    Emails are sent on Sundays, Wednesdays, and Fridays.

    Args:
        reference_date: Defaults to today. Pass a custom date for testing.
    """
    today = reference_date or date.today()
    return today.weekday() in SEND_DAYS


def next_send_day(reference_date: date | None = None) -> str:
    """
    Return the name of the next scheduled send day (including today if applicable).
    """
    day_names = {6: "Sunday", 2: "Wednesday", 4: "Friday"}
    today = reference_date or date.today()
    for offset in range(7):
        candidate = today.toordinal() + offset
        weekday = date.fromordinal(candidate).weekday()
        if weekday in SEND_DAYS:
            return day_names[weekday]
    return "Unknown"
