import requests
import datetime
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

EUROPE_PRICE = 50
WORLD_PRICE = 150

ORIGINS = ["BCN", "GRO"]

# ------------------------------
# 1. Generate weekend list
# ------------------------------
def generate_weekends(start_date=None):
    weekends = []

    if start_date is None:
        today = datetime.date.today()
        days_until_friday = (4 - today.weekday()) % 7
        next_friday = today + datetime.timedelta(days=days_until_friday)
    else:
        # start_date puede ser string "YYYY-MM-DD" o datetime.date
        if isinstance(start_date, str):
            next_friday = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            next_friday = start_date

    limit = next_friday + datetime.timedelta(days=365)  # 1 año

    while next_friday < limit:
        friday = next_friday
        monday = friday + datetime.timedelta(days=3)
        weekends.append((friday, monday))

        # Siguiente fin de semana cada 14 días
        next_friday = friday + datetime.timedelta(days=14)

    return weekends

# ------------------------------
# 2. Check region
# ------------------------------
def is_europe_or_morocco(country_code):
    if country_code == "MA":
        return True
    try:
        r = requests.get(f"https://restcountries.com/v3.1/alpha/{country_code}").json()
        return r[0]["region"] == "Europe"
    except:
        return False

# ------------------------------
# 3. Search Kiwi API
# ------------------------------
def search_flights(origin, dep_date, ret_date):
    url = "https://api.skypicker.com/flights"
    params = {
        "fly_from": origin,
        "fly_to": "anywhere",
        "date_from": dep_date.strftime("%d/%m/%Y"),
        "date_to": dep_date.strftime("%d/%m/%Y"),
        "return_from": ret_date.strftime("%d/%m/%Y"),
        "return_to": ret_date.strftime("%d/%m/%Y"),
        "partner": "picky",
        "curr": "EUR",
        "limit": 100,
        "sort": "price",
        "flight_type": "round"
    }
    r = requests.get(url, params=params)
    return r.json().get("data", [])

# ------------------------------
# 4. Filter flights
# ------------------------------
def filter_flights(flights):
    results = []
    for f in flights:
        duration = f.get("duration", {}).get("total", 0) / 3600
        if duration < 1:
            continue
        country_code = f.get("countryTo", {}).get("code", "")
        price_cap = EUROPE_PRICE if is_europe_or_morocco(country_code) else WORLD_PRICE
        if f["price"] <= price_cap:
            results.append(f)
    return results

# ------------------------------
# 5. Build email
# ------------------------------
def build_email(results):
    if not results:
        return "No hay ofertas hoy."
    lines = []
    for f in results:
        city = f["cityTo"]
        country = f["countryTo"]["name"]
        price = f["price"]
        link = f["deep_link"]
        duration = round(f["duration"]["total"] / 3600, 1)
        lines.append(
            f"✈️ {city}, {country}\n"
            f"Precio: {price} €\n"
            f"Duración vuelo: {duration} h\n"
            f"Link: {link}\n"
            f"------------------------\n"
        )
    return "\n".join(lines)

# ------------------------------
# 6. Send email
# ------------------------------
def send_email(text):
    sender = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_PASSWORD")
    recipient = os.environ.get("GMAIL_USER")  # mismo correo

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = "Ofertas fin de semana"

    msg.attach(MIMEText(text, "plain"))

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(sender, password)
    server.send_message(msg)
    server.quit()

# ------------------------------
# 7. Main
# ------------------------------
def main():
    start_date_env = os.environ.get("START_DATE")  # formato YYYY-MM-DD
    weekends = generate_weekends(start_date=start_date_env)

    all_results = []
    for origin in ORIGINS:
        for dep, ret in weekends:
            flights = search_flights(origin, dep, ret)
            valid = filter_flights(flights)
            all_results.extend(valid)

    email_text = build_email(all_results)
    send_email(email_text)

if __name__ == "__main__":
    main()
