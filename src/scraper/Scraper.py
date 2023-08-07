from bs4 import BeautifulSoup
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime
import pandas as pd
from selenium.common.exceptions import TimeoutException


class Scraper:
    def __init__(self, main_url):
        self.main_url = main_url
        self.ignore_url = ["https://www.zeit.de/wochenende","https://verlag.zeit.de/",
                           "https://spiele.zeit.de/", "https://www.wiwo.de/",
                           "https://angebot","https://www.zeit.de/video/","https://zeitreisen.zeit.de/",
                           "https://www.zeit.de/newsletter/"]
        self.driver = self.setup_selenium_browser()
        self.first_page = True


    def setup_selenium_browser(self):
        options = webdriver.ChromeOptions()
        #options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        return driver

    def load_main_page(self):
        page = urlopen(self.main_url)
        html = page.read().decode("utf-8")
        soup_main_page = BeautifulSoup(html, "html.parser")
        return soup_main_page

    def collect_free_articles(self, soup_main_page):
        collected_urls = []
        for article in soup_main_page.find_all("article"):
            if not article.get('data-zplus') == "zplus":
                article_link = article.find('a', href=True)
                if article_link.get("data-ct-label") == "link":
                    url = article_link["href"]
                    if not any(ignored in url for ignored in self.ignore_url):
                        collected_urls.append(url)
        return collected_urls

    def load_comments_in_article(self, article_link):
        self.driver.get(article_link)
        wait = WebDriverWait(self.driver, 10)
        if self.first_page:
            accept_button_iframe = self.driver.find_element(By.ID, 'sp_message_iframe_804280')
            self.driver.switch_to.frame(accept_button_iframe)
            accept_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[title="AKZEPTIEREN UND WEITER"]')))
            accept_button.click()
        time.sleep(5)
        try:
            more_comments_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'svelte-13pupk0')))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", more_comments_button)
            self.driver.execute_script("arguments[0].click();", more_comments_button)
        except TimeoutException:
            print("no more comments button")


        initial_document_height = self.driver.execute_script("return document.body.scrollHeight")
        count_scroll = 0

        while count_scroll < 100:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_document_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_document_height == initial_document_height:
                break
            initial_document_height = new_document_height

        page_source = self.driver.page_source
        article_soup = BeautifulSoup(page_source, 'html.parser')
        return article_soup

    def load_comment_replies(self):
        reply_buttons = self.driver.find_elements(By.CSS_SELECTOR, '.comment__link[data-ct-ck4="comment_hide_answers"]')
        for button in reply_buttons:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(1)
            button.click()
            time.sleep(2)
        page_source = self.driver.page_source
        article_soup = BeautifulSoup(page_source, 'html.parser')
        return article_soup

    def extract_id_from_comment(self, comment):
        return int(comment.get("id").replace("cid-", ""))

    def extract_text_from_comment(self, comment):
        comment_body = comment.find("div", {"class": "comment__body"})
        return "\n".join([paragraph.text for paragraph in comment_body.find_all("p")])

    def extract_user_profil_link(self,comment):
        comment_header = comment.find("div", {"class": "comment__header"})
        comment_user = comment_header.find("h4", {"class": "comment__name"})
        return comment_user.find("a").get("href")

    def extract_user_name_from_comment(self, comment):
        comment_header = comment.find("div", {"class": "comment__header"})
        comment_user = comment_header.find("h4", {"class": "comment__name"})
        return comment_user.find("a").text

    def extract_creation_time_comment(self, comment):
        comment_header = comment.find("div", {"class": "comment__header"})
        return comment_header.find("time", {"class": "comment__date"}).get("datetime")

    def extract_article_category(self, article_soup):
        return article_soup.find("span", {"class": "article-heading__kicker"}).text

    def extract_article_title(self, article_soup):
        return article_soup.find("span", {"class": "article-heading__title"}).text

    def extract_article_time(self, article_soup):
        article_metadata = article_soup.find("div", {"class": "metadata"})
        return article_metadata.find("time").get("datetime")

    def extract_keywords_article(self, article_soup):
        keyword_list = article_soup.find("ul", {"class": "article-tags__list"}).find_all('li')
        return [entry.text for entry in keyword_list[:len(keyword_list)-1]]

    def collect_comments_in_article(self, article_soup):
        comments = {}
        #main  comments
        for comment in article_soup.find_all("article", {"class": "comment"}):
            comment_id = self.extract_id_from_comment(comment)
            comments[comment_id] = {}
            comments[comment_id]["text"] = self.extract_text_from_comment(comment)
            comments[comment_id]["user_profil_link"] = self.extract_user_profil_link(comment)
            comments[comment_id]["user_name"] = self.extract_user_name_from_comment(comment)
            comments[comment_id]["time"] = self.extract_creation_time_comment(comment)
            comments[comment_id]["type"] = "main"
            comments[comment_id]["root_id"] = None
            comments[comment_id]["article_category"] = self.extract_article_category(article_soup)
            comments[comment_id]["article_title"] = self.extract_article_title(article_soup)
            comments[comment_id]["article_time"] = self.extract_article_time(article_soup)
            comments[comment_id]["article_keywords"] = self.extract_keywords_article(article_soup)
        article_soup = self.load_comment_replies()
        #same for replies
        for comment_stack in article_soup.find_all("div", {"class": "comment__stack"}):
            for index, comment in enumerate(comment_stack.find_all("article", {"class": "comment"})):
                if index == 0:
                    main_comment_id = self.extract_id_from_comment(comment)
                else:
                    comments[comment_id] = {}
                    comments[comment_id]["text"] = self.extract_text_from_comment(comment)
                    comments[comment_id]["user_profil_link"] = self.extract_user_profil_link(comment)
                    comments[comment_id]["user_name"] = self.extract_user_name_from_comment(comment)
                    comments[comment_id]["time"] = self.extract_creation_time_comment(comment)
                    comments[comment_id]["type"] = "reply"
                    comments[comment_id]["root_id"] = main_comment_id
                    comments[comment_id]["article_category"] = self.extract_article_category(article_soup)
                    comments[comment_id]["article_title"] = self.extract_article_title(article_soup)
                    comments[comment_id]["article_time"] = self.extract_article_time(article_soup)
                    comments[comment_id]["article_keywords"] = self.extract_keywords_article(article_soup)
        return comments


if __name__ == "__main__":
    main_url = "https://www.zeit.de/index"
    scraper = Scraper(main_url)
    main_page_soup = scraper.load_main_page()
    url_list = scraper.collect_free_articles(main_page_soup)
    print(len(url_list))
    for url in url_list:
        article_soup = scraper.load_comments_in_article(url)
        comments = scraper.collect_comments_in_article(article_soup)
        print(comments)
        comments_df = pd.DataFrame.from_dict(comments, orient='index')
        if not comments_df.empty:
            comments_df["article_url"] = url
            timestamp = int(round(datetime.now().timestamp()))
            comments_df.to_csv(f"data/{timestamp}.csv")
        scraper.first_page = False
        time.sleep(5)

