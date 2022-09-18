from lib2to3.pgen2 import driver
import mysql.connector
import re
from pathlib import Path
from dotenv import dotenv_values
from selenium import webdriver
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

env_path = Path(__file__).parent / ".\\.env"
config = dotenv_values(str(env_path))
HOST=config["HOST"]
USER=config["USER"]
PASSWORD=config["PASSWORD"]
DATABASE=config["DATABASE"]
GITHUB_TOKEN=config["GITHUB_TOKEN"]

db = mysql.connector.connect(
  host=HOST,
  user=USER,
  password=PASSWORD,
  database=DATABASE
)

browser = webdriver.Chrome(ChromeDriverManager().install())

cursor = db.cursor(dictionary=True)

cursor.execute("SELECT * FROM repository")

results = cursor.fetchall()

def setDescription(name):
    url = "https://github.com/"+name["name_with_owner"]
    id = name["id"]
    browser.get(url)
    data = browser.find_element(By.XPATH, '//*[@id="repo-content-pjax-container"]/div/div/div[3]/div[2]/div/div[1]/div/p').text
    sql = "UPDATE repository SET full_description = '%s' where id = %s"%(data,id)
    cursor.execute(sql)
    db.commit()
    browser.quit()

def setTags(name):
    url = "https://github.com/"+name["name_with_owner"]
    idRepo = name["id"]
    idTagTable = None
    browser.get(url)
    tags = browser.find_elements(By.CSS_SELECTOR, "a.topic-tag.topic-tag-link")
    cursor.execute("SELECT MAX(id) FROM repository_tag")
    maxId = cursor.fetchall()
    cursor.execute("UPDATE repository SET number_of_tags = '%s' where id = %s"%(len(tags),idRepo))
    db.commit()
    if (maxId[0]['MAX(id)']==None):
        idTagTable = 1
    else: 
        idTagTable = maxId[0]['MAX(id)']+1
    for tag in tags:
        cursor.execute('insert into repository_tag (id,tag,repository_id) values (%s,"%s",%s)'%(idTagTable,tag.text,idRepo))
        idTagTable=idTagTable+1
    db.commit()
    browser.quit()


def getMissingData(item):
    if(item["full_description"]==None):
        setDescription(item)
    # if(item["number_of_tags"]==0):
    #     setTags(item)

for result in results:
    getMissingData(result)

