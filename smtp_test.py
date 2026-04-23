print("Script start")

import smtplib

print("Module geladen")

try:
    print("Verbinding maken...")
    server = smtplib.SMTP("smtp.gmail.com", 587)
    print("Server object gemaakt")

    print("TLS starten...")
    server.starttls()
    print("TLS gestart")

    print("Inloggen...")
    server.login("empbot8@gmail.com", "mqtw sksm jqbx jann")
    print("Login OK")

except Exception as e:
    print("ERROR:", e)

print("Script klaar")

