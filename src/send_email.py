import os
import smtplib
import mimetypes
from email.message import EmailMessage

def send_email_with_attachment(to_email: str, subject: str, body: str, attachment_path: str):
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")

    if not email_user or not email_pass:
        raise RuntimeError("❌ EMAIL_USER / EMAIL_PASS not found. Restart terminal after setx.")

    msg = EmailMessage()
    msg["From"] = email_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    # attach file
    ctype, encoding = mimetypes.guess_type(attachment_path)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)

    with open(attachment_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype=maintype,
            subtype=subtype,
            filename=os.path.basename(attachment_path),
        )

    # Gmail SMTP
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)

    print(f"✅ Email sent to: {to_email}")


if __name__ == "__main__":
    # TEST: send the certificate you generated
    cert_path = os.path.join("certificates", "suryansa_certificate.png")

    # CHANGE THIS to the email where you want to receive (can be same as sender too)
    receiver = "suryansapatra200@gmail.com"

    send_email_with_attachment(
        to_email=receiver,
        subject="🎉 Face Award Certificate",
        body="Congratulations! Your face match successfully ✅\nCertificate attached.",
        attachment_path=cert_path
    )
