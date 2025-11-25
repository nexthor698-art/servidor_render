# server_render.py
import os
import json
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# Directorio para archivos temporales y la base de datos de estado
TEMP_DIR = './temp_uploads'
STATUS_FILE = './pc_status.json' # Archivo para guardar los IDs y nombres de las PCs

app = Flask(__name__)

# --- Inicialización del Servidor ---
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def load_pc_status():
    """Carga los IDs y nombres de las PCs desde el archivo JSON."""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_pc_status(status_data):
    """Guarda los IDs y nombres de las PCs en el archivo JSON."""
    with open(STATUS_FILE, 'w') as f:
        json.dump(status_data, f, indent=4)

PC_STATUS = load_pc_status()

# -----------------------------------------------------
# ** 1. REGISTRO y ESTATUS **
# -----------------------------------------------------

@app.route('/register', methods=['POST'])
def register_pc():
    """Registra o actualiza el nombre amigable de una PC Receptora."""
    data = request.json
    pc_id = data.get('id')
    pc_name = data.get('name')
    
    if not pc_id:
        return jsonify({"message": "Falta 'id' de la PC"}), 400

    PC_STATUS[pc_id] = {
        'name': pc_name if pc_name else f"PC_{pc_id[:4]}", # Nombre predeterminado
        'pending_file': None # Usado para notificar al Receptor
    }
    save_pc_status(PC_STATUS)
    return jsonify({"message": "PC registrada/actualizada", "current_name": PC_STATUS[pc_id]['name']})


@app.route('/list_pcs', methods=['GET'])
def list_pcs():
    """Devuelve la lista de PCs registradas para el Remitente."""
    pc_list = [{"id": pid, "name": PC_STATUS[pid]['name']} for pid in PC_STATUS]
    return jsonify(pc_list)


# -----------------------------------------------------
# ** 2. SUBIDA DE ARCHIVO (DEL REMITENTE AL SERVIDOR) **
# -----------------------------------------------------

@app.route('/upload', methods=['POST'])
def upload_file():
    """Recibe el archivo y los comandos del PC Remitente."""
    if 'file' not in request.files:
        return jsonify({"message": "Falta el archivo ('file') en la petición"}), 400
    
    file = request.files['file']
    pc_id = request.form.get('pc_id')
    target_path = request.form.get('target_path')
    execute_after_save = request.form.get('execute', 'false') == 'true'

    if not pc_id or pc_id not in PC_STATUS:
        return jsonify({"message": "ID de PC de destino no válido."}), 400

    if file.filename == '':
        return jsonify({"message": "No se seleccionó ningún archivo."}), 400
    
    # 1. Guarda el archivo temporalmente
    filename = secure_filename(file.filename)
    unique_filename = f"{pc_id}_{filename}" # Nombra el archivo para su ID
    file_path = os.path.join(TEMP_DIR, unique_filename)
    file.save(file_path)

    # 2. Notifica a la PC de destino
    PC_STATUS[pc_id]['pending_file'] = {
        'unique_filename': unique_filename,
        'original_name': filename,
        'target_path': target_path,
        'execute': execute_after_save
    }
    save_pc_status(PC_STATUS)

    return jsonify({"message": f"Archivo '{filename}' recibido. PC destino notificada."}), 200

# -----------------------------------------------------
# ** 3. DESCARGA DE ARCHIVO (DEL SERVIDOR AL RECEPTOR) **
# -----------------------------------------------------

@app.route('/check_status/<pc_id>', methods=['GET'])
def check_status(pc_id):
    """El PC Receptor usa este endpoint para preguntar por archivos pendientes."""
    if pc_id not in PC_STATUS:
        return jsonify({"message": "ID de PC no registrado"}), 404
    
    pending = PC_STATUS[pc_id]['pending_file']
    
    if pending:
        # Devuelve la información necesaria para la descarga
        return jsonify({
            "message": "Archivo pendiente",
            "file_info": pending
        }), 200
    
    return jsonify({"message": "No hay archivos pendientes"}), 204 # Código 204: No Content


@app.route('/download/<unique_filename>', methods=['GET'])
def download_file(unique_filename):
    """Entrega el archivo al PC Receptor y lo borra del estado."""
    file_path = os.path.join(TEMP_DIR, unique_filename)
    
    if not os.path.exists(file_path):
        return jsonify({"message": "Archivo no encontrado"}), 404

    # Encuentra a qué PC correspondía
    pc_id = unique_filename.split('_')[0]
    
    # 1. Borra la notificación del estado
    if pc_id in PC_STATUS and PC_STATUS[pc_id]['pending_file']:
        PC_STATUS[pc_id]['pending_file'] = None
        save_pc_status(PC_STATUS)
        
    # 2. Envía el archivo al cliente
    from flask import send_from_directory
    return send_from_directory(TEMP_DIR, unique_filename, as_attachment=True)


# Punto de entrada para Gunicorn/Render
if __name__ == '__main__':
    # Usar el puerto 8080 en desarrollo para coincidir con Render
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
