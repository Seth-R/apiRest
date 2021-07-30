from calendar import month
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from re import template
from typing import Text
from marshmallow import base, fields
from werkzeug import Client, security
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, json, request, jsonify, abort, make_response
from flask_sqlalchemy import BaseQuery, SQLAlchemy
from flask_marshmallow import Marshmallow
from datetime import datetime 
from datetime import timedelta
import uuid
import jwt
from functools import wraps
import sys
from pyngrok import ngrok
import requests


app = Flask(__name__)

#------------------------------------------------------------
app.config['SECRET_KEY']='estoessecreto'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/pruebamia'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
ma = Marshmallow(app)

#------------------modelo de la base de datos--------------
#Chats
class ContactClient(db.Model):
    id_agente =  db.Column(db.Integer, db.ForeignKey('user.id_agent'), primary_key=True)
    #db.Column(db.Integer, db.ForeignKey('interests.id'), primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('managment_client.id_client'), primary_key=True)

#tabla de user(Only for admin)
class User(db.Model):
  id_agent=db.Column(db.Integer, primary_key=True)
  id_empresa = db.Column(db.Integer, db.ForeignKey("cliente.id_empresa"))
  id_template = db.Column(db.ForeignKey("template_messages.id_template"))
  #cliente = relationship("Managment_client", secondary=secondary_foo, back_populates="name")
  public_id=db.Column(db.String(50), unique=True)
  name=db.Column(db.String(80))
  password=db.Column(db.String(80))
  admin=db.Column(db.Boolean)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(50))
    complete = db.Column(db.Boolean)
    user_id = db.Column(db.Integer)

#cliente (contactos del cliente)
class Managment_client(db.Model):
  name= db.Column(db.String(80))
  id_client = db.Column(db.Integer, primary_key=True)
  #contacto = db.relationship("User", secondary=secondary_foo, backref = 'clients', lazy = "joined")
  password = db.Column(db.String(80))
  user = db.Column(db.Boolean)

#Templates messages management
class Template_messages(db.Model):
  id_template = db.Column(db.Integer, primary_key=True)
  template_name = db.Column(db.String(80))
  status = db.Column(db.String(15))
  messages = db.Column(db.String(300))

  def __init__(self, template_name, status, messages):
    self.template_name = template_name
    self.status = status
    self.messages = messages

