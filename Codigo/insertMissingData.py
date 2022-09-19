import mysql.connector
import requests
from pathlib import Path
from dotenv import dotenv_values
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium import webdriver

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

def setDescription(repo, browser):
    url = "https://github.com/"+repo["name_with_owner"]
    id = repo["id"]
    browser.get(url)
    try:
        data = browser.find_element(By.XPATH, '//*[@id="repo-content-pjax-container"]/div/div/div[3]/div[2]/div/div[1]/div/p').text
    except: 
        data = ""
    sql = "UPDATE repository SET full_description = '%s' where id = %s"%(data, id)
    cursor.execute(sql)
    db.commit()

def setTags(repo, browser):
    url = "https://github.com/"+repo["name_with_owner"]
    idRepo = repo["id"]
    idTagTable = None
    browser.get(url)
    try:
        tags = browser.find_elements(By.CSS_SELECTOR, "a.topic-tag.topic-tag-link")
    except:
        return
    cursor.execute("SELECT MAX(id) FROM repository_tag")
    maxId = cursor.fetchall()
    cursor.execute("UPDATE repository SET number_of_tags = '%s' where id = %s"%(len(tags), idRepo))
    db.commit()
    if (maxId[0]['MAX(id)']==None):
        idTagTable = 1
    else: 
        idTagTable = maxId[0]['MAX(id)']+1
    for tag in tags:
        cursor.execute('insert into repository_tag (id,tag,repository_id) values (%s,"%s",%s)'%(idTagTable, tag.text,idRepo))
        idTagTable=idTagTable+1
    db.commit()

def setCreatedAt2(repo):
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
        print(dateFormated)
        # yyyy-mm-dd
        sql = "UPDATE repository SET created_at = '%s' where id = %s"%(dateFormated, id)
        cursor.execute(sql)
        db.commit()
    else:
        raise Exception("Query failed to run by returning code of {}.".format(
            request.status_code))   
        
def setPullRequests(repo):
    idRepo = repo["id"]
    data = repo["name_with_owner"].split("/")
    owner = data[0]
    repoName = data[1]
    request = requests.get("https://api.github.com/repos/%s/%s/pulls?state=all"%(owner, repoName))
    if request.status_code == 200:
        responses = (request.json())
        cursor.execute("SELECT MAX(id) FROM repository_pull_request")
        maxId = cursor.fetchall()
        if (maxId[0]['MAX(id)']==None):
            idPrTable = 1
        else: 
            idPrTable = maxId[0]['MAX(id)']+1
        for response in responses:
            if(response['merged_at']!=None):
                date = (response['merged_at'])[0:4]
                cursor.execute('insert into repository_pull_request (id,year,open,merged,canceled,repository_id) values (%s,%s,0,1,0,%s)'%(idPrTable, date, idRepo))
                idPrTable=idPrTable+1
            elif(response['merged_at']==None and response['closed_at']!=None):
                date = (response['closed_at'])[0:4]
                cursor.execute('insert into repository_pull_request (id,year,open,merged,canceled,repository_id) values (%s,%s,0,0,1,%s)'%(idPrTable, date, idRepo))
                idPrTable=idPrTable+1
            else:
                date = (response['created_at'])[0:4]
                cursor.execute('insert into repository_pull_request (id,year,open,merged,canceled,repository_id) values (%s,%s,1,0,0,%s)'%(idPrTable, date, idRepo))
                idPrTable=idPrTable+1
        db.commit()
        return
    else:
        return

def setCreatedAT(repo, browser):
    split = repo["name_with_owner"].split("/")
    id = repo["id"]
    url = "https://github.com/%s/%s/graphs/code-frequency"%(split[0], split[1])
    browser.get(url)
    browser.implicitly_wait(20)
    try: 
        dateComplete = browser.find_element(By.CSS_SELECTOR, "g.tick").text
    except:
        return
    dateFormated = dateComplete.split('/')
    # yyyy-mm-dd
    date = "20%s-%s-01"%(dateFormated[1],dateFormated[0])
    sql = "UPDATE repository SET created_at = '%s' where id = %s"%(date, id)
    cursor.execute(sql)
    db.commit()
    
def setMissingData(item, browser):
    if(item["full_description"]==None):
        setDescription(item, browser)
    if(item["number_of_tags"]==0):
        setTags(item, browser)
    # essa tratativa foi so pq os repos que tinham estavam com a data do dia que foram criados (2022-09-17) 
    date=item["created_at"]
    date = date.strftime("20%y-%m-%d")
    if(date=='2022-09-17'):
    # despois pode tirar
        setCreatedAT(item, browser)
    setPullRequests(item)

def getAll():
    browser = webdriver.Chrome(ChromeDriverManager().install())
    for result in results:
        print("Analisando: "+result["name_with_owner"])
        setMissingData(result, browser)
    browser.quit()

getAll()

