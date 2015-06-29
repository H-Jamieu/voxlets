'''
some functions etc for loading data for object discovery.
these will probably not be needed in the long run
'''
import yaml
import sys, os
sys.path.append(os.path.expanduser('~/projects/shape_sharing/src/'))
sys.path.append(os.path.expanduser('~/projects/shape_sharing/src/real_data/'))

import matplotlib.pyplot as plt
from oisin_house import real_data_paths as paths
from common import scene
from common import images
import scipy.io
import numpy as np

labels_dir = '/media/ssd/data/oisin_house/obj_discovery/labelling/'

# load labels and create inverse mapping
scene_to_labels = yaml.load(open(labels_dir + 'labels.yaml'))

labels_to_scene = {}

for scene_t, labels in scene_to_labels.items():
    for idx, label in labels.items():
        if label == '':
            continue
        elif label in labels_to_scene:
            labels_to_scene[label].append((scene_t, idx))
        else:
            labels_to_scene[label] = [(scene_t, idx)]


# create mapping from a scene name to all the sequences of this scene
scene_to_sequence = {}

for scene_t in paths.all_train_data:
    if scene_t['scene'] in scene_to_sequence:
        scene_to_sequence[scene_t['scene']].append(scene_t)
    else:
        scene_to_sequence[scene_t['scene']] = [scene_t]


def crop_image_to_mask(img, mask):
    '''returns a cropped version of the image tightly cropped on the mask'''
    left = np.argmax(mask.sum(0) > 0)
    top = np.argmax(mask.sum(1) > 0)
    right = mask.shape[1] - np.argmax(mask.sum(0)[::-1] > 0)
    bottom = mask.shape[0] - np.argmax(mask.sum(1)[::-1] > 0)
    if len(img.shape) == 3:
        return img[top:bottom, left:right, :]
    else:
        return img[top:bottom, left:right]


def floor_plane_to_3d(labels_floor_plane, sc):
    '''expands a grid to 3D. Code modified from scenes.py'''
    labels3d = np.expand_dims(labels_floor_plane, axis=2)
    labels3d = np.tile(labels3d, (1, 1, sc.gt_tsdf.V.shape[2]))

    labels_3d_grid = sc.gt_tsdf.copy()
    labels_3d_grid.V = labels3d
    labels_3d_grid.V[:, :, :sc.floor_height] = 0

    return labels_3d_grid


def load_images_of_object(obj_name, maximum=None):
    '''returns a list of rgb images of the named object'''
    imgs = []
    xyzs = []
    ims = []
    masks = []
    regions = []

    scene_idxs = labels_to_scene[obj_name]
    for scene_name, idx in scene_idxs:

        if scene_name not in scene_to_sequence:
            print "Skipping", scene_name
            continue

        sequences = scene_to_sequence[scene_name]

        for sequence in sequences:
            # load the sequence
            sc = scene.Scene(mu=0.025)
            sc.load_sequence(sequence, frame_nos=0, segment_with_gt=False,
                segment=False, save_grids=False, carve=False)

            # load the mask
            labels_floor_plane = \
                scipy.io.loadmat(labels_dir + 'labels/' + sequence['scene'] + '.mat')['seg']

            labels_3d = floor_plane_to_3d(labels_floor_plane, sc)
            labels_im = sc.im.label_from_grid(labels_3d)
            mask = labels_im==idx

            temp = crop_image_to_mask(sc.im.depth, mask)
            xyz = sc.im.get_world_xyz()[mask.ravel(), :]

            imgs.append(temp)
            xyzs.append(xyz)
            ims.append(sc.im)
            masks.append(mask)
            regions.append(images.Rgbd_region(sc.im, mask))


    if maximum is not None:
        np.random.seed(42)
        idxs = np.random.choice(len(imgs), maximum, replace=False).astype(int)
        print idxs
        return [imgs[i] for i in idxs], [xyzs[i] for i in idxs], \
               [ims[i] for i in idxs], [masks[i] for i in idxs], \
               [regions[i] for i in idxs]
    else:
        return imgs, xyzs, ims, masks, regions



def imshow_subplot(imgs):
    '''
    plots each image in its own subplot using imshow
    '''

    # compute optimal dimensions
    H = np.ceil(np.sqrt(float(len(imgs)))).astype(int)
    W = np.ceil(len(imgs) / H).astype(int)

    for count, img in enumerate(imgs):
        plt.subplot(H, W, count+1)
        plt.imshow(img)
        plt.title(str(count))
        plt.axis('off')
# #  plot all the iamges
# plt.figure(figsize=(12, 12))
# for count, img in enumerate(imgs):
