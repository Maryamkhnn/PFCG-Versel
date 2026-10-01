import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="maryam1234",
    database="pfcg_db"
)

cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INT AUTO_INCREMENT PRIMARY KEY,
name VARCHAR(100),
email VARCHAR(255) UNIQUE,
role VARCHAR(20),
password VARCHAR(255)
)
""")

db.commit()

print("Database Ready")

db.close()