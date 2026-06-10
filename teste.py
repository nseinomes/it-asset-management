# teste.py
import mysql.connector
from mysql.connector import Error

print("A tentar ligar...")

try:
    conn = mysql.connector.connect(
        host="127.0.0.1",  # usa IP em vez de localhost
        port=3306,
        user="root",
        password="",
        database="it_asset_management",
        connection_timeout=5
    )
    print("Ligado!")
    print("Versão MySQL:", conn.get_server_info())
    conn.close()
except Error as e:
    print(f"ERRO: {e}")
except Exception as e:
    print(f"ERRO INESPERADO: {type(e).__name__}: {e}")

print("Fim do script.")