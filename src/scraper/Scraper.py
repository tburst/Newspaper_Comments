from bs4 import BeautifulSoup
from urllib.request import urlopen

# extract info on articles on main page
# classify article as premium/open
# extract comments on open article
# save comments in postgres database

class Scraper:
    def __init__(self, main_url):
        self.main_url = main_url
        self.ignore_url = ["https://www.zeit.de/wochenende","https://verlag.zeit.de/",
                           "https://spiele.zeit.de/", "https://www.wiwo.de/",
                           "https://angebot","https://www.zeit.de/video/","https://zeitreisen.zeit.de/",
                           "https://www.zeit.de/newsletter/"]

    def load_main_page(self):
        page = urlopen(self.main_url)
        html = page.read().decode("utf-8")
        self.soup_main_page = BeautifulSoup(html, "html.parser")

    def collect_free_articles(self):
        self.load_main_page()
        collected_urls = []
        for article in self.soup_main_page.find_all("article"):
            if not article.get('data-zplus') == "zplus":
                article_link = article.find('a', href=True)
                if article_link.get("data-ct-label") == "link":
                    url = article_link["href"]
                    if not any(ignored in url for ignored in self.ignore_url):
                        collected_urls.append(url)
        return collected_urls

    def scrape(self):
        pass

    def extract(self):
        pass

    def classify(self):
        pass

    def save(self):
        pass


if __name__ == "__main__":
    main_url = "https://www.zeit.de/index"
    scraper = Scraper(main_url)
    print(scraper.collect_free_articles())