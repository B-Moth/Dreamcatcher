from datetime import datetime


WEEKDAYS = [
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche"
]

MONTHS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre"
]


def get_time():
    now = datetime.now()
    return now.strftime("%H:%M")


def get_date():
    now = datetime.now()

    return (
        f"{WEEKDAYS[now.weekday()]} "
        f"{now.day} "
        f"{MONTHS[now.month - 1]}"
    )
