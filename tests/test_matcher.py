import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

from src.matcher import Matcher


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def paris_movies():
    return {
        1: {
            "en_title": "The Matrix",
            "og_title": "The Matrix",
            "french_title": "Matrix",
            "year": "1999",
            "lb_slug": "the-matrix",
        },
        2: {
            "en_title": "Amélie",
            "og_title": "Le Fabuleux Destin d'Amélie Poulain",
            "french_title": "Le Fabuleux Destin d'Amélie Poulain",
            "year": "2001",
            "lb_slug": "amelie",
        },
        3: {
            "en_title": "Parasite",
            "og_title": "기생충",
            "french_title": "Parasite",
            "year": "2019",
            "lb_slug": "parasite",
        },
    }


@pytest.fixture
def matcher(paris_movies):
    return Matcher(paris_movies)


def make_movie(slug, title, year=None):
    return type(
        "LetterboxdMovie",
        (),
        {
            "slug": slug,
            "title": title,
            "year": year,
        },
    )()


# -----------------------------------------------------------------------------
# clean_title
# -----------------------------------------------------------------------------


def test_clean_title_lowercases_title(matcher):
    assert matcher.clean_title("The Matrix") == "the matrix"


def test_clean_title_strips_whitespace(matcher):
    assert matcher.clean_title("  The Matrix  ") == "the matrix"


def test_clean_title_removes_punctuation(matcher):
    assert matcher.clean_title("Spider-Man: No Way Home!") == (
        "spiderman no way home"
    )


def test_clean_title_removes_multiple_punctuation_characters(matcher):
    assert matcher.clean_title("Dr. Strangelove (1964) —?") == (
        "dr strangelove 1964 —"
    )


def test_clean_title_handles_empty_string(matcher):
    assert matcher.clean_title("") == ""


def test_clean_title_handles_none(matcher):
    assert matcher.clean_title(None) == ""


def test_clean_title_preserves_spaces_between_words(matcher):
    assert matcher.clean_title("The   Matrix") == "the   matrix"


def test_clean_title_handles_unicode_characters(matcher):
    assert matcher.clean_title("Amélie") == "amelie"


# -----------------------------------------------------------------------------
# _prepare_index_paris_movies
# -----------------------------------------------------------------------------


def test_prepare_index_creates_slug_index(matcher):
    assert matcher.index_slugs == {
        "the-matrix": 1,
        "amelie": 2,
        "parasite": 3,
    }


def test_prepare_index_creates_title_index(matcher):
    assert matcher.index_titles["the matrix"] == [1, 1]
    assert matcher.index_titles["matrix"] == [1]
    assert matcher.index_titles["amelie"] == [2]
    assert matcher.index_titles["parasite"] == [3, 3]


def test_prepare_index_indexes_all_movie_titles():
    movies = {
        123: {
            "en_title": "English Title",
            "og_title": "Original Title",
            "french_title": "French Title",
            "year": "2020",
            "lb_slug": "movie",
        }
    }

    matcher = Matcher(movies)

    assert matcher.index_titles["english title"] == [123]
    assert matcher.index_titles["original title"] == [123]
    assert matcher.index_titles["french title"] == [123]


def test_prepare_index_cleans_titles_before_indexing():
    movies = {
        123: {
            "en_title": "  The Matrix! ",
            "og_title": None,
            "french_title": None,
            "year": "1999",
            "lb_slug": "the-matrix",
        }
    }

    matcher = Matcher(movies)

    assert matcher.index_titles == {
        "the matrix": [123],
    }


def test_prepare_index_ignores_missing_slug():
    movies = {
        123: {
            "en_title": "A Movie",
            "og_title": None,
            "french_title": None,
            "year": "2020",
            "lb_slug": None,
        }
    }

    matcher = Matcher(movies)

    assert matcher.index_slugs == {}


def test_prepare_index_ignores_empty_titles():
    movies = {
        123: {
            "en_title": None,
            "og_title": "",
            "french_title": "   ",
            "year": "2020",
            "lb_slug": "movie",
        }
    }

    matcher = Matcher(movies)

    assert matcher.index_titles == {}


