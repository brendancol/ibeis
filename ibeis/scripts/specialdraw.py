from __future__ import absolute_import, division, print_function
import utool as ut
(print, rrr, profile) = ut.inject2(__name__, '[specialdraw]')


def double_depcache_graph():
    r"""
    CommandLine:
        python -m ibeis.scripts.specialdraw double_depcache_graph --show --testmode

        python -m ibeis.scripts.specialdraw double_depcache_graph --save=figures5/doubledepc.png --dpath ~/latex/cand/  --diskshow  --figsize=8,20 --dpi=220 --testmode --show --clipwhite
        python -m ibeis.scripts.specialdraw double_depcache_graph --save=figures5/doubledepc.png --dpath ~/latex/cand/  --diskshow  --figsize=8,20 --dpi=220 --testmode --show --clipwhite --arrow-width=.5

        python -m ibeis.scripts.specialdraw double_depcache_graph --save=figures5/doubledepc.png --dpath ~/latex/cand/  --diskshow  --figsize=8,20 --dpi=220 --testmode --show --clipwhite --arrow-width=5


    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.scripts.specialdraw import *  # NOQA
        >>> result = double_depcache_graph()
        >>> print(result)
        >>> ut.quit_if_noshow()
        >>> import plottool as pt
        >>> ut.show_if_requested()
    """
    import ibeis
    import networkx as nx
    import plottool as pt
    pt.ensure_pylab_qt4()
    # pt.plt.xkcd()
    ibs = ibeis.opendb('testdb1')
    reduced = 1
    annot_graph = ibs.depc_annot.make_graph(reduced=reduced)
    image_graph = ibs.depc_image.make_graph(reduced=reduced)
    graph = nx.compose_all([image_graph, annot_graph])
    # userdecision = ut.nx_makenode(graph, 'user decision', shape='rect', color=pt.DARK_YELLOW, style='diagonals')
    # userdecision = ut.nx_makenode(graph, 'user decision', shape='circle', color=pt.DARK_YELLOW)
    userdecision = ut.nx_makenode(graph, 'User decision', shape='rect',
                                  #width=100, height=100,
                                  color=pt.YELLOW, style='diagonals')
    #longcat = True
    longcat = False
    graph.add_edge('detections', userdecision, constraint=longcat)
    graph.add_edge(userdecision, 'annotations', constraint=longcat)
    # graph.add_edge(userdecision, 'annotations', implicit=True, color=[0, 0, 0])
    if not longcat:
        pass
        #graph.add_edge('images', 'annotations', style='invis')
        #graph.add_edge('thumbnails', 'annotations', style='invis')
        #graph.add_edge('thumbnails', userdecision, style='invis')
    graph.remove_node('Has_Notch')
    graph.remove_node('annotmask')
    layoutkw = {
        'ranksep': 5,
        'nodesep': 5,
        'dpi': 96,
        # 'nodesep': 1,
    }

    ns = 1000

    ut.nx_set_default_node_attributes(graph, 'fontsize', 72)
    ut.nx_set_default_node_attributes(graph, 'fontname', 'Ubuntu')
    ut.nx_set_default_node_attributes(graph, 'style',  'filled')

    ut.nx_set_default_node_attributes(graph, 'width', ns * ut.PHI)
    ut.nx_set_default_node_attributes(graph, 'height', ns * (1 / ut.PHI))

    for u, v, d in graph.edges(data=True):
        localid = d.get('local_input_id')
        if localid:
            # d['headlabel'] = localid
            d['taillabel'] = localid
            #d['label'] = localid
            pass
    node_alias = {
        'chips': 'Chip',
        'images': 'Image',
        'feat': 'Feats',
        'featweight': 'Feat Weights',
        'thumbnails': 'Thumbnail',
        'detections': 'Detections',
        'annotations': 'Annotation',
        'Notch_Tips': 'Notch Tips',
        'probchip': 'Prob Chip',
        'Cropped_Chips': 'Croped Chip',
        'Trailing_Edge': 'Trailing\nEdge',
        'Block_Curvature': 'Block\nCurvature',
        # 'BC_DTW': 'block curvature /\n dynamic time warp',
        'BC_DTW': 'DTW Distance',
        'vsone': 'Hots vsone',
        'feat_neighbs': 'Nearest\nNeighbors',
        'neighbor_index': 'Neighbor\nIndex',
        'vsmany': 'Hots vsmany',
        'sver': 'Spatial\nVerification',
    }
    node_alias = ut.delete_dict_keys(node_alias, ut.setdiff(node_alias.keys(), graph.nodes()))
    nx.relabel_nodes(graph, node_alias, copy=False)

    fontkw = dict(fontname='Ubuntu', fontweight='normal', fontsize=12)
    pt.gca().set_aspect('equal')
    pt.figure()
    pt.show_nx(graph, layoutkw=layoutkw, fontkw=fontkw)
    pt.zoom_factory()


