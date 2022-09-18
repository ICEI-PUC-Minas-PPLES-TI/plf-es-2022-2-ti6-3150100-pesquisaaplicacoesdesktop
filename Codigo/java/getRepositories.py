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
    (2,'org.swinglabs'),
    (3,'org.openjfx')
]

def run_gquery(after):
    if after != "null":
        after = f'"{after}"'
    request = requests.post('https://api.github.com/graphql',
                            json={'query': """
                                    {
                                        search(first: 100, type: REPOSITORY, query: "stars:>1000 language:Java", after: %s) {
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
mycursor.execute("SELECT * FROM repository_language WHERE `language`='Java'")
myresult = mycursor.fetchall()
if len(myresult) == 0:
    sql = "INSERT INTO repository_language (language) VALUES (%s)"
    val = ("Java",)
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
    print(after)
    result = run_gquery(after)
    data = result['data']['search']['nodes']
    print(data)

    for dt in data:
        url = 'https://github.com/{}/network/dependencies'.format(dt['nameWithOwner'])
        r = requests.get(url)
        
        soup = BeautifulSoup(r.content, "html.parser")

        for t in soup.findAll("small"):
            inDep = checkDependency(t.text)
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