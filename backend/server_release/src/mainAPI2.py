from flask import Flask, render_template, url_for, flash, redirect, request, abort,jsonify,make_response
from flask_restful import Resource, Api, reqparse
from flask_restful.utils import cors
from flask_cors import CORS, cross_origin
#from flask_jsonpify import jsonify
import json
import requests
import numpy as np
import nibabel as nb
import matplotlib.pyplot as plt
import os
import datetime as dt
import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin import firestore, initialize_app, db, storage
import tensorflow as tf


app = Flask(__name__)
CORS(app) 
app.config["UPLOAD_FOLDER"] = "static/"
api = Api(app)

config = credentials.Certificate("jsonconst/key.json")
fireapp = firebase_admin.initialize_app(config, {
    'storageBucket': 'niiwebsite-794a2.appspot.com',
    'databaseURL' : 'https://niiwebsite-794a2.firebaseio.com/',
    'databaseAuthVariableOverride': {
        'uid': 'my-service-worker'
    }
})

print(fireapp.name)
print("72k4w4lp90")

ref = db.reference('filenames')
niifiles = storage.bucket()
STANDARD= dt.datetime(2030, month = 12, day = 30)

MODEL_FILE = open("jsonconst/model.json")
LOADED_MODEL = MODEL_FILE.read()
MODEL_FILE.close()
MODEL = None

ALLOWED_EXTENSIONS = {'nii', 'nii.gz'}


# gpus = tf.config.experimental.list_physical_devices('GPU')
# if len(gpus) != 0:
#     for gpu in gpus:
#         tf.config.experimental.set_memory_growth(gpu, True)
#
# MODEL = tf.keras.models.model_from_json(LOADED_MODEL)
# # MODEL.load_weights(app.config["UPLOAD_FOLDER"] + "model.h5")
# MODEL.load_weights("jsonconst/model.h5")
# MODEL.summary()

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

def valid_load(filename):
    try:
        nii = nb.load(app.config["UPLOAD_FOLDER"] + filename)
        return nii, 'nii'
    except:
        try:
            os.remove(app.config["UPLOAD_FOLDER"] + filename)
        except:
            print(f"{filename} non existent")
        return None, None

    

class processMask(Resource):
    # @cross_origin()
    @cors.crossdomain(origin='*')
    def options(self, filename):
        return {'Allow': 'GET,POST,DELETE'}, 200, {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,POST,DELETE'}

    @cors.crossdomain(origin='*', methods = 'GET, POST, DELETE')
    def post(self, filename):
        tfilename = None
        if "/" in filename:
            abort(400, "no subdirectories allowed")
        print(request.files['file'])
        file = request.files['file']
        if file.filename == '':
            abort(400, "no file selected")

        tfilename = filename
        basename = file.filename.replace('/', '~').replace('.', '>')
        count = 0

        while ref.child(basename).get() != None:
            flistrep = tfilename.split('.')
            count += 1
            flistrep[0] = flistrep[0] + str(count)
            tfilename = ".".join(flistrep)
            basename = tfilename.replace('/', '~').replace('.', '>')

        if file:
            file.save(app.config["UPLOAD_FOLDER"] + tfilename)

        file, type = valid_load(tfilename)

        if (file == None):
            abort(400, "invalid file type")
        elif (file != None and type == "nii"):
            niidata = nb.Nifti1Image(file.dataobj, file.affine)
            npaffine = file.affine
        
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
        try:
            os.remove(app.config["UPLOAD_FOLDER"] + tfilename)
        except:
            print(f"{tfilename} non existent")

        # add all files
        add_file(img, img, nchildname=basename)
        add_file(affinefile + ".npy", affinefile + ".npy", nchildname=basename)
        add_file(datafile + ".npy", datafile + ".npy", nchildname=basename)

        open = (img.replace('/', '~').replace('.', '>'))
        valret = dict(ref.child(basename).get())
        try:
            valurl = valret[basename + "_slice>png"]['url']
        except:
            valurl = None
        print(valurl)
        return json.dumps({'filename': tfilename, 'url':valurl}), 201 #, {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST,DELETE'}#ref.child(basename).get(), 201#, {'Access-Control-Allow-Origin': '*'}

    #@cross_origin()
    @cors.crossdomain(origin='*', methods = 'GET, POST, DELETE')
    def get(self, filename):
        print(filename)
        basename = filename.replace('/', '~').replace('.', '>')
        print(basename)

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

        
        if (np.max(dblob) > 0):
            dblob = dblob / np.max(dblob)
        else:
            dblob = dblob * 0

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
        #if (ablob):
        print(ablob)
        niinew = nb.Nifti1Image(predictions, ablob)
        nb.save(niinew, app.config["UPLOAD_FOLDER"] + nfilename)

        try:
            os.remove(app.config["UPLOAD_FOLDER"] + data)
        except:
            print(f"{data} non existent")
        try:
            os.remove(app.config["UPLOAD_FOLDER"] + affine)
        except:
            print(f"{affine} non existent")

        add_file(img, img, nchildname=basename)
        add_file(nfilename, nfilename, nchildname=basename)
        valret = dict(filref.get())
        valurl = valret[basename + "_sliceog>png"]['url']
        maskurl = valret[basename + "_mask>nii>gz"]['url']
        print({'url':valurl, 'maskUrl':maskurl})
        return json.dumps({'url':valurl, 'maskUrl':maskurl}), 201 

    @cors.crossdomain(origin='*', methods = 'GET, POST, DELETE')
    def delete(self, filename):
        basename = filename.replace('/', '~').replace('.', '>')
        print(basename)
        files = ref.child(basename)
        print(files)
        
        vals = files.get()
        if (vals != None):
            flist = list(vals.keys())
            hold = None
            for file in flist:
                hold = niifiles.get_blob(vals[file]["name"])
                if not(hold == None):
                    hold.delete()
            files.delete()
            return "file deleted", 201 
        else:
            return "file not in database", 200
            #abort(400, "cleared")

api.add_resource(processMask, "/api/getmask/<filename>")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(threaded=True, host='0.0.0.0', port=port)
    #app.run(debug=True, port=4200)
