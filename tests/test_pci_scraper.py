import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from unittest.mock import Mock, patch

from src.scrapers.paris_cine_info import ParisCineInfoScraper, Screening


@pytest.fixture
def scraper():
    return ParisCineInfoScraper()


@pytest.fixture
def mock_response():
    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    return response


# -----------------------------------------------------------------------------
# Screening
# -----------------------------------------------------------------------------


def test_screening_defaults():
    screening = Screening(
        movie_id=123,
        theater="Le Champo",
        date="2026-08-18 20:00",
    )

    assert screening.movie_id == 123
    assert screening.theater == "Le Champo"
    assert screening.date == "Mardi 18 Août à 20h00"
    assert screening.booking_url is None
    assert screening.version == "VO"


def test_screening_accepts_optional_values():
    screening = Screening(
        movie_id=123,
        theater="MK2",
        date="2026-08-18 21:00",
        booking_url="https://example.com/book",
        version="VF",
    )

    assert screening.booking_url == "https://example.com/book"
    assert screening.version == "VF"


# -----------------------------------------------------------------------------
# get_movies_from_api - success cases
# -----------------------------------------------------------------------------


def test_get_movies_from_api_returns_movies(scraper, mock_response):
    mock_response.json.return_value = {
        "data": [
            {
                "id": 123,
                "ti": "Le Fabuleux Destin",
                "o_ti": "Amélie",
                "en_ti": "Amelie",
                "di": "Jean-Pierre Jeunet",
                "y": "2001",
                "lb_u": "amelie",
            },
            {
                "id": 456,
                "ti": "Parasite",
                "o_ti": "기생충",
                "en_ti": "Parasite",
                "di": "Bong Joon-ho",
                "y": "2019",
                "lb_u": "parasite",
            },
        ]
    }

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ) as mock_get:
        result = scraper.get_movies_from_api()

    assert result == {
        123: {
            "french_title": "Le Fabuleux Destin",
            "og_title": "Amélie",
            "en_title": "Amelie",
            "director": "Jean-Pierre Jeunet",
            "year": "2001",
            "lb_slug": "amelie",
        },
        456: {
            "french_title": "Parasite",
            "og_title": "기생충",
            "en_title": "Parasite",
            "director": "Bong Joon-ho",
            "year": "2019",
            "lb_slug": "parasite",
        },
    }

    mock_get.assert_called_once_with(
        scraper.api_url_movies,
        headers=scraper.headers,
    )
    mock_response.raise_for_status.assert_called_once()


