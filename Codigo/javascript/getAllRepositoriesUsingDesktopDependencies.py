import mysql.connector
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

mydb = mysql.connector.connect(
  host=HOST,
  user=USER,
  password=PASSWORD,
  database=DATABASE
)

repo = "electron/electron"
url = 'https://github.com/{}/network/dependents'.format(repo)
browser = webdriver.Chrome(ChromeDriverManager().install())

cont = True
i=0

while cont is not False:
    print("GET " + url)
    browser.get(url)
    r = browser.page_source
    soup = BeautifulSoup(r, "html.parser")

    data = [
        "{}/{}".format(
            t.find('a', {"data-repository-hovercards-enabled":""}).text,
            t.find('a', {"data-hovercard-type":"repository"}).text
        )
        for t in soup.findAll("div", {"class": "Box-row"})
    ]

    mycursor = mydb.cursor()
    sql = "INSERT INTO repository (name_with_owner) VALUES (%s)"
    ll = []
    for d in data:
        ll.append((d,))
    mycursor.executemany(sql, ll)
    mydb.commit()
    print(f"Inserted {len(data)} repos")

    paginationContainer = soup.find("div", {"class":"paginate-container"}).findAll('a')
    print(len(paginationContainer))
    if len(paginationContainer) > 1 or i == 0:
        url = paginationContainer[-1]["href"]
        i += 1
    else:
        cont = False
        print("END")