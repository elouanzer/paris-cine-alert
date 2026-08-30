import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv

from src.mailer import Mailer
from src.data_manager import SheetManager
from src.matcher import Matcher
from src.scrapers.paris_cine_info import ParisCineInfoScraper
from src.scrapers.letterboxd import LetterboxdScraper, Movie

def main():
    load_dotenv()
    print("Launching Paris Ciné Alert...")

    print("Getting movies from ParisCineInfo...")
    pci_scraper = ParisCineInfoScraper()
    movies_pci = pci_scraper.get_movies_from_api()

    print("Connecting to Google Sheet...")
    try:
        sheet_manager = SheetManager("Paris Cine Alert")
        users = sheet_manager.get_users()
        print(f"{len(users)} users found.")
    except Exception as e:
        print(f"Error while reading Google Sheet: {e}")
        return

    lb_scraper = LetterboxdScraper()
    mailer = Mailer()
    matcher = Matcher(movies_pci)

    for i, user in enumerate(users):

        email = user.get("Adresse e-mail")
        lb_list = user.get("Lien de la liste Letterboxd")
        
        if not email or not lb_list:
            print("Missing data, line ignored.")
            continue
            
        print(f"\n Processing user {i}...")
        
        try:
            movies_lb = lb_scraper.scrape_list(lb_list)
            print(f"{len(movies_lb)} found in list")
            
            matches = matcher.movies_matcher(movies_lb, movies_pci)
            print(f"{len(matches)} matches.")
            
            mailer(recipient=email, matches=matches, pci_scrapper=pci_scraper)
                
        except Exception as e:
            print(f"Error for {email}: {e}")

    print("End.")

if __name__ == "__main__":
    main()