# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
import numpy as np
import utool as ut
import vtool as vt  # NOQA
import plottool as pt
import six
import networkx as nx
import itertools as it
nx.set_edge_attrs = nx.set_edge_attributes
nx.get_edge_attrs = nx.get_edge_attributes
nx.set_node_attrs = nx.set_node_attributes
nx.get_node_attrs = nx.get_node_attributes
print, rrr, profile = ut.inject2(__name__, '[graph_inference]')


CUT_WEIGHT_KEY = 'cut_weight'


def _dz(a, b):
    a = a.tolist() if isinstance(a, np.ndarray) else list(a)
    b = b.tolist() if isinstance(b, np.ndarray) else list(b)
    if len(a) == 0 and len(b) == 1:
        # This introduces a corner case
        b = []
    elif len(b) == 1 and len(a) > 1:
        b = b * len(a)
    assert len(a) == len(b), 'out of alignment a=%r, b=%r' % (a, b)
    return dict(zip(a, b))


def get_cm_breaking(qreq_, cm_list, ranks_top=None, ranks_bot=None):
    """
    """
    # Construct K-broken graph
    qaid_list = [cm.qaid for cm in cm_list]
    edges = []
    edge_data = []

    if ranks_bot is None:
        ranks_bot = 0

    #ranks_top = (infr.qreq_.qparams.K + 1) * 2
    #ranks_top = (infr.qreq_.qparams.K) * 2
    #ranks_top = (qreq_.qparams.K + 2)
    for count, cm in enumerate(cm_list):
        score_list = cm.annot_score_list
        rank_list = ut.argsort(score_list)[::-1]
        sortx = ut.argsort(rank_list)

        top_sortx = sortx[:ranks_top]
        bot_sortx = sortx[-ranks_bot:]
        short_sortx = ut.unique(top_sortx + bot_sortx)

        score_list = ut.take(score_list, short_sortx)
        daid_list = ut.take(cm.daid_list, short_sortx)
        rank_list = ut.take(rank_list, short_sortx)

        for score, rank, daid in zip(score_list, rank_list, daid_list):
            if daid not in qaid_list:
                continue
            data = {
                'score': score,
                'rank': rank,
            }
            edge_data.append(data)
            edges.append((cm.qaid, daid))

    # Maybe just K-break graph here?
    # Condense graph?

    # make symmetric
    directed_edges = dict(zip(edges, edge_data))
    # Find edges that point in both directions
    undirected_edges = {}
    for (u, v), data in directed_edges.items():
        if (v, u) in undirected_edges:
            undirected_edges[(v, u)]['score'] += data['score']
            undirected_edges[(v, u)]['score'] /= 2
        else:
            undirected_edges[(u, v)] = data
    return undirected_edges


def estimate_threshold(curve, method=None):
    """
        import plottool as pt
        idx3 = vt.find_elbow_point(curve[idx1:idx2 + 1]) + idx1
        pt.plot(curve)
        pt.plot(idx1, curve[idx1], 'bo')
        pt.plot(idx2, curve[idx2], 'ro')
        pt.plot(idx3, curve[idx3], 'go')
    """
    if len(curve) == 0:
        return None
    if method is None:
        method = 'mean'
    if method == 'mean':
        thresh = np.mean(curve)
    elif method == 'elbow':
        idx1 = vt.find_elbow_point(curve)
        idx2 = vt.find_elbow_point(curve[idx1:]) + idx1
        thresh = curve[idx2]
    else:
        raise ValueError('method = %r' % (method,))
    return thresh


