import mysql.connector
import requests

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="root",
  database="appdesktop"
)


headers = {"Authorization": "Bearer TOKEN"}

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
                                    """ }, headers=headers)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}.".format(
            request.status_code))


mycursor = mydb.cursor()

limit = 5
cont = True

while cont:
    mycursor.execute(f"SELECT * FROM repositorio WHERE stars IS NULL LIMIT {limit}")
    print(f"Consulta")

    myresult = mycursor.fetchall()
    if len(myresult) > 0:
        for x in myresult:
            print(x[1])
            repsplit = x[1].split("/")
            json = run_gquery(repsplit[0], repsplit[1])
            if json['data']['repository'] is not None:
                description = json['data']['repository']['description']
                if description is not None:
                    descriptionSplit = description.split()
                    for ds in descriptionSplit:
                        if len(ds) > 1:
                            sql = "INSERT INTO repositorio_descricao (repositorio_id, word) VALUES (%s, %s)"
                            val = (x[0],ds)
                            mycursor.execute(sql,val)
                            mydb.commit()
                            
                
                topics = json['data']['repository']['repositoryTopics']['edges']
                if len(topics) > 0:
                    print("Salvando topicos")
                    topicsSave = []
                    for t in topics:
                        topicName = t['node']['topic']['name']
                        topicsSave.append((x[0], topicName))
                    print(topicsSave)
                    sql = "INSERT INTO repositorio_tags (repositorio_id, tag) VALUES (%s, %s)"
                    mycursor.executemany(sql, topicsSave)
                    mydb.commit()

                stars = json['data']['repository']['stargazerCount']
                sql = f"UPDATE repositorio SET stars = {stars} WHERE id={x[0]}"
                mycursor.execute(sql)
                mydb.commit()
            else:
                sql = f"UPDATE repositorio SET stars = 0 WHERE id={x[0]}"
                mycursor.execute(sql)
                mydb.commit()
    else:
        cont = False


#