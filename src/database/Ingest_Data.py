import psycopg2
import json
import os
from datetime import datetime

#load sql database settings
settings_file = open("sql_settings.json")
settings_dict = json.load(settings_file)


def get_connection(settings_dict):
    return psycopg2.connect(**settings_dict)

def extract_user_id(profil_link):
    return profil_link.split("/")[-1]

def add_user(user_id, name, profile_link, settings_dict):
    with get_connection(settings_dict) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO comment_schema.users (user_id, name, profil_link)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING;
            """, (user_id, name, profile_link))

def add_article(created, article_link, settings_dict):
    with get_connection(settings_dict) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO comment_schema.articles (created, article_link)
                VALUES (%s, %s)
                ON CONFLICT (article_link) DO NOTHING
                RETURNING article_id;
            """, (created, article_link))
            result = cur.fetchone()
            if result:
                return result[0]
            else:
                cur.execute("SELECT article_id FROM comment_schema.articles WHERE article_link = %s;", (article_link,))
                return cur.fetchone()[0]

def add_keyword(keyword, settings_dict):
    with get_connection(settings_dict) as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO comment_schema.keywords(keyword) 
                VALUES (%s)
                ON CONFLICT (keyword) DO NOTHING
                RETURNING keyword_id;;
                ''',
                (keyword,)
            )
            result = cur.fetchone()
            if result:
                return result[0]
            else:
                cur.execute("SELECT keyword_id FROM comment_schema.keywords WHERE keyword = %s;", (keyword,))
                return cur.fetchone()[0]

def add_article_keyword_match(article_id, keyword_id, settings_dict):
    with get_connection(settings_dict) as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO comment_schema.article_keywords(article_id, keyword_id)  
                VALUES (%s, %s)
                ON CONFLICT (article_id, keyword_id) DO NOTHING;
                ''',
                (article_id, keyword_id)
            )

def add_comment(comment_id, text, ctype, root_id, user_id, article_id, created, settings_dict):
    with get_connection(settings_dict) as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO comment_schema.comments(comment_id, text, type, root_id, user_id, article_id, created) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                 ON CONFLICT (comment_id) DO NOTHING;
                ''',
                (comment_id, text, ctype, root_id, user_id, article_id, created)
            )



for file in os.listdir("../../data/raw_data"):
    file_object = open(f"../../data/raw_data/{file}")
    json_data = json.load(file_object)
    print(json_data)
    #insert article data
    timestamp = datetime.fromisoformat(json_data["article_time"])
    article_link = json_data["article_url"]
    article_id =  add_article(timestamp, article_link, settings_dict)
    for keyword in json_data["article_keywords"]:
        keyword_id = add_keyword(keyword.replace(",",""), settings_dict)
        add_article_keyword_match(article_id, keyword_id, settings_dict)
    for comment_id in json_data["comments"]:
        single_comment_data = json_data["comments"][comment_id]
        #insert user data
        profile_link = single_comment_data["user_profil_link"]
        user_id = extract_user_id(profile_link)
        if profile_link == "" or user_id == "":
            continue
        name = single_comment_data["user_name"]
        add_user(user_id, name, profile_link, settings_dict)
        #insert comment data
        comment_created = datetime.strptime(single_comment_data["time"], '%Y-%m-%dT%H:%M:%S.%fZ')
        add_comment(comment_id, single_comment_data["text"], single_comment_data["type"], single_comment_data["root_id"],
                    user_id, article_id, comment_created , settings_dict)

