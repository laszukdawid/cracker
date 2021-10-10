"""
Class KeyBoardManager is based on an example [1] provided by the Python-xlib with very few changes.
This means that it's likely suboptimal and have plenty of unnecessary code.
If this bothers your, please suggest or request changes.

[1] https://github.com/python-xlib/python-xlib/blob/376703ebb0069cf01727e22a679590fc14ac0152/examples/record_demo.py
"""

import sys
from typing import List

from PyQt5.QtCore import QObject, pyqtSignal
from Xlib import XK, X, display
from Xlib.ext import record
from Xlib.protocol import rq


class KeyBoardManager(QObject):
    GlobalReadSignal = pyqtSignal()

    def run(self, sequence: List[str]):
        """*Should be run in deamon mode (preferrably as thread)*

        Sequence (list of str) is a list of key names that are checked against.
        For example, sequence = ['space', 'k'] tiggers an event when 'space' and 'k' 
        are pressed (down) at the same time.

        """
        local_dpy = display.Display()
        record_dpy = display.Display()
        self.check_keys = sequence
        self.pressed_keys = [False]*len(self.check_keys)

        def lookup_keysym(keysym):
            for name in dir(XK):
                if name[:3] == "XK_" and getattr(XK, name) == keysym:
                    return name[3:]
            return "[%d]" % keysym

        def record_callback(reply):
            if reply.category != record.FromServer or reply.client_swapped:
                return
            if not len(reply.data) or reply.data[0] < 2:
                # not an event
                return

            data = reply.data
            while len(data):
                event, data = rq.EventField(None).parse_binary_value(data, record_dpy.display, None, None)

                if event.type not in (X.KeyPress, X.KeyRelease):
                    continue

                keysym = local_dpy.keycode_to_keysym(event.detail, 0)
                if keysym:
                    pressed = event.type == X.KeyPress
                    key = lookup_keysym(keysym).lower()
                    for idx, check_key in enumerate(self.check_keys):
                        if key.startswith(check_key):
                            self.pressed_keys[idx] =pressed
                
                # Shortcut pressed
                if all(self.pressed_keys):
                    self.GlobalReadSignal.emit()

                # # Exit on Escape
                # if event.type == X.KeyPress and keysym == XK.XK_Escape:
                #     local_dpy.record_disable_context(ctx)
                #     local_dpy.flush()
                #     return

        # Check if the extension is present
        if not record_dpy.has_extension("RECORD"):
            print("RECORD extension not found")
            sys.exit(1)

        # Create a recording context; we only want key and mouse events
        ctx = record_dpy.record_create_context(
                0,
                [record.AllClients],
                [{
                        'core_requests': (0, 0),
                        'core_replies': (0, 0),
                        'ext_requests': (0, 0, 0, 0),
                        'ext_replies': (0, 0, 0, 0),
                        'delivered_events': (0, 0),
                        'device_events': (X.KeyPress, X.MotionNotify),
                        'errors': (0, 0),
                        'client_started': False,
                        'client_died': False,
                }])

        # Enable the context; this only returns after a call to record_disable_context,
        # while calling the callback function in the meantime
        record_dpy.record_enable_context(ctx, record_callback)

        # Finally free the context
        record_dpy.record_free_context(ctx)
