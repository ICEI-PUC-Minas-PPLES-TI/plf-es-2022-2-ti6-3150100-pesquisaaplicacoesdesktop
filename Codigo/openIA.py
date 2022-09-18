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
        print(f"Something went wrong at exeute_openia: {task}")
        print("Waiting one minute")
        time.sleep(60)


limit = 100

mycursor.execute(
    f"SELECT * FROM repository LIMIT {limit}")
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
            first_question_for_openia = "Describe the domain of this software from this description"
            domain_description_by_openia = execute_openia(
                f"{first_question_for_openia}:{description}")
            if domain_description_by_openia is None:
                continue
            print("OpenIA domain description: " + domain_description_by_openia)
            sql = f"INSERT INTO repository_description_openia (repository_id, description) VALUES ({repository_id}, '{domain_description_by_openia}')"
            # time.sleep(10)
            db_execute(sql)

            second_question_for_openia = "Extract a comma-separated list of categories in one word each category from the software description"
            categories_by_openia = execute_openia(
                f"{second_question_for_openia}:{description}")
            if categories_by_openia is None:
                continue
            categories_by_openia = categories_by_openia.split(',')
            print("OpenIA domain categories: ")
            print(categories_by_openia)
            if len(categories_by_openia) > 0:
                categoryToSave = []
                for category in categories_by_openia:
                    category = re.sub('[^A-Za-z0-9- ]+', '', category)
                    category = category.lstrip()
                    if(category is not None and len(category) > 0 and category != ''):
                        categoryToSave.append((repository_id, category))

                if(len(categoryToSave) > 0):
                    sql = "INSERT INTO repository_category_openia (repository_id, category) VALUES (%s, %s)"
                    # time.sleep(10)
                    db_execute_many(sql, categoryToSave)

        print("---\n")
else:
    print("No repositories without OpenIA data found!")
