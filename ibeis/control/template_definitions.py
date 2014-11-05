import utool as ut

"""
CommandLine:
    python ibeis/control/templates.py
"""

Theader_ibeiscontrol = ut.codeblock(
    r'''
    # STARTBLOCK
    # AUTOGENERATED ON {timestamp}
    """
    ToRegenerate:
    python ibeis/control/templates.py --dump-autogen-controller
    """
    from __future__ import absolute_import, division, print_function
    import functools  # NOQA
    import six  # NOQA
    from six.moves import map, range  # NOQA
    from ibeis import constants
    from ibeis.control.IBEISControl import IBEISController
    import utool  # NOQA
    import utool as ut  # NOQA
    print, print_, printDBG, rrr, profile = ut.inject(__name__, '[autogen_ibsfuncs]')

    # Create dectorator to inject these functions into the IBEISController
    register_ibs_aliased_method   = ut.make_class_method_decorator((IBEISController, 'autogen'))
    register_ibs_unaliased_method = ut.make_class_method_decorator((IBEISController, 'autogen'))


    def register_ibs_method(func):
        aliastup = (func, 'autogen_' + ut.get_funcname(func))
        register_ibs_unaliased_method(func)
        register_ibs_aliased_method(aliastup)
    # ENDBLOCK
    ''')

#
#
#-----------------
# --- CONFIG ---
#-----------------

Tcfg_config_rowid_getter = ut.codeblock(
    r'''
    # STARTBLOCK
    #@ider
    def get_{child}_config_rowid({self}, qreq_=None):
        """
        returns config_rowid of the current configuration
        Config rowids are always ensured

        Tcfg_config_rowid_getter

        Example:
            >>> import ibeis; ibs = ibeis.opendb('testdb1')
        """
        if qreq_ is not None:
            {child}_cfg_suffix = qreq_.qparams.{child}_cfgstr
            # TODO store config_rowid in qparams
        else:
            {child}_cfg_suffix = {self}.cfg.{child}_cfg.get_cfgstr()
        {child}_cfg_rowid = {self}.add_config({child}_cfg_suffix)
        return {child}_cfg_rowid
    # ENDBLOCK
    '''
)

#
#
#-----------------
# --- IDERS ---
#-----------------


Tider_all_rowids = ut.codeblock(
    r'''
    # STARTBLOCK
    @ider
    def _get_all_{tbl}_rowids({self}):
        """
        Tider_all_rowids

        Returns:
            list_ (list): unfiltered {tbl}_rowids
        """
        all_{tbl}_rowids = {self}.{dbself}.get_all_rowids({TABLE})
        return all_{tbl}_rowids
    # ENDBLOCK
    '''
)


#
#
#-----------------
# --- ADDERS ---
#-----------------


Tadder_dependant_child = ut.codeblock(
    r'''
    # STARTBLOCK
    #@adder
    def add_{parent}_{child}({self}, {parent}_rowid_list, qreq_=None):
        """
        Adds / ensures / computes a dependant property

        Tadder_dependant_child

        returns config_rowid of the current configuration
        """
        raise NotImplementedError('this code is a stub, you must populate it')
        from ibeis.model.preproc import preproc_{child}
        config_rowid = {self}.get_{child}_config_rowid(qreq_=qreq_)
        {child}_rowid_list = ibs.get_{parent}_{child}_rowids({parent}_rowid_list, qreq_=qreq_, ensure=False)
        dirty_{parent}_rowid_list = utool.get_dirty_items({parent}_rowid_list, {child}_rowid_list)
        if len(dirty_{parent}_rowid_list) > 0:
            if utool.VERBOSE:
                print('[ibs] adding %d / %d {child}' % (len(dirty_{parent}_rowid_list), len({parent}_rowid_list)))

            get_rowid_from_superkey = functools.partial(ibs.get_{parent}_{child}_rowids, ensure=False)
            ###
            colnames = {nonprimary_child_colnames}
            {child_other_propname_lists} = preproc_{child}.add_{child}_params_gen(ibs, {parent}_rowid_list)
            params_iter = (({parent}_rowid, config_rowid, {child_other_propnames}) for {parent}_rowid, {child_other_propnames} in
                           zip({parent}_rowid_list, {child_other_propname_lists}))
            ###
            # params_iter = preproc_{child}.add_{child}_params_gen(ibs, dirty_{parent}_rowid_list)
            # params_iter = params_list
            {child}_rowid_list = ibs.dbcache.add_cleanly({TABLE}, colnames, params_iter, get_rowid_from_superkey)
        return {child}_rowid_list
    # ENDBLOCK
    '''
)

