# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

#import cv, cv2
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import scipy.io
import time
# <codecell>

plt.ion()

modelname = "1f8275f1c106144ff11c3739edd52fa3";

modelpath = "/Users/Michael/projects/shape_sharing/data/3D/basis_models/renders/%s/depth_%d.mat"
renderspath = "/Users/Michael/projects/shape_sharing/data/3D/basis_models/renders/"
#modelname = "1046b3d5a381a8902e5ae31c6c631a39";
halopath = "/Users/Michael/projects/shape_sharing/data/3D/basis_models/halo/mat_%d.mat"
savedir = "/Users/Michael/projects/shape_sharing/data/3D/basis_models/voxelised/"
imheight = 240
imwidth = 320
nbFrames = 42
res = 100  # resolution of the voxel grid


def render_model(modelname):
    #origin = np.array([[-0.475, 3.062, -0.582, 1]]).T
    origin = np.array([[0, 0, 0, 1]]).T
    volume = np.zeros((res,res,res), dtype=np.uint8)
    size = 0.5

    coords = np.ones((4,res,res,res))
    coords[0:3,:,:,:] = np.mgrid[origin[0]-size:origin[0]+size:res*1j, origin[1]-size:origin[1]+size:res*1j, origin[2]-size:origin[2]+size:res*1j]

    X = coords.reshape((4, res**3))

    for i in xrange(42):

        #print "Printing frame %d" % i

        depth_mats = scipy.io.loadmat(modelpath % (modelname, i+1))
        img_raw = depth_mats["depth"]
        #print img_raw.min()
        #print img_raw.max()
        mask = np.uint8(img_raw < 3 )
        fmask = mask.flatten()
    #plt.imshow(mask)
        #plt.draw()

        # loading extrinsic (R) and intrinsic (K) parameters
        mat_path = halopath % (i+1)
        mats = scipy.io.loadmat(mat_path)
        K = mats["K"]
        R = mats["R"].newbyteorder('=')
            
        # some fudge for some reason...?
        K[0,0] *= -1

        # combining parameters into one
        R1 = np.linalg.pinv(R).T
        #print R1
        R1 = R1[0:3,0:4]
        P = np.dot(K,R1)

        # projecting the voxel coordinates through the matrices into image coordinates
        p = np.dot(P, X)
        #print p[0:3, 0:10]
        lmbd = p[2,:]  # this is the depth?
        p = p[0:2,:] / lmbd# + np.array([[0.5, 0.5]]).T
        ip = np.int32(np.round(p))

        # finding the voxels which actually land in the image
        valid = np.logical_and(ip[0,:] >= 0, np.logical_and(ip[0,:] < imwidth, np.logical_and(ip[1,:] >= 0, ip[1,:] < imheight)))
        
        # list of indices of voxels which project into image
        valid_volume_coords = np.where(valid)[0]  

        # which pixels in the image these voxels project to
        valid_img_coords = ip[:,valid_volume_coords] 
        
        # boolean array – do these voxels fall inside the object mask or not? 
        vals = mask[valid_img_coords[1,:], valid_img_coords[0,:]] 

        # ...and what are their depths in the input image?
        image_depths = img_raw[valid_img_coords[1,:], valid_img_coords[0,:]] 
        voxel_depths = -lmbd[valid] 

        # negating items in the boolean array which are at the wrong depth
        #print voxel_depths.min()
        #print voxel_depths.max()
        vals[voxel_depths < image_depths] = 0
        
        # creating voxel matrix for this image, populate with boolean array values (in mask or not?)
        tempv = np.zeros(res**3, dtype=np.uint8)
        tempv[valid_volume_coords] = vals

        # reshaping and adding to the overall voxel array
        tempv = np.reshape(tempv, (res, res, res))
        volume = volume + tempv
        
    print "Done all frames."

    d = dict(vol=volume, coords=coords, res=res, origin=origin, size=size, depth=lmbd)
    savepath = savedir + modelname + '.mat'
    scipy.io.savemat(savepath, d)


#def render_all():
# rendering all views
number = 1;
for modelname in os.listdir(renderspath):
    tic = time.time()
    number += 1

    print "Processing " + modelname

    if not os.path.isdir(renderspath + modelname):
        print modelname + " does not seem to be a directory"
        continue

    savepath = savedir + modelname + '.mat'
    if os.path.isfile(savepath):
        print "Skipping " + modelname
        continue

    render_model(modelname)
    
    toc = time.time() - tic;
    print "Done " + str(number) + " in " + str(toc) + "s"



# <codecell>

#mlab.pipeline.volume(mlab.pipeline.scalar_field(volume), vmin=29)
#mlab.pipeline.image_plane_widget(mlab.pipeline.scalar_field(volume), plane_orientation='y_axes', slice_index=1,)
#mlab.pipeline.image_plane_widget(mlab.pipeline.scalar_field(volume),plane_orientation='z_axes',slice_index=32,)
#mlab.outline()
#mlab.show()


