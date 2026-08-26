import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import argparse
from dotenv import load_dotenv

from src.mailer import Mailer
from src.data_manager import SheetManager
from src.matcher import Matcher
from src.scrapers.paris_cine_info import ParisCineInfoScraper
from src.scrapers.letterboxd import LetterboxdScraper, Movie

def main():
    parser = argparse.ArgumentParser(description="Scrape une liste Letterboxd et notifie par email les correspondances.")
    parser.add_argument("--url", "-u", required=True, help="URL de la liste Letterboxd")
    parser.add_argument("--email", "-e", required=True, help="Adresse e-mail du destinataire")
    args = parser.parse_args()

    print("Getting movies from ParisCineInfo...")
    pci_scraper = ParisCineInfoScraper()
    movies_pci = pci_scraper.get_movies_from_api()

    lb_scraper = LetterboxdScraper()
    mailer = Mailer()
    matcher = Matcher(movies_pci)

    lb_list = args.url
    email = args.email

    print(f"\nProcessing {lb_list} ({email})...")

    try:
        movies_lb = lb_scraper.scrape_list(lb_list)
        print(f"{len(movies_lb)} found in {lb_list}.")

        matches = matcher.movies_matcher(movies_lb, movies_pci)
        print(f"{len(matches)} matches.")

        mailer(recipient=email, matches=matches, pci_scrapper=pci_scraper)

    except Exception as e:
        print(f"Error for {email}: {e}")

    print("End.")

if __name__ == "__main__":
    main()