# - All messages management Outbound
class all_messages_managment_outbound(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  type_of_messages = db.Column(db.String(15))
  status = db.Column(db.String(15))
  messages = db.Column(db.String(300))  
  direction = db.Column(db.Boolean)
  sending_time = db.Column(db.DateTime, nullable = False, default = datetime.hour)
  contact_number = db.Column(db.Integer(), nullable = False)
  id_agent = db.Column(db.Integer, db.ForeignKey("user.id_agent"), primary_key=True)

# + All messages management Inbound
class all_message_managment_inbound(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  type_of_messages = db.Column(db.String(15))
  status = db.Column(db.String(15))
  messages = db.Column(db.String(300))  
  direction = db.Column(db.Boolean)
  sending_time = db.Column(db.DateTime, nullable = False, default = datetime.hour)
  contact_number = db.Column(db.Integer(), nullable = False)
  id_agent = db.Column(db.Integer, primary_key=True)
  contact_name = db.Column(db.String(80))
  id_agent = db.Column(db.Integer, db.ForeignKey("user.id_agent"), primary_key=True)


#Tabla datos usuario(cliente, empresa)
#va a tener un id del contactos del cliente 
class cliente(db.Model):
  id_empresa=db.Column(db.Integer, primary_key=True)
  licencia_activa=db.Column(db.Boolean)
  licencias=db.Column(db.Integer(), nullable=False)
  fecha_compra=db.Column(db.Date(), nullable=False)
  fecha_fin=db.Column(db.Date(), nullable=False)

  def __init__(self, licencia_activa, licencias, fecha_compra, fecha_fin ):
    self.licencia_activa = licencia_activa
    self.fecha_compra = datetime.strptime(fecha_compra, "%d-%m-%y")
    self.fecha_fin = datetime.strptime(fecha_fin, "%d-%m-%y")
    self.licencias = licencias

#tabla de datos del cliente
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String(13))
    nombre = db.Column(db.String(70), unique=True)
    mensaje = db.Column(db.String(300))
    #autor=db.Column(db.String(70), unique=True)
    #pub_date = db.Column(DateTime, nullable = False)
    pub_date = db.Column(db.DateTime, nullable=False,
        default=datetime.utcoffset)
   # created = db.Column(db.DateTime)

    def __init__(self, nombre, mensaje, telefono):
        self.nombre = nombre
        self.mensaje = mensaje
        self.telefono = telefono

db.create_all()
class userSchema(ma.Schema):
  class Meta:
    model = User
class managmentClientSchema(ma.Schema):
  class Meta:
    model = Managment_client
class TemplateSchema(ma.Schema):
  class Meta:
    fields = ('template_name', 'status', 'messages')
class TaskSchema(ma.Schema):
    class Meta:
        fields = ('id', 'nombre', 'mensaje', 'telefono', 'pub_date')
class ClientSchema(ma.Schema):
    class Meta:
        fields = ('id', 'licencia_activa', 'licencias', 'fecha_compra', 'fecha_fin')


#schemas marshmallow
user_schema = userSchema()
users_schema = userSchema(many=True)

managment_client_schema = managmentClientSchema()
managment_Clients_schema = managmentClientSchema(many=True)

template_schema = TemplateSchema()
templates_schema = TemplateSchema(many=True)

client_schema = ClientSchema()
clients_schema = ClientSchema(many=True)

task_schema = TaskSchema()
tasks_schema = TaskSchema(many=True)


#peticion de token(validacion de token)s
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message' : 'Token faltante'}), 401

        try: 
            data = jwt.decode(token, app.config['SECRET_KEY'])
            current_user = User.query.filter_by(public_id=data['public_id']).first()
        except:
            return jsonify({'message' : 'Token invalido'}), 401

        return f(current_user, *args, **kwargs)

    return decorated
#----------------------------webhook-------------------------------inicio

@app.route("/webhook/messages", methods=["GET"])
def webhook_get_chat():

# Get latest queued messages
  url = "https://api.wassenger.com/v1/messages"

  querystring = {"size":"50","page":"0","status":"any"}

  headers = {"Token": "8294218044be1390a0538f7bbb35a68593214a4bf3928635422ee12c7b366c451e812265663fb1e8"}

  response = requests.request("GET", url, headers=headers, params=querystring)

  return response.text

@app.route("/webhook/messages", methods=["POST"])
def webhook_post_chat():
  url = "https://api.wassenger.com/v1/messages"

  phone = request.json['phone']
  message = request.json['message']
  payload = {
      "phone": phone,
      "message": message
  }
  headers = {
      "Content-Type": "application/json",
      "Token": "0cea57c569ed0fabba05b08a3ce7c4181661c33d21751beb4e7ced4e44668dcdd20eaa1c6ae03ea2"
  }

  response = requests.request("POST", url, json=payload, headers=headers)
  return response

@app.route("/webhook/messages_by_agent", methods=["GET"])
def webhook_Get_messages_by_agent():

  url = "https://api.wassenger.com/v1/messages"

  phone = request.json['phone']
  querystring = {"size":"30","status":"processed","phone":phone}

  headers = {"Token": "0cea57c569ed0fabba05b08a3ce7c4181661c33d21751beb4e7ced4e44668dcdd20eaa1c6ae03ea2"}

  response = requests.request("GET", url, headers=headers, params=querystring)


@app.route('/webhook/Get_messages_by_status', methods=['GET'])
def webhook_get_messages_by_status():

  url = "https://api.wassenger.com/v1/messages"

  status = request.json['status']

  querystring = {"size":"50","page":"0","status":status}

  headers = {"Token": "0cea57c569ed0fabba05b08a3ce7c4181661c33d21751beb4e7ced4e44668dcdd20eaa1c6ae03ea2"}

  response = requests.request("GET", url, headers=headers, params=querystring)
  return response

app.route('/webhook/get_messages_by_agent_and_customers', methods=['GET'])
def webhook_get_messages_by_agent_and_customers():
  url = "https://api.wassenger.com/v1/messages"

  customer = request.json['customer']

  querystring = {"size":"10","status":"any","search":customer}

  headers = {"Token": "0cea57c569ed0fabba05b08a3ce7c4181661c33d21751beb4e7ced4e44668dcdd20eaa1c6ae03ea2"}

  response = requests.request("GET", url, headers=headers, params=querystring)

  return response

@app.route('/webhook/get_chat_messages', methods=['GET'])
def webhook_get_chat_messages():

  device_id = request.json['device_id']
  chat_wid = request.json['chat_wid']

  url = "https://api.wassenger.com/v1/io/"+device_id+"60d5ef39c222dd4fca00bb80""/"+chat_wid+"/sync"

  querystring = {"size":"200"}

  headers = {"Token": "0cea57c569ed0fabba05b08a3ce7c4181661c33d21751beb4e7ced4e44668dcdd20eaa1c6ae03ea2"}

  response = requests.request("GET", url, headers=headers, params=querystring)

  return response.text
#----------------------------webhook-------------------------------final

#///////////////////////users(contacto)///////////////////////////
#obtiene todos los usuarios
@app.route('/user', methods=['GET'])
#@token_required
def get_all_user():

  users= User.query.all()
#crear lista para los datos
  output = []

  for user in users:
    user_data={}
    #user_data['id_agent']=user.id_agent
    user_data['public_id']= user.public_id
    user_data['name']= user.name
    user_data['password']= user.password
    user_data['admin']= user.admin
    output.append(user_data)
  return jsonify({'users': output})

#obtiene un usuario en especifico
@app.route('/user/<public_id>', methods=['GET'])
@token_required
def get_one_user(current_user, public_id):
  if not current_user.admin:
    return jsonify({'mensaje' : 'no puedes acceder a esta funcion'})

  user = User.query.filter_by(public_id=public_id).first()
    
  if not user:
    return jsonify({'mensaje': 'no se encontro el usuario'})
  
  user_data={}
  user_data['public_id']= user.public_id
  user_data['name']= user.name
  user_data['password']= user.password
  user_data['admin']= user.admin
#manda diccionario de datos
  return jsonify({'user': user_data})

#crea un usuario
@app.route('/user', methods=['POST'])
def create_user():
  data = request.get_json()
  hashed_password = generate_password_hash(data['password'], method='sha256')
  new_user = User(public_id=str(uuid.uuid4()),name=data['name'], password=hashed_password, admin=False)
  db.session.add(new_user)
  db.session.commit()
  if User.query.filter_by(id_agent=1).first():
    User.query.filter_by(id_agent=1).update(dict(admin=True))
    db.session.commit()

  return jsonify({'mensaje': 'usuario creado'})

#promover un usuario a admin
@app.route('/user/<public_id>', methods=['PUT'])
def promote_user(public_id):
  user = User.query.filter_by(public_id=public_id).first()
    
  if not user:
    return jsonify({'mensaje': 'no se encontro el usuario'})
  
  user.admin = True
  db.session.commit()
  return jsonify({'mensaje': 'el usuario a sido promovido'})

#eliminar un usuario
@app.route('/user/<public_id>', methods=['DELETE'])
def delete_user(public_id):
  user = User.query.filter_by(public_id=public_id).first()
    
  if not user:
    return jsonify({'mensaje': 'no se encontro el usuario'})
  
  db.session.delete(user)
  db.session.commit()

  return jsonify({'mensaje': 'el usuario a sido eliminado'})

#modificar usuario

# @app.route('/user/<public_id>', methods=['PATCH'])
# def modificar_user(public_id):
#   user = User.query.filter_by(public_id=public_id).first()

#   if not user:
#     return jsonify({'mensaje': 'no se encontro el usuario'})
  


#login
@app.route('/login')
def login():
  auth = request.authorization

  if not auth or not auth.username or not auth.password:
    return make_response('No se pudo verificar', 401, {'WWW-Authenticate' : 'Basic realm="login requerido"'})

  user = User.query.filter_by(name=auth.username).first()

  if not user:
    return make_response('No se pudo verificar', 401, {'WWW-Authenticate' : 'Basic realm="login requerido"'})
  #autenticacion y token con tiempo de expiracion
  if check_password_hash(user.password, auth.password):
    token = jwt.encode({'public_id': user.public_id, 'exp' : datetime.utcnow() + timedelta(minutes=30)}, app.config['SECRET_KEY'])

    return jsonify({'token' : token.decode('UTF-8')})

  return make_response('No se pudo verificar', 401, {'WWW-Authenticate' : 'Basic realm="login requerido"'})

#info
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
#////////////////////////////////cliente////////////////////////////////////////////
@app.route('/cliente', methods=['POST'])
def add_client():
  #name = request.json['name']
  licencia_activa=request.json['licencia_activa']
  licencias=request.json['licencias']
  fecha_compra=request.json['fecha_compra']
  fecha_fin=request.json['fecha_fin']

  #guardo la informacion del cliente en una variable
  new_client= cliente(licencia_activa, licencias, fecha_compra, fecha_fin)

#mando la informcaion a la base de datos
  db.session.add(new_client)
  db.session.commit()

#respuesta del servidor
  return client_schema.jsonify(new_client)


@app.route('/cliente', methods=['GET'])
def get_clients():
  all_clients = cliente.query.all()
  result = clients_schema.dump(all_clients)
  return jsonify(result)
#//////////////////////////////////////////////////////////////////////////////////
#//////////////////////////////Chat////////////////////////////////////////////////

# @app.route("/chats", methods=["GET"])
# def get_chats():

#/////////////////////////templates////////////////////////////////////////////////
@app.route('/template', methods=['POST'])
def add_template():
  template_name = request.json['template_name']
  status = request.json['status']
  messages = request.json['messages']

  new_template = Template_messages(template_name, status, messages)

  db.session.add(new_template)
  db.session.commit()

  return template_schema.jsonify(new_template)

@app.route('/template', methods=['GET'])
def get_template():
  templates = Template_messages.query.all()
  output = []

  for template in templates:
    template_data={}
    template_data['id']= template.id
    template_data['template_name']= template.template_name
    template_data['status']= template.status
    template_data['messages']= template.messages
    output.append(template_data)
  return jsonify({'template': output})

@app.route('/template/<id>', methods=['DELETE'])
def delete_template(id):
  template = Template_messages.query.filter_by(id=id).first()
    
  if not template:
    return jsonify({'mensaje': 'no se encontro el template'})
  
  db.session.delete(template)
  db.session.commit()

  return jsonify({'mensaje': 'el template a sido eliminado'})

@app.route('/template/<id>', methods=['PUT'])
def modificar_template(id):
  template = Template_messages.query.filter_by(id=id).first()
    
  if not template:
    return jsonify({'mensaje': 'no se encontro el template'})
  
  template_name_data = request.json['template_name']
  status_data = request.json['status']
  messages_data = request.json['messages']

  template = Template_messages.query.filter_by(id=id).update(dict(template_name=template_name_data,status=status_data,messages=messages_data))
  db.session.commit()
  return jsonify({'mensaje': 'el template a sido modificado'})

#////////////////////////////////////////////////////////////////////////


if __name__ == "__main__":
    app.run(debug=True)
