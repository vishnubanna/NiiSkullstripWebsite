from flask import Flask, render_template, url_for, flash, redirect, request
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
from flask_jsonpify import jsonify
import numpy as np
import nibabel as nb
import matplotlib.pyplot as plt

import json


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///entities/data.db' # temporary data bas for storing images
app.config["UPLOAD_FOLDER"] = "static/"

api = Api(app)
db = SQLAlchemy(app)

class FileStorage(db.Model):
    __tablename__ = "FileStorage"
    id = db.Column(db.Integer, primary_key = True)
    filename = db.Column(db.String(300))
    data = db.Column(db.LargeBinary)

class FileAdded(Resource):
    def get(self):
        item = FileStorage.query.first()
        FileStorage.query.delete()
        db.session.commit()
        if item != None:
            vals = vars(item)
            print(vals.keys())
            del vals[list(vals.keys())[0]]
            print(vals.keys())
            for key in vals.keys():
                vals[key] = str(vals[key])
            return json.dumps({"FileStorage": str(vals)})
        else:
            return "{None}"

api.add_resource(FileAdded, '/files')

@app.route('/')
def index():
    FileStorage.query.delete()
    db.session.commit()
    return render_template('base.html', title = "Home")

@app.route('/getimg', methods = ['POST', 'GET']) # if the function has inputs
def getimg():
    if (request.method == 'POST'):
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        print("file: ",file.filename)
        if file.filename == '':
            flash("no file selected")
            return redirect(request.url)
        if file:
            newFile = FileStorage(filename = file.filename, data = file.read())
            db.session.add(newFile)
            db.session.commit()
            return redirect(url_for('download', filename = file.filename))#file.filename

#generates json for data
@app.route('/download/<filename>')
def download(filename):
    item = FileStorage.query.first()
    if item != None:
        # may need to delete
        #FileStorage.query.delete()
        #db.session.commit()
        with open(app.config["UPLOAD_FOLDER"] + item.filename, 'wb') as file:
            file.write(item.data)
        return redirect(url_for('fileadded'))
    else:
        # may need to delete
        FileStorage.query.delete()
        db.session.commit()
        return render_template('base.html', title = "Home")



if __name__ == '__main__':
    app.run(debug = True)
