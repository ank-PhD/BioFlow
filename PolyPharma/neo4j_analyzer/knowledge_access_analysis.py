"""
Builds on the knowledge
"""
__author__ = 'ank'

from Matrix_Interactome_DB_interface import  MatrixGetter
from Matrix_Knowledge_DB_Interface import GO_Interface
from multiprocessing import Pool
from PolyPharma.configs import UP_rand_samp
from pprint import PrettyPrinter
import pickle
import numpy as np
import matplotlib.pyplot as plt
from copy import copy
from random import shuffle
from PolyPharma.Utils.better_histogram import better2D_desisty_plot

filtr = ['biological_process']
pprinter = PrettyPrinter(indent=4)
MG = MatrixGetter(True, False)
MG.fast_load()


def spawn_sampler(sample_size_list_plus_iteration_list):
    """
    Spawns a sampler initalized from the default GO_Interface

    :param sample_size_list_plus_iteration_list: combined list of sample swizes and iterations (requried for Pool.map usage)
    """
    print sample_size_list_plus_iteration_list
    KG = GO_Interface(filtr, MG.Uniprots, 1, True, 3)
    KG.load()
    print KG.pretty_time()
    sample_size_list = sample_size_list_plus_iteration_list[0]
    iteration_list = sample_size_list_plus_iteration_list[1]
    KG.randomly_sample(sample_size_list, iteration_list)


def spawn_sampler_pool(pool_size, sample_size_list, interation_list_per_pool):
    """
    Spawns a pool of samplers of the information flow within the GO system

    :param pool_size: number of processes that are performing the sample pooling and analyzing
    :param sample_size_list: size of the sample list
    :param interation_list_per_pool: number of iterations performing the pooling of the samples in each list
    """
    p = Pool(pool_size)
    payload = [(sample_size_list, interation_list_per_pool)]
    p.map(spawn_sampler, payload * pool_size)


def show_corrs(tri_corr_array):
    plt.figure()

    plt.subplot(331)
    plt.title('current through nodes')
    plt.hist(tri_corr_array[0, :], bins=100, histtype='step', log=True)

    plt.subplot(332)
    plt.title('current vs pure informativity')
    # better2D_desisty_plot(tri_corr_array[0, :], tri_corr_array[1, :])
    plt.scatter(tri_corr_array[0, :], tri_corr_array[1, :])

    plt.subplot(333)
    plt.title('current v.s. confusion potential')
    plt.scatter(tri_corr_array[0, :], tri_corr_array[2, :])

    plt.subplot(335)
    plt.title('GO_term pure informativity')
    plt.hist(tri_corr_array[1, :], bins=100, histtype='step', log=True)

    plt.subplot(336)
    plt.title('Informativity vs. confusion potential')
    plt.scatter(tri_corr_array[1, :], tri_corr_array[2, :])

    plt.subplot(339)
    plt.title('confusion potential')
    plt.hist(tri_corr_array[2, :], bins=100, histtype='step', log=True)

    plt.show()

    return np.corrcoef(tri_corr_array)


def stats_on_existing_circsys(size):
    """
    Recovers the statistics on the existing circulation systems.

    :return:
    """

    KG = GO_Interface(filtr, MG.Uniprots, 1, True, 3)
    KG.load()
    MD5_hash = KG._MD5hash()

    curr_inf_conf_general = []
    count = 0
    for i, sample in enumerate(UP_rand_samp.find({'size':size, 'sys_hash' : MD5_hash})):
        # UP_set = pickle.loads(sample['UPs'])
        _, node_currs = pickle.loads(sample['currents'])
        # tensions = pickle.loads(sample['voltages'])
        Dic_system = KG.compute_conduction_system(node_currs)
        curr_inf_conf = list(Dic_system.itervalues())
        curr_inf_conf_general.append(np.array(curr_inf_conf).T)
        count = i

    final = np.concatenate(tuple(curr_inf_conf_general), axis=1)
    print "stats on %s samples" % count
    print show_corrs(final)


def decide_regeneration():
    """
    A script to decide at what point it is better to recompute anew a network rather then go through the time it
    requires to be upickled.
    The current decision is that for the samples of the size of ~ 100 Uniprots, we are better off unpickling from 4
    and more by factor 2 and by factor 10 from 9
    Previous experimets have shown that memoization with pickling incurred no noticeable delay on samples of up to
    50 UPs, but that the storage limit on mongo DB was rapidly exceeded, leading us to create an allocated dump file.
    """

    sample_root = ['530239', '921394', '821224', '876133', '537471', '147771', '765141', '783757', '161100', '996641',
    '568357', '832606', '888857', '443125', '674855', '703465', '770454', '585061', '767349', '454684', '476323',
    '890779', '699374', '699085', '926841', '719433', '979188', '750252', '884148', '452226', '510869', '934804',
    '450711', '654463', '475017', '836128', '869961', '833908', '748293', '642129', '511971', '450103', '465344',
    '664249', '759667', '479667', '945097', '934005', '474459', '616764', '993605', '151251', '881579', '1010120',
    '567103', '177132', '914246', '818797', '734031', '983957', '988876', '907270', '764944', '457147', '574367',
    '605567', '950635', '184544', '372652', '440372', '630427', '446382', '195073', '790029', '941318', '572041',
    '469852', '1009569', '969215', '571784', '794977', '991385', '511515', '592947', '517667', '746802', '685187',
    '877373', '860329', '589231', '1013595', '679330', '808630', '774665', '663924', '615588', '497135', '628832',
    '841054', '657304']
    rooot_copy = copy(sample_root)
    KG = GO_Interface(filtr, MG.Uniprots, 1, True, 3)
    KG.load()
    print KG.pretty_time()
    KG.set_Uniprot_source(sample_root)
    KG.build_extended_conduction_system()
    KG.export_conduction_system()
    print KG.pretty_time()
    for i in range(2, 9):
        shuffle(rooot_copy)
        KG.export_subsystem(sample_root,rooot_copy[:i**2])
        print i**2, 'retrieve: \t', KG.pretty_time()
        KG.set_Uniprot_source(rooot_copy[:i**2])
        KG.build_extended_conduction_system(memoized = False)
        KG.export_conduction_system()
        print i**2, '    redo: \t', KG.pretty_time()


def get_estimated_time(samples, sample_sizes, operations_per_sec=2.2):
    counter = 0
    for sample, sample_size in zip(samples, sample_sizes):
        counter += sample_size*sample**2/operations_per_sec
        print "Computing a sample of %s proteins would take %s secs. \t Repeated %s times: %s h. Total time after phase: %s h" %(
            sample, "{0:.2f}".format(sample**2/operations_per_sec),
            sample_size, "{0:.2f}".format(sample_size*sample**2/operations_per_sec/3600),
            "{0:.2f}".format(counter/3600)
        )
    return counter


if __name__ == "__main__":
    # spawn_sampler(([10, 100], [2, 1]))
    spawn_sampler_pool(6, [10, 25, 50, 100,], [15, 10, 10, 8,])
    # get_estimated_time([10, 25, 50, 100,], [15, 10, 10, 8,])
    # stats_on_existing_circsys(10)