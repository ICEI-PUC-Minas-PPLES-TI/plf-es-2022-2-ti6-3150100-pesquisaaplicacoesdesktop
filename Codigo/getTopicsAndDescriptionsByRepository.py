import mysql.connector
import requests
import openai

from pathlib import Path
from dotenv import dotenv_values

env_path = Path(__file__).parent / ".\\.env"
config = dotenv_values(str(env_path))
HOST = config["HOST"]
USER = config["USER"]
PASSWORD = config["PASSWORD"]
DATABASE = config["DATABASE"]
GITHUB_TOKEN = config["GITHUB_TOKEN"]

openai.api_key = config["OPENAI_API_KEY"]

mydb = mysql.connector.connect(
    host=HOST,
    user=USER,
    password=PASSWORD,
    database=DATABASE
)

headers = {"Authorization": ("Bearer " + GITHUB_TOKEN)}


def run_gquery(owner, repository):
    request = requests.post('https://api.github.com/graphql',
                            json={'query': """
                                    {
                                      repository(owner: \"""" + owner + """\", name: \"""" + repository + """\") {
                                            id
                                            name
                                            stargazerCount
                                            isFork
                                            description
                                            repositoryTopics(first: 20) {
                                            edges {
                                                node {
                                                id
                                                topic {
                                                    name
                                                }
                                                }
                                            }
                                            }
                                        }
                                    }
                                    """}, headers=headers)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}.".format(
            request.status_code))


mycursor = mydb.cursor()

limit = 100
cont = True

while cont:
    mycursor.execute(
        f"SELECT * FROM repository WHERE stars IS NULL LIMIT {limit}")
    print("Consulta")

    myresult = mycursor.fetchall()
    # print(myresult)
    # if len(myresult) > 0:
    for x in myresult:
        print(x[1])
        repsplit = x[1].split("/")
        json = run_gquery(repsplit[0], repsplit[1])
        if json['data']['repository'] is not None:
            description = json['data']['repository']['description']
            print("Descricao: ")
            print(description)
            if description is not None:
                # descriptionSplit = description.split()
                response = openai.Completion.create(
                    model="text-davinci-002",
                    prompt=f"Set the domain of this GitHub description:{description}",
                    temperature=0.6,
                )
                result = response.choices[0].text
                print("Resultado openIA")
                print(result)
                if len(result) < 50:
                    # descriptionSplitNew = [
                    #     str for str in descriptionSplit if len(str) > 1]
                    sql = "INSERT INTO repository_description (repository_id, word) VALUES (%s, %s)"
                    ll = []
                    # for d in descriptionSplitNew:
                    ll.append((x[0], result))
                    try:
                        mycursor.executemany(sql, ll)
                        mydb.commit()
                    except:
                        print(
                            "Erro ao executar essa query  (repository_description): ")
                        print(sql)
            else:
                description = ""
            topics = json['data']['repository']['repositoryTopics']['edges']
            if len(topics) > 0:
                print("Salvando topicos")
                topicsSave = []
                for t in topics:
                    topicName = t['node']['topic']['name']
                    topicsSave.append((x[0], topicName))
                print(topicsSave)
                try:
                    sql = "INSERT INTO repository_tag (repository_id, tag) VALUES (%s, %s)"
                    mycursor.executemany(sql, topicsSave)
                    mydb.commit()
                except:
                    print("Erro ao executar essa query (repository_tag): ")
                    print(sql)

            stars = json['data']['repository']['stargazerCount']
            # try:
            #     sql = f"UPDATE repository SET stars = {stars}, full_description = '{description}' WHERE id={x[0]}"
            #     mycursor.execute(sql)
            #     mydb.commit()
            # except:
            #     print("Erro ao executar essa query  (repository): ")
            #     print(sql)

        else:
            sql = f"UPDATE repository SET stars = 0 WHERE id={x[0]}"
            mycursor.execute(sql)
            mydb.commit()
    else:
        cont = False


#
