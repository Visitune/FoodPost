from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_notification(pdf_paths: list[Path], summary_lines: list[str]):
    host = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
    port = int(os.environ.get("EMAIL_PORT", "587"))
    user = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")
    to_addr = os.environ.get("EMAIL_TO", user)

    if not user or not password:
        print("[email] EMAIL_USER / EMAIL_PASS non configurés : notification ignorée.")
        print("Résumé de ce qui aurait été envoyé :")
        for line in summary_lines:
            print(" -", line)
        return

    msg = EmailMessage()
    msg["Subject"] = f"Veille food safety — {len(pdf_paths)} post(s) LinkedIn prêt(s)"
    msg["From"] = user
    msg["To"] = to_addr
    body = "Nouveaux carrousels prêts à relire puis poster sur LinkedIn :\n\n"
    body += "\n".join(f"- {line}" for line in summary_lines)
    body += "\n\nLes PDF sont en pièce jointe (format LinkedIn document post, 1080x1350)."
    msg.set_content(body)

    for pdf_path in pdf_paths:
        with open(pdf_path, "rb") as f:
            msg.add_attachment(
                f.read(), maintype="application", subtype="pdf", filename=pdf_path.name
            )

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
    print(f"[email] notification envoyée à {to_addr}")
