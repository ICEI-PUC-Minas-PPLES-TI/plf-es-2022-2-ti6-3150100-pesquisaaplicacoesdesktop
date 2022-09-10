import mysql.connector
import re
from pathlib import Path
from dotenv import dotenv_values
from selenium import webdriver
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

env_path = Path(__file__).parent / "..\\.env"
config = dotenv_values(str(env_path))
HOST=config["HOST"]
USER=config["USER"]
PASSWORD=config["PASSWORD"]
DATABASE=config["DATABASE"]

filename = str(Path(__file__).parent / "lastURL.txt")

mydb = mysql.connector.connect(
  host=HOST,
  user=USER,
  password=PASSWORD,
  database=DATABASE
)

repo = "electron/electron"
browser = webdriver.Chrome(ChromeDriverManager().install())

file1 = open(filename,"r")

content = file1.read()
if not content:
    url = 'https://github.com/{}/network/dependents'.format(repo)
else:
    url = content

file1.close()

cont = True
i=0

while cont is not False:
    print("GET " + url)
    browser.get(url)
    r = browser.page_source
    soup = BeautifulSoup(r, "html.parser")

    data = [
        ("{}/{}".format(
            t.find('a', {"data-repository-hovercards-enabled":""}).text,
            t.find('a', {"data-hovercard-type":"repository"}).text
        ), re.sub("[^0-9]", "", t.find('span', {"class":"color-fg-muted text-bold pl-3"}).text))
        for t in soup.findAll("div", {"class": "Box-row"})
    ]

    print(data)

    mycursor = mydb.cursor()
    sql = "INSERT INTO repository (name_with_owner, stars, created_at, repository_language_id, repository_dependency_id) VALUES (%s, %s,  NOW() ,1, 1)"
    ll = []
    for d in data:
        if int(d[1]) >= 100:
            ll.append((d[0],d[1]))
    mycursor.executemany(sql, ll)
    mydb.commit()
    print(f"Inserted {len(data)} repos")

    paginationContainer = soup.find("div", {"class":"paginate-container"}).findAll('a')
    print(len(paginationContainer))
    if len(paginationContainer) > 1 or i == 0:
        url = paginationContainer[-1]["href"]
        file1 = open(filename,"w+")
        file1.write(url)
        file1.close()
        i += 1
    else:
        cont = False
        print("END")