@six.add_metaclass(ut.ReloadingMetaclass)
class InfrModel(ut.NiceRepr):
    """
    Wrapper around graphcut algorithms
    """

    def __init__(model, graph):
        #def __init__(model, n_nodes, edges, edge_weights=None, n_labels=None,
        model.graph = graph
        model._update_state()

    def _update_state(model):
        import networkx as nx
        name_label_key = 'name_label'
        weight_key = CUT_WEIGHT_KEY
        # Get nx graph properties
        external_nodes = sorted(list(model.graph.nodes()))
        external_edges = list(model.graph.edges())
        edge2_weights = nx.get_edge_attrs(model.graph, weight_key)
        node2_labeling = nx.get_node_attrs(model.graph, name_label_key)
        edge_weights = ut.dict_take(edge2_weights, external_edges, 0)
        external_labeling = ut.take(node2_labeling, external_nodes)
        # Map to internal ids for pygco
        internal_nodes = ut.rebase_labels(external_nodes)
        extern2_intern = dict(zip(external_nodes, internal_nodes))
        internal_edges = ut.unflat_take(extern2_intern, external_edges)
        internal_labeling = ut.rebase_labels(external_labeling)
        n_nodes = len(internal_nodes)
        # Model state
        model.n_nodes = n_nodes
        model.extern2_intern = extern2_intern
        model.intern2_extern = ut.invert_dict(extern2_intern)
        model.edges = internal_edges
        model.edge_weights = edge_weights
        # Model parameters
        model.labeling = np.zeros(model.n_nodes, dtype=np.int32)
        model._update_labels(labeling=internal_labeling)
        model._update_weights()

    def __nice__(self):
        return '(n_nodes=%r, n_labels=%r)' % (self.n_nodes, self.n_labels)
        #return '(n_nodes=%r, n_labels=%r, nrg=%r)' % (self.n_nodes,
        #self.n_labels, self.total_energy)

    def _update_labels(model, n_labels=None, unaries=None, labeling=None):
        if labeling is not None:
            n_labels_ = max(labeling) + 1
            assert n_labels is None or n_labels == n_labels_
            n_labels = n_labels_
        if n_labels is None:
            n_labels = 2
        if unaries is None:
            unaries = np.zeros((model.n_nodes, n_labels), dtype=np.int32)
        # Update internals
        model.pairwise_potts = -1 * np.eye(n_labels, dtype=np.int32)
        model.n_labels = n_labels
        model.unaries = unaries
        if model.labeling.max() >= n_labels:
            model.labeling = np.zeros(model.n_nodes, dtype=np.int32)

    def _update_weights(model, thresh=None):
        int_factor = 1E2
        edge_weights = np.array(model.edge_weights)
        if thresh is None:
            thresh = model._estimate_threshold()
        else:
            if isinstance(thresh, six.string_types):
                thresh = model._estimate_threshold(method=thresh)
            #np.mean(edge_weights)
        if True:
            # Center and scale weights between -1 and 1
            centered = (edge_weights - thresh)
            centered[centered < 0] = (centered[centered < 0] / thresh)
            centered[centered > 0] = (centered[centered > 0] / (1 - thresh))
            newprob = (centered + 1) / 2
            newprob[np.isnan(newprob)] = .5
            # Apply logit rule
            # prevent infinity
            #pad = 1 / (int_factor * 2)
            pad = 1E6
            perbprob = (newprob * (1.0 - pad * 2)) + pad
            weights = vt.logit(perbprob)
        else:
            weights = (edge_weights - thresh)
            # Conv
            weights[np.isnan(edge_weights)] = 0

        weights = (weights * int_factor).astype(np.int32)
        edges_ = np.round(model.edges).astype(np.int32)
        edges_ = vt.atleast_nd(edges_, 2)
        edges_.shape = (edges_.shape[0], 2)
        weighted_edges = np.vstack((edges_.T, weights)).T
        weighted_edges = np.ascontiguousarray(weighted_edges)
        weighted_edges = np.nan_to_num(weighted_edges)
        # Remove edges with 0 weight as they have no influence
        weighted_edges = weighted_edges.compress(weighted_edges.T[2] != 0, axis=0)
        # Update internals
        model.thresh = thresh
        model.weighted_edges = weighted_edges
        model.weights = weights

    @property
    def total_energy(model):
        pairwise_potts = model.pairwise_potts
        wedges = model.weighted_edges
        unary_idxs = (model.labeling,)
        pairwise_idxs = (model.labeling[wedges.T[0]],
                         model.labeling[wedges.T[1]])
        _unary_energies = model.unaries[unary_idxs]
        _potts_energies = pairwise_potts[pairwise_idxs]
        unary_energy = _unary_energies.sum()
        pairwise_energy = (wedges.T[2] * _potts_energies).sum()
        total_energy = unary_energy + pairwise_energy
        return total_energy

    @property
    def node_to_label(model):
        # External nodes to label
        nodes = ut.take(model.intern2_extern, range(model.n_nodes))
        extern_node2_new_label = dict(zip(nodes, model.labeling))
        return extern_node2_new_label

    def _estimate_threshold(model, method=None, curve=None):
        """
            import plottool as pt
            idx3 = vt.find_elbow_point(curve[idx1:idx2 + 1]) + idx1
            pt.plot(curve)
            pt.plot(idx1, curve[idx1], 'bo')
            pt.plot(idx2, curve[idx2], 'ro')
            pt.plot(idx3, curve[idx3], 'go')
        """
        if curve is None:
            isvalid = ~np.isnan(model.edge_weights)
            curve = sorted(ut.compress(model.edge_weights, isvalid))
        thresh = estimate_threshold(curve, method)
        #if len(curve) == 0:
        #    return 0
        #if method is None:
        #    method = 'mean'
        #if method == 'mean':
        #    thresh = np.mean(curve)
        #elif method == 'elbow':
        #    idx1 = vt.find_elbow_point(curve)
        #    idx2 = vt.find_elbow_point(curve[idx1:]) + idx1
        #    thresh = curve[idx2]
        #else:
        #    raise ValueError('method = %r' % (method,))
        return thresh

    def run_inference(model, thresh=None, n_labels=None, n_iter=5,
                      algorithm='expansion'):
        import pygco
        if n_labels is not None:
            model._update_labels(n_labels)
        if thresh is not None:
            model._update_weights(thresh=thresh)
        if model.n_labels <= 0:
            raise ValueError('cannot run inference with zero labels')
        if model.n_labels == 1:
            labeling = np.zeros(model.n_nodes, dtype=np.int32)
        else:
            cutkw = dict(n_iter=n_iter, algorithm=algorithm)
            if 0:
                print(ut.code_repr(model.unaries, 'unaries'))
                print(ut.code_repr(model.weighted_edges, 'weighted_edges'))
                print(ut.code_repr(model.pairwise_potts, 'pairwise_potts'))
                print(ut.code_repr(cutkw, 'cutkw'))
            labeling = pygco.cut_from_graph(model.weighted_edges, model.unaries,
                                            model.pairwise_potts, **cutkw)
            model.labeling = labeling
        #print('model.total_energy = %r' % (model.total_energy,))
        return labeling

    def run_inference2(model, min_labels=1, max_labels=10):
        cut_params = ut.all_dict_combinations({
            #'n_labels': list(range(min_labels, max_labels + 1)),
            #'n_labels': list(range(min_labels, max_labels + 1)),
            'n_labels': list(range(max_labels, max_labels + 1)),
        })
        cut_energies = []
        cut_labeling = []
        for params in cut_params:
            model.run_inference(**params)
            nrg = model.total_energy
            #complexity = .1 * model.n_nodes * model.thresh * params['n_labels']
            complexity = 0
            nrg2 = nrg + complexity
            print('used %d labels' % (len(set(model.labeling))),)
            print('complexity = %r' % (complexity,))
            print('nrg = %r' % (nrg,))
            print('nrg + complexity = %r' % (nrg2,))
            cut_energies.append(nrg2)
            cut_labeling.append(model.labeling)

        best_paramx = np.argmin(cut_energies)
        print('best_paramx = %r' % (best_paramx,))
        params = cut_params[best_paramx]
        print('params = %r' % (params,))
        labeling = cut_labeling[best_paramx]
        model.labeling = labeling
        #labeling = model.run_inference(**params)
        return labeling, params

    @staticmethod
    def weights_as_matrix(weighted_edges):
        n_labels = weighted_edges.T[0:2].max() + 1
        mat = np.zeros((n_labels, n_labels))
        flat_idxs = np.ravel_multi_index(weighted_edges.T[0:2], dims=(n_labels, n_labels))
        assert ut.isunique(flat_idxs)
        mat.ravel()[flat_idxs] = weighted_edges.T[2]
        #mat[tuple(weighted_edges.T[0:2])] = weighted_edges.T[2]

    def get_cut_edges(model):
        extern_uv_list = np.array(list(model.graph.edges()))
        intern_uv_list = ut.unflat_take(model.extern2_intern, extern_uv_list)
        intern_uv_list = np.array(intern_uv_list)
        u_labels = model.labeling[intern_uv_list.T[0]]
        v_labels = model.labeling[intern_uv_list.T[1]]
        # Remove edges between all annotations with different labels
        cut_edges = extern_uv_list[u_labels != v_labels]
        cut_edges = [tuple(uv.tolist()) for uv in cut_edges]
        return cut_edges


