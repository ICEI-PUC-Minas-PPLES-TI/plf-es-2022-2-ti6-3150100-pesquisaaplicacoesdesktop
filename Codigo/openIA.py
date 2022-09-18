import mysql.connector
import openai
import re

from pathlib import Path
from dotenv import dotenv_values

env_path = Path(__file__).parent / ".\\.env"
config = dotenv_values(str(env_path))
HOST = config["HOST"]
USER = config["USER"]
PASSWORD = config["PASSWORD"]
DATABASE = config["DATABASE"]
OPENAI_API_KEY = config["OPENAI_API_KEY"]

mydb = mysql.connector.connect(
    host=HOST,
    user=USER,
    password=PASSWORD,
    database=DATABASE
)
mycursor = mydb.cursor()

openai.api_key = OPENAI_API_KEY

limit = 100

mycursor.execute(
    f"SELECT * FROM repository LIMIT {limit}")
print("---\n")
print("Fetching database repositories and descriptions...")
print("---\n")

repositories = mycursor.fetchall()
temperature = 0.6

if len(repositories) > 0:
    for repository in repositories:
        print("---")
        
        repository_id = repository[0]
        repository_name_with_owner = repository[1]
        repository_description = repository[5].decode() # decode() to remove b'' of MySQL TEXT type 
        description = repository_description

        print("Repository: " + repository_name_with_owner)
        print("Description: " + description)

        if description is not None and len(description)>0:
            first_question_for_openia = "Describe the domain of this software from this description"
            response = openai.Completion.create(
                model="text-davinci-002",
                prompt=f"{first_question_for_openia}:{description}",
                temperature=temperature, # randomness
            )
            domain_description_by_openia = response.choices[0].text.strip()
            print("OpenIA domain description: " + domain_description_by_openia)
            try:
                sql = f"INSERT INTO repository_description_openia (repository_id, openia_describe) VALUES ({repository_id}, '{domain_description_by_openia}')"
                mycursor.execute(sql)
                mydb.commit()
            except:
                print(
                    "Error executing this query (repository_description_openia): ")
                print(sql)
            
            second_question_for_openia = "Extract a comma-separated list of categories in one word each category from the software description"
            responseDaResponse = openai.Completion.create(
                model="text-davinci-002",
                prompt=f"{second_question_for_openia}:{description}",
                temperature=temperature,  # randomness
            )
            categories_by_openia = responseDaResponse.choices[0].text.strip().replace('\n', ' ').replace('\r', '').replace('  ',  ' ')
            categories_by_openia = categories_by_openia.split(',')
            print("OpenIA domain categories: ")
            print(categories_by_openia)
            for category in categories_by_openia:
                category = re.sub('[^A-Za-z0-9- ]+', '', category)
                category = category.lstrip()
                if(category is not None and len(category)>0):
                    try:
                        sql = f"INSERT INTO repository_category_openia (repository_id, category) VALUES ({repository_id}, '{category}')"
                        mycursor.execute(sql)
                        mydb.commit()
                    except:
                        print(
                            "Error executing this query (repository_category_openia): ")
                        print(sql)

        print("---\n")
else:
    print("No repositories without OpenIA data found!")
