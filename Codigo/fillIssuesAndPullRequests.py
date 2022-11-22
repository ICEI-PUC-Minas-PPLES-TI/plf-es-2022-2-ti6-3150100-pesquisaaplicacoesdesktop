from distutils.log import log
import re
import mysql.connector
import requests
import time
from pathlib import Path
from dotenv import dotenv_values
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium import webdriver

env_path = Path(__file__).parent / ".\\.env"
config = dotenv_values(str(env_path))
HOST = config["HOST"]
USER = config["USER"]
PASSWORD = config["PASSWORD"]
DATABASE = config["DATABASE"]
GITHUB_TOKEN = config["GITHUB_TOKEN"]

headers = {"Authorization": ("Bearer " + GITHUB_TOKEN)}

db = mysql.connector.connect(
    host=HOST,
    user=USER,
    password=PASSWORD,
    database=DATABASE
)

cursor = db.cursor(dictionary=True)

cursor.execute("SELECT * FROM repository")
# cursor.execute("select * from repository where full_description IS NULL")
# cursor.execute("select * from repository where number_of_tags = 0")


results = cursor.fetchall()

lastRepo = ""


def setDescription(repo, browser):
    url = "https://github.com/"+repo["name_with_owner"]
    id = repo["id"]
    browser.get(url)
    try:
        data = browser.find_element(
            By.XPATH, '//*[@id="repo-content-pjax-container"]/div/div/div[3]/div[2]/div/div[1]/div/p').text
        data = data.replace("'", "")
    except:
        print(repo["name_with_owner"]+" failed at set description")
        data = browser.find_element(
            By.XPATH, '//*[@id="repo-content-pjax-container"]/div/div/div[3]/div[2]/div/div[1]/div/div[1]').text
        data = data.replace("'", "")
        if(data == None):
            return
    if(len(data) < 3):
        data = "Not Found"
    sql = "UPDATE repository SET full_description = '%s' where id = %s" % (
        data, id)
    cursor.execute(sql)
    db.commit()


def setTags(repo, browser):
    url = "https://github.com/"+repo["name_with_owner"]
    idRepo = repo["id"]
    idTagTable = None
    browser.get(url)
    try:
        tags = browser.find_elements(
            By.CSS_SELECTOR, "a.topic-tag.topic-tag-link")
    except:
        print(repo["name_with_owner"]+" failed at set tags")
        return
    cursor.execute("SELECT MAX(id) FROM repository_tag")
    maxId = cursor.fetchall()
    cursor.execute("UPDATE repository SET number_of_tags = '%s' where id = %s" % (
        len(tags), idRepo))
    db.commit()
    if (maxId[0]['MAX(id)'] == None):
        idTagTable = 1
    else:
        idTagTable = maxId[0]['MAX(id)']+1
    for tag in tags:
        cursor.execute('insert into repository_tag (id,tag,repository_id) values (%s,"%s",%s)' % (
            idTagTable, tag.text, idRepo))
        idTagTable = idTagTable+1
    db.commit()


def setCreatedAt(repo):
    id = repo["id"]
    headers = {"Authorization": ("Bearer " + GITHUB_TOKEN)}
    data = repo["name_with_owner"].split("/")
    owner = data[0]
    repoName = data[1]
    request = requests.post('https://api.github.com/graphql',
                            json={'query': """
                                    {
                                      repository(owner: \"""" + owner + """\", name: \"""" + repoName + """\") {
                                            createdAt
                                        }
                                    }
                                    """
                                  }, headers=headers)
    if request.status_code == 200:
        response = (request.json())
        dateFormated = response["data"]["repository"]["createdAt"][0:10]
        # yyyy-mm-dd
        sql = "UPDATE repository SET created_at = '%s' where id = %s" % (
            dateFormated, id)
        cursor.execute(sql)
        db.commit()
    else:
        print(repo["name_with_owner"]+" failed at setCreatedAt")
        raise Exception("Query failed to run by returning code of {}.".format(
            request.status_code))


def auxSetPullRequests(prs, idRepo):
    cursor.execute("SELECT MAX(id) FROM repository_pull_request")
    maxId = cursor.fetchall()
    if (maxId[0]['MAX(id)'] == None):
        idPrTable = 1
    else:
        idPrTable = maxId[0]['MAX(id)']+1
    for pr in prs:
        if(pr['merged_at'] != None):
            date = (pr['merged_at'])[0:4]
            cursor.execute('insert into repository_pull_request (id,year,open,merged,canceled,repository_id) values (%s,%s,0,1,0,%s)' % (
                idPrTable, date, idRepo))
            idPrTable = idPrTable+1
        elif(pr['merged_at'] == None and pr['closed_at'] != None):
            date = (pr['closed_at'])[0:4]
            cursor.execute('insert into repository_pull_request (id,year,open,merged,canceled,repository_id) values (%s,%s,0,0,1,%s)' % (
                idPrTable, date, idRepo))
            idPrTable = idPrTable+1
        else:
            date = (pr['created_at'])[0:4]
            cursor.execute('insert into repository_pull_request (id,year,open,merged,canceled,repository_id) values (%s,%s,1,0,0,%s)' % (
                idPrTable, date, idRepo))
            idPrTable = idPrTable+1
    db.commit()
    return


