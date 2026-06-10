import pymysql
import pymysql.cursors

def get_connection():
    return pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="",
        database="it_asset_management",
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor
    )