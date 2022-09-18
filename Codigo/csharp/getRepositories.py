from pathlib import Path
from dotenv import dotenv_values
import requests
from bs4 import BeautifulSoup
import mysql.connector

env_path = Path(__file__).parent / "..\\.env"
config = dotenv_values(str(env_path))

HOST=config["HOST"]
USER=config["USER"]
PASSWORD=config["PASSWORD"]
DATABASE=config["DATABASE"]
GITHUB_TOKEN=config["GITHUB_TOKEN"]

filename = str(Path(__file__).parent / "lastURL.txt")

mydb = mysql.connector.connect(
  host=HOST,
  user=USER,
  password=PASSWORD,
  database=DATABASE
)


headers = {"Authorization": ("Bearer " + GITHUB_TOKEN)}

dependencies = [
    (4,'System.Windows.Forms')
]

def run_gquery(after):
    if after != "null":
        after = f'"{after}"'
    request = requests.post('https://api.github.com/graphql',
                            json={'query': """
                                    {
                                        search(first: 100, type: REPOSITORY, query: "stars:>1000 language:C#", after: %s) {
                                            pageInfo {
                                            startCursor
                                            hasNextPage
                                            endCursor
                                            }
                                            nodes {
                                            ... on Repository {
                                                nameWithOwner
                                                stargazerCount
                                            }
                                            }
                                        }
                                    }
                                    """ % ( after ) }, headers=headers)
    

    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}.".format(
            request.status_code))

def checkDependency(dependency):
    for d in dependencies:
        if d[1] in dependency:
            return d[0]
    return 0

mycursor = mydb.cursor()
mycursor.execute("SELECT * FROM repository_language WHERE `language`='C#'")
myresult = mycursor.fetchall()
if len(myresult) == 0:
    sql = "INSERT INTO repository_language (language) VALUES (%s)"
    val = ("C#",)
    mycursor.execute(sql, val)
    mydb.commit()
    languageID = mycursor.lastrowid
else:
    languageID = myresult[0][0]

try:
    file1 = open(filename,"r")
    content = file1.read()
    print(content)
    if not content:
        after = "null"
    else:
        after = content
except:
    after = "null"

while after != "":
    result = run_gquery(after)
    data = result['data']['search']['nodes']

    for dt in data:
        print(f"Checking repo {dt['nameWithOwner']}")
        url = 'https://github.com/{}/network/dependencies'.format(dt['nameWithOwner'])
        r = requests.get(url)
        
        soup = BeautifulSoup(r.content, "html.parser")

        dt2 = [
            t.find('a', {"data-octo-click":"dep_graph_manifest"})['href']
            for t in soup.findAll("div", {"class": "Box-header"})
        ]

        for d2 in dt2:
            if d2.endswith('.csproj'):
                url2 = 'https://github.com/{}'.format(d2)
                print(f"Checking repo {dt['nameWithOwner']} link {d2}")
                r2 = requests.get(url2)
                soup2 = BeautifulSoup(r2.content, "html.parser")
                txt = soup2.find("div", {"itemprop": "text"})
                if txt is not None:
                    inDep = checkDependency(txt.text)
                    if inDep > 0:
                        mycursor = mydb.cursor()
                        sql = "INSERT INTO repository (name_with_owner, stars, created_at, repository_language_id, repository_dependency_id) VALUES (%s, %s,  NOW() ,%s, %s)"
                        val = (dt['nameWithOwner'], dt['stargazerCount'], languageID, inDep)
                        mycursor.execute(sql, val)
                        mydb.commit()
                        print("Inserted ROW")
                        break
            

    if result['data']['search']['pageInfo']['endCursor']:
        after = result['data']['search']['pageInfo']['endCursor']
        file1 = open(filename,"w+")
        file1.write(after)
        file1.close()
    else:
        break