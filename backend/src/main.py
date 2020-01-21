from flask import Flask, render_template, url_for, flash, redirect, request
from flask_restful import Resource, Api
from flask_jsonpify import jsonify
import numpy as np
import nibabel as nb
import matplotlib.pyplot as plt
import time
import os
import datetime as dt
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore, initialize_app, db, storage
import random
import tensorflow as tf
import json

app = Flask(__name__)

# temporary data bas for storing images
app.config["UPLOAD_FOLDER"] = "static/"
api = Api(app)

config = credentials.Certificate("jsonconst/key.json")
firebase_admin.initialize_app(config, {
    'storageBucket': 'niiwebsite-794a2.appspot.com',
    'databaseURL' : 'https://niiwebsite-794a2.firebaseio.com/'
})
ref = db.reference('filenames')
#print(ref.get())
#file_ref = base.collection('filenames')
niifiles = storage.bucket()
STANDARD= dt.datetime(2030, month = 12, day = 30)

MODEL_FILE = open(app.config["UPLOAD_FOLDER"] + "model.json")
LOADED_MODEL = MODEL_FILE.read()
MODEL_FILE.close()
# MODEL = tf.keras.models.model_from_json(LOADED_MODEL)
# MODEL.load_weights(app.config["UPLOAD_FOLDER"] + "model.h5")
# MODEL.summary()



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
            #file = open(file, 'rb')
            file.save(app.config["UPLOAD_FOLDER"] + file.filename)
            name = add_file(file.filename, file.filename)
            get_nii(file.filename.replace('/', '~').replace('.', '>'), 'f')
            print(file.filename)
            return redirect(url_for('processnii', filename = file.filename))

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
    #print(nii.generate_signed_url(STANDARD))
    print(ref.get())
    return ref.get()


@app.route('/get_nii/<namedb>/<show>')
def get_nii(namedb, show):
    print("file", namedb)
    file = ref.child(namedb).get()
    fileblob = niifiles.get_blob(file['name'])
    urlhold = file['url']
    print(fileblob)
    print(urlhold)
    #with open(app.config["UPLOAD_FOLDER"] + file['name'], 'wb') as file:
    fileblob.download_to_filename(app.config["UPLOAD_FOLDER"] + file['name'])
    fileblob.delete()
    ref.child(namedb).delete()
    if show == 't':
        return render_template('imgshow.html', url = urlhold)
    else:
        pass

@app.route('/processnii/<filename>')
def processnii(filename):
    nii = nb.load(app.config["UPLOAD_FOLDER"] + filename)
    niidata = nb.Nifti1Image(nii.dataobj, nii.affine)
    npaffine = nii.affine
    shift = 0#20
    bshift = 0#75

    volume = niidata.get_fdata()
    volume = np.transpose(volume, (0,2,1))

    data_in = np.zeros((256 - (shift + bshift), 256, 192), dtype = np.float16)
    counter = 0

    for i in range(shift, volume.shape[2] - bshift):
        h2 = volume[:, :, i]

        if np.max(h2) > 0:
            h2 = h2/np.max(h2)
        else:
            h2 = h2 * 0

        data_in[counter, :, :] = np.expand_dims(h2, axis = 0)
        counter += 1
    h2 = None
    img = None

    basename = filename.replace('/', '~').replace('.', '>')
    img = basename + "_slice.png"
    affinefile = basename + '_affine'
    datafile = basename + '_data'

    plt.imsave(app.config["UPLOAD_FOLDER"] + img, data_in[random.randint(0, volume.shape[2] - 1), :,:])
    np.save(app.config["UPLOAD_FOLDER"] + affinefile, npaffine)
    np.save(app.config["UPLOAD_FOLDER"] + datafile, data_in)

    # remove of file from server
    os.remove(app.config["UPLOAD_FOLDER"] + filename)

    #add all files
    add_file(img, img, nchildname=basename)
    add_file(affinefile + ".npy", affinefile + ".npy", nchildname=basename)
    add_file(datafile + ".npy", datafile + ".npy", nchildname=basename)

    open = (img.replace('/', '~').replace('.', '>'))

    #return jsonify({basename : ref.child(basename).get()})#redirect(url_for('get_file', namedb = open, show = 't'))
    #return json.dumps({basename: ref.child(basename).get()})
    #return redirect(url_for('tfmaskproduce', basename = {basename: ref.child(basename).get()}))
    return redirect(url_for('tfmaskproduce', basename=basename))

@app.route('/tfmaskproduce/<basename>')
def tfmaskproduce(basename):
#     MODEL_FILE = open(app.config["UPLOAD_FOLDER"] + "model.json")
#     LOADED_MODEL = MODEL_FILE.read()
#     MODEL_FILE.close()
#     MODEL = tf.keras.models.model_from_json(LOADED_MODEL)
#     MODEL.load_weights(app.config["UPLOAD_FOLDER"] + "model.h5")
#     MODEL.summary()
    MODEL = tf.keras.models.model_from_json(LOADED_MODEL)
    MODEL.load_weights(app.config["UPLOAD_FOLDER"] + "model.h5")
    MODEL.summary()
    filref = ref.child(basename)
    print(type(filref.get()))
    frefdat = filref.get()
    flist = list(frefdat.keys())
    data = None
    dblob = None
    affine = None
    ablob = None
    slice = None
    sblob = None
    for file in flist:
        if "data" in file:
            data = frefdat[file]['name']
            filref.child(file).delete()
        elif "affine" in file:
            affine = frefdat[file]['name']
            filref.child(file).delete()
        elif "slice" in file:
            slice = frefdat[file]['name']
            filref.child(file).delete()

    dblob = niifiles.get_blob(data)
    dblob.download_to_filename(app.config["UPLOAD_FOLDER"] + data)
    dblob.delete()
    dblob = None
    data = np.load(app.config["UPLOAD_FOLDER"] + data)

    ablob = niifiles.get_blob(affine)
    ablob.download_to_filename(app.config["UPLOAD_FOLDER"] + affine)
    ablob.delete()
    ablob = None
    affine = np.load(app.config["UPLOAD_FOLDER"] + affine)

    sblob = niifiles.get_blob(slice)
    sblob.download_to_filename(app.config["UPLOAD_FOLDER"] + slice)
    sblob = None
    #slice = plt.imread(app.config["UPLOAD_FOLDER"] + data)
    predictions = MODEL.predict(np.expand_dims(data, axis = -1))
    print(predictions.shape)


    return 'done'

if __name__ == '__main__':
    app.run(debug = True)
