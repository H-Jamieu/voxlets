% a script to load in a depth image, convert to xyz, compute normals and segment
clear
cd ~/projects/shape_sharing/3D/features/
addpath ../plotting/
addpath ../transformations/
addpath ../../2D/src/segment/
run ../define_params_3d.m

%% loading in depth
num = 100;
render_idx = 10;
model = params.model_filelist{num};
depth_name = sprintf(paths.basis_models.rendered, model, render_idx);
load(depth_name, 'depth');
depth(abs(depth-3) < 0.001) = nan;

%% project depth and compute normals
cloud.xyz = reproject_depth(depth, params.half_intrinsics);
[cloud.normals, cloud.curvature] = normals_wrapper(cloud.xyz, 'knn', 150);
plot_normals(cloud.xyz, cloud.normals, 0.05)

%% now do some kind of segmentation...
opts.min_cluster_size = 50;
opts.max_cluster_size = 1e6;
opts.num_neighbours = 50;
opts.smoothness_threshold = (7.0 / 180.0) * pi;
opts.curvature_threshold = 1.0;

idx = segment_wrapper(cloud, opts);
imagesc(reshape(idx, 240, 320))

%% running segment soup algorithm
[idxs, idxs_without_nans] = segment_soup_3d(cloud, opts);
imagesc(idxs)

%% plotting
clf
[n, m] = best_subplot_dims(size(idxs, 2));

for ii = 1:size(idxs, 2)
    
    temp_image = reshape(idxs(:, ii), 240, []);
    
    subplot(n, m, ii)
    imagesc(temp_image);
    axis image
    
end