@six.add_metaclass(ut.ReloadingMetaclass)
class AnnotInferenceVisualization(object):
    """ contains plotting related code """

    def initialize_visual_node_attrs(infr):
        if infr.verbose:
            print('[infr] initialize_visual_node_attrs')
        import networkx as nx
        #import plottool as pt
        graph = infr.graph
        node_to_aid = nx.get_node_attrs(graph, 'aid')
        nodes = list(graph.nodes())
        aid_list = [node_to_aid.get(node, node) for node in nodes]
        #aid_list = sorted(list(graph.nodes()))
        chip_width = 256
        imgpath_list = infr.ibs.depc_annot.get('chips', aid_list, 'img',
                                               config=dict(dim_size=chip_width),
                                               read_extern=False)
        nx.set_node_attrs(graph, 'framewidth', 3.0)
        #nx.set_node_attrs(graph, 'framecolor', pt.DARK_BLUE)
        nx.set_node_attrs(graph, 'shape', 'rect')
        nx.set_node_attrs(graph, 'image', dict(zip(nodes, imgpath_list)))

    def get_colored_edge_weights(infr):
        # Update color and linewidth based on scores/weight
        edges = list(infr.graph.edges())
        edge2_weight = nx.get_edge_attrs(infr.graph, CUT_WEIGHT_KEY)
        #edges = list(edge2_weight.keys())
        weights = np.array(ut.dict_take(edge2_weight, edges, np.nan))
        nan_idxs = []
        if len(weights) > 0:
            # give nans threshold value
            nan_idxs = np.where(np.isnan(weights))[0]
            weights[nan_idxs] = infr.thresh
        #weights = weights.compress(is_valid, axis=0)
        #edges = ut.compress(edges, is_valid)
        colors = infr.get_colored_weights(weights)
        #print('!! weights = %r' % (len(weights),))
        #print('!! edges = %r' % (len(edges),))
        #print('!! colors = %r' % (len(colors),))
        if len(nan_idxs) > 0:
            import plottool as pt
            for idx in nan_idxs:
                colors[idx] = pt.GRAY
        return edges, weights, colors

    def get_colored_weights(infr, weights):
        import plottool as pt
        #pt.rrrr()
        cmap_ = 'viridis'
        cmap_ = 'plasma'
        #cmap_ = pt.plt.get_cmap(cmap_)
        weights[np.isnan(weights)] = infr.thresh
        #colors = pt.scores_to_color(weights, cmap_=cmap_, logscale=True)
        colors = pt.scores_to_color(weights, cmap_=cmap_, score_range=(0, 1),
                                    logscale=False)
        return colors

    @property
    def visual_edge_attrs(infr):
        return ['implicit', 'style', 'tail_lp', 'taillabel', 'label', 'lp',
                'headlabel', 'linestyle', 'color', 'stroke', 'lw', 'end_pt',
                'start_pt', 'head_lp', 'alpha', 'ctrl_pts', 'pos', 'zorder']

    def update_visual_attrs(infr, show_cuts=False, show_reviewed_cuts=True,
                            only_reviewed=False):
        if infr.verbose:
            print('[infr] update_visual_attrs')
        #edge2_weight = nx.get_edge_attrs(infr.graph, 'score')
        graph = infr.graph
        ut.nx_delete_edge_attr(graph, 'style')
        ut.nx_delete_edge_attr(graph, 'implicit')
        ut.nx_delete_edge_attr(graph, 'color')
        ut.nx_delete_edge_attr(graph, 'lw')
        ut.nx_delete_edge_attr(graph, 'stroke')
        ut.nx_delete_edge_attr(graph, 'alpha')
        ut.nx_delete_edge_attr(graph, 'linestyle')

        # Set node labels
        node2_aid = nx.get_node_attrs(infr.graph, 'aid')
        node2_nid = nx.get_node_attrs(infr.graph, 'name_label')
        node2_label = {
            #node: '%d:aid=%r' % (node, aid)
            node: 'aid=%r\nnid=%r' % (aid, node2_nid[node])
            for node, aid in node2_aid.items()
        }
        nx.set_node_attributes(infr.graph, 'label', node2_label)

        # Color nodes by name label
        ut.color_nodes(graph, labelattr='name_label')

        # Update color and linewidth based on scores/weight
        edges, edge_weights, edge_colors = infr.get_colored_edge_weights()
        #nx.set_edge_attrs(graph, 'len', _dz(edges, [10]))
        nx.set_edge_attrs(graph, 'color', _dz(edges, edge_colors))
        maxlw = 4
        minlw = .5
        lw = ((maxlw - minlw) * edge_weights + minlw)
        nx.set_edge_attrs(graph, 'lw', _dz(edges, lw))

        # Mark reviewed edges witha stroke
        reviewed_states = nx.get_edge_attrs(graph, 'reviewed_state')

        edge2_stroke = {
            edge: {'linewidth': 3, 'foreground': infr.truth_colors[state]}
            for edge, state in reviewed_states.items()
        }
        nx.set_edge_attrs(graph, 'stroke', edge2_stroke)

        # Are cuts visible or invisible?
        edge2_cut = nx.get_edge_attrs(graph, 'is_cut')
        cut_edges = [edge for edge, cut in edge2_cut.items() if cut]
        nx.set_edge_attrs(graph, 'implicit', _dz(cut_edges, [True]))
        if infr.verbose:
            print('show_cuts = %r' % (show_cuts,))
            print('show_reviewed_cuts = %r' % (show_reviewed_cuts,))
        nx.set_edge_attrs(graph, 'linestyle', _dz(cut_edges, ['dashed']))

        # Non-matching edges should not impose a constraint on the graph layout
        nonmatch_edges = {edge: state for edge, state in reviewed_states.items()
                          if state == 'nonmatch'}
        nx.set_edge_attrs(graph, 'implicit', _dz(nonmatch_edges, [True]))

        if only_reviewed:
            # only reviewed edges contribute
            unreviewed_edges = ut.setdiff(edges, reviewed_states.keys())
            nx.set_edge_attrs(graph, 'implicit', _dz(unreviewed_edges, [True]))
            nx.set_edge_attrs(graph, 'style', _dz(unreviewed_edges, ['invis']))

        if show_cuts or show_reviewed_cuts:
            if not show_cuts:
                nonfeedback_cuts = ut.setdiff(cut_edges, reviewed_states.keys())
                nx.set_edge_attrs(graph, 'style', _dz(nonfeedback_cuts, ['invis']))
        else:
            nx.set_edge_attrs(graph, 'style', _dz(cut_edges, ['invis']))

        # Make MST edge have more alpha
        edge_to_ismst = nx.get_edge_attrs(graph, '_mst_edge')
        mst_edges = [edge for edge, flag in edge_to_ismst.items() if flag]
        nx.set_edge_attrs(graph, 'alpha', _dz(mst_edges, [.5]))

        nodes = list(graph.nodes())
        nx.set_node_attributes(infr.graph, 'zorder', _dz(nodes, [10]))
        nx.set_edge_attributes(infr.graph, 'zorder', _dz(edges, [0]))

        # update the positioning layout
        layoutkw = dict(
            prog='neato',
            #defaultdist=100,
            splines='spline',
            sep=10 / 72,
            #esep=10 / 72
        )
        pt.nx_agraph_layout(graph, inplace=True, **layoutkw)

    def show_graph(infr, use_image=False, only_reviewed=False):
        infr.update_visual_attrs(only_reviewed=only_reviewed)
        plotinfo = pt.show_nx(
            infr.graph, layout='custom', as_directed=False, modify_ax=False,
            use_image=use_image, verbose=0)
        pt.zoom_factory()
        pt.pan_factory(pt.gca())
        plotinfo
        #return plotinfo


