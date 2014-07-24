function vox = load_vox(model_name)

voxel_filename = sprintf('/Users/Michael/projects/shape_sharing/data/3D/basis_models/voxelised/%s.mat', model_name);
vox_struct = load(voxel_filename);
V = vox_struct.vol;
V(V<30) = 0;
V = permute(V, [2, 1, 3]);
[inds] = find(V);
[i, j, k] = ind2sub(size(V), inds);
vox = [i, j, k];