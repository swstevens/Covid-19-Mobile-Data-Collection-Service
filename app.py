import uuid

import MySQLdb.cursors
from flask import Flask, request, Response
from flask import redirect, flash
from flask import render_template, url_for
from flask_login import LoginManager
from flask_login import UserMixin
from flask_login import current_user, login_required
from flask_login import logout_user
from flask_wtf.form import FlaskForm
from itsdangerous import (TimedJSONWebSignatureSerializer \
                              as Serializer, BadSignature, \
                          SignatureExpired)
import csv
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from wtforms import PasswordField, BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)

app.secret_key = 'abc'
class DB:
    def __init__(self):
        conn = None

    def connect(self):
        self.conn = MySQLdb.connect(port=3548,
                     host='ix-dev.cs.uoregon.edu',
                     user='a',
                     password='a',
                     db='project_1',
                     charset='utf8')

    def query(self, sql):
        self.conn.ping(True)
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
        except (AttributeError, MySQLdb.OperationalError):
            self.connect(port=3548,
                     host='ix-dev.cs.uoregon.edu',
                     user='a',
                     password='a',
                     db='project_1',
                     charset='utf8')
            cursor = self.conn.cursor()
            cursor.execute(sql)
        return cursor

    def get(self, sql):
        try:
            self.conn.query(sql)
            r=self.conn.store_result()
            results = r.fetch_row(maxrows=0)
        except (AttributeError, MySQLdb.OperationalError):
            self.connect(port=3018,
                     host='ix-dev.cs.uoregon.edu',
                     user='a',
                     password='a',
                     db='project_1',
                     charset='utf8')
            self.conn.query(sql)
            r=self.conn.store_result()
            results = r.fetch_row(maxrows=0)
        return results



db = DB()
db.connect()
# db = MySQLdb.connect(port=3018,
#                      host='ix-dev.cs.uoregon.edu',
#                      user='a',
#                      password='a',
#                      db='project_1',
#                      charset='utf8')
# cursor = db.cursor()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

global gl_username
global gl_id


# Handles routing to the home page
@app.route("/")
@app.route("/index")
@login_required
def index():
    return render_template('location.html', username=current_user.username), 200


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


USERS = [
    {
        "id": 1,
        "name": 'lily',
        "password": generate_password_hash('123')
    },
    {
        "id": 2,
        "name": 'tom',
        "password": generate_password_hash('123')
    }
]


def create_user(user_name, password):
    user = {
        "name": user_name,
        "password": generate_password_hash(password),
        "id": uuid.uuid4()
    }
    USERS.append(user)


def get_user(user_name):
    for user in USERS:
        if user.get("name") == user_name:
            return user
    return None


class User(UserMixin):
    def __init__(self, user):
        self.username = user.get("name")
        self.password_hash = user.get("password")
        self.id = user.get("id")

    def verify_password(self, password):
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.id

    @staticmethod
    def get(user_id):
        if not user_id:
            return None
        for user in USERS:
            if user.get('id') == user_id:
                return User(user)
        return None


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


class LoginForm(FlaskForm):
    username = StringField('user', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('log in')


class RegistrationForm(FlaskForm):
    username = StringField('user', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])


class DisplayForm(FlaskForm):
    username = StringField('user', validators=[DataRequired()])

def generate_auth_token(id, expiration=600):
    s = Serializer(app.secret_key, expires_in=expiration)
    token = s.dumps({'id': id})
    return {'token': token, 'duration': expiration}


def verify_auth_token(token):
    s = Serializer(app.secret_key)
    try:
        data = s.loads(token)
    except SignatureExpired:
        return None
    except BadSignature:
        return None
    return "Success"


