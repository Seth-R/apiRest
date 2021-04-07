from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/pruebamia'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ma = Marshmallow(app)

#modelo de la base de datos
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String(13))
    nombre = db.Column(db.String(70), unique=True)
    mensaje = db.Column(db.String(300))
   # created = db.Column(db.DateTime)

    def __init__(self, nombre, mensaje, telefono):
        self.nombre = nombre
        self.mensaje = mensaje
        #self.created = created
        self.telefono = telefono

db.create_all()

class TaskSchema(ma.Schema):
    class Meta:
        fields = ('id', 'nombre', 'mensaje', 'telefono')


task_schema = TaskSchema()
tasks_schema = TaskSchema(many=True)

@app.route('/tasks', methods=['Post'])
def create_task():
#llega la informacion del cliente
  nombre = request.json['nombre']
  mensaje = request.json['mensaje']
  telefono = request.json['telefono']
  #created = request.json['created']
#guardo la informacion del cliente en una variable
  new_task= Task(nombre, mensaje, telefono)

#mando la informcaion a la base de datos
  db.session.add(new_task)
  db.session.commit()

#respuesta del servidor
  return task_schema.jsonify(new_task)

#preguntar por los datos
@app.route('/tasks', methods=['GET'])
def get_tasks():
  all_tasks = Task.query.all()
  result = tasks_schema.dump(all_tasks)
  return jsonify(result)

@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'API PRUEBA'})
    
if __name__ == "__main__":
    app.run(debug=True)