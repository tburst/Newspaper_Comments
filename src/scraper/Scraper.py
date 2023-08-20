from bs4 import BeautifulSoup
from urllib.request import urlopen
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
from selenium.common.exceptions import TimeoutException
import json
from google.cloud import storage


class Scraper:
    def __init__(self, main_url):
        self.main_url = main_url
        self.ignore_url = ["https://www.zeit.de/wochenende","https://verlag.zeit.de/",
                           "https://spiele.zeit.de/", "https://www.wiwo.de/",
                           "https://angebot","https://www.zeit.de/video/","https://zeitreisen.zeit.de/",
                           "https://www.zeit.de/newsletter/","https://z2x.zeit.de"]
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
        if comment_user.find("a"):
            return comment_user.find("a").get("href")
        return ""

    def extract_user_name_from_comment(self, comment):
        comment_header = comment.find("div", {"class": "comment__header"})
        comment_user = comment_header.find("h4", {"class": "comment__name"})
        if comment_user.find("a"):
            return comment_user.find("a").text
        return ""

    def extract_creation_time_comment(self, comment):
        comment_header = comment.find("div", {"class": "comment__header"})
        return comment_header.find("time", {"class": "comment__date"}).get("datetime")

    def extract_article_category(self, article_soup):
        classes_to_try = [
            "article-heading__kicker",
            "column-heading__kicker",
            "column-header__kicker",
            "headline__supertitle",
            "article-header__kicker"]
        for class_name in classes_to_try:
            result = article_soup.find("span", {"class": class_name})
            if result:
                return result.text
        return None

    def extract_article_title(self, article_soup):
        classes_to_try = [
            "article-heading__title",
            "column-heading__title",
            "column-header__title",
            "headline__title",
            "article-header",
            "article-header__title"]
        for class_name in classes_to_try:
            result = article_soup.find("span", {"class": class_name})
            if result:
                return result.text
        return None


    def extract_article_time(self, article_soup):
        classes_to_try = [
            "metadata",
            "meta",
            "article-header__metadata"]
        for class_name in classes_to_try:
            result = article_soup.find("div", {"class": class_name})
            if result:
                return result.find("time").get("datetime")
        return None

    def extract_keywords_article(self, article_soup):
        keyword_list = article_soup.find("ul", {"class": "article-tags__list"}).find_all('li')
        return [entry.text for entry in keyword_list[:len(keyword_list)-1]]

    def collect_comments_in_article(self, article_soup):
        comments = {"article_category" : self.extract_article_category(article_soup),
                    "article_title": self.extract_article_title(article_soup),
                    "article_time": self.extract_article_time(article_soup),
                    "article_keywords": self.extract_keywords_article(article_soup),
                    "comments": {}}
        #main  comments
        for comment in article_soup.find_all("article", {"class": "comment"}):
            comment_id = self.extract_id_from_comment(comment)
            comments["comments"][comment_id] = {}
            comments["comments"][comment_id]["text"] = self.extract_text_from_comment(comment)
            comments["comments"][comment_id]["user_profil_link"] = self.extract_user_profil_link(comment)
            comments["comments"][comment_id]["user_name"] = self.extract_user_name_from_comment(comment)
            comments["comments"][comment_id]["time"] = self.extract_creation_time_comment(comment)
            comments["comments"][comment_id]["type"] = "main"
            comments["comments"][comment_id]["root_id"] = None
        article_soup = self.load_comment_replies()
        #same for replies
        for comment_stack in article_soup.find_all("div", {"class": "comment__stack"}):
            for index, comment in enumerate(comment_stack.find_all("article", {"class": "comment"})):
                if index == 0:
                    main_comment_id = self.extract_id_from_comment(comment)
                else:
                    comments["comments"][comment_id] = {}
                    comments["comments"][comment_id]["text"] = self.extract_text_from_comment(comment)
                    comments["comments"][comment_id]["user_profil_link"] = self.extract_user_profil_link(comment)
                    comments["comments"][comment_id]["user_name"] = self.extract_user_name_from_comment(comment)
                    comments["comments"][comment_id]["time"] = self.extract_creation_time_comment(comment)
                    comments["comments"][comment_id]["type"] = "reply"
                    comments["comments"][comment_id]["root_id"] = main_comment_id
        return comments


def write_to_google_cloud_storage(bucket_name, json_dict):
    storage_client = storage.Client.from_service_account_json("../../secrets/service_key.json")
    bucket = storage_client.bucket(bucket_name)
    timestamp = int(round(datetime.now().timestamp()))
    blob = bucket.blob(f"{timestamp}.json")
    blob.upload_from_string(
        data=json.dumps(json_dict),
        content_type='application/json'
        )
    result = f"{timestamp}.json" + " upload complete"
    return {'response' : result}


if __name__ == "__main__":

    main_url = "https://www.zeit.de/index"
    scraper = Scraper(main_url)
    main_page_soup = scraper.load_main_page()
    url_list = scraper.collect_free_articles(main_page_soup)
    file_object = open(f"../../Config.json", "r")
    config_settings = json.load(file_object)
    bucket_name = config_settings["bucket_name"]
    for url in url_list:
        print(url)
        article_soup = scraper.load_comments_in_article(url)
        comments = scraper.collect_comments_in_article(article_soup)
        comments["article_url"] = url
        timestamp = int(round(datetime.now().timestamp()))
        print(comments)
        #with open(f"../../data/raw_data/{timestamp}.json", "w") as outfile:
            #json.dump(comments, outfile)
        write_to_google_cloud_storage(bucket_name, comments)
        scraper.first_page = False
        time.sleep(5)

