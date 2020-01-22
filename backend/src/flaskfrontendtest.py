from flask import Flask, render_template, url_for, flash, redirect, request, get_template_attribute, send_from_directory
from flask_restful import Resource, Api, reqparse
from flask_jsonpify import jsonify
import requests
import numpy as np
import nibabel as nb
import matplotlib.pyplot as plt
import os
import datetime as dt
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore, initialize_app, db, storage
import tensorflow as tf

## turn into a class based api with methods get post put etc.

app = Flask(__name__)

# temporary data bas for storing images
app.config["UPLOAD_FOLDER"] = "static/"
app.config["TEMPLATES_AUTO_RELOAD"] = True
api = Api(app)

config = credentials.Certificate("jsonconst/key.json")
firebase_admin.initialize_app(config, {
    'storageBucket': 'niiwebsite-794a2.appspot.com',
    'databaseURL' : 'https://niiwebsite-794a2.firebaseio.com/'
})

ref = db.reference('filenames')
niifiles = storage.bucket()
STANDARD= dt.datetime(2030, month = 12, day = 30)
backendurl = "http://127.0.0.1:5000/getmask/"
MODEL_FILE = open("jsonconst/model.json")
LOADED_MODEL = MODEL_FILE.read()
MODEL_FILE.close()
MODEL = None

@app.route('/')
def index():
    ref.delete()
    files = niifiles.list_blobs()
    niifiles.delete_blobs(files)
    return render_template('base.html')

@app.route('/getimg', methods = ['POST', 'GET'])
def getimg():
    if request.method == 'POST':
        file = request.files['file']
        if file == None:
            return redirect(url_for('index'))
        elif file == '':
            return redirect(url_for('index'))
        else:
            file.save(app.config["UPLOAD_FOLDER"] + file.filename)
            print(file.filename)
            name = add_file(file.filename, file.filename)
            # keys = requests.put(backendurl + file.filename)
            # keys =  keys.json()
            # url = None
            # for key in keys.keys():
            #     if "slice" in key:
            #         url = keys[key]['url']
            # dimg = get_template_attribute("base.html", "geturl1")
            # dimg(url)
            #
            # keys = requests.get(backendurl + file.filename)
            # keys = keys.json()
            # url2 = None
            # file2 = None
            # for key in keys.keys():
            #     if "sliceog" in key:
            #         url2 = keys[key]['url']
            #     elif "mask" in key:
            #         file2 = key
            # dimg = get_template_attribute("base.html", "geturl2")
            # dimg(url2)
            # return "done"
            #redirect(url_for('processnii', filename = file.filename))
            return redirect(url_for('load_img1', filename = file.filename))

@app.route('/load_img1/<filename>')
def load_img1(filename):
    keys = requests.put(backendurl + filename)
    keys = keys.json()
    url = None
    for key in keys.keys():
        if "slice" in key:
            url = keys[key]['url']
    dimg = get_template_attribute("base.html", "geturl1")

    keys = requests.get(backendurl + filename)
    keys = keys.json()
    url2 = None
    file2 = None
    for key in keys.keys():
        if "sliceog" in key:
            url2 = keys[key]['url']
        elif "mask" in key:
            file2 = key
    dimg = get_template_attribute("base.html", "geturl2")
    dimg(url2)

    fin = niifiles.get_blob(keys[file2]['name'])
    fin.download_to_filename(app.config["UPLOAD_FOLDER"] + keys[file2]['name'])
    #return send_from_directory(directory = app.config["UPLOAD_FOLDER"], filename=keys[file2]['name'])

    os.remove(app.config["UPLOAD_FOLDER"] + keys[file2]['name'])
    keyfil = requests.delete(backendurl + filename)
    return render_template("base.html", urlslice = url, urlslice1 = url2)#, send_from_directory(directory = app.config["UPLOAD_FOLDER"], filename=keys[file2]['name'])



def add_file(namedb, name, nchildname = None, delete = 't'):
    nii = niifiles.blob(namedb)
    with open(app.config["UPLOAD_FOLDER"] + name, 'rb') as file:
        nii.upload_from_file(file)
    if delete == 't':
        os.remove(app.config["UPLOAD_FOLDER"] + name)
    if nchildname == None:
        file_ref = ref.child(namedb.replace('/', '~').replace('.', '>'))
        file_ref.set({'name': namedb, 'url' : nii.generate_signed_url(STANDARD)})
    else:
        file_ref = ref.child(nchildname).child(namedb.replace('/', '~').replace('.', '>'))
        file_ref.set({'name': namedb, 'url': nii.generate_signed_url(STANDARD)})
    print(ref.get())
    return ref.get()

if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.run(debug = True, port=5002)
