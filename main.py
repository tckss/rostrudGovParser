import requests
import sqlite3
import colorama
import datetime
from bs4 import BeautifulSoup

class Logger:
    @staticmethod
    def log(message : str) -> None:
        print(colorama.Fore.GREEN + f"[{datetime.datetime.now()}] - {message}")
    
    @staticmethod
    def error(message : str) -> None:
        print(colorama.Fore.RED + f"[{datetime.datetime.now()}] - {message}")

class Parser:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "accept" : "*/*",
            "user-agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        })
    
    def parse_pages_by_host(self, host : str) -> list:
        export_data : list = []

        Logger.log(f"Обработка хоста {host}")

        response = self.session.get(f"https://{host}.rostrud.gov.ru/news/?SHOWALL_1=1#nav_start")

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup.find_all("div", {"class" : "list-ell"}):
            element_response = self.session.get(f"https://{host}.rostrud.gov.ru" + element.find("a").get("href"))

            element_soup = BeautifulSoup(element_response.text, "html.parser")
  
            export_data.append({
                "date" : element_soup.find("span", {"class" : "date"}).get_text(strip=True),
                "text" : element_soup.find("h1").get_text(strip=True) + "\n" + element_soup.find("div", {"class" : "text-block"}).find("div", {"class" : "text-block"}).get_text(strip=True)
            })
        
        Logger.log(f"Обработка хоста {host} завершена")
        return export_data

class SqlService:
    def __init__(self, db_path : str) -> None:
        self.db_path = db_path
    
    def upload_exporting_data(self, data : list) -> None:
        Logger.log(f"Подключение к базе данных {self.db_path}...")
        try:
            connection = sqlite3.connect(self.db_path)
        except:
            Logger.error("Некорректный ввод пути до базы данных")

        cursor = connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS NewsData (
        date VARCHAR(20),
        text TEXT               
        )         
        """)

        cursor.execute("SELECT * FROM NewsData")
        db_before_update = cursor.fetchall()

        uploaded_textes = [x[1] for x in db_before_update]
        to_upload_textes = []

        for element in data:
            if (element["text"] in uploaded_textes):
                continue

            else:
                to_upload_textes.append(element)

        Logger.log("Выгрузка элементов в базу данных...")

        cursor.executemany("INSERT INTO NewsData(date, text) VALUES(:date, :text)", to_upload_textes)

        connection.commit()
        connection.close()

        Logger.log(f"Данные выгружены успешно! (Всего выгружено: {len(to_upload_textes)} элементов)")

def main() -> None:
    colorama.init()

    parser = Parser()
    sqlservice = SqlService(db_path = "news_data.sqlite")

    with open("hosts.txt", "r") as file:
        hosts = [x.replace("\n", "") for x in file.readlines()]
    

    for host in hosts:
        export_data = parser.parse_pages_by_host(host)
        sqlservice.upload_exporting_data(export_data)
        

if __name__ == "__main__":
    main()
