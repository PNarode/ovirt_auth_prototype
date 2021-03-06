from flask import Flask
from flask import session, request
from flask import make_response, redirect
from flask import jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from ovirtsdk4 import AuthError
import logging
import ovirtsdk4 as sdk
import ovirtsdk4.types as types

logging.basicConfig(level=logging.DEBUG, filename='example.log')
app = Flask(__name__)
app.secret_key = 'api_wrapper'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), unique=False, nullable=False)
    token = db.Column(db.String(120), unique=True)

# Create the connection to the server:
def create_conn(user, password):
    connection = sdk.Connection(
        url='https://ns547432.ip-66-70-177.net/ovirt-engine/api',
        username=user,
        password=password,
        debug=True,
        log=logging.getLogger(),
    )
    try:
        token = connection.authenticate()
        print "User Authenticated"
        session["id"] = token
        cred = User.query.filter_by(username=user).first()
        if cred is None:
            item = User(
                username= user,
                password= password,
                token= token
            )
        else:
            item = User.query.filter_by(username=user).first()
            item.token = token
        db.session.add(item)
        db.session.commit()
    except AuthError as e:
        print e.message
        abort(401, e.message)
 
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.errorhandler(401)
def unauthorized(error):
    session.clear()
    return make_response(jsonify({'error': str(error)}), 401)

def current_user():
    if "id" in session:
        token = session['id'] #= request.cookies.get('token')
        print token
        return token
    return None

@app.before_request
def require_authorization():
    print "Before request"
    if not current_user():
        if "user" in request.headers:
            user = request.headers["user"]
        else:
            user = None
        if "password" in request.headers:
            password = request.headers["password"]
        else:
            password = None
        if (not user) and (not password):
            msg = 'UnAuthorized User. Please Pass Username and Password for authorization in the request header'
            abort(401, msg)
        else:
            create_conn(user, password)

@app.route('/list_vm', methods=('GET', 'POST'))
def list_vm():
    while True:
        token = session["id"]
        # Get the reference to the "vms" service:
        connection = sdk.Connection(
                            url='https://ns547432.ip-66-70-177.net/ovirt-engine/api',
                            token=token
                        )
        try:
            vms_service = connection.system_service().vms_service()
            # Use the "list" method of the "vms" service to list all the virtual machines of the system:
            vms = vms_service.list()
            data = [{'name': vm.name, 'id': vm.id} for vm in vms]

            resp = make_response(jsonify(data))
            break
        except AuthError as e:
            cred = User.query.filter_by(token=token).first()
            if cred is None:
                abort(401,e.message)
                break
            else:
                create_conn(cred.username, cred.password)
    #resp.set_cookie('token', token)
    connection.close()
    return resp

@app.route('/list_host', methods=('GET', 'POST'))
def list_host():
    while True:
        token = session["id"]
        # Get the reference to the "vms" service:
        connection = sdk.Connection(
                            url='https://ns547432.ip-66-70-177.net/ovirt-engine/api',
                            token=token
                        )
        try:
            host_service = connection.system_service().hosts_service()
            hosts = host_service.list()
            data = [{'name': host.name, 'id': host.id} for host in hosts]
        
            resp = make_response(jsonify(data))
            break
        except AuthError as e:
            cred = User.query.filter_by(token=token).first()
            if cred is None:
                abort(401,e.message)
                break
            else:
                create_conn(cred.username, cred.password)
        #resp.set_cookie('token', token)
    connection.close()
    return resp

if __name__ == '__main__':
    db.create_all()
    app.run()