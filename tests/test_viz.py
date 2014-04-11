#!/usr/bin/env python
# TODO: ADD COPYRIGHT TAG
from __future__ import absolute_import, division, print_function
#-----
TEST_NAME = 'TEST_VIZ'
#-----
import sys
sys.argv.append('--nogui')
import __testing__
import multiprocessing
import utool
from ibeis.view import viz
from drawtool import draw_func2 as df2
print, print_, printDBG, rrr, profile = utool.inject(__name__, '[%s]' % TEST_NAME)
printTEST = __testing__.printTEST


@__testing__.testcontext2(TEST_NAME)
def TEST_VIZ():
    main_locals = __testing__.main(defaultdb='test_big_ibeis')
    ibs = main_locals['ibs']    # IBEIS Control  # NOQA

    valid_gids = ibs.get_valid_gids()
    valid_rids = ibs.get_valid_rids()

    printTEST('''
    * len(valid_rids) = %r
    * len(valid_gids) = %r
    ''' % (len(valid_rids), len(valid_gids)))
    assert len(valid_gids) > 0, 'database images cannot be empty for test'
    gindex = int(utool.get_arg('--gx', default=0))
    gid = valid_gids[gindex]
    rid_list = ibs.get_rids_in_gids(gid)
    cid_list = ibs.get_roi_cids(rid_list)
    cindex = int(utool.get_arg('--cx', default=0))
    qcid = cid = cid_list[cindex]
    sel_rids = rid_list[1:3]
    qres = ibs.query_database([qcid])[qcid]
    top_cids = qres.get_top_cids(ibs)
    assert len(top_cids) > 0, 'there does not seem to be results'
    cid2 = top_cids[0]  # 294

    #----------------------
    #printTEST('Show Image')
    viz.show_image(ibs, gid, sel_rids=sel_rids, fnum=1)
    df2.set_figtitle('Show Image')

    #----------------------
    #printTEST('Show Chip')
    viz.show_chip(ibs, cid, in_image=False, fnum=2)
    df2.set_figtitle('Show Chip (normal)')
    viz.show_chip(ibs, cid, in_image=True, fnum=3)
    df2.set_figtitle('Show Chip (in_image)')

    #----------------------
    printTEST('Show Query')
    viz.show_chipres(ibs, qres, cid2, fnum=4)
    df2.set_figtitle('Show Chipres')

    viz.show_qres(ibs, qres, fnum=5)
    df2.set_figtitle('Show QRes')

    ##----------------------
    df2.present(wh=1000)
    main_locals.update(locals())
    __testing__.main_loop(main_locals)
    printTEST('return test locals')
    return main_locals


if __name__ == '__main__':
    multiprocessing.freeze_support()  # For windows
    test_locals = TEST_VIZ()
    exec(test_locals['execstr'])
