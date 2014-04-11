# flake8: noqa
from __future__ import absolute_import, division, print_function
# Python
import __builtin__
from collections import OrderedDict, defaultdict
from os.path import (dirname, realpath, join, exists, normpath, splitext,
                     expanduser, relpath)
from itertools import izip, chain, imap, cycle
from itertools import product as iprod
import imp
import itertools
import logging
import multiprocessing
import os
import re
import shutil
import site
import sys
import textwrap
import operator
# Matplotlib
import matplotlib
import matplotlib as mpl
import matplotlib.pyplot as plt
# Scientific
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS
import cv2
from scipy.cluster.hierarchy import fclusterdata
import networkx as netx
try:
    import graph_tool
except ImportError as ex:
    #print('Warning: %r' % ex)
    pass
# Qt
import PyQt4
from PyQt4 import QtCore, QtGui
from PyQt4.Qt import (QAbstractItemModel, QModelIndex, QVariant, QWidget,
                      Qt, QObject, pyqtSlot, QKeyEvent)
# UTool
import utool
from utool import *
# A bit of a hack right now
utool.util_sysreq.ensure_in_pythonpath('hesaff')
# VTool
import vtool
from vtool import chip as ctool
from vtool import image as gtool
from vtool import histogram as htool
from vtool import patch as ptool
from vtool import keypoint as ktool
from vtool import linalg as ltool
from vtool import segmentation

from vtool import *
# DrawTool
import drawtool
from drawtool import draw_func2 as df2
# GUITool
import guitool
# IBEIS DEV
from ibeis.dev import main_api
from ibeis.dev import main_commands
from ibeis.dev import params
# IBEIS MODEL
import ibeis.model
from ibeis.model import Config
from ibeis.model import preproc
from ibeis.model import hots
from ibeis.model.preproc import preproc_image
from ibeis.model.preproc import preproc_chip
from ibeis.model.preproc import preproc_feat
from ibeis.model.hots import matching_functions as mf
from ibeis.model.hots import match_chips3 as mc3
from ibeis.model.hots import match_chips3 as nn_filters
from ibeis.model.hots import QueryResult
from ibeis.model.hots import QueryRequest
from ibeis.model.hots import spatial_verification2 as sv2
from ibeis.model.hots import voting_rules2 as vr2
from ibeis.model.hots import coverage
# IBEIS VIEW
from ibeis.view import viz_helpers as vh
from ibeis.view import viz_image
from ibeis.view import viz_chip
from ibeis.view import viz_matches
from ibeis.view import viz
from ibeis.view import interact
from ibeis.view import guifront
from ibeis.view import guiback
from ibeis.view import gui_item_tables
from ibeis.view import interact
from ibeis.view import interact_helpers
from ibeis.view import interact_image
from ibeis.view import interact_chip
# IBEIS CONTROl
import ibeis.control
from ibeis.control import SQLDatabaseControl
from ibeis.control import __SQLITE3__ as lite
from ibeis.control import IBEIS_SCHEMA
from ibeis.control import IBEISControl
from ibeis.control import accessor_decors


def get_ibeis_modules():
    ibeis_modules = [
        utool,
        vtool,
        guitool,
        drawtool
    ]
    return ibeis_modules
