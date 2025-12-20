from app import create_app, db
from app.models import User, Measurement, SystemConfig

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Measurement': Measurement, 'SystemConfig': SystemConfig}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
