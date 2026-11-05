import os

from backend import create_app

# Instancia la aplicación desde la carpeta backend/
app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print("  DIGITAL SPORTS DMC — Backend (Flask + MySQL / XAMPP)")
    print("=" * 60)
    print("  Aplicación: http://localhost:5000")
    print("  API REST:   http://localhost:5000/api")
    print("=" * 60)

    # Inicia el servidor de desarrollo (debug solo en configuración de desarrollo)
    app.run(debug=app.config.get('DEBUG', False), port=int(os.getenv('PORT', '5000')))
