import re
import time
import requests

from dataclasses import dataclass
from typing import List, Optional
from bs4 import BeautifulSoup

@dataclass
class Movie:
    title: str
    slug: str
    letterboxd_url: str
    year: Optional[str] = None
    french_title: Optional[str] = None
    director: Optional[str] = None

class LetterboxdScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
        }

    def _is_url_valid(self, url:str) -> bool:
        """Tell if an URL is a Letterboxd list."""
        pattern = r"^https://letterboxd\.com/[A-Za-z0-9_]+/(?:list/[A-Za-z0-9_-]+/|watchlist/)(?:page/[0-9]+/)?$"
        return re.fullmatch(pattern, url) is not None

    def _get_page_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Download and parse a HTML page."""
        try:
            if self._is_url_valid(url):
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            else:
                raise ValueError(f"Provided link {url} is not a list from Letterboxd. It should follow this format: https://letterboxd.com/username/list_name/")
        except requests.RequestException as e:
            print(f"Error while accessing {url} : {e}")
            return None

    def _extract_movies_from_soup(self, soup: BeautifulSoup) -> List[Movie]:
        """Extract movies from a single page of a HTML soup."""
        movies = []
        posters = soup.find_all("div", class_="react-component")
        
        for poster in posters:
            slug = poster.get("data-item-slug")
            if not slug:
                continue
                
            img_tag = poster.find("img")
            title = img_tag.get("alt") if img_tag else slug.replace('-', ' ').title()

            year = None
            full_name = poster.get("data-item-full-display-name", "")
            if "(" in full_name and ")" in full_name:
                year = full_name.split("(")[-1].replace(")", "").strip()
            
            movies.append(
                Movie(
                    title=title,
                    slug=slug,
                    letterboxd_url=f"https://letterboxd.com/film/{slug}/",
                    year=year
                )
            )
            
        return movies

    def scrape_list(self, base_url: str) -> List[Movie]:
        """
        Scrap a whole Letterboxd list.
        
        Args:
            base_url (str): Letterboxd list URL.

        Returns:
            movies (list): the list of every movie in the Letterboxd list.
        """
        all_movies = []
        page_number = 1
        
        while True:
            page_url = f"{base_url}page/{page_number}/" if page_number > 1 else base_url
            print(f"Scraping page {page_number}...")
            
            soup = self._get_page_soup(page_url)
            if not soup:
                break

            movies_on_page = self._extract_movies_from_soup(soup)
            if not movies_on_page:
                break
                
            all_movies.extend(movies_on_page)
            
            next_button = soup.find("a", class_="next")
            if not next_button:
                break
                
            page_number += 1
            time.sleep(1) 

        return all_movies