def lighten_hex(hexcolor, amount):
    import plottool as pt
    import matplotlib.colors as colors
    return pt.color_funcs.lighten_rgb(colors.hex2color(hexcolor), amount)


def general_identify_flow():
    r"""
    CommandLine:
        python -m ibeis.scripts.specialdraw general_identify_flow --show --save pairsim.png --dpi=100 --diskshow --clipwhite

        python -m ibeis.scripts.specialdraw general_identify_flow --dpi=200 --diskshow --clipwhite --dpath ~/latex/cand/ --figsize=20,10  --save figures4/pairprob.png --arrow-width=2.0


    Example:
        >>> # SCRIPT
        >>> from ibeis.scripts.specialdraw import *  # NOQA
        >>> general_identify_flow()
        >>> ut.quit_if_noshow()
        >>> ut.show_if_requested()
    """
    import networkx as nx
    import plottool as pt
    pt.ensure_pylab_qt4()
    # pt.plt.xkcd()

    graph = nx.DiGraph()

    def makecluster(name, num, **attrkw):
        return [ut.nx_makenode(name + str(n), **attrkw) for n in range(num)]

    def add_edge2(u, v, *args, **kwargs):
        v = ut.ensure_iterable(v)
        u = ut.ensure_iterable(u)
        for _u, _v in ut.product(u, v):
            graph.add_edge(_u, _v, *args, **kwargs)

    # *** Primary color:
    p_shade2 = '#41629A'
    # *** Secondary color
    s1_shade2 = '#E88B53'
    # *** Secondary color
    s2_shade2 = '#36977F'
    # *** Complement color
    c_shade2 = '#E8B353'

    ns = 512

    ut.inject_func_as_method(graph, ut.nx_makenode)

    annot1_color = p_shade2
    annot2_color = s1_shade2
    #annot1_color2 = pt.color_funcs.lighten_rgb(colors.hex2color(annot1_color), .01)

    annot1 = graph.nx_makenode('Annotation X', width=ns, height=ns, groupid='annot', color=annot1_color)
    annot2 = graph.nx_makenode('Annotation Y', width=ns, height=ns, groupid='annot', color=annot2_color)

    featX = graph.nx_makenode('Features X', size=(ns / 1.2, ns / 2), groupid='feats', color=lighten_hex(annot1_color, .1))
    featY = graph.nx_makenode('Features Y', size=(ns / 1.2, ns / 2), groupid='feats', color=lighten_hex(annot2_color, .1))
    #'#4771B3')

    global_pairvec = graph.nx_makenode('Global similarity\n(viewpoint, quality, ...)', width=ns * ut.PHI * 1.2, color=s2_shade2)
    findnn = graph.nx_makenode('Find correspondences\n(nearest neighbors)', shape='ellipse', color=c_shade2)
    local_pairvec = graph.nx_makenode('Local similarities\n(LNBNN, spatial error, ...)',
                                      size=(ns * 2.2, ns), color=lighten_hex(c_shade2, .1))
    agglocal = graph.nx_makenode('Aggregate', size=(ns / 1.1, ns / 2), shape='ellipse', color=lighten_hex(c_shade2, .2))
    catvecs = graph.nx_makenode('Concatenate', size=(ns / 1.1, ns / 2), shape='ellipse', color=lighten_hex(s2_shade2, .1))
    pairvec = graph.nx_makenode('Vector of\npairwise similarities', color=lighten_hex(s2_shade2, .2))
    classifier = graph.nx_makenode('Classifier\n(SVM/RF/DNN)', color=lighten_hex(s2_shade2, .3))
    prob = graph.nx_makenode('Matching Probability\n(same individual given\nsimilar viewpoint)', color=lighten_hex(s2_shade2, .4))

    graph.add_edge(annot1, global_pairvec)
    graph.add_edge(annot2, global_pairvec)

    add_edge2(annot1, featX)
    add_edge2(annot2, featY)

    add_edge2(featX, findnn)
    add_edge2(featY, findnn)

    add_edge2(findnn, local_pairvec)

    graph.add_edge(local_pairvec, agglocal, constraint=True)
    graph.add_edge(agglocal, catvecs, constraint=False)
    graph.add_edge(global_pairvec, catvecs)

    graph.add_edge(catvecs, pairvec)

    # graph.add_edge(annot1, classifier, style='invis')
    # graph.add_edge(pairvec, classifier , constraint=False)
    graph.add_edge(pairvec, classifier)
    graph.add_edge(classifier, prob)

    ut.nx_set_default_node_attributes(graph, 'shape',  'rect')
    #ut.nx_set_default_node_attributes(graph, 'fillcolor', nx.get_node_attributes(graph, 'color'))
    #ut.nx_set_default_node_attributes(graph, 'style',  'rounded')
    ut.nx_set_default_node_attributes(graph, 'style',  'filled,rounded')
    ut.nx_set_default_node_attributes(graph, 'fixedsize', 'true')
    ut.nx_set_default_node_attributes(graph, 'xlabel', nx.get_node_attributes(graph, 'label'))
    ut.nx_set_default_node_attributes(graph, 'width', ns * ut.PHI)
    ut.nx_set_default_node_attributes(graph, 'height', ns)
    ut.nx_set_default_node_attributes(graph, 'regular', False)

    #font = 'MonoDyslexic'
    #font = 'Mono_Dyslexic'
    font = 'Ubuntu'
    ut.nx_set_default_node_attributes(graph, 'fontsize', 72)
    ut.nx_set_default_node_attributes(graph, 'fontname', font)

    #ut.nx_delete_node_attr(graph, 'width')
    #ut.nx_delete_node_attr(graph, 'height')
    #ut.nx_delete_node_attr(graph, 'fixedsize')
    #ut.nx_delete_node_attr(graph, 'style')
    #ut.nx_delete_node_attr(graph, 'regular')
    #ut.nx_delete_node_attr(graph, 'shape')

    #graph.node[annot1]['label'] = "<f0> left|<f1> mid&#92; dle|<f2> right"
    #graph.node[annot2]['label'] = ut.codeblock(
    #    '''
    #    <<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
    #      <TR><TD>left</TD><TD PORT="f1">mid dle</TD><TD PORT="f2">right</TD></TR>
    #    </TABLE>>
    #    ''')
    #graph.node[annot1]['label'] = ut.codeblock(
    #    '''
    #    <<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
    #      <TR><TD>left</TD><TD PORT="f1">mid dle</TD><TD PORT="f2">right</TD></TR>
    #    </TABLE>>
    #    ''')

    #graph.node[annot1]['shape'] = 'none'
    #graph.node[annot1]['margin'] = '0'

    layoutkw = {
        'forcelabels': True,
        'prog': 'dot',
        'rankdir': 'LR',
        # 'splines': 'curved',
        'splines': 'line',
        'samplepoints': 20,
        'showboxes': 1,
        # 'splines': 'polyline',
        #'splines': 'spline',
        'sep': 100 / 72,
        'nodesep': 300 / 72,
        'ranksep': 300 / 72,
        #'inputscale': 72,
        # 'inputscale': 1,
        # 'dpi': 72,
        # 'concentrate': 'true', # merges edge lines
        # 'splines': 'ortho',
        # 'aspect': 1,
        # 'ratio': 'compress',
        # 'size': '5,4000',
        # 'rank': 'max',
    }

    #fontkw = dict(fontfamilty='sans-serif', fontweight='normal', fontsize=12)
    #fontkw = dict(fontname='Ubuntu', fontweight='normal', fontsize=12)
    #fontkw = dict(fontname='Ubuntu', fontweight='light', fontsize=20)
    fontkw = dict(fontname=font, fontweight='light', fontsize=12)
    #prop = fm.FontProperties(fname='/usr/share/fonts/truetype/groovygh.ttf')

    pt.show_nx(graph, layout='agraph', layoutkw=layoutkw, **fontkw)
    pt.zoom_factory()