@six.add_metaclass(ut.ReloadingMetaclass)
class AnnotInference2(ut.NiceRepr, AnnotInferenceVisualization):
    """
    Sandbox class for maintaining state of an identification

    CommandLine:
        python -m ibeis.viz.viz_graph2 make_qt_graph_interface --show --aids=1,2,3,4,5,6,7,8,9

    """

    truth_texts = {
        0: 'nonmatch',
        1: 'match',
        2: 'notcomp',
        3: 'unreviewed',
    }

    truth_colors = {
        'match': pt.TRUE_GREEN,
        #'match': pt.TRUE_BLUE,
        'nonmatch': pt.FALSE_RED,
        'notcomp': pt.YELLOW,
        'unreviewed': pt.UNKNOWN_PURP
    }

    def __init__(infr, ibs, aids, nids=None, verbose=True):
        infr.verbose = verbose
        if infr.verbose:
            print('[infr] __init__')
        infr.ibs = ibs
        infr.aids = aids
        if nids is None:
            nids = ibs.get_annot_nids(aids)
        infr.orig_name_labels = nids
        #if current_nids is None:
        #    current_nids = nids
        assert len(aids) == len(nids), 'must correspond'
        #assert len(aids) == len(current_nids)
        infr.graph = None
        infr.user_feedback = {}
        infr.thresh = .5
        infr.cm_list = None
        infr.qreq_ = None

    def __nice__(infr):
        if infr.graph is None:
            return '(nAids=%r, G=None)' % (len(infr.aids))
        else:
            return '(nAids=%r, nEdges=%r)' % (len(infr.aids),
                                              infr.graph.number_of_edges())

    def reset_feedback(infr):
        if infr.verbose:
            print('[infr] reset_feedback')
        infr.user_feedback = infr.load_user_feedback()

    def remove_feedback(infr):
        if infr.verbose:
            print('[infr] remove_feedback')
        infr.user_feedback = ut.ddict(list)

    def connected_compoment_subgraphs(infr):
        """
        Two kinds of edges are considered in connected compoment analysis: user
        reviewed edges, and algorithmally inferred edges.  If an inference
        algorithm is not run, then user review is all that matters.
        """
        graph = infr.graph
        # Make a graph where connections do indicate same names
        graph2 = graph.copy()

        reviewed_states = nx.get_edge_attrs(graph, 'reviewed_state')
        #edge_to_ismst = nx.get_edge_attrs(graph, '_mst_edge')

        keep_edges = [key for key, val in reviewed_states.items() if val == 'match']
        #keep_edges += list(edge_to_ismst.keys())

        graph2.remove_edges_from(list(graph2.edges()))
        graph2.add_edges_from(keep_edges)
        ccs = list(nx.connected_components(graph2))
        cc_subgraphs = [graph.subgraph(cc) for cc in ccs]
        return cc_subgraphs

    def connected_compoment_relabel(infr):
        if infr.verbose:
            print('[infr] connected_compoment_relabel')
        cc_subgraphs = infr.connected_compoment_subgraphs()
        num_inconsistent = 0
        num_names = len(cc_subgraphs)

        for count, subgraph in enumerate(cc_subgraphs):
            reviewed_states = nx.get_edge_attrs(subgraph, 'reviewed_state')
            inconsistent_edges = [edge for edge, val in reviewed_states.items()
                                  if val == 'nonmatch']
            if len(inconsistent_edges) > 0:
                #print('Inconsistent')
                num_inconsistent += 1

            nx.set_node_attrs(infr.graph, 'name_label',
                              _dz(list(subgraph.nodes()), [count]))
            # Check for consistency
        return num_names, num_inconsistent

    def load_user_feedback(infr):
        """
        Loads feedback from annotmatch table
        """
        if infr.verbose:
            print('[infr] load_user_feedback')
        ibs = infr.ibs
        aids = infr.aids
        aid_pairs = list(it.combinations(aids, 2))
        am_rowids = ibs.get_annotmatch_rowid_from_undirected_superkey(*zip(*aid_pairs))
        flags = ut.not_list(ut.flag_None_items(am_rowids))
        am_rowids = ut.compress(am_rowids, flags)
        aid_pairs = ut.compress(aid_pairs, flags)
        aids1 = ut.take_column(aid_pairs, 0)
        aids2 = ut.take_column(aid_pairs, 1)

        is_split = ibs.get_annotmatch_prop('SplitCase', am_rowids)
        is_merge = ibs.get_annotmatch_prop('JoinCase', am_rowids)
        is_split = np.array(is_split).astype(np.bool)
        is_merge = np.array(is_merge).astype(np.bool)

        truth = np.array(ibs.get_annotmatch_truth(am_rowids))
        # Hack, if we didnt set it, it probably means it matched
        need_truth = np.array(ut.flag_None_items(truth)).astype(np.bool)
        need_aids1 = ut.compress(aids1, need_truth)
        need_aids2 = ut.compress(aids2, need_truth)
        needed_truth = ibs.get_aidpair_truths(need_aids1, need_aids2)
        truth[need_truth] = needed_truth
        #truth = [
        #    ibs.get_aidpair_truths([aid1], [aid2])[0]
        #    if t is None else t
        #    for t, aid1, aid2 in zip(truth, aids1, aids2)
        #]
        #ut.replace_nones(truth, ibs.const.TRUTH_MATCH)
        truth = np.array(truth, dtype=np.int)
        truth[is_split] = ibs.const.TRUTH_NOT_MATCH
        truth[is_merge] = ibs.const.TRUTH_MATCH

        p_match = (truth == ibs.const.TRUTH_MATCH).astype(np.float)
        p_nomatch = (truth == ibs.const.TRUTH_NOT_MATCH).astype(np.float)
        p_notcomp = (truth == ibs.const.TRUTH_UNKNOWN).astype(np.float)

        # CHANGE OF FORMAT
        user_feedback = ut.ddict(list)
        for count, (aid1, aid2) in enumerate(zip(aids1, aids2)):
            edge = tuple(sorted([aid1, aid2]))
            review = {
                'p_match': p_match[count],
                'p_nomatch': p_nomatch[count],
                'p_notcomp': p_notcomp[count],
            }
            user_feedback[edge].append(review)

        # merge_aid_pairs = ibs.filter_aidpairs_by_tags(has_any='JoinCase')
        # for aid1, aid2 in merge_aid_pairs:
        #     infr.add_feedback(aid1, aid2, 'match')
        return user_feedback

    def initialize_graph(infr):
        if infr.verbose:
            print('[infr] initialize_graph')
        #infr.graph = graph = nx.DiGraph()
        infr.graph = graph = nx.Graph()
        graph.add_nodes_from(infr.aids)

        node2_aid = {aid: aid for aid in infr.aids}
        node2_nid = {aid: nid for aid, nid in
                     zip(infr.aids, infr.orig_name_labels)}
        assert len(node2_nid) == len(node2_aid), '%r - %r' % (
            len(node2_nid), len(node2_aid))
        nx.set_node_attrs(graph, 'aid', node2_aid)
        nx.set_node_attrs(graph, 'name_label', node2_nid)
        nx.set_node_attrs(graph, 'orig_name_label', node2_nid)

    #def add_edges(infr, aid_pairs):
    #    #attr_dict={}):
    #    #, attr_dict)
    #    graph = infr.graph
    #    graph.add_edges_from(aid_pairs)

    def reset_name_labels(infr):
        if infr.verbose:
            print('[infr] reset_name_labels')
        graph = infr.graph
        orig_names = nx.get_node_attrs(graph, 'orig_name_label')
        nx.set_node_attrs(graph, 'name_label', orig_names)

    def lookup_cm(infr, aid1, aid2):
        if infr.cm_list is None:
            return None, aid1, aid2
        aid2_idx = ut.make_index_lookup(
            [cm.qaid for cm in infr.cm_list])
        try:
            idx = aid2_idx[aid1]
            cm = infr.cm_list[idx]
        except KeyError:
            # switch order
            aid1, aid2 = aid2, aid1
            idx = aid2_idx[aid1]
            cm = infr.cm_list[idx]
        return cm, aid1, aid2

    def remove_name_labels(infr):
        if infr.verbose:
            print('[infr] remove_name_labels()')
        graph = infr.graph
        # make distinct names for all nodes
        #import utool
        #with utool.embed_on_exception_context:
        distinct_names = {node: -graph.node[node]['aid'] for node in graph.nodes()}
        nx.set_node_attrs(graph, 'name_label', distinct_names)

    def remove_mst_edges(infr):
        if infr.verbose:
            print('[infr] remove_mst_edges')
        graph = infr.graph
        edge_to_ismst = nx.get_edge_attrs(graph, '_mst_edge')
        mst_edges = [edge for edge, flag in edge_to_ismst.items() if flag]
        graph.remove_edges_from(mst_edges)

    def exec_scoring(infr, vsone=False, prog_hook=None):
        """ Helper """
        if infr.verbose:
            print('[infr] exec_scoring')
        #from ibeis.algo.hots import graph_iden
        ibs = infr.ibs
        aid_list = infr.aids
        cfgdict = {
            'can_match_samename': True,
            'K': 3,
            'Knorm': 3,
            'prescore_method': 'csum',
            'score_method': 'csum'
        }
        # TODO: use current nids
        qreq_ = ibs.new_query_request(aid_list, aid_list, cfgdict=cfgdict)
        cm_list = qreq_.execute(prog_hook=prog_hook)
        vsmany_qreq_ = qreq_
        vsmany_cms = cm_list

        #infr.cm_list = cm_list
        #infr.qreq_ = qreq_

        if vsone:
            # Post process ranks_top and bottom vsmany queries with vsone
            # Execute vsone queries on the best vsmany results
            undirected_edges = get_cm_breaking(qreq_, vsmany_cms,
                                               ranks_top=(vsmany_qreq_.qparams.K + 2),
                                               ranks_bot=(2),)
            parent_rowids = list(undirected_edges.keys())
            # Hack to get around default product of qaids
            qreq_ = ibs.depc.new_request('vsone', [], [], cfgdict={})
            cm_list = qreq_.execute(parent_rowids=parent_rowids,
                                    prog_hook=prog_hook)
        return qreq_, cm_list

    def add_feedback(infr, aid1, aid2, state):
        """ External helepr """
        if infr.verbose:
            print('[infr] add_feedback(%r, %r, %r)' % (aid1, aid2, state))

        edge = tuple(sorted([aid1, aid2]))
        if state == 'unreviewed':
            if edge in infr.user_feedback:
                del infr.user_feedback[edge]
        else:
            review = {
                'p_match': 0.0,
                'p_nomatch': 0.0,
                'p_notcomp': 0.0,
            }
            if state == 'match':
                review['p_match'] = 1.0
            elif state == 'nonmatch':
                review['p_nonmatch'] = 1.0
            elif state == 'notcomp':
                review['p_notcomp'] = 1.0
            else:
                msg = 'state=%r is unknown' % (state,)
                print(msg)
                assert state in infr.truth_texts.values(), msg
            infr.user_feedback[edge].append(review)

    def get_feedback_probs(infr):
        """ Helper """
        unique_pairs = list(infr.user_feedback.keys())
        # Take most recent review
        review_list = [infr.user_feedback[edge][-1] for edge in unique_pairs]
        p_nomatch = np.array(ut.dict_take_column(review_list, 'p_nomatch'))
        p_match = np.array(ut.dict_take_column(review_list, 'p_match'))
        p_notcomp = np.array(ut.dict_take_column(review_list, 'p_notcomp'))
        state_probs = np.vstack([p_nomatch, p_match, p_notcomp])
        review_stateid = state_probs.argmax(axis=0)
        review_state = ut.take(infr.truth_texts, review_stateid)
        p_bg = 0.5  # Needs to be thresh value
        part1 = p_match * (1 - p_notcomp)
        part2 = p_bg * p_notcomp
        p_same_list = part1 + part2
        return p_same_list, unique_pairs, review_state

    def apply_mst(infr):
        if infr.verbose:
            print('[infr] apply_mst')
        # Remove old MST edges
        infr.remove_mst_edges()
        infr.ensure_mst()

    def ensure_mst(infr):
        """
        Use minimum spannning tree to ensure all names are connected

        Needs to be applied after any operation that adds/removes edges
        """
        if infr.verbose:
            print('[infr] ensure_mst')
        import networkx as nx
        # Find clusters by labels
        node2_label = nx.get_node_attrs(infr.graph, 'name_label')
        label2_nodes = ut.group_items(node2_label.keys(), node2_label.values())

        aug_graph = infr.graph.copy().to_undirected()

        # remove cut edges
        edge_to_iscut = nx.get_edge_attrs(aug_graph, 'is_cut')
        cut_edges = [edge for edge, flag in edge_to_iscut.items() if flag]
        aug_graph.remove_edges_from(cut_edges)

        # Enumerate cliques inside labels
        #unflat_edges = [list(ut.product(nodes, nodes)) for nodes in label2_nodes.values()]
        unflat_edges = [list(ut.itertwo(nodes)) for nodes in label2_nodes.values()]
        node_pairs = [tup for tup in ut.iflatten(unflat_edges) if tup[0] != tup[1]]

        # Remove candidate MST edges that exist in the original graph
        orig_edges = list(aug_graph.edges())
        candidate_mst_edges = [edge for edge in node_pairs if not aug_graph.has_edge(*edge)]

        # randomness prevents chains and visually looks better
        rng = np.random.RandomState(42)

        aug_graph.add_edges_from(candidate_mst_edges)
        # Weight edges in aug_graph such that existing edges are chosen
        # to be part of the MST first before suplementary edges.
        nx.set_edge_attributes(aug_graph, 'weight',
                               {edge: 0.1 for edge in orig_edges})
        nx.set_edge_attributes(aug_graph, 'weight',
                               {edge: 10.0 + rng.randint(1, 100)
                                for edge in candidate_mst_edges})
        new_mst_edges = []
        if infr.verbose:
            print('[infr] adding %d MST edges' % (len(new_mst_edges)))
        for cc_sub_graph in nx.connected_component_subgraphs(aug_graph):
            mst_sub_graph = nx.minimum_spanning_tree(cc_sub_graph)
            for edge in mst_sub_graph.edges():
                redge = edge[::-1]
                # Only add if this edge is not in the original graph
                if not (infr.graph.has_edge(*edge) and infr.graph.has_edge(*redge)):
                    new_mst_edges.append(redge)

        # Add new MST edges to original graph
        infr.graph.add_edges_from(new_mst_edges)
        nx.set_edge_attrs(infr.graph, '_mst_edge', _dz(new_mst_edges, [True]))

    def mst_review(infr):
        """
        Adds implicit reviews to connect all ndoes with the same name label
        """
        if infr.verbose:
            print('[infr] ensure_mst')
        import networkx as nx
        # Find clusters by labels
        node2_label = nx.get_node_attrs(infr.graph, 'name_label')
        label2_nodes = ut.group_items(node2_label.keys(), node2_label.values())

        aug_graph = infr.graph.copy().to_undirected()

        # remove cut edges
        edge_to_iscut = nx.get_edge_attrs(aug_graph, 'is_cut')
        cut_edges = [edge for edge, flag in edge_to_iscut.items() if flag]
        aug_graph.remove_edges_from(cut_edges)

        # Enumerate chains inside labels
        unflat_edges = [list(ut.itertwo(nodes)) for nodes in label2_nodes.values()]
        node_pairs = [tup for tup in ut.iflatten(unflat_edges) if tup[0] != tup[1]]

        # Remove candidate MST edges that exist in the original graph
        orig_edges = list(aug_graph.edges())
        candidate_mst_edges = [edge for edge in node_pairs if not aug_graph.has_edge(*edge)]

        aug_graph.add_edges_from(candidate_mst_edges)
        # Weight edges in aug_graph such that existing edges are chosen
        # to be part of the MST first before suplementary edges.

        def get_edge_mst_weights(edge):
            state = aug_graph.get_edge_data(*edge).get('reviewed_state', 'unreviewed')
            is_mst = aug_graph.get_edge_data(*edge).get('_mst_edge', False)
            normscore = aug_graph.get_edge_data(*edge).get('normscore', 0)

            if state == 'match':
                # favor reviewed edges
                weight = .01
            else:
                # faveor states with high scores
                weight = 1 + (1 - normscore)
            if is_mst:
                # try to not use mst edges
                weight += 3.0
            return weight

        rng = np.random.RandomState(42)

        nx.set_edge_attributes(aug_graph, 'weight',
                               {edge: get_edge_mst_weights(edge) for edge in orig_edges})
        nx.set_edge_attributes(aug_graph, 'weight',
                               {edge: 10.0 + rng.randint(1, 100)
                                for edge in candidate_mst_edges})
        new_mst_edges = []
        for cc_sub_graph in nx.connected_component_subgraphs(aug_graph):
            mst_sub_graph = nx.minimum_spanning_tree(cc_sub_graph)
            for edge in mst_sub_graph.edges():
                data = aug_graph.get_edge_data(*edge)
                state = data.get('reviewed_state', 'unreviewed')
                # Append only if this edge needs a review flag
                if state != 'match':
                    new_mst_edges.append(edge)

        if infr.verbose:
            print('[infr] reviewing %d MST edges' % (len(new_mst_edges)))

        # Apply data / add edges if needed
        graph = infr.graph
        for edge in new_mst_edges:
            redge = edge[::-1]
            # Only add if this edge is not in the original graph
            if graph.has_edge(*edge):
                nx.set_edge_attrs(graph, 'reviewed_state', {edge: 'match'})
                infr.add_feedback(edge[0], edge[1], 'match')
            elif graph.has_edge(*redge):
                nx.set_edge_attrs(graph, 'reviewed_state', {redge: 'match'})
                infr.add_feedback(edge[0], edge[1], 'match')
            else:
                graph.add_edge(*edge, attr_dict={
                    '_mst_edge': True, 'reviewed_state': 'match'})
                infr.add_feedback(edge[0], edge[1], 'match')

    def apply_scores(infr, review_cfg={}, prog_hook=None):
        if infr.verbose:
            print('[infr] apply_scores')
        qreq_, cm_list = infr.exec_scoring(vsone=False, prog_hook=prog_hook)
        infr.cm_list = cm_list
        infr.qreq_ = qreq_
        ranks_top = review_cfg.get('ranks_top', 2)
        ranks_bot = review_cfg.get('ranks_bot', 2)
        undirected_edges = get_cm_breaking(qreq_, cm_list,
                                           ranks_top=ranks_top,
                                           ranks_bot=ranks_bot)

        # Do some normalization of scores
        edges = list(undirected_edges.keys())
        edge_scores = np.array(list(ut.take_column(undirected_edges.values(), 'score')))
        edge_ranks = np.array(list(ut.take_column(undirected_edges.values(), 'rank')))
        normscores = edge_scores / np.nanmax(edge_scores)

        infr.remove_mst_edges()

        # Create match-based graph structure
        infr.graph.add_edges_from(edges)
        # Remove existing attrs
        ut.nx_delete_edge_attr(infr.graph, 'score')
        ut.nx_delete_edge_attr(infr.graph, 'rank')
        ut.nx_delete_edge_attr(infr.graph, 'normscore')
        # Add new attrs
        nx.set_edge_attrs(infr.graph, 'score', dict(zip(edges, edge_scores)))
        nx.set_edge_attrs(infr.graph, 'rank', dict(zip(edges, edge_ranks)))
        nx.set_edge_attrs(infr.graph, 'normscore', dict(zip(edges, normscores)))
        infr.thresh = infr.get_threshold()

        infr.ensure_mst()

    def apply_feedback(infr):
        """
        Updates nx graph edge attributes for feedback
        """
        if infr.verbose:
            print('[infr] apply_feedback')
        infr.remove_mst_edges()

        ut.nx_delete_edge_attr(infr.graph, 'reviewed_weight')
        ut.nx_delete_edge_attr(infr.graph, 'reviewed_state')
        p_same_list, unique_pairs_, review_state = infr.get_feedback_probs()
        # Put pair orders in context of the graph
        unique_pairs = [(aid2, aid1) if infr.graph.has_edge(aid2, aid1) else
                        (aid1, aid2) for (aid1, aid2) in unique_pairs_]
        # Ensure edges exist
        for edge in unique_pairs:
            if not infr.graph.has_edge(*edge):
                #print('add review edge = %r' % (edge,))
                infr.graph.add_edge(*edge)
            #else:
            #    #print('have edge edge = %r' % (edge,))
        nx.set_edge_attrs(infr.graph, 'reviewed_state',
                          _dz(unique_pairs, review_state))
        nx.set_edge_attrs(infr.graph, 'reviewed_weight',
                          _dz(unique_pairs, p_same_list))

        infr.ensure_mst()

    def get_threshold(infr):
        # Only use the normalized scores to estimate a threshold
        normscores = np.array(nx.get_edge_attrs(infr.graph, 'normscore').values())
        if infr.verbose:
            print('len(normscores) = %r' % (len(normscores),))
        isvalid = ~np.isnan(normscores)
        curve = np.sort(normscores[isvalid])
        thresh = estimate_threshold(curve, method=None)
        if infr.verbose:
            print('[estimate] thresh = %r' % (thresh,))
        if thresh is None:
            thresh = .5
        infr.thresh = thresh
        return thresh

    def apply_weights(infr):
        """
        Combines scores and user feedback into edge weights used in inference.
        """
        if infr.verbose:
            print('[infr] apply_weights')
        ut.nx_delete_edge_attr(infr.graph, 'cut_weight')
        # mst not needed. No edges are removed

        edges = list(infr.graph.edges())
        edge2_normscore = nx.get_edge_attrs(infr.graph, 'normscore')
        normscores = np.array(ut.dict_take(edge2_normscore, edges, np.nan))

        edge2_reviewed_weight = nx.get_edge_attrs(infr.graph, 'reviewed_weight')
        reviewed_weights = np.array(ut.dict_take(edge2_reviewed_weight,
                                                 edges, np.nan))
        # Combine into weights
        weights = normscores.copy()
        has_review = ~np.isnan(reviewed_weights)
        weights[has_review] = reviewed_weights[has_review]
        # remove nans
        is_valid = ~np.isnan(weights)
        weights = weights.compress(is_valid, axis=0)
        edges = ut.compress(edges, is_valid)
        nx.set_edge_attrs(infr.graph, 'cut_weight', _dz(edges, weights))

    def get_scalars(infr):
        scalars = {}
        scalars['reviewed_weight'] = nx.get_edge_attrs(
            infr.graph, 'reviewed_weight').values()
        scalars['score'] = nx.get_edge_attrs(infr.graph, 'score').values()
        scalars['normscore'] = nx.get_edge_attrs(infr.graph, 'normscore').values()
        scalars[CUT_WEIGHT_KEY] = nx.get_edge_attrs(infr.graph, CUT_WEIGHT_KEY).values()
        return scalars

    def remove_cuts(infr):
        """
        Undo all cuts HACK
        """
        if infr.verbose:
            print('[infr] apply_cuts')
        graph = infr.graph
        infr.ensure_mst()
        ut.nx_delete_edge_attr(graph, 'is_cut')

    def apply_cuts(infr):
        """
        Cuts edges with different names and uncuts edges with the same name
        """
        if infr.verbose:
            print('[infr] apply_cuts')
        graph = infr.graph
        infr.ensure_mst()
        ut.nx_delete_edge_attr(graph, 'is_cut')
        node_to_label = nx.get_node_attrs(graph, 'name_label')
        edge_to_cut = {(u, v): node_to_label[u] != node_to_label[v]
                       for (u, v) in graph.edges()}
        nx.set_edge_attrs(graph, 'is_cut', edge_to_cut)

    def infer_cut(infr, **kwargs):
        """
        Applies name labels based on graph inference and then cuts edges
        """
        from ibeis.algo.hots import graph_iden
        if infr.verbose:
            print('[infr] infer_cut')

        infr.remove_mst_edges()
        infr.model = graph_iden.InfrModel(infr.graph)
        model = infr.model
        thresh = infr.get_threshold()
        #weights = np.array(nx.get_edge_attrs(infr.graph, 'weight').values())
        #isvalid = ~np.isnan(weights)
        #curve = np.sort(weights[isvalid])
        model._update_weights(thresh=thresh)
        labeling, params = model.run_inference2(max_labels=len(infr.aids))
        #min_labels=min_labels, max_labels=max_labels)

        nx.set_node_attrs(infr.graph, 'name_label', model.node_to_label)
        infr.apply_cuts()
        infr.ensure_mst()

    def apply_all(infr):
        if infr.verbose:
            print('[infr] apply_all')
        infr.apply_mst()
        infr.apply_scores()
        infr.apply_feedback()
        infr.apply_weights()
        infr.infer_cut()