#
#
#-----------------
# --- GETTERS ---
#-----------------

# CHILD ROWID GETTERS

Tline_pc_dependant_rowid = ut.codeblock(
    r'''
    # STARTBLOCK
    {child}_rowid_list = {self}.get_{parent}_{child}_rowids({parent}_rowid_list, qreq_=qreq_)
    # ENDBLOCK
    '''
)

Tgetter_rl_pclines_dependant_column = ut.codeblock(
    r'''
    # STARTBLOCK
    #@getter
    def get_{root}_{col}({self}, {root}_rowid_list, qreq_=None):
        """ get {col} data of the {parent} table using the dependant {child} table

        Tgetter_rl_pclines_dependant_column

        Args:
            {parent}_rowid_list (list):

        Returns:
            list: {col}_list
        """
        {pc_dependant_rowid_lines}
        {col}_list = {self}.get_{leaf}_{col}({leaf}_rowid_list, qreq_=qreq_)
        return {col}_list
    # ENDBLOCK
    ''')

Tgetter_rl_dependant_all_rowids = ut.codeblock(
    r'''
    # STARTBLOCK
    #@getter
    def get_{root}_{leaf}_all_rowids({self}, {root}_rowid_list, eager=True, nParams=None):
        """
        get_{root}_{leaf}_rowids

        get {leaf} rowids of {root} under the current state configuration

        Tgetter_rl_dependant_all_rowids

        Args:
            {root}_rowid_list (list):

        Returns:
            list: {leaf}_rowid_list
        """
        colnames = ({LEAF_PARENT}_ROWID,)
        {leaf}_rowid_list = {self}.{dbself}.get(
            {LEAF_TABLE}, colnames, {root}_rowid_list,
            id_colname={ROOT}_ROWID, eager=eager, nParams=nParams)
        return {leaf}_rowid_list
    # ENDBLOCK
    ''')

Tgetter_rl_dependant_rowids = ut.codeblock(
    r'''
    # STARTBLOCK
    #@getter
    def get_{root}_{leaf}_rowids({self}, {root}_rowid_list, qreq_=None, ensure=True, eager=True, nParams=None):
        """
        get_{root}_{leaf}_rowids

        get {leaf} rowids of {root} under the current state configuration

        Tgetter_rl_dependant_rowids

        Args:
            {root}_rowid_list (list):

        Returns:
            list: {leaf}_rowid_list
        """
        if ensure:
            {self}.add_{leaf}s({root}_rowid_list)
        colnames = ({LEAF}_ROWID,)
        config_rowid = {self}.get_{leaf}_config_rowid(qreq_=qreq_)
        andwhere_colnames = [{ROOT}_ROWID, CONFIG_ROWID]
        params_iter = (({root}_rowid, config_rowid,) for {root}_rowid in {root}_rowid_list)
        {leaf}_rowid_list = {self}.{dbself}.get_where2(
            {LEAF_TABLE}, colnames, params_iter, andwhere_colnames, eager=eager, nParams=nParams)
        return {leaf}_rowid_list
    # ENDBLOCK
    ''')

Tgetter_table_column = ut.codeblock(
    r'''
    # STARTBLOCK
    #@getter
    def get_{tbl}_{col}({self}, {tbl}_rowid_list, eager=True):
        """gets data from the level 0 column "{col}" in the "{tbl}" table

        Tgetter_table_column

        Args:
            {tbl}_rowid_list (list):

        Returns:
            list: {col}_list
        """
        id_iter = {tbl}_rowid_list
        colnames = ({COLNAME},)
        {col}_list = {self}.dbcache.get({TABLE}, colnames, id_iter, id_colname='rowid', eager=eager)
        return {col}_list
    # ENDBLOCK
    ''')

Tgetter_pc_dependant_column = ut.codeblock(
    r'''
    # STARTBLOCK
    #@getter
    def get_{parent}_{col}({self}, {parent}_rowid_list, qreq_=None):
        """
        get {col} data of the {parent} table using the dependant {child} table

        Tgetter_pc_dependant_column

        Args:
            {parent}_rowid_list (list):

        Returns:
            list: {col}_list
        """
        {child}_rowid_list = {self}.get_{parent}_{child}_rowids({parent}_rowid_list)
        {col}_list = {self}.get_{child}_{col}({child}_rowid_list, qreq_=qreq_)
        return {col}_list
    # ENDBLOCK
    ''')

