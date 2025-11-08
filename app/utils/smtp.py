import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from app.keys import smtp_pass

SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 465
EMAIL_ADDRESS = "no-reply@devoriole.ru"
EMAIL_PASSWORD = smtp_pass


def gen_code() -> str:
    return str(random.randint(100000, 999999))


def send_ver(email: str, code: str):
    subject = f"Подтверждение email - {code}"

    body = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset='utf-8'>
        <style amp4email-boilerplate>body{{visibility:hidden}}</style>
        <style>
          body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f7;
            margin: 0;
            padding: 0;
            color: #1d1d1f;
          }}
          .background {{
            background-image: url('cid:bgimage');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            width: 100%;
            padding: 40px 0;
          }}
          .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            text-align: center;
          }}
          h1 {{
            font-size: 26px;
            color: #1d1d1f;
            margin-bottom: 20px;
          }}
          .code {{
            font-size: 32px;
            font-weight: bold;
            letter-spacing: 8px;
            background-color: #f2f2f5;
            padding: 16px;
            border-radius: 12px;
            display: inline-block;
            margin: 20px 0;
            font-family: monospace;
          }}
          p {{
            font-size: 16px;
            line-height: 1.6;
            color: #333;
          }}
          .footer {{
            margin-top: 30px;
            font-size: 13px;
            color: #888;
          }}
        </style>
      </head>
      <body>
        <div class="background">
          <div class="container">
            <h1>Подтвердите ваш email</h1>
            <p>Введите этот код на сайте, чтобы активировать аккаунт:</p>
            <div class="code">{code}</div>
            <p>Код действителен 10 минут.</p>
            <p class="footer">
              Если вы не регистрировались — проигнорируйте это письмо.<br>
              С любовью, <strong>devoriole.ru ❤️</strong>
            </p>
          </div>
        </div>
      </body>
    </html>
    """

    message = MIMEMultipart("related")
    message["From"] = EMAIL_ADDRESS
    message["To"] = email
    message["Subject"] = subject
    html_part = MIMEText(body, "html")
    message.attach(html_part)

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, email, message.as_string())
        print(f"Письмо с кодом отправлено на {email}")
    except Exception as e:
        print(f"Ошибка отправки письма: {e}")
        raise



def welcome(email: str):
    subject = "Добро пожаловать в Мобильную Систему Инвентаризации!"
    body = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset='utf-8'>
        <style amp4email-boilerplate>body{{visibility:hidden}}</style>
        <style>
          body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f5f5f7;
            margin: 0;
            padding: 0;
            color: #1d1d1f;
          }}
          .background {{
            background-image: url('cid:bgimage');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            width: 100%;
            padding: 40px 0;
          }}
          .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            text-align: center;
          }}
          h1 {{
            font-size: 26px;
            color: #1d1d1f;
            margin-bottom: 20px;
          }}
          p {{
            font-size: 16px;
            line-height: 1.6;
            color: #333;
          }}
          .footer {{
            margin-top: 30px;
            font-size: 13px;
            color: #888;
          }}
        </style>
      </head>
      <body>
        <div class="background">
          <div class="container">
            <h1>Добро пожаловать!</h1>
            <p>Вы успешно подтвердили email и теперь можете использовать <strong>Мобильную Систему Инвентаризации</strong></p>
            <p><strong>rsue.devoriole.ru</strong> — для товароведов: учёт, документы, склады.<br>
               <strong>Мобильное приложение</strong> — для проверяющих: сканирование, синхронизация, контроль.</p>
            <p>Присоединяйтесь к организации по QR-коду и добавьте свою организацию в личном кабинете.</p>
            <p class="footer">
              С любовью, команда <strong>devoriole.ru ❤️</strong><br>
              flagman-it.ru
            </p>
          </div>
        </div>
      </body>
    </html>
    """
    message = MIMEMultipart("related")
    message["From"] = EMAIL_ADDRESS
    message["To"] = email
    message["Subject"] = subject
    html_part = MIMEText(body, "html")
    message.attach(html_part)
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, email, message.as_string())
        print(f"Приветственное письмо отправлено на {email}")
    except Exception as e:
        print(f"Ошибка отправки письма: {e}")
        raise