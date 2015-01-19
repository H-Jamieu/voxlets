'''
script to train a model
based on training data
'''
import sys, os
import numpy as np
import yaml
import scipy.io
import sklearn.ensemble
import cPickle as pickle

sys.path.append(os.path.expanduser('~/projects/shape_sharing/src/'))
from common import paths

with open(paths.yaml_train_location, 'r') as f:
    train_sequences = yaml.load(f)

all_X = []
all_Y = []

for sequence in train_sequences:

    # loading the data and adding to arrays
    seq_foldername = paths.sequences_save_location + sequence['name'] + '/'
    training_pair = scipy.io.loadmat(seq_foldername + 'training_pairs.mat')

    all_X.append(training_pair['X'])
    all_Y.append(training_pair['Y'])

all_X_np = np.concatenate(all_X, axis=0).astype(np.float32)
all_Y_np = np.concatenate(all_Y, axis=1).flatten().astype(np.float16)

print all_X_np.shape
print all_Y_np.shape
print all_X_np.dtype
print all_Y_np.dtype

print "Training the model"
rf = sklearn.ensemble.RandomForestRegressor(
    n_estimators=50, oob_score=True, n_jobs=4, max_depth=14)
rf.fit(all_X_np, all_Y_np)

print "Saving the model"
pickle.dump(rf, open(paths.implicit_models_folder + 'model.pkl', 'wb'))