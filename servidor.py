import os
import psycopg2 # Biblioteca para falar com Postgres
from flask import Flask, request, jsonify

# --- Configuração ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERRO CRÍTICO: Variável de ambiente DATABASE_URL não encontrada.")

app = Flask(__name__) 
# --- Banco de Dados ---
def iniciar_banco_de_dados():
    """ Cria a tabela (se não existir) no banco de dados Postgres """
    print("Iniciando banco de dados Postgres...")
    
    comando_sql = """
    CREATE TABLE IF NOT EXISTS log_testes_central (
        id SERIAL PRIMARY KEY,
        timestamp_recebido TIMESTAMPTZ DEFAULT NOW(),
        esp32_id TEXT,
        serial_number TEXT,
        internal_resistance REAL,
        process_time_sec REAL,
        delta_soc REAL,
        resultado TEXT
    );
    """
    
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(comando_sql)
        conn.commit()
        cursor.close()
        print("Banco de dados pronto.")
    except Exception as e:
        print(f"ERRO CRÍTICO ao iniciar banco de dados: {e}")
    finally:
        if conn:
            conn.close()

# --- A API (O "Ouvinte") ---
@app.route('/api/log_teste', methods=['POST'])
def receber_log_teste():
    """ Este é o URL que o ESP32 vai chamar """
    
    data = request.json
    print(f"Recebido: {data}")

    if not data:
        return jsonify({"erro": "Nenhum dado recebido"}), 400

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
    
        cursor.execute("""
        INSERT INTO log_testes_central 
            (esp32_id, serial_number, internal_resistance, process_time_sec, delta_soc, resultado)
        VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data.get('esp32_id'),
            data.get('serial_number'),
            data.get('internal_resistance'),
            data.get('process_time_sec'),
            data.get('delta_soc'),
            data.get('resultado')
        ))
        
        conn.commit()
        cursor.close()
        
        print("Log salvo no banco de dados central com sucesso.")
        return jsonify({"sucesso": True, "msg": "Log recebido"}), 201
        
    except Exception as e:
        print(f"ERRO ao salvar no BD: {e}")
        return jsonify({"sucesso": False, "erro": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/')
def health_check():
    return "Servidor de Baterias está online.", 200

# --- Roda o Servidor ---
if __name__ == '__main__':
    iniciar_banco_de_dados()
    print("Inicialização concluída.")
