"""
Small GUI for asking the user to enter the clock time shown, and moving along a gid list if the first image isn't a clock
"""
from __future__ import absolute_import, division, print_function
from functools import partial
from guitool import qtype, APIItemWidget, APIItemModel, FilterProxyModel, ChangeLayoutContext
from guitool.__PYQT__ import QtGui, QtCore
from guitool.__PYQT__.QtCore import Qt
from ibeis import ibsfuncs
from ibeis.dev import results_organizer
from ibeis.viz import interact
from ibeis.viz import viz_helpers as vh
from plottool import fig_presenter
from plottool import interact_helpers as ih
from plottool import imshow, close_figure, next_fnum
from six.moves import range
import guitool
import numpy as np
import six
import utool
import utool as ut
from datetime import date, datetime
from time import mktime
(print, print_, printDBG, rrr, profile) = utool.inject(__name__, '[co_gui]')



class ClockOffsetWidget(QtGui.QWidget):

    def __init__(co_wgt, ibs, gid_list, parent=None):
        print('[co_gui] Initializing')
        QtGui.QWidget.__init__(co_wgt, parent=parent)

        co_wgt.fnum = next_fnum()

        co_wgt.main_layout = QtGui.QVBoxLayout(co_wgt)
        co_wgt.button_layout = guitool.newWidget(co_wgt, orientation=Qt.Horizontal)
        co_wgt.main_layout.addWidget(co_wgt.button_layout)

        co_wgt.combo_layout = guitool.newWidget(co_wgt, orientation=Qt.Horizontal)
        co_wgt.main_layout.addWidget(co_wgt.combo_layout)
        #co_wgt.combo_layout = QtGui.QHBoxLayout(co_wgt)#.main_layout)
        #co_wgt.button_layout = QtGui.QHBoxLayout(co_wgt)#.main_layout)

        co_wgt.imfig = None
        co_wgt.imax = None

        co_wgt.ibeis = ibs
        co_wgt.gid_list = gid_list
        co_wgt.current_gindex = 0
        co_wgt.offset = 0
        # Set image datetime with first image
        co_wgt.get_image_datetime()
        co_wgt.add_combo_boxes()
        co_wgt.add_buttons()
        co_wgt.update_ui()


    def get_image_datetime(co_wgt):
        # Function that extracts the unixtime from an image and stores it
        utime = co_wgt.ibeis.get_image_unixtime(co_wgt.gid_list[co_wgt.current_gindex])
        co_wgt.dtime = datetime.fromtimestamp(utime)

    def update_ui(co_wgt):
        if co_wgt.current_gindex == 0:
            co_wgt.button_list[0].setEnabled(False)
        else:
            co_wgt.button_list[0].setEnabled(True)
        if co_wgt.current_gindex == len(co_wgt.gid_list) - 1:
            co_wgt.button_list[1].setEnabled(False)
        else:
            co_wgt.button_list[1].setEnabled(True)

        #TODO Either integrate this into utool or check if it's already there
        extract_tuple = lambda li, idx: list(zip(*li)[idx])
        # Update option setting, assume datetime has been updated
        co_wgt.combo_list[0].setCurrentIndex(extract_tuple(co_wgt.opt_list['year'],1).index(co_wgt.dtime.year))
        co_wgt.combo_list[1].setCurrentIndex(extract_tuple(co_wgt.opt_list['month'],1).index(co_wgt.dtime.month))
        co_wgt.combo_list[2].setCurrentIndex(extract_tuple(co_wgt.opt_list['day'],1).index(co_wgt.dtime.day))
        co_wgt.combo_list[3].setCurrentIndex(extract_tuple(co_wgt.opt_list['hour'],1).index(co_wgt.dtime.hour))
        co_wgt.combo_list[4].setCurrentIndex(extract_tuple(co_wgt.opt_list['minute'],1).index(co_wgt.dtime.minute))
        co_wgt.combo_list[5].setCurrentIndex(extract_tuple(co_wgt.opt_list['second'],1).index(co_wgt.dtime.second))

        # Redraw image
        if co_wgt.imfig is not None:
            close_figure(co_wgt.imfig)
        co_wgt.imfig, co_wgt.imax = imshow(ibs.get_images(co_wgt.gid_list[co_wgt.current_gindex]), fnum=co_wgt.fnum)
        co_wgt.imfig.show()

    def add_buttons(co_wgt):
        _BUTTON = partial(guitool.newButton, parent=co_wgt)
        co_wgt.button_list = [
            _BUTTON(text='Previous Image',
                    clicked=co_wgt.go_prev),
            _BUTTON(text='Next Image',
                    clicked=co_wgt.go_next),
            _BUTTON(text='Skip',
                    clicked=co_wgt.cancel),
            _BUTTON(text='Set',
                    clicked=co_wgt.accept),
        ]
        # Copying from inspect_gui

        for button in co_wgt.button_list:
            co_wgt.button_layout.addWidget(button)

    def add_combo_boxes(co_wgt):
        _CBOX = partial(guitool.newComboBox, parent=co_wgt)
        to_opt_list = lambda x: [(str(i), i) for i in x]
        co_wgt.opt_list = {
                'year': to_opt_list(range(1969, date.today().year+1)),
                'month': to_opt_list(range(1,13)),
                'day': to_opt_list(range(1,32)), # yes this will allow invalid dates, but it's not a real issue
                'hour': to_opt_list(range(24)),
                'minute': to_opt_list(range(60)),
                'second': to_opt_list(range(60)),
        }
        co_wgt.combo_list = [
                _CBOX(changed=partial(co_wgt.change_dt, 'year'),
                    options=co_wgt.opt_list['year'], default=str(co_wgt.dtime.year)),
                _CBOX(changed=partial(co_wgt.change_dt, 'month'),
                    options=co_wgt.opt_list['month'], default=str(co_wgt.dtime.month)),
                _CBOX(changed=partial(co_wgt.change_dt, 'day'),
                    options=co_wgt.opt_list['day'], default=str(co_wgt.dtime.day)),
                _CBOX(changed=partial(co_wgt.change_dt, 'hour'),
                    options=co_wgt.opt_list['hour'], default=str(co_wgt.dtime.hour)),
                _CBOX(changed=partial(co_wgt.change_dt, 'minute'),
                    options=co_wgt.opt_list['minute'], default=str(co_wgt.dtime.minute)),
                _CBOX(changed=partial(co_wgt.change_dt, 'second'),
                    options=co_wgt.opt_list['second'], default=str(co_wgt.dtime.second)),
        ]

        for combo in co_wgt.combo_list:
            co_wgt.combo_layout.addWidget(combo)

    @guitool.slot_()
    def go_prev(co_wgt):
        # Decrement current gid index, then call update
        co_wgt.current_gindex -= 1
        co_wgt.get_image_datetime()
        co_wgt.update_ui()

    @guitool.slot_()
    def go_next(co_wgt):
        # Increment current gid index, then call update
        co_wgt.current_gindex += 1
        co_wgt.get_image_datetime()
        co_wgt.update_ui()

    @guitool.slot_()
    def cancel(co_wgt):
        # Just close
        close_figure(co_wgt.imfig)
        co_wgt.close()

    @guitool.slot_()
    def accept(co_wgt):
        # Calculate offset
        # Get current image's actual time
        image_time = co_wgt.ibeis.get_image_unixtime(co_wgt.gid_list[co_wgt.current_gindex])
        # Get unixtime from current dtime
        #TODO put into utool
        input_time = mktime(co_wgt.dtime.timetuple())
        # Go through gid list, and add that offset to every unixtime
        offset = input_time - image_time
        print("[co_gui] Unixtime offset is %d" % offset)
        # Set the unixtimes with the new ones
        utimes = ibs.get_image_unixtime(co_wgt.gid_list)
        new_utimes = [time+offset for time in utimes]
        ibs.set_image_unixtime(co_wgt.gid_list, new_utimes)
        # Close
        close_figure(co_wgt.imfig)
        co_wgt.close()

    @guitool.slot_(str, int, str)
    def change_dt(co_wgt, attr, val_ind, val):
        co_wgt.dtime = co_wgt.dtime.replace(**{attr:co_wgt.opt_list[attr][val_ind][1]})
        print("[co_gui] Base datetime is %r" % co_wgt.dtime)


if __name__ == "__main__":
    import ibeis
    main_locals = ibeis.main(db='testdb1')
    ibs = main_locals['ibs']
    gid_list = ibs.get_valid_gids()
    co = ClockOffsetWidget(ibs, gid_list)
    co.show()

    ibeis.main_loop(main_locals)