Tgetter_native_rowid_from_superkey = ut.codeblock(
    r'''
    # STARTBLOCK
    #@getter
    def get_{tbl}_rowid_from_superkey({self}, {superkey_args},
                                      eager=False, nParams=None):
        """
        Tgetter_native_rowid_from_superkey

        Args:
            superkey lists: {superkey_args}

        Returns:
            {tbl}_rowid_list
        """
        colnames = ({TBL}_ROWID),
        # FIXME: col_rowid is not correct
        params_iter = zip({superkey_args})
        andwhere_colnames = [{superkey_args}]
        {tbl}_rowid_list = {self}.{dbself}.get_where2(
            {TABLE}, colnames, params_iter, andwhere_colnames, eager=eager,
            nParams=nParams)
        return {tbl}_rowid_list
    # ENDBLOCK
    ''')

#id_iter = (({tbl}_rowid,) for {tbl}_rowid in {tbl}_rowid_list)


#
#
#-----------------
# --- SETTERS ---
#-----------------

#
#
#-----------------
# --- DELETERS ---
#-----------------


# ========
# UNFINISHED
# ========


# eg. get_chip_sizes
Tgetter_native_multicolumn = ut.codeblock(
    r'''
    # STARTBLOCK
    #@getter
    def get_{tbl}_{multicol}({self}, {tbl}_rowid_list):
        """
        Returns zipped tuple of information from {multicol} columns

        Tgetter_native_multicolumn

        Args:
            {tbl}_rowid_list (list):

        Returns:
            list: {multicol}_list
        """
        {multicol}_list  = ibs.dbcache.get({TABLE}, ({MULTI_COLNAMES},), {tbl}_rowid_list)
        return {multicol}_list
    # ENDBLOCK
    ''')

Tsetter_native_column = ut.codeblock(
    r'''
    # STARTBLOCK
    #@setter
    def set_{tbl}_{colname}({self}, {tbl}_rowid_list, val_list):
        pass
    # ENDBLOCK
    ''')

Tsetter_native_multicolumn = ut.codeblock(
    r'''
    def set_{tbl}_{multicolname}({self}, {tbl}_rowid_list, vals_list):
        pass
    # ENDBLOCK
    ''')


Tdeleter_native_tbl = ut.codeblock(
    r'''
    # STARTBLOCK
    #@deleter
    #@cache_invalidator({TABLE})
    def delete_annots({self}, {tbl}_rowid_list):
        """ deletes annotations from the database """
        if utool.VERBOSE:
            print('[{self}] deleting %d {tbl} rows' % len({tbl}_rowid_list))
        # Delete dependant properties
        {self}.delete_{tbl}_chips({tbl}_rowid_list)
        {self}.{dbself}.delete_rowids({TABLE}, {tbl}_rowid_list)
        {self}.delete_{tbl}_relations({tbl}_rowid_list)
    # ENDBLOCK
    '''
)

Tdeleter_table_relation = ut.codeblock(
    r'''
    # STARTBLOCK
    #@deleter
    def delete_{tbl}_relations(ibs, {tbl}_rowid_list):
        """ Deletes the relationship between an {tbl} row and a label """
        {relation}_rowids_list = ibs.get_{tbl}_{relation}_rowids({tbl}_rowid_list)
        {relation}_rowid_list = utool.flatten({relation}_rowids_list)
        ibs.db.delete_rowids({RELATION_TABLE}, {relation}_rowid_list)
    # ENDBLOCK
    '''
)

Tadder_relationship = ut.codeblock(
    r'''
    # STARTBLOCK
    #@adder
    def add_image_relationship(ibs, gid_list, eid_list):
        """
        Adds a relationship between an image and and encounter

        Tadder_relationship
        """
        colnames = ('image_rowid', 'encounter_rowid',)
        params_iter = list(zip(gid_list, eid_list))
        get_rowid_from_superkey = ibs.get_egr_rowid_from_superkey
        superkey_paramx = (0, 1)
        egrid_list = ibs.db.add_cleanly(EG_RELATION_TABLE, colnames, params_iter,
                                        get_rowid_from_superkey, superkey_paramx)
        return egrid_list
    # ENDBLOCK
    ''')

'''
s/ibs/{self}/gc
s/db/{dbself}/gc
'''