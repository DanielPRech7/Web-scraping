import requests
from bs4 import BeautifulSoup
import json
import csv
import logging
import sqlite3
import pandas as pd
from flask import Flask, jsonify, Response
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import base64
#import pytz

# Configuração do logger
LOG_FILE = "logger.txt"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(LOG_FILE, encoding='utf-8')
])
logger = logging.getLogger()

IMDB_URL = "https://www.imdb.com/chart/top/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.imdb.com/",
    "Connection": "keep-alive"
}

json_base64 = ""

#timezone = pytz.timezone('America/Sao_Paulo')

# raspagem da lista de filmes
def raspagem_dos_filmes():
    """Raspa a lista dos filmes do site IMDb e salva em JSON, CSV e banco de dados SQLite."""
    try:
        requisicao = requests.get(IMDB_URL, headers=HEADERS)
        requisicao.raise_for_status()

        logger.info("Requisição feita com sucesso, status code: %s", requisicao.status_code)
        site = BeautifulSoup(requisicao.text, "html.parser")

        filmes = site.select('.ipc-title__text')
        lista_dos_filmes = [{"filme": filme.get_text()} for filme in filmes]

        if lista_dos_filmes:
            logger.info("Títulos extraídos com sucesso:")
            for filme_ in lista_dos_filmes:
                logger.info("Filme: %s", filme_["filme"])
        else:
            logger.warning("Nenhum título encontrado.")

        # Salvar JSON e CSV
        salvar_dados(lista_dos_filmes, "filmes.json", "filmes.csv")
        
        # Salvar dados no SQLite
        salvar_dados_no_banco(lista_dos_filmes, 'movies.db')

    except requests.RequestException as e:
        logger.error("Erro ao fazer a requisição: %s", e)

def salvar_dados(lista_dos_filmes, json_path, csv_path):
    """Salva os dados em arquivos JSON e CSV, e gera a string base64 do JSON."""
    global json_base64

    df_filmes = pd.DataFrame(lista_dos_filmes)
    print(df_filmes)
    
    logger.info("Salvando filmes.json")
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(lista_dos_filmes, json_file, ensure_ascii=False, indent=4)

    # Converter JSON em Base64
    json_string = json.dumps(lista_dos_filmes, ensure_ascii=False)
    base64_bytes = base64.b64encode(json_string.encode('utf-8'))
    json_base64 = base64_bytes.decode('utf-8')
    
    logger.info("JSON convertido para Base64 e salvo em filmes_base64.txt")

    logger.info("Salvando filmes.csv")
    with open(csv_path, "w", newline='', encoding="utf-8") as csv_file:
        fieldnames = ["filme"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(lista_dos_filmes)

    logger.info("Dados salvos em filmes.csv e filmes.json")

def salvar_dados_no_banco(lista_dos_filmes, db_path):
    """Salva os dados em um banco de dados SQLite."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filme TEXT NOT NULL
            )
        ''')
        logger.info("Tabela 'movies' criada.")

        cursor.executemany('''
            INSERT INTO movies (filme) VALUES (?)
        ''', [(filme_['filme'],) for filme_ in lista_dos_filmes])
        logger.info("Dados inseridos na tabela 'movies' com sucesso.")

def tirar_print(url, file_name):
    """Tira uma captura de tela da URL especificada e salva no arquivo dado."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        logger.info("Driver iniciado com sucesso.")
        
        driver.get(url)
        logger.info("URL carregada: %s", url)
        
        driver.save_screenshot(file_name)
        logger.info("Captura salva como: %s", file_name)
    except Exception as e:
        logger.error("Erro ao tirar captura de tela: %s", e)
    finally:
        driver.quit()
        logger.info("Driver finalizado.")

# Configuração do Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "API de Filmes"

@app.route('/movies')
def get_movies():
    """Retorna os filmes armazenados no banco de dados."""
    with sqlite3.connect('movies.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT filme FROM movies')
        filmes = cursor.fetchall()
    return jsonify([{"filme": filme_[0]} for filme_ in filmes])

@app.route('/movies/base64')
def get_movies_base64():
    """Retorna os filmes em formato JSON, decodificando a string Base64."""
    global json_base64
    # Decodificar a string Base64 de volta para JSON
    decoded_bytes = base64.b64decode(json_base64)
    decoded_json = decoded_bytes.decode('utf-8')
    # Retornar o JSON decodificado
    return Response(decoded_json, mimetype='application/json')

def main():
    raspagem_dos_filmes()
    tirar_print(IMDB_URL, "screenshot.png")

if __name__ == "__main__":
    scheduler = BackgroundScheduler()

    # Agendar a execução
    run_date = datetime(2024, 8, 2, 21, 57, 0)
    scheduler.add_job(main, 'date', run_date=run_date)
    scheduler.start()

    logger.info("Scheduler iniciado.")

    # Iniciar o servidor Flask
    app.run(host='0.0.0.0', port=5000,debug=True)