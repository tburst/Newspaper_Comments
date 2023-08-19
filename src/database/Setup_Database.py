import psycopg2
import json

#load sql database settings
settings_file = open("sql_settings.json")
settings_dict = json.load(settings_file)
dbname = settings_dict['dbname']
user = settings_dict["user"]
password = settings_dict["password"]
host = settings_dict["host"]
port = settings_dict["port"]

connection = psycopg2.connect(
    dbname=dbname,
    user=user,
    password=password,
    host=host,
    port=port
)

cursor = connection.cursor()

create_comment_table = '''
CREATE TABLE IF NOT EXISTS comment_schema.comments (
    comment_id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    type VARCHAR(5) CHECK (type IN ('main', 'reply')),
    root_id INTEGER REFERENCES comment_schema.comments(comment_id),
    user_id INTEGER REFERENCES comment_schema.users(user_id) NOT NULL,
    article_id INTEGER REFERENCES comment_schema.articles(article_id) NOT NULL,
    created TIMESTAMP NOT NULL);
'''

create_user_table = '''
CREATE TABLE IF NOT EXISTS comment_schema.users (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    profil_link TEXT NOT NULL);
'''

create_article_table = '''
CREATE TABLE IF NOT EXISTS comment_schema.articles (
    article_id SERIAL PRIMARY KEY,
    created TIMESTAMP NOT NULL,
    article_link TEXT NOT NULL UNIQUE);
'''

create_keyword_table = '''
CREATE TABLE IF NOT EXISTS comment_schema.keywords (
    keyword_id SERIAL PRIMARY KEY,
    keyword TEXT NOT NULL,
    UNIQUE(keyword)
);
'''

create_keyword_article_matching_table = '''
CREATE TABLE IF NOT EXISTS comment_schema.article_keywords (
    article_id INTEGER REFERENCES comment_schema.articles(article_id),
    keyword_id INTEGER REFERENCES comment_schema.keywords(keyword_id),
    PRIMARY KEY (article_id, keyword_id)
);
'''



cursor.execute(create_user_table)
cursor.execute(create_article_table)
cursor.execute(create_comment_table)
cursor.execute(create_keyword_table)
cursor.execute(create_keyword_article_matching_table)
connection.commit()
cursor.close()
connection.close()