import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import requests

from bs4 import BeautifulSoup

from src.scrapers.letterboxd import LetterboxdScraper, Movie


@pytest.fixture
def scraper():
    return LetterboxdScraper()


# ---------------------------------------------------------------------------
# Movie
# ---------------------------------------------------------------------------

def test_movie_dataclass():
    movie = Movie(
        title="The Matrix",
        slug="the-matrix",
        letterboxd_url="https://letterboxd.com/film/the-matrix/",
        year="1999",
    )

    assert movie.title == "The Matrix"
    assert movie.slug == "the-matrix"
    assert movie.letterboxd_url == "https://letterboxd.com/film/the-matrix/"
    assert movie.year == "1999"


def test_movie_year_is_optional():
    movie = Movie(
        title="The Matrix",
        slug="the-matrix",
        letterboxd_url="https://letterboxd.com/film/the-matrix/",
    )

    assert movie.year is None


# ---------------------------------------------------------------------------
# _is_url_valid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "url",
    [
        "https://letterboxd.com/user/list/my-list/",
        "https://letterboxd.com/user_name/list/my-list/",
        "https://letterboxd.com/user123/list/my_list/",
        "https://letterboxd.com/user/list/my-list/page/2/",
        "https://letterboxd.com/user_name/list/my_list-2024/page/123/",
    ],
)
def test_is_url_valid_accepts_valid_urls(scraper, url):
    assert scraper._is_url_valid(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://letterboxd.com/user/list/my-list/",
        "https://www.letterboxd.com/user/list/my-list/",
        "https://letterboxd.com/user/",
        "https://letterboxd.com/user/list/",
        "https://letterboxd.com/user/list/my-list",
        "https://letterboxd.com/user/list/my-list/page/",
        "https://letterboxd.com/user/list/my-list/page/abc/",
        "https://letterboxd.com/user/list/my-list/page/1/extra/",
        "https://example.com/user/list/my-list/",
    ],
)
def test_is_url_valid_rejects_invalid_urls(scraper, url):
    assert scraper._is_url_valid(url) is False


# ---------------------------------------------------------------------------
# _get_page_soup
# ---------------------------------------------------------------------------

def test_get_page_soup_success(scraper, mocker):
    html = "<html><body><h1>My List</h1></body></html>"

    response = mocker.Mock()
    response.text = html
    response.raise_for_status.return_value = None

    mock_get = mocker.patch(
        "src.scrapers.letterboxd.requests.get",
        return_value=response,
    )

    url = "https://letterboxd.com/user/list/my-list/"

    soup = scraper._get_page_soup(url)

    assert isinstance(soup, BeautifulSoup)
    assert soup.h1.text == "My List"

    mock_get.assert_called_once_with(
        url,
        headers=scraper.headers,
        timeout=10,
    )
    response.raise_for_status.assert_called_once()


def test_get_page_soup_rejects_invalid_url(scraper, mocker):
    mock_get = mocker.patch("src.scrapers.letterboxd.requests.get")

    url = "https://example.com/not-a-letterboxd-list/"

    with pytest.raises(ValueError, match="is not a list from Letterboxd"):
        scraper._get_page_soup(url)

    mock_get.assert_not_called()


def test_get_page_soup_returns_none_on_request_error(scraper, mocker):
    mocker.patch(
        "src.scrapers.letterboxd.requests.get",
        side_effect=requests.RequestException("Connection failed"),
    )

    url = "https://letterboxd.com/user/list/my-list/"

    result = scraper._get_page_soup(url)

    assert result is None


def test_get_page_soup_returns_none_when_raise_for_status_fails(
    scraper,
    mocker,
):
    response = mocker.Mock()
    response.raise_for_status.side_effect = requests.HTTPError("404")

    mocker.patch(
        "src.scrapers.letterboxd.requests.get",
        return_value=response,
    )

    url = "https://letterboxd.com/user/list/my-list/"

    result = scraper._get_page_soup(url)

    assert result is None


# ---------------------------------------------------------------------------
# _extract_movies_from_soup
# ---------------------------------------------------------------------------

def test_extract_movies_from_soup_with_title_and_year(scraper):
    html = """
    <html>
        <body>
            <div
                class="react-component"
                data-item-slug="the-matrix"
                data-item-full-display-name="The Matrix (1999)"
            >
                <img alt="The Matrix" />
            </div>
        </body>
    </html>
    """

    soup = BeautifulSoup(html, "html.parser")

    movies = scraper._extract_movies_from_soup(soup)

    assert movies == [
        Movie(
            title="The Matrix",
            slug="the-matrix",
            letterboxd_url="https://letterboxd.com/film/the-matrix/",
            year="1999",
        )
    ]


