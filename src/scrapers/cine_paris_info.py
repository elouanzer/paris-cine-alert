import requests

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Screening:
    """Movie screening."""
    movie_id: int
    theater: str
    date: str
    booking_url: Optional[str] = None
    version: Optional[str] = "VO"

class CineParisInfoScraper:

    def __init__(self):
        self.api_url_movies = "https://paris-cine.info/get_movies.php" 
        self.api_showtimes_url = "https://paris-cine.info/get_showtimes.php"#?mov_id={movie_id}"
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WatchlistNotifierBot/1.0"}

    def get_movies_from_api(self) -> Dict[int, Dict[str, str]]:
        """
        Get the PHP movie file from https://paris-cine.info/?.

        Args:

        Returns:
            movies (dict): dict of movies with an ID as key and metadata as value.
        """
        try:
            response = requests.get(self.api_url_movies, headers=self.headers)
            response.raise_for_status()
            json_data = response.json()

            movies = {}
            for item in json_data.get("data", []):
                id = item.get("id")
                movies[id] = {
                    "french_title": item.get("ti"),
                    "og_title": item.get("o_ti"),
                    "en_title": item.get("en_ti"),
                    "director": item.get("di"),
                    "year": item.get("y"),
                    "lb_slug": item.get("lb_u")
                }
                
            return movies
            
        except Exception as e:
            print(f"Error while accessing {self.api_url_movies}: {e}")
            return {}

    def get_movie_screening(self, movie_id: str) -> List[Dict]:
        """
        Get available screenings for a given movie.
        
        Args:
            movie_id (int): movie ID in the movies database.

        Returns:
            screenings (list): movie screenings with metadata.
        """
        params = {"mov_id": movie_id}
        response = requests.get(self.api_showtimes_url, params=params, headers=self.headers)

        if response.status_code != 200:
            return []
            
        data = response.json()
        showtimes = data.get("showtimes", [])
        
        screenings = []
        for st in showtimes:
            screenings.append(
                Screening(
                    movie_id=movie_id,
                    theater=st.get("title"),
                    date=st.get("start"),
                    version=st.get("type"),
                    booking_url=st.get("book")
                )
            )
        return screenings