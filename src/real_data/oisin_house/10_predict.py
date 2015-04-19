'''
make predictions for all of bigbird dataset
using my algorhtm
saves each prediction to disk
'''
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cPickle as pickle
import sys
import os
sys.path.append(os.path.expanduser("~/projects/shape_sharing/src/"))
from time import time
import scipy.misc  # for image saving
import scipy.io
import yaml
import shutil
import collections

import real_data_paths as paths
import real_params as parameters

from common import voxlets
from common import scene

import sklearn.metrics

print "Loading model..."
# with open(paths.voxlet_model_oma_path.replace('_full_split', ''), 'rb') as f:
with open(paths.voxlet_model_oma_path, 'rb') as f:
    model_without_implicit = pickle.load(f)
print "Done loading model..."

combine_renders = False
render_predictions = True
render_top_view = False
do_greedy_oracles = True
# save_prediction_grids = True
save_simple = False
save_scores_to_yaml = True
distance_experiments = False

# this overrides all other parameters. Means we don't botther with orables etc
only_prediction = False

test_type = 'oma_full_split_with_greedy'

def save_render_assess(dic, sc):
    '''
    does whatever is required in terms of saving results, rendering them etc
    '''

    # Path where any renders will be saved to
    gen_renderpath = paths.voxlet_prediction_img_path % \
        (test_type, sc.sequence['name'], '%s')

    if render_predictions:
        dic['grid'].render_view(gen_renderpath % dic['desc'])

    if save_simple:
        D = dict(grid=dic['grid'].V, name=dic['desc'], vox_size=dic['grid'].vox_size)
        scipy.io.savemat(gen_renderpath.replace('png', 'mat'), D)

    dic['results'] = sc.evaluate_prediction(dic['grid'].V)

    # finally removing the grid
    dic['grid'] = []

    return dic


def combine_renders(rec, combines, su, sv, gen_renderpath, savename):

    fig = plt.figure(figsize=(25, 10), dpi=1000)
    plt.subplots(su, sv)
    plt.subplots_adjust(left=0, bottom=0, right=0.98, top=0.98, wspace=0.02, hspace=0.02)

    for count, (name, dic) in enumerate(combines.iteritems()):

        if count >= su*sv:
            raise Exception("Error! Final subplot is reserved for the ROC curve")

        plt.subplot(su, sv, count + 1)
        plt.imshow(scipy.misc.imread(gen_renderpath % name)[:240, 300:600, :])
        plt.axis('off')
        plt.title(dic['name'], fontsize=10)

        " Add to the roc plot, which is in the final subplot"
        if name != 'input':
            "Add the AUC"
            plt.text(0, 50, "AUC=%0.3f, prec=%0.3f, rec=%0.3f" % \
                (dic['results']['auc'],
                 dic['results']['precision'],
                 dic['results']['recall']),
                fontsize=6, color='white')

            plt.subplot(su, sv, su*sv)
            plt.plot(dic['results']['fpr'], dic['results']['tpr'], label=dic['name'])
            plt.hold(1)
            plt.legend(prop={'size':6}, loc='lower right')

        else:
            plt.hold(1)
            plt.plot(rec.sampled_idxs[:, 1], rec.sampled_idxs[:, 0], 'r.', ms=2)

    plt.savefig(savename, dpi=400)
    plt.close()


