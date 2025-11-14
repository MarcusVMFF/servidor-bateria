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
create_tables()


# Rota principal para testes
@app.route('/')
def home():
    return "API de Log de Baterias está online."

# Rota para o ESP32 receber dados
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

# 4. Rota de visualização

@app.route('/visualizar')
def show_logs():
    """Busca os dados no banco e exibe em uma tabela HTML."""
    conn = get_db_connection()
    if conn is None:
        return "<h1>Erro 500: Não foi possível conectar ao banco de dados.</h1>", 500

    logs = []
    try:
        with conn.cursor() as cur:
            # Busca os 100 logs mais recentes
            cur.execute("SELECT * FROM log_bateria ORDER BY id DESC LIMIT 100")
            logs = cur.fetchall()
            print(f"Buscando logs... {len(logs)} encontrados.")
    except Exception as e:
        print(f"Erro ao buscar logs: {e}")
        return f"<h1>Erro ao consultar o banco: {e}</h1>", 500
    finally:
        if conn:
            conn.close()

    # Monta a página HTML
    html = """
    <html>
    <head>
        <title>Logs das Baterias</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; }
            h1 { color: #333; }
            table { width: 100%; border-collapse: collapse; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            th { background-color: #007bff; color: white; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            tr:hover { background-color: #f1f1f1; }
        </style>
    </head>
    <body>
        <h1>Logs de Bateria (Últimos 100)</h1>
        <p>Esta página atualiza automaticamente a cada 30 segundos.</p>
        <table>
            <tr>
                <th>ID</th>
                <th>ESP32 ID</th>
                <th>Battery ID</th>
                <th>Timestamp</th>
                <th>Voltagem</th>
                <th>Porcentagem</th>
                <th>SOH</th>
                <th>Ciclos</th>
                <th>Capacidade</th>
            </tr>
    """

    # Adiciona cada linha de log na tabela HTML
    for log in logs:
        # Colunas do banco: [0]id, [1]esp32_id, [2]battery_id, [3]timestamp, [4]voltagem, [5]porcentagem, [6]soh, [7]ciclos, [8]capacidade
        html += "<tr>"
        html += f"<td>{log[0]}</td>" # ID
        html += f"<td>{log[1]}</td>" # esp32_id
        html += f"<td>{log[2]}</td>" # battery_id
        html += f"<td>{log[3].strftime('%Y-%m-%d %H:%M:%S')}</td>" # timestamp formatado
        html += f"<td>{log[4]:.2f} V</td>" # voltagem
        html += f"<td>{log[5]:.1f} %</td>" # porcentagem
        html += f"<td>{log[6]} %</td>" # soh
        html += f"<td>{log[7]}</td>" # ciclos
        html += f"<td>{log[8]} mAh</td>" # capacidade
        html += "</tr>"

    html += """
        </table>
    </body>
    </html>
    """
    
    return html


# Bloco principal
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
