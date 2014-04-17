from __future__ import absolute_import, division, print_function
import sys

sys.argv.append('--strict')  # do not supress any errors


def _on_ctrl_c(signal, frame):
    print('Caught ctrl+c')
    _close_parallel()
    sys.exit(0)

#-----------------------
# private init functions


def _init_signals():
    import signal
    signal.signal(signal.SIGINT, _on_ctrl_c)


def _reset_signals():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # reset ctrl+c behavior


def _parse_args(**kwargs):
    from ibeis.dev import params
    params.parse_args(**kwargs)


def _init_matplotlib():
    import matplotlib
    import multiprocessing
    import utool
    backend = matplotlib.get_backend()
    if  multiprocessing.current_process().name == 'MainProcess':
        if not utool.QUIET:
            print('--- INIT MPL---')
            print('[main]  current backend is: %r' % backend)
            print('[main]  matplotlib.use(Qt4Agg)')
        if backend != 'Qt4Agg':
            matplotlib.use('Qt4Agg', warn=True, force=True)
            backend = matplotlib.get_backend()
            if not utool.QUIET:
                print('[main] current backend is: %r' % backend)
        if utool.get_flag('--notoolbar') or utool.get_flag('--devmode'):
            toolbar = 'None'
        else:
            toolbar = 'toolbar2'
        matplotlib.rcParams['toolbar'] = toolbar
        matplotlib.rc('text', usetex=False)
        mpl_keypress_shortcuts = [key for key in matplotlib.rcParams.keys() if key.find('keymap') == 0]
        for key in mpl_keypress_shortcuts:
            matplotlib.rcParams[key] = ''
        #matplotlib.rcParams['text'].usetex = False
        #for key in mpl_keypress_shortcuts:
            #print('%s = %s' % (key, matplotlib.rcParams[key]))
        # Disable mpl shortcuts
            #matplotlib.rcParams['toolbar'] = 'None'
            #matplotlib.rcParams['interactive'] = True


def _init_gui():
    import guitool
    from ibeis.view import guiback
    import utool
    if not utool.QUIET:
        print('[main] _init_gui()')
    guitool.ensure_qtapp()
    back = guiback.MainWindowBackend()
    guitool.activate_qwindow(back)
    return back


def _init_ibeis():
    import utool
    from ibeis.control import IBEISControl
    from . import params
    if not utool.QUIET:
        print('[main] _init_ibeis()')
    dbdir = params.args.dbdir
    if dbdir is None:
        print('[main!] WARNING args.dbdir is None')
        ibs = None
    else:
        ibs = IBEISControl.IBEISControl(dbdir=dbdir)
    return ibs


def __import_parallel_modules():
    # Import any modules which parallel process will use here
    # so they are accessable when the program forks
    from utool import util_sysreq
    util_sysreq.ensure_in_pythonpath('hesaff')
    import pyhesaff  # NOQA


def _init_parallel():
    from utool import util_parallel
    from ibeis.dev import params
    __import_parallel_modules()
    util_parallel.init_pool(params.args.num_procs)


def _close_parallel():
    from utool import util_parallel
    util_parallel.close_pool()


def _init_numpy():
    import numpy as np
    floating_error_options = ['ignore', 'warn', 'raise', 'call', 'print', 'log']
    on_float_err = floating_error_options[0]
    numpy_err = {
        'divide':  on_float_err,
        'over':    on_float_err,
        'under':   on_float_err,
        'invalid': on_float_err,
    }
    numpy_print = {
        'precision': 8,
        'threshold': 1000,
        'edgeitems': 3,
        'linewidth': 200,  # default 75
        'suppress': False,
        'nanstr': 'nan',
        'formatter': None,
    }
    np.seterr(**numpy_err)
    np.set_printoptions(**numpy_print)


#-----------------------
# private loop functions


def _guitool_loop(main_locals, ipy=False):
    import guitool
    from ibeis.dev import params
    back = main_locals['back']
    loop_freq = params.args.loop_freq
    guitool.qtapp_loop(back=back, ipy=ipy or params.args.cmd, frequency=loop_freq)


def main(**kwargs):
    # Display an intro message
    msg1 = '''
    _____ ....... _______ _____ _______
      |   |_____| |______   |   |______
    ..|.. |.....| |______s__|__ ______|
    '''
    msg2 = '''
    _____ ______  _______ _____ _______
      |   |_____] |______   |   |______
    __|__ |_____] |______ __|__ ______|
    '''
    print(msg2 if not '--myway' in sys.argv else msg1)
    # Init the only two main system api handles
    ibs = None
    back = None
    if not '--quiet' in sys.argv:
        print('[main] ibeis.main_api.main()')
    _setup()
    _preload_commands()
    try:
        ibs = _init_ibeis()
        if '--gui' in sys.argv or not '--nogui' in sys.argv:
            back = _init_gui()
            back.connect_ibeis_control(ibs)
    except Exception as ex:
        print('[main()] IBEIS LOAD encountered exception: %s %s' % (type(ex), ex))
        raise
    _postload_commands()
    return {'ibs': ibs, 'back': back}


def _setup(**kwargs):
    from ibeis.dev import params
    _parse_args(**kwargs)
    _init_matplotlib()
    _init_numpy()
    _init_parallel(**kwargs)
    _init_signals()
    _init_utool()
    args = params.args
    return args


def _init_utool():
    import utool
    from ibeis.dev import main_registration
    # Inject colored exceptions
    utool.util_inject._inject_colored_exception_hook()
    # Register type aliases for debugging
    main_registration.register_utool_aliases()


def _preload_commands():
    from ibeis.dev import main_commands
    main_commands.preload_commands()  # PRELOAD CMDS


def _postload_commands():
    from ibeis.dev import main_commands
    main_commands.preload_commands()  # PRELOAD CMDS


def main_loop(main_locals, rungui=True, ipy=False, persist=True):
    print('[main] ibeis.main_api.main_loop()')
    from ibeis.dev import params
    import utool
    if rungui and not params.args.nogui:
        try:
            _guitool_loop(main_locals, ipy=ipy)
        except Exception as ex:
            print('[main_loop] IBEIS Caught: %s %s' % (type(ex), ex))
            raise
    if not persist or params.args.cmd:
        main_close()
    execstr = utool.ipython_execstr()
    return execstr


def main_close(main_locals=None):
    _close_parallel()
    _reset_signals()
