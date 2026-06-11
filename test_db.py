from mysql.connector import Error

try:
    from database import get_connection
    conn = get_connection()
    if conn.is_connected():
        info = conn.get_server_info()
        print(f"Ligado ao MySQL versão: {info}")
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        print(f"Base de dados activa: {cursor.fetchone()}")
        conn.close()
except Error as e:
    print(f"Erro: {e}")