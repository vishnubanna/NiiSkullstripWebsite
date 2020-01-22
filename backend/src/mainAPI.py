from flask import Flask, render_template, url_for, flash, redirect, request
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
#####ERROR  ##### FIX !!!!!! FAILS IF THERE ARE 2 FILES WITH THW SAME NAME
app = Flask(__name__)
# implement error checking
# temporary data bas for storing images
app.config["UPLOAD_FOLDER"] = "static/"
api = Api(app)

config = credentials.Certificate("jsonconst/key.json")
firebase_admin.initialize_app(config, {
    'storageBucket': 'niiwebsite-794a2.appspot.com',
    'databaseURL' : 'https://niiwebsite-794a2.firebaseio.com/'
})

ref = db.reference('filenames')
niifiles = storage.bucket()
STANDARD= dt.datetime(2030, month = 12, day = 30)

MODEL_FILE = open("jsonconst/model.json")
LOADED_MODEL = MODEL_FILE.read()
MODEL_FILE.close()
MODEL = None

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

def get_nii(namedb, show): #post
    print("file", namedb)
    file = ref.child(namedb).get()
    print("ref",file)
    fileblob = niifiles.get_blob(file['name'])
    urlhold = file['url']
    print(fileblob)
    print(urlhold)
    fileblob.download_to_filename(app.config["UPLOAD_FOLDER"] + file['name'])
    fileblob.delete()
    ref.child(namedb).delete()
    if show == 't':
        return render_template('imgshow.html', url = urlhold)
    else:
        pass

def getnames(filename):
    basename = filename.replace('/', '~').replace('.', '>')
    files = ref.child(basename)
    vals = files.get()
    flist = list(vals.keys())
    return flist


class processMask(Resource):
    def post(self):
        pass

    def get(self, filename):
        basename = filename.replace('/', '~').replace('.', '>')

        gpus = tf.config.experimental.list_physical_devices('GPU')
        if len(gpus) != 0:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
        MODEL = tf.keras.models.model_from_json(LOADED_MODEL)
        # MODEL.load_weights(app.config["UPLOAD_FOLDER"] + "model.h5")
        MODEL.load_weights("jsonconst/model.h5")
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

        dblob = niifiles.get_blob(data)
        dblob.download_to_filename(app.config["UPLOAD_FOLDER"] + data)
        dblob.delete()
        dblob = None
        dblob = np.load(app.config["UPLOAD_FOLDER"] + data)

        ablob = niifiles.get_blob(affine)
        ablob.download_to_filename(app.config["UPLOAD_FOLDER"] + affine)
        ablob.delete()
        ablob = None
        ablob = np.load(app.config["UPLOAD_FOLDER"] + affine)

        predictions = np.squeeze(MODEL.predict(np.expand_dims(dblob, axis=-1)), axis=-1)
        print(predictions.shape)

        nfilename = basename + "_mask.nii.gz"
        img = basename + "_sliceog.png"
        tpose = (1, 0, 2)
        dbolb = np.transpose(dblob, tpose)
        predictions = np.transpose(predictions * dblob, tpose)
        plt.imsave(app.config["UPLOAD_FOLDER"] + img, predictions[90, :, :])
        niinew = nb.Nifti1Image(predictions, ablob)
        nb.save(niinew, app.config["UPLOAD_FOLDER"] + nfilename)

        os.remove(app.config["UPLOAD_FOLDER"] + data)
        os.remove(app.config["UPLOAD_FOLDER"] + affine)

        add_file(img, img, nchildname=basename)
        add_file(nfilename, nfilename, nchildname=basename)
        return filref.get()#{basename: filref.get()}

    def put(self, filename):
        basename = filename.replace('/', '~').replace('.', '>')
        get_nii(basename, 'f')
        nii = nb.load(app.config["UPLOAD_FOLDER"] + filename)
        niidata = nb.Nifti1Image(nii.dataobj, nii.affine)
        npaffine = nii.affine
        shift = 0  # 20
        bshift = 0  # 75
        img = None

        volume = niidata.get_fdata()
        img = basename + "_slice.png"
        plt.imsave(app.config["UPLOAD_FOLDER"] + img, volume[90, :, :])

        volume = np.transpose(volume, (0, 2, 1))
        data_in = np.zeros((256 - (shift + bshift), 256, 192), dtype=np.float16)
        counter = 0

        for i in range(shift, volume.shape[2] - bshift):
            h2 = volume[:, :, i]

            if np.max(h2) > 0:
                h2 = h2 / np.max(h2)
            else:
                h2 = h2 * 0

            data_in[counter, :, :] = np.expand_dims(h2, axis=0)
            counter += 1
        h2 = None

        affinefile = basename + '_affine'
        datafile = basename + '_data'

        np.save(app.config["UPLOAD_FOLDER"] + affinefile, npaffine)
        np.save(app.config["UPLOAD_FOLDER"] + datafile, data_in)

        # remove of file from server
        os.remove(app.config["UPLOAD_FOLDER"] + filename)

        # add all files
        add_file(img, img, nchildname=basename)
        add_file(affinefile + ".npy", affinefile + ".npy", nchildname=basename)
        add_file(datafile + ".npy", datafile + ".npy", nchildname=basename)

        open = (img.replace('/', '~').replace('.', '>'))
        return ref.child(basename).get()  # redirect(url_for('tfmaskproduce', filename=filename))

    def delete(self, filename):
        basename = filename.replace('/', '~').replace('.', '>')
        files = ref.child(basename)
        vals = files.get()
        flist = list(vals.keys())
        hold = None

        for file in flist:
            hold = niifiles.get_blob(vals[file]["name"])
            hold.delete()
        files.delete()
        return "done"

api.add_resource(processMask, "/getmask/<filename>")

if __name__ == '__main__':
    app.run(debug = True)
