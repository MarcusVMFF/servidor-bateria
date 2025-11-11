import os
import psycopg2
from flask import Flask, request, jsonify

# Inicializa o aplicativo Flask
app = Flask(__name__)

# Pega a URL do banco de dados e a chave de API secreta 
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
    """Cria a tabela 'log_bateria' se ela não existir."""
    print("Iniciando verificação de tabela 'log_bateria'...")
    conn = get_db_connection()
    if conn is None:
        print("ERRO CRÍTICO: Não foi possível conectar ao DB para criar tabelas. Verifique a DATABASE_URL.")
        return

    try:
        with conn.cursor() as cur:
            # Estrutura da tabela log_bateria (compatível com seu .ino)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS log_bateria (
                    id SERIAL PRIMARY KEY,
                    esp32_id TEXT,
                    battery_id TEXT, 
                    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    voltagem REAL,
                    porcentagem REAL,
                    soh INTEGER,
                    ciclos INTEGER,
                    capacidade INTEGER
                );
            """)
        conn.commit()
        print("SUCESSO: Tabela 'log_bateria' verificada/criada.")
    except Exception as e:
        print(f"ERRO CRÍTICO ao criar tabela: {e}")
    finally:
        if conn:
            conn.close()

# ====================================================================
# AQUI ESTÁ A CORREÇÃO:
# Chamamos a função de criação da tabela aqui, no escopo principal.
# O Gunicorn VAI executar isso ao carregar o arquivo 'servidor.py'.
# ====================================================================
create_tables()


# Rota principal para testes
@app.route('/')
def home():
    return "API de Log de Baterias está online."

# Endpoint atualizado para receber 'log_bateria'
@app.route('/log_bateria', methods=['POST'])
def add_log_bateria():
    """Recebe dados de telemetria da bateria e salva no banco."""
    
    # 1. Checagem de Segurança
    auth_key = request.headers.get('X-API-Key')
    if auth_key != API_KEY_SECRET:
        print(f"Tentativa de acesso não autorizada.")
        return jsonify({"error": "Nao autorizado"}), 401
    
    # 2. Obter dados (JSON) enviados pelo ESP32
    try:
        data = request.get_json()
        print(f"Recebido: {data}")

        # Extrai os dados do JSON para log_bateria
        esp_id = data.get('esp32_id')
        bat_id = data.get('battery_id')
        volt = data.get('voltagem')
        perc = data.get('porcentagem')
        soh_val = data.get('soh')
        ciclos_val = data.get('ciclos')
        cap = data.get('capacidade')

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
                INSERT INTO log_bateria 
                (esp32_id, battery_id, voltagem, porcentagem, soh, ciclos, capacidade) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql, (esp_id, bat_id, volt, perc, soh_val, ciclos_val, cap))
        
        conn.commit()
        print("Log de bateria salvo com sucesso no DB.")
        return jsonify({"success": True, "message": "Log salvo"}), 201

    except Exception as e:
        conn.rollback()
        print(f"Erro ao inserir no DB: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500
    finally:
        if conn:
            conn.close()

# Este bloco não é executado pelo Gunicorn, mas não faz mal deixá-lo.
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