def piecewise_weighting(infr, normscores, edges):
    # Old code
    edge_scores = normscores
    # Try to put scores in a 0 to 1 range
    control_points = [
        (0.0, .001),
        (3.0, .05),
        (15.0, .95),
        (None, .99),
    ]
    edge_weights = edge_scores.copy()
    for (pt1, prob1), (pt2, prob2) in ut.itertwo(control_points):
        if pt1 is None:
            pt1 = np.nanmin(edge_scores)
        if pt2 is None:
            pt2 = np.nanmax(edge_scores) + .0001
        pt_len = pt2 - pt1
        prob_len = prob2 - prob1
        flag = np.logical_and(edge_scores >= pt1, edge_scores < pt2)
        edge_weights[flag] = (((edge_scores[flag] - pt1) / pt_len) * prob_len) + prob1

    nx.set_edge_attrs(infr.graph, CUT_WEIGHT_KEY, _dz(edges, edge_weights))

    p_same, unique_pairs = infr.get_feedback_probs()
    unique_pairs = [tuple(x.tolist()) for x in unique_pairs]
    for aid1, aid2 in unique_pairs:
        if not infr.graph.has_edge(aid1, aid2):
            infr.graph.add_edge(aid1, aid2)
    nx.set_edge_attrs(infr.graph, CUT_WEIGHT_KEY, _dz(unique_pairs, p_same))
    #nx.set_edge_attrs(infr.graph, 'lw', _dz(unique_pairs, [6.0]))
    """
    pt.plot(sorted(edge_weights))
    pt.plot(sorted(vt.norm01(edge_scores)))
    """
    #import scipy.special
    #a = 1.5
    #b = 2
    #p_same = scipy.special.expit(b * edge_scores - a)
    #confidence = (2 * np.abs(0.5 - p_same)) ** 2


if __name__ == '__main__':
    r"""
    CommandLine:
        python -m ibeis.algo.hots.graph_iden
        python -m ibeis.algo.hots.graph_iden --allexamples
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()
