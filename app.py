import sqlite3
from flask import Flask, request, abort, render_template, url_for
import os.path

app = Flask(__name__)

# Handles routing to the home page
@app.route("/")
@app.route("/index")
def index():
    return render_template('location.html'), 200

# Handles location send requests
@app.route('/send_location', methods=['POST'])
def send():
    data = request.form # This will have all location/user data
    print(data)
    # TODO: Validate data and send to the database
    return render_template('location.html')

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
    app.run(debug=True,host='localhost') # Use 'localhost' for testing because it is "trusted" and therefore has access to location data