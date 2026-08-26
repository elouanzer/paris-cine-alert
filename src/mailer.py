import os
import smtplib
from email.message import EmailMessage
from jinja2 import Environment, FileSystemLoader

from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_LOGIN = os.getenv("SMTP_LOGIN")

URL_LOGO = "https://cdn.jsdelivr.net/gh/elouanzer/paris-cine-alert@main/assets/paris_cine_alert_logo_no_background.png"

class Mailer:

    def __init__(self):
        pass

    def build_data_for_mail(self, matches: dict, pci_scraper):
        """
        Generate the data that will be used for the future email.

        Args:
            matches (dict): dict of movies with an ID as key and a Movie object as value.
            pci_scraper (src.scrapers.paris_cine_info.ParisCineInfoScraper): scraper for paris ciné info.

        Returns:
            mail_data (list): list of dict with the Movie object and a list of Screening objects.
        """
        mail_data = []
        for movie_id, lb_movie in matches.items():
            screenings = pci_scraper.get_movie_screening(movie_id)        
            mail_data.append({
                "movie_lb": lb_movie,
                "screenings": screenings
            })
        return mail_data

    def generate_email(
            self, 
            mail_data: list, 
            header_color: str,
        ) -> str:
        """
        Generate the final email based on the mail_data. The data should follow the format returned by build_data_for_mail.

        Args:
            mail_data (list): data for emails.
            background_color (str): background color (hex format) for the header.

        Returns:
            html_mail (str): mail in HTML format.
        """
        current_path = os.path.dirname(os.path.abspath(__file__))
        templates_path = os.path.join(current_path, "templates", "email")
        env = Environment(
            loader=FileSystemLoader(templates_path),
            autoescape=True
        )
        
        template = env.get_template("email_template.html")
        html_mail = template.render(
            mail_data=mail_data, 
            header_color=header_color,
            url_logo=URL_LOGO
        )
        
        return html_mail

    def send_mail(self, html_mail, recipient):
        """
        Send en email.

        Args:
            html_mail (str): content of the mail in HTML.
            recipient (str): mail recipient.
        """
        
        msg = EmailMessage()
        msg['Subject'] = "Ton programme Ciné de la semaine!"
        msg['From'] = f"Paris Ciné Alert <{EMAIL_SENDER}>"
        msg['To'] = recipient
        
        msg.set_content(html_mail, subtype='html')
        
        try:
            print("Connecting to SMTP...")
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=60) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_LOGIN, SMTP_PASSWORD)
                server.send_message(msg)
                print(f"Email sent to {recipient}.")
                
        except Exception as e:
            print(f"Error while sending mail to {recipient}: {e}")

    def __call__(self, recipient:str, matches: list, pci_scrapper):
        header_color = "#475262"

        mail_data = self.build_data_for_mail(matches, pci_scrapper)
        mail_html = self.generate_email(mail_data, header_color)
        self.send_mail(mail_html, recipient)
        return mail_html