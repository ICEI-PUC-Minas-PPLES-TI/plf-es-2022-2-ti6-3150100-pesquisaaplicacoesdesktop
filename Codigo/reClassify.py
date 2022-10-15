import mysql.connector
import openai
import re
import time
from pathlib import Path
from dotenv import dotenv_values

env_path = Path(__file__).parent / ".\\.env"
config = dotenv_values(str(env_path))
HOST = config["HOST"]
USER = config["USER"]
PASSWORD = config["PASSWORD"]
DATABASE = config["DATABASE"]
openai.api_key = config["OPENAI_API_KEY"]

listCategories = ["animation","artificial intelligence","authenticator","automation","browser","converter","cryptocurrency","data visualization","database","downloader","editor","extension","file management","framework","image viewer","library","object detection","peer-to-peer","reader","remote desktop","screen capture","screen recorder","screen sharing","steam","streaming","task manager","taskbar","time tracking","usb","3d","audio","blockchain","bot","camera","chat","color palette","compression","crm","design","diagram","discord","docker","drawing","drivers","email","engine","finance","game","geospatial","ide","iot","keyboard","kubernetes","midi","minecraft","monitor","music","notes","notifications","player","plugin","pomodoro","proxy","security","server","terminal","test","voice","wallet"]
categoriesString = ",".join(listCategories)

mydb = mysql.connector.connect(
    host=HOST,
    user=USER,
    password=PASSWORD,
    database=DATABASE
)
mycursor = mydb.cursor()


def db_execute(sql):
    try:
        mycursor.execute(sql)
        mydb.commit()
    except mysql.connector.Error as err:
        print(f"Error at query: {sql}")
        print("Something went wrong: {}".format(err))


def db_execute_many(sql, arrayOfRecords):
    try:
        mycursor.executemany(sql, arrayOfRecords)
        mydb.commit()
    except mysql.connector.Error as err:
        print(f"Error at query: {sql}")
        print("Something went wrong: {}".format(err))


def execute_openia(task):
    try:
        response = openai.Completion.create(
            model="text-davinci-002",
            prompt=task,
            temperature=0.6,  # randomness
        )
        return response.choices[0].text.strip().replace(
            '\n', ' ').replace('\r', '').replace('  ',  ' ')
    except:
        print(f"Something went wrong at execute_openia: {task}")
        print("Waiting one minute")
        time.sleep(60)

def populate_description(limit, offset):
    mycursor.execute(
        f"SELECT * FROM repository LIMIT {limit} OFFSET {offset}")
    print("---\n")
    print("Fetching database repositories and descriptions...")
    print("---\n")

    repositories = mycursor.fetchall()
    # temperature = 0.6

    if len(repositories) > 0:
        for repository in repositories:
            print("---")

            repository_id = repository[0]
            repository_name_with_owner = repository[1]
            # decode() to remove b'' of MySQL TEXT type
            repository_description = repository[5].decode()
            description = repository_description

            print("Repository: " + repository_name_with_owner)
            print("Description: " + description)

            if description is not None and len(description) > 0:
                question_for_openia = f"Classify the repository description {description} according to exclusively the following categories: [{categoriesString}]"
                rulesForQuestion =  "If it suits to more than one of the categories, write then comma separated, limited to 1,2 or 3 categories. If it doens't fit any of the categories, write None."
            
                for attempt in range(3):
                    categories_choosen_by_openia = execute_openia(
                        f"{question_for_openia}.{rulesForQuestion}")
                    if categories_choosen_by_openia is None:
                        continue
                    
                    categories_by_openia = categories_choosen_by_openia.split(',')
                    print("OpenIA classified word(s): ")
                    print(categories_by_openia)

                    
                    if len(categories_by_openia) > 0:
                        categoryToSave = []
                        numberOfCategories = 0
                        for category in categories_by_openia:
                            category = re.sub('[^A-Za-z0-9- ]+', '', category)
                            category = category.lstrip()
                            if(category is not None and len(category) > 0 and category != '' and (category == 'None' or any(category == x for x in listCategories))):
                                numberOfCategories = numberOfCategories + 1
                                if (category != 'None'):
                                    categoryToSave.append((repository_id, category))

                        if(len(categoryToSave) > 0):
                            sql = "INSERT INTO repository_description (repository_id, word) VALUES (%s, %s)"
                            # time.sleep(10)
                            db_execute_many(sql, categoryToSave)
                        if (numberOfCategories > 0):
                            break
                        else:
                            print(f"Repository did not retrive valid response in attempt {attempt}.\n")
                            if attempt < 2:
                                print("Retrying to get a valid answer from Open AI...\n")
                            else:
                                print("No attempts left. Repository won't be classified.\n")
            print("---\n")

        if len(repositories) == limit:
            offset = offset + limit
            populate_description(limit, offset)

    elif offset == 0:
        print("No repositories found!")
    else:
        print("--Finished--")


limit = 100
offset = 0
populate_description(limit, offset)