print "MAIN LOOP"
# Note: if parallelising, should either do here (at top level) or at the
# bottom level, where the predictions are accumulated (although this might be)
# better off being GPU...)
def process_sequence(sequence):

    print "Processing ", sequence['name']
    sc = scene.Scene(parameters.mu,
        model_without_implicit.voxlet_params)
    sc.load_sequence(sequence, frame_nos=0, segment_with_gt=True,
        save_grids=False, load_implicit=False, voxel_normals='gt_tsdf')

    print "-> Creating folder"
    fpath = paths.voxlet_prediction_folderpath % \
        (test_type, sequence['name'])
    if not os.path.exists(fpath):
        os.makedirs(fpath)
    print "-> Doing prediction"
    # sc.santity_render(save_folder='/tmp/')

    combines = collections.OrderedDict()
    combines['input'] = {'name':'Input image'}
    combines['gt'] = save_render_assess(
        {'name':'Ground truth', 'grid':sc.gt_tsdf, 'desc':'gt'}, sc)
    combines['visible'] = save_render_assess(
        {'name':'Visible surfaces', 'grid':sc.im_tsdf, 'desc':'visible'}, sc)

    print "-> Reconstructing with oma forest"
    rec = voxlets.Reconstructer(
        reconstruction_type='kmeans_on_pca', combine_type='modal_vote')
    rec.set_scene(sc)
    rec.sample_points(parameters.VoxletPrediction.number_samples,
                      parameters.VoxletPrediction.sampling_grid_size)

    # Path where any renders will be saved to
    gen_renderpath = paths.voxlet_prediction_img_path % \
        (test_type, sequence['name'], '%s')

    rec.initialise_output_grid(gt_grid=sc.gt_tsdf)
    rec.set_model(model_without_implicit)
    pred_voxlets = rec.fill_in_output_grid_oma(
        add_ground_plane=True, feature_collapse_type='pca', render_type=['slice', 'tree_predictions'], render_savepath=fpath)
    pred_voxlets_exisiting = rec.keeping_existing

    print "-> Doing the empty voxlet thing"
    rec.save_empty_voxel_counts(fpath)

    combines['pred_voxlets'] = save_render_assess({'name':'Voxlets', 'grid':pred_voxlets, 'desc':'pred_voxlets'}, sc)
    combines['pred_voxlets_exisiting'] = save_render_assess(
        {'name':'Voxlets existing', 'grid':pred_voxlets_exisiting, 'desc':'pred_voxlets_exisiting'}, sc)

    if render_top_view:
        print "-> Rendering top view"
        rec.plot_voxlet_top_view(savepath=gen_renderpath % 'top_view')
        print gen_renderpath % 'top_view'

    if only_prediction:
        return

    if distance_experiments:
        # here I'm doing an experiment to see which distance measure makes sense to use...
        for d_measure in ['narrow_band', 'largest_of_free_zones', 'just_empty']:
            rec.initialise_output_grid(gt_grid=sc.gt_tsdf)
            narrow_band = rec.fill_in_output_grid_oma(
                add_ground_plane=True, feature_collapse_type='pca', distance_measure=d_measure)
            combines[d_measure] = save_render_assess(
                {'name':d_measure, 'grid':narrow_band, 'desc':d_measure}, sc)



    # must save the input view to the save folder
    scipy.misc.imsave(gen_renderpath % 'input', sc.im.rgb)

    if combine_renders:
        print "-> Combining renders"
        su, sv = 3, 3

        fname = 'all_' + rec.sc.sequence['name']
        all_savename = gen_renderpath.replace('png', 'pdf') % fname

        combine_renders(rec, combines, su, sv, gen_renderpath, all_savename)

    if do_greedy_oracles:
        print "-> DOING GREEDY ORACLES"

        # true greedy oracle prediction - without the ground truth
        greedy_combines = collections.OrderedDict()
        greedy_combines['gt'] = save_render_assess(
            {'name':'Ground truth', 'grid':sc.gt_tsdf, 'desc':'gt'}, sc)
        greedy_combines['visible'] = save_render_assess(
            {'name':'Visible surfaces', 'grid':sc.im_tsdf, 'desc':'visible'}, sc)

        for d_measure in ['narrow_band', 'largest_of_free_zones', 'just_empty']:

            print "in outer loop" , d_measure
            rec.initialise_output_grid(gt_grid=sc.gt_tsdf)
            true_greedy = rec.fill_in_output_grid_oma(
                render_type=[], add_ground_plane=True, feature_collapse_type='pca',
                oracle='true_greedy', distance_measure=d_measure)

            for key, result in true_greedy.iteritems():
                print "In innder loop ", key
                dic = {'desc':'greedy_%s_%04d' % (d_measure, key),
                       'name': 'Greedy %s %04d' % (d_measure, key),
                       'grid': result}
                greedy_combines['greedy_%s_%04d' % (d_measure, key)] = \
                    save_render_assess(dic, sc)
            true_greedy = None

        # now combining the greedy renders...
        fname = 'all_greedy_' + rec.sc.sequence['name']
        all_savename = gen_renderpath.replace('png', 'pdf') % fname

        print "-> COMBINING GREEDY ORACLES"
        combine_renders(rec, greedy_combines, 3, 4, gen_renderpath, all_savename)

        # hack to align the plotting
        # combines['blankblank'] = []

        # # true greedy oracle prediction -with the ground truth
        # rec.initialise_output_grid(gt_grid=sc.gt_tsdf)
        # true_greedy_gt = rec.fill_in_output_grid_oma(
        #     render_type=[], add_ground_plane=True, feature_collapse_type='pca',
        #     oracle='true_greedy_gt')

        # for key, result in true_greedy_gt.iteritems():
        #     dic = {'desc':'true_greedy_gt_%04d' % key, 'name': 'True greedy GT %04d' % key, 'grid': result}
        #     combines['true_greedy_gt_%04d' % key] = save_render_assess(dic, sc)
        # true_greedy_gt = None

    if render_top_view:
        print "-> Rendering top view"
        rec.plot_voxlet_top_view(savepath=gen_renderpath % 'top_view')
        print gen_renderpath % 'top_view'

    if save_scores_to_yaml:
        print "-> Writing scores to YAML"
        results_dict = {}
        for name, dic in combines.iteritems():
            if name != 'input':
                test_key = name
                results_dict[test_key] = \
                    {'description': dic['name'],
                     'auc':         float(dic['results']['auc']),
                     'precision':   float(dic['results']['precision']),
                     'recall':      float(dic['results']['recall'])}

        with open(fpath + 'scores.yaml', 'w') as f:
            f.write(yaml.dump(results_dict, default_flow_style=False))


    print "Done sequence %s" % sequence['name']


# need to import these *after* the pool helper has been defined
if False:
    # parameters.multicore:
    import multiprocessing
    pool = multiprocessing.Pool(3)
    mapper = pool.map
else:
    mapper = map


if __name__ == '__main__':

    # print "Warning - just doing this one"
    # this_one = []
    # for t in paths.test_data:
    #     if t['name'] == 'saved_00196_[92]':
    #         this_one.append(t)
    # temp = [s for s in paths.RenderedData.test_sequence() if s['name'] == 'd2p8ae7t0xi81q3y_SEQ']
    # print temp
    tic = time()
    mapper(process_sequence, paths.test_data[6:])
    # [:48], chunksize=1)
    print "In total took %f s" % (time() - tic)