def setPullRequests(repo):
    idRepo = repo["id"]
    data = repo["name_with_owner"].split("/")
    owner = data[0]
    repoName = data[1]
    cursor.execute(
        "select count(`year`) from repository_pull_request rpr where repository_id = %s" % (idRepo))
    numberOfPrs = cursor.fetchall()
    prs = []
    havePages = True
    page = 1
    if((numberOfPrs[0]['count(`year`)']) < 1):
        while havePages:
            url = "https://api.github.com/repos/%s/%s/pulls?state=all&page=%s" % (
                owner, repoName, page)
            print(url)
            try:
                request = requests.get(url, headers=headers)
                if request.status_code == 200:
                    responses = (request.json())
                    if(len(responses) > 0):
                        for pr in responses:
                            prs.append(pr)
                        page += 1
                    else:
                        havePages = False
            except:
                print("Erro ao pegar dados de pr: %s" % (repoName))
                return
        auxSetPullRequests(prs, idRepo)
    else:
        return


def setIssues(repo):
    repoNameSplit = repo["name_with_owner"].split("/")
    hasNextPage = True
    endCursor = None
    print(f"Insert issues from {repoNameSplit[0]}")
    try:
        while(hasNextPage == True):
            af = f', after: "{endCursor}"' if endCursor is not None else ''

            request = requests.post('https://api.github.com/graphql',
                                    json={'query': """
                                            {
                                                repository(owner: \"""" + repoNameSplit[0] + """\", name: \"""" + repoNameSplit[1] + """\") {
                                                    issues(first: 100   """ + af + """) {
                                                    nodes {
                                                        closed
                                                        createdAt
                                                    }
                                                    pageInfo {
                                                        hasNextPage
                                                        endCursor
                                                        }
                                                    }
                                                }
                                                }
                                            """
                                          }, headers={"Authorization": ("Bearer " + GITHUB_TOKEN)})
            if request.status_code == 200:
                response = (request.json())
                try:
                    if response["data"]["repository"] is None:
                        break
                    issues = response["data"]["repository"]["issues"]["nodes"]
                    hasNextPage = response["data"]["repository"]["issues"]["pageInfo"]["hasNextPage"]
                    endCursor = response["data"]["repository"]["issues"]["pageInfo"]["endCursor"]
                    issuesToSave = []
                    for issue in issues:
                        y = issue['createdAt'][2:4]
                        if issue['closed']:
                            issuesToSave.append((y, 1, 0, repo["id"]))
                        else:
                            issuesToSave.append((y, 0, 1, repo["id"]))

                    if len(issuesToSave) > 0:
                        try:
                            sql = "INSERT INTO repository_issue (year, open, closed, repository_id) VALUES (%s, %s, %s, %s)"
                            cursor.executemany(sql, issuesToSave)
                            db.commit()
                        except mysql.connector.Error as err:
                            print(f"Error at query: {sql}")
                            print("Something went wrong: {}".format(err))
                    else:
                        print(repo["name_with_owner"]+" failed at setIssue")
                        raise Exception("Query failed to run by returning code of {}.".format(
                            request.status_code))
                except:
                    break
    except mysql.connector.Error as err:
        print(f"Error pegando issues de {repoNameSplit[0]}")


def setMissingData(item, browser):
    # if(item["full_description"] == None or len(item["full_description"]) == 0):
    #     setDescription(item, browser)
    # if(item["number_of_tags"] == 0):
    #     setTags(item, browser)
    # setCreatedAt(item)
    # setPullRequests(item)
    setIssues(item)


def getAllData():
    browser = webdriver.Chrome(ChromeDriverManager().install())
    total = len(results)
    for result in results:
        print('faltam: %s' % (total))
        print("Analisando: "+result["name_with_owner"])
        time.sleep(0.5)
        setMissingData(result, browser)
        time.sleep(0.5)
        total -= 1
    browser.quit()


def getLastRepoId():
    f = open("lastRepo.txt", "r")
    sql = 'select id from repository where name_with_owner = "%s"' % (f.read())
    cursor.execute(sql)
    id = cursor.fetchall()
    return id[0]['id']


getAllData()
