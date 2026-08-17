import string
from typing import Dict, List

class Matcher:

    def __init__(self):
        pass

    def clean_title(self, title: str) -> str:
        """Clean title by removing the punctuation and lowering the case."""
        if not title:
            return ""
        title = title.lower().strip()
        title = title.translate(str.maketrans('', '', string.punctuation))
        return title

    def _prepare_index_paris_movies(self, paris_movies: Dict) -> (Dict, Dict):
        """
        Create an index for every user. The goal is to low down time complexity.
        """
        index_slugs = {}
        index_titles = {}
        
        for movie_id, p_movie in paris_movies.items():
            slug = p_movie.get("lb_slug")
            if slug:
                index_slugs[slug] = movie_id
                
            titles = [p_movie.get("en_title"), p_movie.get("og_title"), p_movie.get("french_title")]
            for t in titles:
                t_clean = self.clean_title(t)
                if t_clean:
                    if t_clean not in index_titles:
                        index_titles[t_clean] = []
                    index_titles[t_clean].append(movie_id)
                    
        return index_slugs, index_titles

    def movies_matcher(self, letterboxd_movies: List, paris_movies: Dict) -> List:
        """
        Get the movies that are in the 2 sets.

        Args:
            letterboxd_movies (list): Letterboxd movies from the user's list.
            paris_movies (dict): movies from Paris Ciné Info.
        Returns:
            matches (dict): dict of movies with an ID as key and a Movie object as value.
        """
        index_slugs, index_titles = self._prepare_index_paris_movies(paris_movies)
        matches = {}
        
        for lb_movie in letterboxd_movies:
            if lb_movie.slug in index_slugs:
                movie_id = index_slugs[lb_movie.slug]
                matches[movie_id] = lb_movie
                continue
                
            clean_title_lb = self.clean_title(lb_movie.title)
            candidats = index_titles.get(clean_title_lb, [])
            
            for movie_id in candidats:
                candidat = paris_movies[movie_id]
                if lb_movie.year and candidat.get("year"):
                    try:
                        ecart = abs(int(lb_movie.year) - int(candidat.get("year")))
                        if ecart <= 1:
                            matches[movie_id] = lb_movie
                            break
                    except ValueError:
                        pass
                else:
                    matches[movie_id] = lb_movie
                    break
                        
        return matches