def test_extract_movies_from_soup_without_image_uses_slug_as_title(scraper):
    html = """
    <div
        class="react-component"
        data-item-slug="the-godfather"
        data-item-full-display-name="The Godfather (1972)"
    ></div>
    """

    soup = BeautifulSoup(html, "html.parser")

    movies = scraper._extract_movies_from_soup(soup)

    assert len(movies) == 1
    assert movies[0].title == "The Godfather"
    assert movies[0].slug == "the-godfather"
    assert movies[0].year == "1972"


def test_extract_movies_from_soup_without_year(scraper):
    html = """
    <div
        class="react-component"
        data-item-slug="unknown-movie"
    >
        <img alt="Unknown Movie" />
    </div>
    """

    soup = BeautifulSoup(html, "html.parser")

    movies = scraper._extract_movies_from_soup(soup)

    assert len(movies) == 1
    assert movies[0].title == "Unknown Movie"
    assert movies[0].year is None


def test_extract_movies_from_soup_skips_elements_without_slug(scraper):
    html = """
    <div class="react-component">
        <img alt="Movie Without Slug" />
    </div>

    <div
        class="react-component"
        data-item-slug="valid-movie"
        data-item-full-display-name="Valid Movie (2020)"
    >
        <img alt="Valid Movie" />
    </div>
    """

    soup = BeautifulSoup(html, "html.parser")

    movies = scraper._extract_movies_from_soup(soup)

    assert len(movies) == 1
    assert movies[0].slug == "valid-movie"


def test_extract_movies_from_soup_extracts_multiple_movies(scraper):
    html = """
    <div
        class="react-component"
        data-item-slug="movie-one"
        data-item-full-display-name="Movie One (2020)"
    >
        <img alt="Movie One" />
    </div>

    <div
        class="react-component"
        data-item-slug="movie-two"
        data-item-full-display-name="Movie Two (2021)"
    >
        <img alt="Movie Two" />
    </div>

    <div
        class="react-component"
        data-item-slug="movie-three"
    >
        <img alt="Movie Three" />
    </div>
    """

    soup = BeautifulSoup(html, "html.parser")

    movies = scraper._extract_movies_from_soup(soup)

    assert len(movies) == 3

    assert movies[0].title == "Movie One"
    assert movies[0].year == "2020"

    assert movies[1].title == "Movie Two"
    assert movies[1].year == "2021"

    assert movies[2].title == "Movie Three"
    assert movies[2].year is None


def test_extract_movies_from_empty_soup(scraper):
    soup = BeautifulSoup("<html><body></body></html>", "html.parser")

    movies = scraper._extract_movies_from_soup(soup)

    assert movies == []


# ---------------------------------------------------------------------------
# scrape_list
# ---------------------------------------------------------------------------

def test_scrape_list_single_page(scraper, mocker):
    first_page = BeautifulSoup(
        """
        <div
            class="react-component"
            data-item-slug="the-matrix"
            data-item-full-display-name="The Matrix (1999)"
        >
            <img alt="The Matrix" />
        </div>
        """,
        "html.parser",
    )

    mocker.patch.object(
        scraper,
        "_get_page_soup",
        return_value=first_page,
    )

    mock_extract = mocker.patch.object(
        scraper,
        "_extract_movies_from_soup",
        return_value=[
            Movie(
                title="The Matrix",
                slug="the-matrix",
                letterboxd_url="https://letterboxd.com/film/the-matrix/",
                year="1999",
            )
        ],
    )

    mock_sleep = mocker.patch("src.scrapers.letterboxd.time.sleep")

    base_url = "https://letterboxd.com/user/list/my-list/"

    movies = scraper.scrape_list(base_url)

    assert len(movies) == 1
    assert movies[0].title == "The Matrix"

    scraper._get_page_soup.assert_called_once_with(base_url)
    mock_extract.assert_called_once_with(first_page)
    mock_sleep.assert_not_called()


