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
page_num = 3448
url = 'https://github.com/{}/network/dependents'.format(repo)
browser = webdriver.Edge()

for i in range(page_num):
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

    print(data)

    for d in data:
        mycursor = mydb.cursor()
        sql = f"INSERT INTO repositorio (repname) VALUES ('{d}')"
        mycursor.execute(sql)
        mydb.commit()
        print("1 record inserted, ID:", mycursor.lastrowid)

    print(len(data))
    paginationContainer = soup.find("div", {"class":"paginate-container"}).findAll('a')
    if paginationContainer[-1]:
        url = paginationContainer[-1]["href"]
    else:
        break