def graphcut_flow():
    r"""
    Returns:
        ?: name

    CommandLine:
        python -m ibeis.scripts.specialdraw graphcut_flow --show --save cutflow.png --diskshow --clipwhite
        python -m ibeis.scripts.specialdraw graphcut_flow --save figures4/cutiden.png --diskshow --clipwhite --dpath ~/latex/crall-candidacy-2015/ --figsize=24,10 --arrow-width=2.0

    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.scripts.specialdraw import *  # NOQA
        >>> graphcut_flow()
        >>> ut.quit_if_noshow()
        >>> import plottool as pt
        >>> ut.show_if_requested()
    """
    import plottool as pt
    pt.ensure_pylab_qt4()
    import networkx as nx
    # pt.plt.xkcd()

    graph = nx.DiGraph()

    def makecluster(name, num, **attrkw):
        return [ut.nx_makenode(graph, name + str(n), **attrkw) for n in range(num)]

    def add_edge2(u, v, *args, **kwargs):
        v = ut.ensure_iterable(v)
        u = ut.ensure_iterable(u)
        for _u, _v in ut.product(u, v):
            graph.add_edge(_u, _v, *args, **kwargs)

    ns = 512

    # *** Primary color:
    p_shade2 = '#41629A'
    # *** Secondary color
    s1_shade2 = '#E88B53'
    # *** Secondary color
    s2_shade2 = '#36977F'
    # *** Complement color
    c_shade2 = '#E8B353'

    annot1 = ut.nx_makenode(graph, 'Unlabeled\nannotations\n(query)', width=ns, height=ns,
                            groupid='annot', color=p_shade2)
    annot2 = ut.nx_makenode(graph, 'Labeled\nannotations\n(database)', width=ns, height=ns,
                            groupid='annot', color=s1_shade2)
    occurprob = ut.nx_makenode(graph, 'Dense \nprobabilities', color=lighten_hex(p_shade2, .1))
    cacheprob = ut.nx_makenode(graph, 'Cached \nprobabilities', color=lighten_hex(s1_shade2, .1))
    sparseprob = ut.nx_makenode(graph, 'Sparse\nprobabilities', color=lighten_hex(c_shade2, .1))

    graph.add_edge(annot1, occurprob)

    graph.add_edge(annot1, sparseprob)
    graph.add_edge(annot2, sparseprob)
    graph.add_edge(annot2, cacheprob)

    matchgraph = ut.nx_makenode(graph, 'Graph of\npotential matches', color=lighten_hex(s2_shade2, .1))
    cutalgo = ut.nx_makenode(graph, 'Graph cut algorithm', color=lighten_hex(s2_shade2, .2), shape='ellipse')
    cc_names = ut.nx_makenode(graph, 'Identifications,\n splits, and merges are\nconnected compoments', color=lighten_hex(s2_shade2, .3))

    graph.add_edge(occurprob, matchgraph)
    graph.add_edge(sparseprob, matchgraph)
    graph.add_edge(cacheprob, matchgraph)

    graph.add_edge(matchgraph, cutalgo)
    graph.add_edge(cutalgo, cc_names)

    ut.nx_set_default_node_attributes(graph, 'shape',  'rect')
    ut.nx_set_default_node_attributes(graph, 'style',  'filled,rounded')
    ut.nx_set_default_node_attributes(graph, 'fixedsize', 'true')
    ut.nx_set_default_node_attributes(graph, 'width', ns * ut.PHI)
    ut.nx_set_default_node_attributes(graph, 'height', ns * (1 / ut.PHI))
    ut.nx_set_default_node_attributes(graph, 'regular', False)

    layoutkw = {
        'prog': 'dot',
        'rankdir': 'LR',
        'splines': 'line',
        'sep': 100 / 72,
        'nodesep': 300 / 72,
        'ranksep': 300 / 72,
    }

    fontkw = dict(fontname='Ubuntu', fontweight='light', fontsize=14)
    pt.show_nx(graph, layout='agraph', layoutkw=layoutkw, **fontkw)
    pt.zoom_factory()