def test_scrape_list_multiple_pages(scraper, mocker):
    page_1 = BeautifulSoup(
        """
        <div
            class="react-component"
            data-item-slug="movie-one"
            data-item-full-display-name="Movie One (2020)"
        >
            <img alt="Movie One" />
        </div>

        <a class="next" href="/user/list/my-list/page/2/">
            Next
        </a>
        """,
        "html.parser",
    )

    page_2 = BeautifulSoup(
        """
        <div
            class="react-component"
            data-item-slug="movie-two"
            data-item-full-display-name="Movie Two (2021)"
        >
            <img alt="Movie Two" />
        </div>
        """,
        "html.parser",
    )

    mocker.patch.object(
        scraper,
        "_get_page_soup",
        side_effect=[page_1, page_2],
    )

    movies = [
        Movie(
            title="Movie One",
            slug="movie-one",
            letterboxd_url="https://letterboxd.com/film/movie-one/",
            year="2020",
        ),
        Movie(
            title="Movie Two",
            slug="movie-two",
            letterboxd_url="https://letterboxd.com/film/movie-two/",
            year="2021",
        ),
    ]

    mocker.patch.object(
        scraper,
        "_extract_movies_from_soup",
        side_effect=[[movies[0]], [movies[1]]],
    )

    mock_sleep = mocker.patch("src.scrapers.letterboxd.time.sleep")

    base_url = "https://letterboxd.com/user/list/my-list/"

    result = scraper.scrape_list(base_url)

    assert result == movies

    assert scraper._get_page_soup.call_args_list == [
        mocker.call("https://letterboxd.com/user/list/my-list/"),
        mocker.call("https://letterboxd.com/user/list/my-list/page/2/"),
    ]

    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_once_with(1)


def test_scrape_list_stops_when_page_request_fails(scraper, mocker):
    mocker.patch.object(
        scraper,
        "_get_page_soup",
        return_value=None,
    )

    mock_extract = mocker.patch.object(scraper, "_extract_movies_from_soup")

    result = scraper.scrape_list(
        "https://letterboxd.com/user/list/my-list/"
    )

    assert result == []
    mock_extract.assert_not_called()


def test_scrape_list_stops_when_page_has_no_movies(scraper, mocker):
    soup = BeautifulSoup("<html></html>", "html.parser")

    mocker.patch.object(
        scraper,
        "_get_page_soup",
        return_value=soup,
    )

    mocker.patch.object(
        scraper,
        "_extract_movies_from_soup",
        return_value=[],
    )

    mock_sleep = mocker.patch("src.scrapers.letterboxd.time.sleep")

    result = scraper.scrape_list(
        "https://letterboxd.com/user/list/my-list/"
    )

    assert result == []
    mock_sleep.assert_not_called()


def test_scrape_list_stops_when_there_is_no_next_button(scraper, mocker):
    soup = BeautifulSoup(
        """
        <div
            class="react-component"
            data-item-slug="movie-one"
            data-item-full-display-name="Movie One (2020)"
        >
            <img alt="Movie One" />
        </div>
        """,
        "html.parser",
    )

    movie = Movie(
        title="Movie One",
        slug="movie-one",
        letterboxd_url="https://letterboxd.com/film/movie-one/",
        year="2020",
    )

    mocker.patch.object(
        scraper,
        "_get_page_soup",
        return_value=soup,
    )

    mocker.patch.object(
        scraper,
        "_extract_movies_from_soup",
        return_value=[movie],
    )

    mock_sleep = mocker.patch("src.scrapers.letterboxd.time.sleep")

    result = scraper.scrape_list(
        "https://letterboxd.com/user/list/my-list/"
    )

    assert result == [movie]
    mock_sleep.assert_not_called()


def test_scrape_list_does_not_sleep_after_last_page(scraper, mocker):
    soup = BeautifulSoup(
        """
        <div
            class="react-component"
            data-item-slug="movie-one"
        >
            <img alt="Movie One" />
        </div>
        """,
        "html.parser",
    )

    mocker.patch.object(
        scraper,
        "_get_page_soup",
        return_value=soup,
    )

    mocker.patch.object(
        scraper,
        "_extract_movies_from_soup",
        return_value=[
            Movie(
                title="Movie One",
                slug="movie-one",
                letterboxd_url="https://letterboxd.com/film/movie-one/",
            )
        ],
    )

    mock_sleep = mocker.patch("src.scrapers.letterboxd.time.sleep")

    scraper.scrape_list(
        "https://letterboxd.com/user/list/my-list/"
    )

    mock_sleep.assert_not_called()