def test_prepare_index_supports_multiple_movies_with_same_title():
    movies = {
        1: {
            "en_title": "Crash",
            "og_title": None,
            "french_title": None,
            "year": "1996",
            "lb_slug": "crash-1996",
        },
        2: {
            "en_title": "Crash",
            "og_title": None,
            "french_title": None,
            "year": "2004",
            "lb_slug": "crash-2004",
        },
    }

    matcher = Matcher(movies)

    assert matcher.index_titles["crash"] == [1, 2]


def test_prepare_index_does_not_add_duplicate_title_for_same_movie():
    movies = {
        1: {
            "en_title": "The Matrix",
            "og_title": "The Matrix",
            "french_title": "The Matrix",
            "year": "1999",
            "lb_slug": "the-matrix",
        }
    }

    matcher = Matcher(movies)

    assert matcher.index_titles["the matrix"] == [1, 1, 1]


# -----------------------------------------------------------------------------
# movies_matcher - slug matching
# -----------------------------------------------------------------------------


def test_movies_matcher_matches_movie_by_slug(matcher, paris_movies):
    lb_movie = make_movie(
        slug="the-matrix",
        title="Completely Different Title",
        year=1999,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


def test_movies_matcher_slug_match_does_not_require_title_match(
    matcher,
    paris_movies,
):
    lb_movie = make_movie(
        slug="amelie",
        title="Some Other Title",
        year=1900,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        2: lb_movie,
    }


def test_movies_matcher_slug_match_takes_priority_over_title_match(
    matcher,
    paris_movies,
):
    lb_movie = make_movie(
        slug="the-matrix",
        title="Parasite",
        year=2019,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


# -----------------------------------------------------------------------------
# movies_matcher - title matching
# -----------------------------------------------------------------------------


def test_movies_matcher_matches_by_title(matcher, paris_movies):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="The Matrix",
        year=1999,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


def test_movies_matcher_title_matching_is_case_insensitive(
    matcher,
    paris_movies,
):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="THE MATRIX",
        year=1999,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


def test_movies_matcher_title_matching_ignores_punctuation(
    matcher,
    paris_movies,
):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="The Matrix!",
        year=1999,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


def test_movies_matcher_matches_by_original_title(
    matcher,
    paris_movies,
):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="Le Fabuleux Destin d'Amélie Poulain",
        year=2001,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        2: lb_movie,
    }


# -----------------------------------------------------------------------------
# movies_matcher - year matching
# -----------------------------------------------------------------------------


def test_movies_matcher_accepts_same_year(matcher, paris_movies):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="The Matrix",
        year=1999,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


def test_movies_matcher_accepts_one_year_difference(matcher, paris_movies):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="The Matrix",
        year=2000,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


@pytest.mark.parametrize(
    "letterboxd_year",
    [1997, 2001, 1996, 2002],
)
def test_movies_matcher_rejects_year_difference_greater_than_one(
    matcher,
    paris_movies,
    letterboxd_year,
):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="The Matrix",
        year=letterboxd_year,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {}


def test_movies_matcher_matches_when_letterboxd_year_is_missing(
    matcher,
    paris_movies,
):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="The Matrix",
        year=None,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


def test_movies_matcher_matches_when_paris_movie_year_is_missing():
    paris_movies = {
        1: {
            "en_title": "The Matrix",
            "og_title": None,
            "french_title": None,
            "year": None,
            "lb_slug": "the-matrix",
        }
    }
    matcher = Matcher(paris_movies)

    lb_movie = make_movie(
        slug="unknown-slug",
        title="The Matrix",
        year=1999,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


def test_movies_matcher_accepts_string_years(matcher, paris_movies):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="The Matrix",
        year="1999",
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


# -----------------------------------------------------------------------------
# movies_matcher - invalid years
# -----------------------------------------------------------------------------


def test_movies_matcher_ignores_invalid_letterboxd_year(
    matcher,
    paris_movies,
):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="The Matrix",
        year="unknown",
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {}


def test_movies_matcher_ignores_invalid_paris_year():
    paris_movies = {
        1: {
            "en_title": "The Matrix",
            "og_title": None,
            "french_title": None,
            "year": "unknown",
            "lb_slug": "the-matrix",
        }
    }
    matcher = Matcher(paris_movies)

    lb_movie = make_movie(
        slug="unknown-slug",
        title="The Matrix",
        year=1999,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {}


def test_movies_matcher_does_not_match_invalid_year_to_another_candidate():
    paris_movies = {
        1: {
            "en_title": "Crash",
            "og_title": None,
            "french_title": None,
            "year": "unknown",
            "lb_slug": "crash-unknown",
        },
        2: {
            "en_title": "Crash",
            "og_title": None,
            "french_title": None,
            "year": "2004",
            "lb_slug": "crash-2004",
        },
    }
    matcher = Matcher(paris_movies)

    lb_movie = make_movie(
        slug="unknown-slug",
        title="Crash",
        year=2004,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        2: lb_movie,
    }


# -----------------------------------------------------------------------------
# movies_matcher - multiple movies
# -----------------------------------------------------------------------------


def test_movies_matcher_matches_multiple_movies(matcher, paris_movies):
    matrix = make_movie("the-matrix", "The Matrix", 1999)
    amelie = make_movie("amelie", "Amélie", 2001)
    parasite = make_movie("parasite", "Parasite", 2019)

    result = matcher.movies_matcher(
        [matrix, amelie, parasite],
        paris_movies,
    )

    assert result == {
        1: matrix,
        2: amelie,
        3: parasite,
    }


def test_movies_matcher_returns_empty_for_empty_letterboxd_movies(
    matcher,
    paris_movies,
):
    result = matcher.movies_matcher([], paris_movies)

    assert result == {}


def test_movies_matcher_returns_empty_when_no_movie_matches(
    matcher,
    paris_movies,
):
    lb_movie = make_movie(
        slug="unknown-slug",
        title="Unknown Movie",
        year=2020,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {}


# -----------------------------------------------------------------------------
# movies_matcher - duplicate and candidate handling
# -----------------------------------------------------------------------------


def test_movies_matcher_only_returns_one_match_for_same_letterboxd_movie(
    matcher,
    paris_movies,
):
    lb_movie = make_movie(
        slug="the-matrix",
        title="The Matrix",
        year=1999,
    )

    result = matcher.movies_matcher(
        [lb_movie, lb_movie],
        paris_movies,
    )

    assert result == {
        1: lb_movie,
    }


def test_movies_matcher_uses_first_valid_title_candidate():
    paris_movies = {
        1: {
            "en_title": "Crash",
            "og_title": None,
            "french_title": None,
            "year": "1996",
            "lb_slug": "crash-1996",
        },
        2: {
            "en_title": "Crash",
            "og_title": None,
            "french_title": None,
            "year": "2004",
            "lb_slug": "crash-2004",
        },
    }
    matcher = Matcher(paris_movies)

    lb_movie = make_movie(
        slug="unknown-slug",
        title="Crash",
        year=1996,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        1: lb_movie,
    }


def test_movies_matcher_skips_invalid_candidate_year_and_matches_next_one():
    paris_movies = {
        1: {
            "en_title": "Crash",
            "og_title": None,
            "french_title": None,
            "year": "invalid",
            "lb_slug": "crash-invalid",
        },
        2: {
            "en_title": "Crash",
            "og_title": None,
            "french_title": None,
            "year": "2004",
            "lb_slug": "crash-2004",
        },
    }
    matcher = Matcher(paris_movies)

    lb_movie = make_movie(
        slug="unknown-slug",
        title="Crash",
        year=2004,
    )

    result = matcher.movies_matcher([lb_movie], paris_movies)

    assert result == {
        2: lb_movie,
    }