def merge_viewpoint_graph():
    r"""
    CommandLine:
        python -m ibeis.scripts.specialdraw merge_viewpoint_graph --show

    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.scripts.specialdraw import *  # NOQA
        >>> result = merge_viewpoint_graph()
        >>> print(result)
        >>> ut.quit_if_noshow()
        >>> import plottool as pt
        >>> ut.show_if_requested()
    """
    import plottool as pt
    import ibeis
    import networkx as nx

    defaultdb = 'PZ_Master1'
    ibs = ibeis.opendb(defaultdb=defaultdb)

    #nids = None
    aids = ibs.get_name_aids(4875)
    ibs.print_annot_stats(aids)

    left_aids = ibs.filter_annots_general(aids, view='left')[0:3]
    right_aids = ibs.filter_annots_general(aids, view='right')
    right_aids = list(set(right_aids) - {14517})[0:3]
    back = ibs.filter_annots_general(aids, view='back')[0:4]
    backleft = ibs.filter_annots_general(aids, view='backleft')[0:4]
    backright = ibs.filter_annots_general(aids, view='backright')[0:4]

    right_graph = nx.DiGraph(ut.upper_diag_self_prodx(right_aids))
    left_graph = nx.DiGraph(ut.upper_diag_self_prodx(left_aids))
    back_edges = [
        tuple([back[0], backright[0]][::1]),
        tuple([back[0], backleft[0]][::1]),
    ]
    back_graph = nx.DiGraph(back_edges)

    # Let the graph be a bit smaller

    right_graph.edge[right_aids[1]][right_aids[2]]['constraint'] = ut.get_argflag('--constraint')
    left_graph.edge[left_aids[1]][left_aids[2]]['constraint'] = ut.get_argflag('--constraint')

    #right_graph = right_graph.to_undirected().to_directed()
    #left_graph = left_graph.to_undirected().to_directed()
    nx.set_node_attributes(right_graph, 'groupid', 'right')
    nx.set_node_attributes(left_graph, 'groupid', 'left')

    #nx.set_node_attributes(right_graph, 'scale', .2)
    #nx.set_node_attributes(left_graph, 'scale', .2)
    #back_graph.node[back[0]]['scale'] = 2.3

    nx.set_node_attributes(back_graph, 'groupid', 'back')

    view_graph = nx.compose_all([left_graph, back_graph, right_graph])
    view_graph.add_edges_from([
        [backright[0], right_aids[0]][::-1],
        [backleft[0], left_aids[0]][::-1],
    ])
    pt.ensure_pylab_qt4()
    graph = graph = view_graph  # NOQA
    #graph = graph.to_undirected()

    nx.set_edge_attributes(graph, 'color', pt.DARK_ORANGE[0:3])
    #nx.set_edge_attributes(graph, 'color', pt.BLACK)
    nx.set_edge_attributes(graph, 'color', {edge: pt.LIGHT_BLUE[0:3] for edge in back_edges})

    #pt.close_all_figures();
    from ibeis.viz import viz_graph
    layoutkw = {
        'nodesep': 1,
    }
    viz_graph.viz_netx_chipgraph(ibs, graph, with_images=1, prog='dot',
                                 augment_graph=False, layoutkw=layoutkw)

    if False:
        """
        #view_graph = left_graph
        pt.close_all_figures(); viz_netx_chipgraph(ibs, view_graph, with_images=0, prog='neato')
        #viz_netx_chipgraph(ibs, view_graph, layout='pydot', with_images=False)
        #back_graph = make_name_graph_interaction(ibs, aids=back, with_all=False)

        aids = left_aids + back + backleft + backright + right_aids

        for aid, chip in zip(aids, ibs.get_annot_chips(aids)):
            fpath = ut.truepath('~/slides/merge/aid_%d.jpg' % (aid,))
            vt.imwrite(fpath, vt.resize_to_maxdims(chip, (400, 400)))

        ut.copy_files_to(, )

        aids = ibs.filterannots_by_tags(ibs.get_valid_aids(),
        dict(has_any_annotmatch='splitcase'))

        aid1 = ibs.group_annots_by_name_dict(aids)[252]
        aid2 = ibs.group_annots_by_name_dict(aids)[6791]
        aids1 = ibs.get_annot_groundtruth(aid1)[0][0:4]
        aids2 = ibs.get_annot_groundtruth(aid2)[0]

        make_name_graph_interaction(ibs, aids=aids1 + aids2, with_all=False)

        ut.ensuredir(ut.truthpath('~/slides/split/))

        for aid, chip in zip(aids, ibs.get_annot_chips(aids)):
            fpath = ut.truepath('~/slides/merge/aidA_%d.jpg' % (aid,))
            vt.imwrite(fpath, vt.resize_to_maxdims(chip, (400, 400)))
        """
    pass


