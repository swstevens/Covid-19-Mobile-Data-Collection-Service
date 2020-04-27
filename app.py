import uuid

import MySQLdb.cursors
from flask import Flask, request, Response
from flask import redirect, flash
from flask import render_template, url_for
from flask_login import LoginManager
from flask_login import UserMixin
from flask_login import current_user, login_required
from flask_login import logout_user, login_user
from flask_wtf.form import FlaskForm
from itsdangerous import (TimedJSONWebSignatureSerializer \
                              as Serializer, BadSignature, \
                          SignatureExpired)
import csv
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from wtforms import PasswordField, BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired
from datetime import *

app = Flask(__name__)

app.secret_key = 'abc'
class DB: # https://stackoverflow.com/questions/207981/how-to-enable-mysql-client-auto-re-connect-with-mysqldb
    def __init__(self):
        conn = None

    def connect(self):
        self.conn = MySQLdb.connect(port=3548,
                     host='ix-dev.cs.uoregon.edu',
                     user='cis422-group7',
                     password='Group7',
                     db='project_1',
                     charset='utf8')

    def query(self, sql):
        self.conn.ping(True)
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
        except (AttributeError, MySQLdb.OperationalError):
            self.connect()
            cursor = self.conn.cursor()
            cursor.execute(sql)
        return cursor

    def get(self, sql):
        results = None
        try:
            self.conn.query(sql)
            if self.conn:
                r = self.conn.store_result()
                results = r.fetch_row(maxrows=0)
        except (AttributeError, MySQLdb.OperationalError):
            self.connect()
            self.conn.query(sql)
            if self.conn:
                r = self.conn.store_result()
                results = r.fetch_row(maxrows=0)
        return results



db = DB()
db.connect() 

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
userObjects = {}


# Handles routing to the home page
@app.route("/")
@app.route("/index")
@login_required
def index():
    return render_template('location.html'), 200

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def create_user(usr, pas, uid=None):
    if not uid:
        uid = uuid.uuid4()
    user = User([usr, pas, uid])
    userObjects[uid] = user
    return user

def get_user(usr):
    for user in userObjects.values():
        if user.username == usr:
            return user
    return None


class User(UserMixin):
    def __init__(self, user):
        self.username = user[0]
        self.password = user[1]
        self.id = user[2]

    def verify_password(self, password):
        if self.password is None:
            return False
        return check_password_hash(self.password, password)

    def get_id(self):
        return self.id


@login_manager.user_loader
def load_user(user_id):
    if user_id not in userObjects:
        return None
    return userObjects[user_id]


class LoginForm(FlaskForm):
    username = StringField('user', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('log in')


class RegistrationForm(FlaskForm):
    username = StringField('user', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')


class DisplayForm(FlaskForm):
    username = StringField('user', validators=[DataRequired()])


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
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = get_user(username)

        if user:
            if user.verify_password(password):
                login_user(user)
                return render_template('location.html', form=form, username=username)
            else:
                emsg = "Error: Password incorrect."
                flash(emsg)
                return render_template('login.html', form=form, msg=emsg)
        else:
            emsg = "No user found. Please regiser if you have not."
            return render_template('login.html', form=form, msg=emsg)
    else:
        return render_template('login.html', form=form)


@app.route('/register', methods=('GET', 'POST'))
def register():
    # store id with random index numbe
    form = RegistrationForm()
    if form.validate_on_submit():
        # Login and validate the user.
        # User should be an instance of your 'User' class
        username = form.username.data
        password = form.password.data

        if get_user(username):
            emsg = "That username is taken. Try another one."
            return render_template('register.html', form=form, msg=emsg), 400
        else:
            newUser = create_user(username, generate_password_hash(password))
            sql = "INSERT INTO user_id VALUES ('%s', '%s', '%s')" % (newUser.id, username, newUser.password)
            db.query(sql)
            emsg = "You have successfully registered! You may now log in."
            return render_template('login.html', form=form, msg=emsg), 200
    else:
        return render_template('register.html', form=form)


# Handles location send requests
@app.route('/send_location', methods=['POST'])
@login_required
def send():
    data = request.form.to_dict(flat=False)
    sql = "SELECT latitude, longitude, date, time FROM user_info WHERE user_id LIKE '%s';" % (current_user.username)
    results = db.get(sql)
    past = results[-1]

    if data.get('lat') is not None and data.get('lng') is not None:
        u_id = current_user.username
        date = data.get('date')[0]
        time = data.get('time')[0]
        lati = data.get('lat')[0]
        longi = data.get('lng')[0]

        #print(past)
        #print(format(past[0], '.6f'))
        #print(data.get('lat')[0])
        #print(format(past[0], '.6f') == format(float(data.get('lat')[0]), '.6f'))
        #print(past[0] == format(float(data.get('lat')[0]), '.7f'))
        if format(past[0], '.6f') == format(float(lati), '.6f') and format(past[1], '.6f') == format(float(longi), '.6f'):
            inter_time = time[0:2]+time[3:5] + time[6:8]
            #print("inter: ", inter_time)
            data_dt = datetime.strptime(inter_time, '%H%M%S').time()
            #print(data_dt)
            #print(past[3])
            past_time = (datetime.min + past[3]).time()
            difference = datetime.combine(datetime.today(), data_dt) - datetime.combine(datetime.today(), past_time)
            #print(difference)
            # difference is the time form of data's time
            # past[3] is a deltatime
            # time_at needs to be int(past[4]) + difference - past[3]

            time_at = int(past[4]) + (difference.total_seconds() % 3600)//60 # make it a difference between date's time and past's time
            TSI = time_at//5 * 5
        else:
            time_at = 0
            TSI = 0
        sql = "INSERT INTO user_info(`user_id`, \
                      `date`, `time`, `latitude`, `longitude`, `time_at_location`, `temporal_sampling_interval`) \
                      VALUES ('%s', '%s',  '%s',  '%s', '%s', '%s', '%s')" % \
              (u_id, date, time, lati, longi, time_at, TSI)
        print(time_at)
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
    sql = "SELECT * FROM user_id"
    results = db.get(sql)
    for user in results:
        create_user(user[1], user[2], user[0])

    app.run(debug=True)  # Use 'localhost' for testing because it is "trusted" and therefore has access to location data