@app.route('/display/', methods=('GET', 'POST'))
def display():
    form = DisplayForm()
    if form.validate_on_submit():
        username = form.username.data
        #TODO: lower() username
        print("Getting location data for: ", username)

        sql = "SELECT latitude, longitude, date, time FROM user_info WHERE user_id LIKE '%s';" % (username)
        results = db.get(sql)
        if results:
            csvList = ["lat,lng,name,color,note"]
            for entry in results:
                csvList.append(",".join(map(str,[entry[0], entry[1], '', "ff0000", ' '.join(map(str,entry[2:]))])))
            csv = "\n".join(csvList)
            return Response(
                csv,
                mimetype="text/csv",
                headers={"Content-disposition":
                         "attachment; filename=locations.csv"})
        else:
            emsg = "No user found. please regiser"
            return render_template('login.html', msg=emsg)

    return render_template('display.html', form=form)


@app.route('/login/', methods=('GET', 'POST'))
def login():
    form = LoginForm()
    emsg = None
    global gl_username
    global gl_id
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        gl_username = username
        # user_id: uuid.uuid4()
        # user_info = get_user(user_name)

        sql = "SELECT * FROM `user_id` \
                WHERE `user_name` = '%s'" % (username)
        c = db.query(sql)
        results = c.fetchone()

        if results:
            check_id = results[0]
            check_name = results[1]
            check_pass = results[2]
            if password == check_pass:
                gl_id = check_id
                return render_template('location.html', form=form, username=check_name)
            else:
                emsg = "error password or username"
                flash(emsg)
                return render_template('login.html', form=form, msg=emsg)
        else:
            emsg = "no user found please regiser"
            return render_template('login.html', msg=emsg)
    else:
        return render_template('login.html', form=form)

    #     if user_info is None:
    #         emsg = "error password or username"
    #     else:
    #         user = User(user_info)
    #         if user.verify_password(password):
    #             login_user(user)
    #             return render_template('location.html',form=form, username = current_user.username)
    #         else:
    #             emsg = "error password or username"
    # return render_template('login.html', form=form, emsg=emsg)


@app.route('/register', methods=('GET', 'POST'))
def register():
    # store id with random index numbe
    form = RegistrationForm()
    if form.validate_on_submit():
        # Login and validate the user.
        # user should be an instance of your `User` class
        username = form.username.data
        password = form.password.data

        sql = "SELECT * FROM `user_id` \
                WHERE `user_name` = '%s'" % (username)
        c = db.query(sql)
        results = c.fetchone()

        if results:
            emsg = "That username is taken. Try another one."
            return render_template('register.html', form=form, msg=emsg), 400
        else:
            userid = uuid.uuid4()
            sql1 = "INSERT INTO `user_id`(`user_id`, \
                `user_name`, `user_wd`) \
                VALUES ('%s', '%s', '%s')" % \
                   (userid, username, password)
            db.query(sql)
            emsg = "You have successfully registered! You may now log in."
            return render_template('login.html', form=form, msg=emsg), 400
    else:
        return render_template('register.html', form=form)



# Handles location send requests
@app.route('/send_location', methods=['POST'])
def send():
    global gl_id
    data = request.form.to_dict(flat=False)
    username = 'hello'

    sql = "SELECT latitude, longitude, date, time FROM user_info WHERE user_id LIKE '%s';" % (username)
    results = db.get(sql)

    if data.get('lat') is not None and data.get('lng') is not None:
        u_id = gl_username
        date = data.get('date')[0]
        time = data.get('time')[0]
        lati = data.get('lat')[0]
        longi = data.get('lng')[0]
        time_at = "1000000000"
        sql = "INSERT INTO user_info(`user_id`, \
                      `date`, `time`, `latitude`, `longitude`, `time_at_location`) \
                      VALUES ('%s', '%s',  '%s',  '%s', '%s', '%s')" % \
              (u_id, date, time, lati, longi, time_at)

        db.query(sql)

    return render_template('location.html'), 200


# Error handling routing
@app.errorhandler(404)
def error_404(error):
    return render_template('404.html'), 404


@app.errorhandler(403)
def error_403(error):
    return render_template('403.html'), 403


@app.errorhandler(401)
def error_401(error):
    return render_template('401.html'), 401


@app.errorhandler(400)
def error_400(error):
    return render_template('400.html'), 400


if __name__ == "__main__":
    app.run(debug=True)  # Use 'localhost' for testing because it is "trusted" and therefore has access to location data