def intraoccurrence_connected():
    r"""
    CommandLine:
        python -m ibeis.scripts.specialdraw intraoccurrence_connected --show
        python -m ibeis.scripts.specialdraw intraoccurrence_connected --show --postcut

    Example:
        >>> # DISABLE_DOCTEST
        >>> from ibeis.scripts.specialdraw import *  # NOQA
        >>> result = intraoccurrence_connected()
        >>> print(result)
        >>> ut.quit_if_noshow()
        >>> import plottool as pt
        >>> ut.show_if_requested()
    """
    import ibeis
    import plottool as pt
    from ibeis.viz import viz_graph
    import networkx as nx
    pt.ensure_pylab_qt4()
    ibs = ibeis.opendb(defaultdb='PZ_Master1')
    nid2_aid = {
        #4880: [3690, 3696, 3703, 3706, 3712, 3721],
        4880: [3690, 3696, 3703],
        6537: [3739],
        6653: [7671],
        6610: [7566, 7408],
        #6612: [7664, 7462, 7522],
        #6624: [7465, 7360],
        #6625: [7746, 7383, 7390, 7477, 7376, 7579],
        6630: [7586, 7377, 7464, 7478],
        #6677: [7500]
    }
    nid2_dbaids = {
        4880: [33, 6120, 7164],
        6537: [7017, 7206],
        6653: [7660]
    }
    if ut.get_argflag('--small'):
        del nid2_aid[6630]
        del nid2_aid[6537]
        del nid2_dbaids[6537]
        #del nid2_aid[4880]
        #del nid2_dbaids[4880]

    aids = ut.flatten(nid2_aid.values())

    temp_nids = [1] * len(aids)
    postcut = ut.get_argflag('--postcut')
    aids_list = ibs.group_annots_by_name(aids)[0]
    ensure_edges = 'all' if True or not postcut else None
    unlabeled_graph = viz_graph.make_netx_graph_from_aid_groups(
        ibs, aids_list,
        #invis_edges=invis_edges,
        ensure_edges=ensure_edges, temp_nids=temp_nids)
    viz_graph.color_by_nids(unlabeled_graph, unique_nids=[1] *
                            len(list(unlabeled_graph.nodes())))
    viz_graph.ensure_node_images(ibs, unlabeled_graph)
    nx.set_node_attributes(unlabeled_graph, 'shape', 'rect')
    #unlabeled_graph = unlabeled_graph.to_undirected()

    # Find the "database exemplars for these annots"
    if False:
        gt_aids = ibs.get_annot_groundtruth(aids)
        gt_aids = [ut.setdiff(s, aids) for s in gt_aids]
        dbaids = ut.unique(ut.flatten(gt_aids))
        dbaids = ibs.filter_annots_general(dbaids, minqual='good')
        ibs.get_annot_quality_texts(dbaids)
    else:
        dbaids = ut.flatten(nid2_dbaids.values())
    exemplars = nx.DiGraph()
    #graph = exemplars  # NOQA
    exemplars.add_nodes_from(dbaids)

    def add_clique(graph, nodes, edgeattrs={}, nodeattrs={}):
        edge_list = ut.upper_diag_self_prodx(nodes)
        graph.add_edges_from(edge_list, **edgeattrs)
        return edge_list

    for aids_, nid in zip(*ibs.group_annots_by_name(dbaids)):
        add_clique(exemplars, aids_)
    viz_graph.ensure_node_images(ibs, exemplars)
    viz_graph.color_by_nids(exemplars, ibs=ibs)

    nx.set_node_attributes(unlabeled_graph, 'framewidth', False)
    nx.set_node_attributes(exemplars,  'framewidth', 4.0)

    nx.set_node_attributes(unlabeled_graph, 'group', 'unlab')
    nx.set_node_attributes(exemplars,  'group', 'exemp')

    #big_graph = nx.compose_all([unlabeled_graph])
    big_graph = nx.compose_all([exemplars, unlabeled_graph])

    # add sparse connections from unlabeled to exemplars
    import numpy as np
    rng = np.random.RandomState(0)
    if True or not postcut:
        for aid_ in unlabeled_graph.nodes():
            flags = rng.rand(len(exemplars)) > .5
            nid_ = ibs.get_annot_nids(aid_)
            exnids = np.array(ibs.get_annot_nids(list(exemplars.nodes())))
            flags = np.logical_or(exnids == nid_, flags)
            exmatches = ut.compress(list(exemplars.nodes()), flags)
            big_graph.add_edges_from(list(ut.product([aid_], exmatches)),
                                     color=pt.ORANGE, implicit=True)
    else:
        for aid_ in unlabeled_graph.nodes():
            flags = rng.rand(len(exemplars)) > .5
            exmatches = ut.compress(list(exemplars.nodes()), flags)
            nid_ = ibs.get_annot_nids(aid_)
            exnids = np.array(ibs.get_annot_nids(exmatches))
            exmatches = ut.compress(exmatches, exnids == nid_)
            big_graph.add_edges_from(list(ut.product([aid_], exmatches)))
        pass

    nx.set_node_attributes(big_graph, 'shape', 'rect')
    #if False and postcut:
    #    ut.nx_delete_node_attr(big_graph, 'nid')
    #    ut.nx_delete_edge_attr(big_graph, 'color')
    #    viz_graph.ensure_graph_nid_labels(big_graph, ibs=ibs)
    #    viz_graph.color_by_nids(big_graph, ibs=ibs)
    #    big_graph = big_graph.to_undirected()

    layoutkw = {
        'sep' : 1 / 5,
        'prog': 'neato',
        'overlap': 'false',
        #'splines': 'ortho',
        'splines': 'spline',
    }

    as_directed = False
    #as_directed = True
    #hacknode = True
    hacknode = 0

    graph = big_graph
    ut.nx_ensure_agraph_color(graph)
    if hacknode:
        nx.set_edge_attributes(graph, 'taillabel', {e: str(e[0]) for e in graph.edges()})
        nx.set_edge_attributes(graph, 'headlabel', {e: str(e[1]) for e in graph.edges()})

    explicit_graph = pt.get_explicit_graph(graph)
    _, layout_info = pt.nx_agraph_layout(explicit_graph, orig_graph=graph,
                                         inplace=True, **layoutkw)

    if ut.get_argflag('--small'):
        graph.node[7660]['pos'] = np.array([750, 350])
        graph.node[33]['pos'] = np.array([300, 600]) + np.array([350, -400])
        graph.node[6120]['pos'] = np.array([500, 600]) + np.array([350, -400])
        graph.node[7164]['pos'] = np.array([410, 480]) + np.array([350, -400])
        nx.set_node_attributes(graph, 'pin', 'true')
        _, layout_info = pt.nx_agraph_layout(graph,
                                             inplace=True, **layoutkw)

    if not postcut:
        #pt.show_nx(graph.to_undirected(), layout='agraph', layoutkw=layoutkw,
        #           as_directed=False)
        #pt.show_nx(graph, layout='agraph', layoutkw=layoutkw,
        #           as_directed=as_directed, hacknode=hacknode)

        pt.show_nx(graph, layout='custom', layoutkw=layoutkw,
                   as_directed=as_directed, hacknode=hacknode)
    else:
        #explicit_graph = pt.get_explicit_graph(graph)
        #_, layout_info = pt.nx_agraph_layout(explicit_graph, orig_graph=graph,
        #                                     **layoutkw)

        #layout_info['edge']['alpha'] = .8
        #pt.apply_graph_layout_attrs(graph, layout_info)

        #graph_layout_attrs = layout_info['graph']
        ##edge_layout_attrs  = layout_info['edge']
        ##node_layout_attrs  = layout_info['node']

        #for key, vals in layout_info['node'].items():
        #    #print('[special] key = %r' % (key,))
        #    nx.set_node_attributes(graph, key, vals)

        #for key, vals in layout_info['edge'].items():
        #    #print('[special] key = %r' % (key,))
        #    nx.set_edge_attributes(graph, key, vals)

        #nx.set_edge_attributes(graph, 'alpha', .8)
        #graph.graph['splines'] = graph_layout_attrs.get('splines', 'line')
        #graph.graph['splines'] = 'polyline'   # graph_layout_attrs.get('splines', 'line')
        #graph.graph['splines'] = 'line'

        cut_graph = graph.copy()
        edge_list = list(cut_graph.edges())
        edge_nids = np.array(ibs.unflat_map(ibs.get_annot_nids, edge_list))
        cut_flags = edge_nids.T[0] != edge_nids.T[1]
        cut_edges = ut.compress(edge_list, cut_flags)
        cut_graph.remove_edges_from(cut_edges)
        ut.nx_delete_node_attr(cut_graph, 'nid')
        viz_graph.ensure_graph_nid_labels(cut_graph, ibs=ibs)

        #ut.nx_get_default_node_attributes(exemplars, 'color', None)
        ut.nx_delete_node_attr(cut_graph, 'color', nodes=unlabeled_graph.nodes())
        aid2_color = ut.nx_get_default_node_attributes(cut_graph, 'color', None)
        nid2_colors = ut.group_items(aid2_color.values(), ibs.get_annot_nids(aid2_color.keys()))
        nid2_colors = ut.map_dict_vals(ut.filter_Nones, nid2_colors)
        nid2_colors = ut.map_dict_vals(ut.unique, nid2_colors)
        #for val in nid2_colors.values():
        #    assert len(val) <= 1
        # Get initial colors
        nid2_color_ = {nid: colors_[0] for nid, colors_ in nid2_colors.items()
                       if len(colors_) == 1}

        graph = cut_graph
        viz_graph.color_by_nids(cut_graph, ibs=ibs, nid2_color_=nid2_color_)
        nx.set_node_attributes(cut_graph, 'framewidth', 4)

        pt.show_nx(cut_graph, layout='custom', layoutkw=layoutkw,
                   as_directed=as_directed, hacknode=hacknode)

    pt.zoom_factory()

    # The database exemplars
    # TODO: match these along with the intra encounter set
    #interact = viz_graph.make_name_graph_interaction(
    #    ibs, aids=dbaids, with_all=False, prog='neato', framewidth=True)
    #print(interact)

    # Groupid only works for dot
    #nx.set_node_attributes(unlabeled_graph, 'groupid', 'unlabeled')
    #nx.set_node_attributes(exemplars, 'groupid', 'exemplars')
    #exemplars = exemplars.to_undirected()
    #add_clique(exemplars, aids_, edgeattrs=dict(constraint=False))
    #layoutkw = {}
    #pt.show_nx(exemplars, layout='agraph', layoutkw=layoutkw,
    #           as_directed=False, framewidth=True,)


if __name__ == '__main__':
    r"""
    CommandLine:
        python -m ibeis.scripts.specialdraw
        python -m ibeis.scripts.specialdraw --allexamples
    """
    import multiprocessing
    multiprocessing.freeze_support()  # for win32
    import utool as ut  # NOQA
    ut.doctest_funcs()