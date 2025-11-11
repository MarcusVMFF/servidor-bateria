import os
import psycopg2
from flask import Flask, request, jsonify

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')
API_KEY_SECRET = os.environ.get('API_KEY_SECRET')

def get_db_connection():
    """Cria uma conexão com o banco de dados PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao DB: {e}")
        return None

def create_tables():
    """Cria a tabela 'log_testes' se ela não existir."""
    conn = get_db_connection()
    if conn is None:
        return

    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS log_testes (
                    id SERIAL PRIMARY KEY,
                    esp32_id TEXT,
                    serial_number TEXT,
                    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    internal_resistance REAL,
                    process_time_sec REAL,
                    delta_soc REAL,
                    resultado TEXT
                );
            """)
        conn.commit()
        print("Tabela 'log_testes' verificada/criada.")
    except Exception as e:
        print(f"Erro ao criar tabela: {e}")
    finally:
        conn.close()

# Rota principal para testes
@app.route('/')
def home():
    return "API de Log de Baterias está online."

# Rota para o ESP32 enviar dados
@app.route('/log_teste', methods=['POST'])
def add_log_teste():
    """Recebe dados de um teste de bateria e salva no banco."""
    
    # 1. Checagem de Segurança
    auth_key = request.headers.get('X-API-Key')
    if auth_key != API_KEY_SECRET:
        print(f"Tentativa de acesso não autorizada.")
        return jsonify({"error": "Nao autorizado"}), 401
    
    # 2. Obter dados (JSON) enviados pelo ESP32
    try:
        data = request.get_json()
        print(f"Recebido: {data}")

        # Extrai os dados do JSON
        esp_id = data.get('esp32_id')
        serial = data.get('serial_number')
        ir = data.get('internal_resistance')
        time_sec = data.get('process_time_sec')
        d_soc = data.get('delta_soc')
        res = data.get('resultado')

    except Exception as e:
        print(f"Erro ao processar JSON: {e}")
        return jsonify({"error": "JSON mal formatado"}), 400

    # 3. Inserir no Banco de Dados
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Falha na conexao com DB"}), 500

    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO log_testes 
                (esp32_id, serial_number, internal_resistance, process_time_sec, delta_soc, resultado) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql, (esp_id, serial, ir, time_sec, d_soc, res))
        
        conn.commit()
        print("Log salvo com sucesso no DB.")
        return jsonify({"success": True, "message": "Log salvo"}), 201

    except Exception as e:
        conn.rollback()
        print(f"Erro ao inserir no DB: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    create_tables()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
