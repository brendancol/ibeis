# -*- coding: utf-8 -*-
"""
Runs functions in pipeline to get query reuslts and does some caching.
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import utool as ut
import six  # NOQA
from os.path import exists
#from ibeis.algo.hots import query_request
#from ibeis.algo.hots import hots_query_result
#from ibeis.algo.hots import exceptions as hsexcept
from ibeis.algo.hots import chip_match
from ibeis.algo.hots import pipeline
from ibeis.algo.hots import _pipeline_helpers as plh  # NOQA
(print, rrr, profile) = ut.inject2(__name__, '[mc4]')


# TODO: Move to params
USE_HOTSPOTTER_CACHE = pipeline.USE_HOTSPOTTER_CACHE
USE_CACHE    = not ut.get_argflag(('--nocache-query', '--noqcache'))  and USE_HOTSPOTTER_CACHE
USE_BIGCACHE = not ut.get_argflag(('--nocache-big', '--no-bigcache-query', '--noqcache', '--nobigcache')) and ut.USE_CACHE
SAVE_CACHE   = not ut.get_argflag('--nocache-save')
#MIN_BIGCACHE_BUNDLE = 20
#MIN_BIGCACHE_BUNDLE = 150
MIN_BIGCACHE_BUNDLE = 64
HOTS_BATCH_SIZE = ut.get_argval('--hots-batch-size', type_=int, default=None)


#----------------------
# Main Query Logic
#----------------------


def empty_query(ibs, qaids):
    r"""
    Hack to give an empty query a query result object

    Args:
        ibs (IBEISController):  ibeis controller object
        qaids (?):

    Returns:
        tuple: (qaid2_cm, qreq_)

    CommandLine:
        python -m ibeis.algo.hots.match_chips4 --test-empty_query
        python -m ibeis.algo.hots.match_chips4 --test-empty_query --show

    Example:
        >>> # ENABLE_DOCTEST
        >>> from ibeis.algo.hots.match_chips4 import *  # NOQA
        >>> import ibeis
        >>> ibs = ibeis.opendb('testdb1')
        >>> qaids = ibs.get_valid_aids(species=ibeis.const.Species.ZEB_PLAIN)
        >>> # execute function
        >>> (qaid2_cm, qreq_) = empty_query(ibs, qaids)
        >>> # verify results
        >>> result = str((qaid2_cm, qreq_))
        >>> print(result)
        >>> cm = qaid2_cm[qaids[0]]
        >>> ut.assert_eq(len(cm.get_top_aids()), 0)
        >>> ut.quit_if_noshow()
        >>> cm.ishow_top(ibs, update=True, make_figtitle=True, show_query=True, sidebyside=False)
        >>> from matplotlib import pyplot as plt
        >>> plt.show()
    """
    daids = []
    qreq_ = ibs.new_query_request(qaids, daids)
    cm = qreq_.make_empty_chip_matches()
    qaid2_cm = dict(zip(qaids, cm))
    return qaid2_cm, qreq_


def submit_query_request_nocache(ibs, qreq_, verbose=pipeline.VERB_PIPELINE):
    assert len(qreq_.get_external_qaids()) > 0, ' no current query aids'
    if len(qreq_.get_external_daids()) == 0:
        print('[mc4] WARNING no daids... returning empty query')
        qaid2_cm, qreq_ = empty_query(ibs, qreq_.get_external_qaids())
        return qaid2_cm
    save_qcache = False
    qaid2_cm = execute_query2(ibs, qreq_, verbose, save_qcache)
    return qaid2_cm


@profile
def submit_query_request(ibs, qaid_list, daid_list, use_cache=None,
                         use_bigcache=None, cfgdict=None, qreq_=None,
                         verbose=pipeline.VERB_PIPELINE, save_qcache=None,
                         prog_hook=None):
    """
    The standard query interface.

    TODO: rename use_cache to use_qcache

    Checks a big cache for qaid2_cm.  If cache miss, tries to load each cm
    individually.  On an individual cache miss, it preforms the query.

    Args:
        ibs (IBEISController) : ibeis control object
        qaid_list (list): query annotation ids
        daid_list (list): database annotation ids
        use_cache (bool):
        use_bigcache (bool):

    Returns:
        qaid2_cm (dict): dict of QueryResult objects

    CommandLine:
        python -m ibeis.algo.hots.match_chips4 --test-submit_query_request

    Examples:
        >>> # SLOW_DOCTEST
        >>> from ibeis.algo.hots.match_chips4 import *  # NOQA
        >>> import ibeis
        >>> qaid_list = [1]
        >>> daid_list = [1, 2, 3, 4, 5]
        >>> use_bigcache = True
        >>> use_cache = True
        >>> ibs = ibeis.opendb(db='testdb1')
        >>> qreq_ = ibs.new_query_request(qaid_list, daid_list, cfgdict={}, verbose=True)
        >>> qaid2_cm = submit_query_request(ibs, qaid_list, daid_list, use_cache, use_bigcache, qreq_=qreq_)
    """
    # Get flag defaults if necessary
    if use_cache is None:
        use_cache = USE_CACHE
    if save_qcache is None:
        save_qcache = SAVE_CACHE
    if use_bigcache is None:
        use_bigcache = USE_BIGCACHE
    # Create new query request object to store temporary state
    if verbose:
        print(' --- Submit QueryRequest_ --- ')
    assert qreq_ is not None, 'query request must be prebuilt'

    qreq_.prog_hook = prog_hook
    # --- BIG CACHE ---
    # Do not use bigcache single queries
    use_bigcache_ = (use_bigcache and use_cache and
                     len(qaid_list) > MIN_BIGCACHE_BUNDLE)
    if (use_bigcache_ or save_qcache) and len(qaid_list) > MIN_BIGCACHE_BUNDLE:
        bc_dpath = ibs.get_big_cachedir()
        # TODO: SYSTEM : semantic should only be used if name scoring is on
        qhashid = ibs.get_annot_hashid_semantic_uuid(qaid_list, prefix='Q')
        dhashid = ibs.get_annot_hashid_semantic_uuid(daid_list, prefix='D')
        pipe_hashstr = qreq_.get_pipe_hashstr()
        #bc_fname = ''.join((ibs.get_dbname(), '_QRESMAP', qhashid, dhashid, pipe_hashstr))
        bc_fname = ''.join((ibs.get_dbname(), '_BIG_CM', qhashid, dhashid, pipe_hashstr))
        bc_cfgstr = ibs.cfg.query_cfg.get_cfgstr()  # FIXME, rectify w/ qparams
        if use_bigcache_:
            # Try and load directly from a big cache
            try:
                qaid2_cm = ut.load_cache(bc_dpath, bc_fname, bc_cfgstr)
            except IOError:
                pass
            else:
                return qaid2_cm
    # ------------
    # Execute query request
    qaid2_cm = execute_query_and_save_L1(ibs, qreq_, use_cache, save_qcache, verbose=verbose)
    # ------------
    if save_qcache and len(qaid_list) > MIN_BIGCACHE_BUNDLE:
        ut.save_cache(bc_dpath, bc_fname, bc_cfgstr, qaid2_cm)
    return qaid2_cm


@profile
def execute_query_and_save_L1(ibs, qreq_, use_cache, save_qcache, verbose=True, batch_size=None):
    """
    Args:
        ibs (IBEISController):
        qreq_ (QueryRequest):
        use_cache (bool):

    Returns:
        qaid2_cm

    CommandLine:
        python -m ibeis.algo.hots.match_chips4 --test-execute_query_and_save_L1:0
        python -m ibeis.algo.hots.match_chips4 --test-execute_query_and_save_L1:1
        python -m ibeis.algo.hots.match_chips4 --test-execute_query_and_save_L1:2
        python -m ibeis.algo.hots.match_chips4 --test-execute_query_and_save_L1:3


    Example0:
        >>> # SLOW_DOCTEST
        >>> from ibeis.algo.hots.match_chips4 import *  # NOQA
        >>> cfgdict1 = dict(codename='vsmany', sv_on=True)
        >>> ibs, qreq_ = plh.get_pipeline_testdata(cfgdict=cfgdict1, qaid_list=[1, 2, 3, 4])
        >>> use_cache, save_qcache, verbose = False, False, True
        >>> qaid2_cm = execute_query_and_save_L1(ibs, qreq_, use_cache, save_qcache, verbose)
        >>> print(qaid2_cm)

    Example1:
        >>> # SLOW_DOCTEST
        >>> from ibeis.algo.hots.match_chips4 import *  # NOQA
        >>> cfgdict1 = dict(codename='vsone', sv_on=True)
        >>> ibs, qreq_ = plh.get_pipeline_testdata(cfgdict=cfgdict1, qaid_list=[1, 2, 3, 4])
        >>> use_cache, save_qcache, verbose = False, False, True
        >>> qaid2_cm = execute_query_and_save_L1(ibs, qreq_, use_cache, save_qcache, verbose)
        >>> print(qaid2_cm)

    Example1:
        >>> # SLOW_DOCTEST
        >>> # TEST SAVE
        >>> from ibeis.algo.hots.match_chips4 import *  # NOQA
        >>> cfgdict1 = dict(codename='vsmany', sv_on=True)
        >>> ibs, qreq_ = plh.get_pipeline_testdata(cfgdict=cfgdict1, qaid_list=[1, 2, 3, 4])
        >>> use_cache, save_qcache, verbose = False, True, True
        >>> qaid2_cm = execute_query_and_save_L1(ibs, qreq_, use_cache, save_qcache, verbose)
        >>> print(qaid2_cm)

    Example2:
        >>> # SLOW_DOCTEST
        >>> # TEST LOAD
        >>> from ibeis.algo.hots.match_chips4 import *  # NOQA
        >>> cfgdict1 = dict(codename='vsmany', sv_on=True)
        >>> ibs, qreq_ = plh.get_pipeline_testdata(cfgdict=cfgdict1, qaid_list=[1, 2, 3, 4])
        >>> use_cache, save_qcache, verbose = True, True, True
        >>> qaid2_cm = execute_query_and_save_L1(ibs, qreq_, use_cache, save_qcache, verbose)
        >>> print(qaid2_cm)

    Example2:
        >>> # ENABLE_DOCTEST
        >>> # TEST PARTIAL HIT
        >>> from ibeis.algo.hots.match_chips4 import *  # NOQA
        >>> cfgdict1 = dict(codename='vsmany', sv_on=False, prescore_method='csum')
        >>> #ibs.cfg.other_cfg.hots_batch_size = 2
        >>> ibs, qreq_ = plh.get_pipeline_testdata(cfgdict=cfgdict1, qaid_list=[1, 2, 3, 4, 5, 6, 7, 8, 9])
        >>> use_cache, save_qcache, verbose = False, True, False
        >>> qaid2_cm = execute_query_and_save_L1(ibs, qreq_, use_cache, save_qcache, verbose, batch_size=3)
        >>> cm = qaid2_cm[1]
        >>> ut.delete(cm.get_fpath(qreq_))
        >>> cm = qaid2_cm[4]
        >>> ut.delete(cm.get_fpath(qreq_))
        >>> cm = qaid2_cm[5]
        >>> ut.delete(cm.get_fpath(qreq_))
        >>> cm = qaid2_cm[6]
        >>> ut.delete(cm.get_fpath(qreq_))
        >>> print('Re-execute')
        >>> qaid2_cm_ = execute_query_and_save_L1(ibs, qreq_, use_cache, save_qcache, verbose, batch_size=3)
        >>> assert all([qaid2_cm_[qaid] == qaid2_cm[qaid] for qaid in qreq_.get_external_qaids()])
        >>> [ut.delete(fpath) for fpath in qreq_.get_chipmatch_fpaths(qreq_.get_external_qaids())]

    Ignore:
        other = cm_ = qaid2_cm_[qaid]
        cm = qaid2_cm[qaid]
    """
    #print('[q1] execute_query_and_save_L1()')
    if use_cache:
        if ut.VERBOSE:
            print('[mc4] cache-query is on')
        if ut.DEBUG2:
            # sanity check
            qreq_.assert_self(ibs)
        # Try loading as many cached results as possible
        qaid2_cm_hit = {}
        external_qaids = qreq_.get_external_qaids()
        fpath_list = qreq_.get_chipmatch_fpaths(external_qaids)
        exists_flags = [exists(fpath) for fpath in fpath_list]
        qaids_hit = ut.list_compress(external_qaids, exists_flags)
        fpaths_hit = ut.list_compress(fpath_list, exists_flags)
        fpath_iter = ut.ProgressIter(
            fpaths_hit, nTotal=len(fpaths_hit), enabled=len(fpaths_hit) > 1,
            lbl='loading cache hits', adjust=True, freq=1)
        cm_hit_list = [
            chip_match.ChipMatch.load_from_fpath(fpath, verbose=False)
            for fpath in fpath_iter
        ]
        assert all([qaid == cm.qaid for qaid, cm in zip(qaids_hit, cm_hit_list)]), 'inconsistent'
        qaid2_cm_hit = {cm.qaid: cm for cm in cm_hit_list}
        #qaid2_cm_hit = {qaid: cm for qaid, cm in zip(qaids_hit, cm_hit_list)}
        if len(qaid2_cm_hit) == len(external_qaids):
            return qaid2_cm_hit
        else:
            if len(qaid2_cm_hit) > 0 and not ut.QUIET:
                print('... partial cm cache hit %d/%d' % (
                    len(qaid2_cm_hit), len(external_qaids)))
        cachehit_qaids = list(qaid2_cm_hit.keys())
        # mask queries that have already been executed
        qreq_.set_external_qaid_mask(cachehit_qaids)
    else:
        if ut.VERBOSE:
            print('[mc4] cache-query is off')
        qaid2_cm_hit = {}
    qaid2_cm = execute_query2(ibs, qreq_, verbose, save_qcache, batch_size)
    if ut.DEBUG2:
        # sanity check
        qreq_.assert_self(ibs)
    # Merge cache hits with computed misses
    if len(qaid2_cm_hit) > 0:
        qaid2_cm.update(qaid2_cm_hit)
    qreq_.set_external_qaid_mask(None)  # undo state changes
    return qaid2_cm


@profile
def execute_query2(ibs, qreq_, verbose, save_qcache, batch_size=None):
    """
    Breaks up query request into several subrequests
    to process "more efficiently" and safer as well.
    """
    qreq_.lazy_preload(verbose=verbose and ut.NOT_QUIET)
    all_qaids = qreq_.get_external_qaids()
    print('len(missed_qaids) = %r' % (len(all_qaids),))
    qaid2_cm = {}
    # vsone must have a chunksize of 1
    if batch_size is None:
        if HOTS_BATCH_SIZE is None:
            hots_batch_size = ibs.cfg.other_cfg.hots_batch_size
        else:
            hots_batch_size = HOTS_BATCH_SIZE
    else:
        hots_batch_size = batch_size
    chunksize = 1 if qreq_.qparams.vsone else hots_batch_size
    # Iterate over vsone queries in chunks. This ensures that we dont lose
    # too much time if a qreq_ crashes after the 2000th nn index.
    nTotalChunks    = ut.get_nTotalChunks(len(all_qaids), chunksize)
    qaid_chunk_iter = ut.ichunks(all_qaids, chunksize)
    _qreq_iter = (
        qreq_.shallowcopy(qaids=qaids)
        for qaids in qaid_chunk_iter
    )
    sub_qreq_iter = ut.ProgressIter(
        _qreq_iter, nTotal=nTotalChunks, freq=1,
        lbl='[mc4] query chunk: ',
        prog_hook=qreq_.prog_hook)
    for sub_qreq_ in sub_qreq_iter:
        if ut.VERBOSE:
            print('Generating vsmany chunk')
        sub_cm_list = pipeline.request_ibeis_query_L0(
            ibs, sub_qreq_, verbose=verbose)
        assert len(sub_qreq_.get_external_qaids()) == len(sub_cm_list)
        assert all([qaid == cm.qaid for qaid, cm in zip(sub_qreq_.get_external_qaids(), sub_cm_list)])
        if save_qcache:
            fpath_list = qreq_.get_chipmatch_fpaths(sub_qreq_.get_external_qaids())
            _iter = zip(sub_cm_list, fpath_list)
            _iter = ut.ProgressIter(_iter, nTotal=len(sub_cm_list),
                                    lbl='saving chip matches', adjust=True, freq=1)
            for cm, fpath in _iter:
                cm.save_to_fpath(fpath, verbose=False)
        else:
            if ut.VERBOSE:
                print('[mc4] not saving vsmany chunk')
        qaid2_cm.update({cm.qaid: cm for cm in sub_cm_list})
    return qaid2_cm


if __name__ == '__main__':
    """
    python -m ibeis.algo.hots.match_chips4
    python -m ibeis.algo.hots.match_chips4 --allexamples --testslow
    python -m ibeis.algo.hots.match_chips4 --test-execute_query_and_save_L1
    """
    import multiprocessing
    multiprocessing.freeze_support()
    ut.doctest_funcs()
