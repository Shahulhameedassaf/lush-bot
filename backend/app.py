from flask import Flask, send_from_directory
from flask_cors import CORS
from api import api_bp
from admin import admin_bp

# MAIN APP - ROUTES ONLY
app = Flask(__name__, 
            template_folder='../frontend',
            static_folder='../frontend')
CORS(app)

# Register blueprints (separate API & Admin)
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api')

# SERVE FRONTEND FILES (Public)
@app.route('/')
def home():
    return send_from_directory('../frontend', 'index.html')

@app.route('/login.html')
def login_page():
    return send_from_directory('../frontend', 'login.html')

@app.route('/logs.html')
def logs_page():
    return send_from_directory('../frontend', 'logs.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Endpoint not found'}, 404

if __name__ == '__main__':
    print("="*60)
    print("🚀 LUSHBOT - MODULAR SERVER")
    print("📱 Users: http://localhost:5000 (No login)")
    print("🔐 Admin: http://localhost:5000/login.html")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, debug=True)
