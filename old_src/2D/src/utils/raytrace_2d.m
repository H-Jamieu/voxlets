function depth = raytrace_2d(mask)
% ray traces a 2d masked image from the bottom. returns a vector 'depth' the same
% length as the width of 'mask', where each value in depth is the first
% non-zero position encountered from the bottom of the image

depth = findfirst(mask, 1, 1, 'first');
depth(depth==0) = nan;