def test_get_movies_from_api_empty_data_returns_empty_dict(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {"data": []}

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movies_from_api()

    assert result == {}


def test_get_movies_from_api_missing_data_returns_empty_dict(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {}

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movies_from_api()

    assert result == {}


def test_get_movies_from_api_missing_movie_fields_are_none(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {
        "data": [
            {
                "id": 123,
                "ti": "Only a title",
            }
        ]
    }

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movies_from_api()

    assert result[123] == {
        "french_title": "Only a title",
        "og_title": None,
        "en_title": None,
        "director": None,
        "year": None,
        "lb_slug": None,
    }


def test_get_movies_from_api_duplicate_ids_use_last_entry(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {
        "data": [
            {"id": 123, "ti": "First"},
            {"id": 123, "ti": "Second"},
        ]
    }

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movies_from_api()

    assert result[123]["french_title"] == "Second"
    assert len(result) == 1


# -----------------------------------------------------------------------------
# get_movies_from_api - error cases
# -----------------------------------------------------------------------------


def test_get_movies_from_api_request_exception_returns_empty_dict(scraper):
    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        side_effect=Exception("connection failed"),
    ):
        result = scraper.get_movies_from_api()

    assert result == {}


def test_get_movies_from_api_http_error_returns_empty_dict(
    scraper,
    mock_response,
):
    mock_response.raise_for_status.side_effect = Exception(
        "500 Server Error"
    )

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movies_from_api()

    assert result == {}


def test_get_movies_from_api_invalid_json_returns_empty_dict(
    scraper,
    mock_response,
):
    mock_response.json.side_effect = ValueError("invalid JSON")

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movies_from_api()

    assert result == {}


# -----------------------------------------------------------------------------
# get_movies_from_api - request
# -----------------------------------------------------------------------------


def test_get_movies_from_api_uses_configured_headers(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {"data": []}

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ) as mock_get:
        scraper.get_movies_from_api()

    _, kwargs = mock_get.call_args

    assert kwargs["headers"] == scraper.headers


# -----------------------------------------------------------------------------
# get_movie_screening - success cases
# -----------------------------------------------------------------------------


def test_get_movie_screening_returns_screenings(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {
        "showtimes": [
            {
                "title": "Le Champo",
                "start": "2026-08-18 20:00",
                "type": "VO",
                "book": "https://example.com/book/123",
            },
            {
                "title": "MK2 Bastille",
                "start": "2026-08-18 21:30",
                "type": "VF",
                "book": None,
            },
        ]
    }

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ) as mock_get:
        result = scraper.get_movie_screening("123")

    assert result == [
        Screening(
            movie_id="123",
            theater="Le Champo",
            date="2026-08-18 20:00",
            version="VO",
            booking_url="https://example.com/book/123",
        ),
        Screening(
            movie_id="123",
            theater="MK2 Bastille",
            date="2026-08-18 21:30",
            version="VF",
            booking_url=None,
        ),
    ]

    mock_get.assert_called_once_with(
        scraper.api_showtimes_url,
        params={"mov_id": "123"},
        headers=scraper.headers,
    )


def test_get_movie_screening_empty_showtimes_returns_empty_list(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {"showtimes": []}

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movie_screening("123")

    assert result == []


def test_get_movie_screening_missing_showtimes_returns_empty_list(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {}

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movie_screening("123")

    assert result == []


def test_get_movie_screening_missing_fields_become_none(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {
        "showtimes": [
            {
                "title": "Le Champo",
            }
        ]
    }

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movie_screening("123")

    assert result == [
        Screening(
            movie_id="123",
            theater="Le Champo",
            date=None,
            version=None,
            booking_url=None,
        )
    ]


def test_get_movie_screening_preserves_movie_id(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {
        "showtimes": [
            {
                "title": "UGC Les Halles",
                "start": "2026-08-18 19:00",
                "type": "VO",
                "book": "https://example.com",
            }
        ]
    }

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movie_screening(987)

    assert len(result) == 1
    assert result[0].movie_id == 987


def test_get_movie_screening_preserves_screening_order(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {
        "showtimes": [
            {
                "title": "Theater A",
                "start": "18:00",
                "type": "VO",
            },
            {
                "title": "Theater B",
                "start": "19:00",
                "type": "VF",
            },
            {
                "title": "Theater C",
                "start": "20:00",
                "type": "VO",
            },
        ]
    }

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ):
        result = scraper.get_movie_screening("123")

    assert [screening.theater for screening in result] == [
        "Theater A",
        "Theater B",
        "Theater C",
    ]


# -----------------------------------------------------------------------------
# get_movie_screening - error cases
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status_code",
    [400, 401, 403, 404, 429, 500, 502, 503],
)
def test_get_movie_screening_non_200_returns_empty_list(
    scraper,
    mock_response,
    status_code,
):
    mock_response.status_code = status_code

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ) as mock_get:
        result = scraper.get_movie_screening("123")

    assert result == []

    mock_get.assert_called_once_with(
        scraper.api_showtimes_url,
        params={"mov_id": "123"},
        headers=scraper.headers,
    )


# -----------------------------------------------------------------------------
# get_movie_screening - request
# -----------------------------------------------------------------------------


def test_get_movie_screening_uses_movie_id_as_parameter(
    scraper,
    mock_response,
):
    mock_response.json.return_value = {"showtimes": []}

    with patch(
        "src.scrapers.paris_cine_info.requests.get",
        return_value=mock_response,
    ) as mock_get:
        scraper.get_movie_screening("456")

    mock_get.assert_called_once_with(
        scraper.api_showtimes_url,
        params={"mov_id": "456"},
        headers=scraper.headers,
    )