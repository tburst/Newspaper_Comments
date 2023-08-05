from bs4 import BeautifulSoup
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time


class Scraper:
    def __init__(self, main_url):
        self.main_url = main_url
        self.ignore_url = ["https://www.zeit.de/wochenende","https://verlag.zeit.de/",
                           "https://spiele.zeit.de/", "https://www.wiwo.de/",
                           "https://angebot","https://www.zeit.de/video/","https://zeitreisen.zeit.de/",
                           "https://www.zeit.de/newsletter/"]
        self.driver = self.setup_selenium_browser()


    def setup_selenium_browser(self):
        options = webdriver.ChromeOptions()
        #options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        return driver

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

    def load_comments_in_article(self, article_link):
        self.driver.get(article_link)
        accept_button_iframe = self.driver.find_element(By.ID, 'sp_message_iframe_804280')
        self.driver.switch_to.frame(accept_button_iframe)
        wait = WebDriverWait(self.driver, 10)
        accept_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[title="AKZEPTIEREN UND WEITER"]')))
        accept_button.click()
        time.sleep(5)
        more_comments_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'svelte-13pupk0')))
        self.driver.execute_script("arguments[0].scrollIntoView(true);",more_comments_button )
        self.driver.execute_script("arguments[0].click();", more_comments_button )

        initial_document_height = self.driver.execute_script("return document.body.scrollHeight")
        count_scroll = 0

        while count_scroll < 100:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_document_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_document_height == initial_document_height:
                break
            initial_document_height = new_document_height

        reply_buttons = self.driver.find_elements(By.CSS_SELECTOR, '.comment__link[data-ct-ck4="comment_hide_answers"]')
        for button in reply_buttons:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(1)
            button.click()
            time.sleep(2)

        page_source = self.driver.page_source
        article_soup = BeautifulSoup(page_source, 'html.parser')
        return article_soup


    def extract(self):
        pass

    def classify(self):
        pass

    def save(self):
        pass


if __name__ == "__main__":
    main_url = "https://www.zeit.de/index"
    scraper = Scraper(main_url)
    print(scraper.load_comments_in_article('https://www.zeit.de/gesellschaft/zeitgeschehen/2023-08/bundeswehr-reservisten-ungediente-ausbildung').prettify())