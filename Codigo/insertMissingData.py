from lib2to3.pgen2 import driver
import mysql.connector
import re
from pathlib import Path
from dotenv import dotenv_values
from selenium import webdriver
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

cursor = db.cursor(dictionary=True)

cursor.execute("SELECT * FROM repository")

results = cursor.fetchall()

def setDescription(repo):
    browser = webdriver.Chrome(ChromeDriverManager().install())
    url = "https://github.com/"+repo["name_with_owner"]
    id = repo["id"]
    browser.get(url)
    try:
        data = browser.find_element(By.XPATH, '//*[@id="repo-content-pjax-container"]/div/div/div[3]/div[2]/div/div[1]/div/p').text
    except: 
        data = ""
    print(data)
    sql = "UPDATE repository SET full_description = '%s' where id = %s"%(data,id)
    cursor.execute(sql)
    db.commit()
    browser.quit()

def setTags(repo):
    browser = webdriver.Chrome(ChromeDriverManager().install())
    url = "https://github.com/"+repo["name_with_owner"]
    idRepo = repo["id"]
    idTagTable = None
    browser.get(url)
    try:
        tags = browser.find_elements(By.CSS_SELECTOR, "a.topic-tag.topic-tag-link")
    except:
        browser.quit()
        return
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

# def setPullRequests

# def setIssues

def setCreatedAT(repo):
    browser = webdriver.Chrome(ChromeDriverManager().install())
    split = repo["name_with_owner"].split("/")
    id = repo["id"]
    url = "https://github.com/%s/%s/graphs/code-frequency"%(split[0],split[1])
    browser.get(url)
    browser.implicitly_wait(10)
    dateComplete = browser.find_element(By.CSS_SELECTOR, "g.tick").text
    dateFormated = dateComplete.split('/')
    # yyyy-mm-dd
    date = "20%s-%s-01"%(dateFormated[1],dateFormated[0])
    sql = "UPDATE repository SET created_at = '%s' where id = %s"%(date,id)
    cursor.execute(sql)
    db.commit()
    browser.quit()

def getMissingData(item):
    # if(item["full_description"]==None):
    #     setDescription(item)
    # if(item["number_of_tags"]==0):
    #     setTags(item)
    setCreatedAT(item)

for result in results:
    getMissingData(result)

