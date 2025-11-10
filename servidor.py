import sqlite3
from flask import Flask, request, jsonify

# --- Configuração ---
NOME_BD_SERVIDOR = "/data/servidor_central.db" 

# --- Banco de Dados ---
def iniciar_banco_de_dados():
    """ Cria a tabela (se não existir) no banco de dados central """
    print("Iniciando banco de dados em: ", NOME_BD_SERVIDOR)
    try:
        conn = sqlite3.connect(NOME_BD_SERVIDOR)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_testes_central (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_recebido TEXT DEFAULT (DATETIME('now', 'localtime')),
            esp32_id TEXT,
            serial_number TEXT,
            internal_resistance REAL,
            process_time_sec REAL,
            delta_soc REAL,
            resultado TEXT
        );
        """)
        conn.commit()
        conn.close()
        print("Banco de dados pronto.")
    except Exception as e:
        print(f"ERRO CRÍTICO ao iniciar banco de dados: {e}")

# --- Inicializa o BD antes de tudo ---
iniciar_banco_de_dados()

# --- Inicia o Servidor ---
app = Flask(__name__) 


# --- API  ---
@app.route('/api/log_teste', methods=['POST'])
def receber_log_teste():
    """ Este é o URL que o ESP32 vai chamar """

    data = request.json
    print(f"Recebido: {data}")

    if not data:
        return jsonify({"erro": "Nenhum dado recebido"}), 400

    try:
        conn = sqlite3.connect(NOME_BD_SERVIDOR)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO log_testes_central 
            (esp32_id, serial_number, internal_resistance, process_time_sec, delta_soc, resultado)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get('esp32_id'),
            data.get('serial_number'),
            data.get('internal_resistance'),
            data.get('process_time_sec'),
            data.get('delta_soc'),
            data.get('resultado')
        ))
        conn.commit()
        conn.close()

        print("Log salvo no banco de dados central com sucesso.")
        return jsonify({"sucesso": True, "msg": "Log recebido"}), 201

    except Exception as e:
        print(f"ERRO ao salvar no BD: {e}")
        return jsonify({"sucesso": False, "erro": str(e)}), 500

@app.route('/')
def health_check():
    return "Servidor de Baterias está online.", 200
