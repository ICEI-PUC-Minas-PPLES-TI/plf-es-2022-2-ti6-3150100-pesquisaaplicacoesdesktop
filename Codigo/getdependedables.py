from bs4 import BeautifulSoup
import mysql.connector
from selenium import webdriver

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="root",
  database="appdesktop"
)


repo = "electron/electron"
url = 'https://github.com/{}/network/dependents'.format(repo)
browser = webdriver.Edge()

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
    sql = "INSERT INTO repositorio (repname) VALUES (%s)"
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