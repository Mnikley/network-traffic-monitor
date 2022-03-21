import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as dt
from functools import partial
from tkinter import Tk, Button, Label, LabelFrame, Frame, DoubleVar, messagebox
from tkinter.ttk import Combobox
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import psutil
from tkintertable import TableCanvas


def get_timestamp():
    return dt.now().strftime("%y-%m-%d %H:%M:%S")


def to_mb(val, update_interval=None):
    """Converts bytes to MB"""
    tmp = 1
    if update_interval:
        tmp = 1/update_interval

    return (val / 1024 / 1024) * tmp


class NetworkMonitor(Tk):
    def __init__(self):
        """GUI init, logging, widget building"""
        super().__init__()
        self.title("Network Traffic Monitor")
        # self.geometry("650x450")

        # threadpool executor
        self.executor = ThreadPoolExecutor(max_workers=4)

        # logging setup
        self.log_fn = "network_monitor.log"
        logging.basicConfig(filename=self.log_fn, level=logging.DEBUG, format="%(asctime)s %(message)s")
        logging.info("\n")
        logging.info("Launched Network Traffic Monitor".center(80, "*"))

        # ******** UI elements ***********
        # settings frame
        frm_settings = LabelFrame(self, text="Settings")
        frm_settings.pack(padx=2, pady=2, ipadx=2, ipady=2)
        Label(frm_settings, text="Network Adapter:").pack(side="left")
        self.adapters = Combobox(frm_settings, state="readonly")
        self.adapters.bind("<<ComboboxSelected>>", self.adapter_callback)
        self.adapters.pack(side="left")
        self.selected_adapter = None
        self.lo = None  # lan-objects
        self.refresh_rate = DoubleVar(value=1)
        Label(frm_settings, text="Refresh-Rate: ").pack(side="left", padx=(10, 0))
        self.rr_label = Label(frm_settings, text=str(round(1/self.refresh_rate.get(), 2)).center(4),
                              font=("Consolas", 10))
        self.rr_label.pack(side="left")
        Label(frm_settings, text=" Hz").pack(side="left")
        Button(frm_settings, text="+", command=partial(self.set_refresh_rate, True, False)).pack(side="left")
        Button(frm_settings, text="-", command=partial(self.set_refresh_rate, False, True)).pack(side="left")

        # current rate frame
        frm_current = LabelFrame(self, text="Current Rate")
        Label(frm_current, text="In: ").pack(side="left")
        self.rate_in_lbl = Label(frm_current, text=str(0.00).center(10), font=("Consolas", 10, "bold"))
        self.rate_in_lbl.pack(side="left")
        Label(frm_current, text="Out: ").pack(side="left")
        self.rate_out_lbl = Label(frm_current, text=str(0.00).center(10), font=("Consolas", 10, "bold"))
        self.rate_out_lbl.pack(side="left")
        Label(frm_current, text=" [MB/s]").pack(side="left")
        frm_current.pack(padx=2, pady=2, ipadx=2, ipady=2)

        # status frame
        frm_status = Frame(self)
        frm_status.pack(fill="both", expand=1)
        self.timestamps = 0
        self.last_timestamp = None
        self.data = {
            "Initial data": {"Timestamp": get_timestamp(), "In [MB]": 0, "Out [MB]": 0},
            "Session": {"Timestamp": 0, "In [MB]": 0, "Out [MB]": 0}
        }

        self.table = TableCanvas(frm_status, read_only=True, thefont=("Arial", 10), data=self.data,
                                 editable=False, showkeynamesinheader=True, rowheaderwidth=100)
        self.table.setSelectedRow(-1)
        self.table.show()

        # reports frame
        frm_reports = LabelFrame(self, text="Control")
        frm_reports.pack(ipady=2, ipadx=2)
        Button(frm_reports, text="Add Timestamp", command=self.add_timestamp).pack(side="left")
        Button(frm_reports, text="Clear Timestamps", command=self.clear_timestamps).pack(side="left")
        Button(frm_reports, text="Open log", command=self.open_last_log).pack(side="left")
        Button(frm_reports, text="Clear log", command=self.clear_log_file).pack(side="left")
        Button(frm_reports, text="Show plot", command=self.show_plot).pack(side="left")

        # plot area
        self.frm_plot = LabelFrame(self, text="Plot")
        self.frm_plot.pack(pady=(0, 4), ipady=2, ipadx=2)

        # run network init
        self.init_data = {}
        self.ts_data = {}
        self.data_log = {}
        self.network_init()

        # start thread
        self.executor.submit(self.fetch_stats)

    def network_init(self):
        """Fetch available adapters"""
        self.lo = partial(psutil.net_io_counters, pernic=True, nowrap=True)
        self.adapters["values"] = list(self.lo().keys())
        self.adapters.current(0)
        self.selected_adapter = self.adapters.get()
        self.fetch_init_stats()
        logging.info(f"Initialized network adapters. Available: {self.adapters['values']}")

    def fetch_init_stats(self):
        """Fetch initial network stats"""
        logging.debug("Fetching initial network stats")
        for adpt in self.lo().keys():
            self.init_data[adpt] = {
                "bytes_recv": to_mb(self.lo()[adpt].bytes_recv),
                "bytes_sent": to_mb(self.lo()[adpt].bytes_sent)
            }
            self.data_log = {
                "timestamp": [dt.now()],
                "data": [self.lo()]
            }

    def fetch_stats(self):
        """Fetch current network stats"""
        while True:
            logging.debug("Fetching network stats")
            _rr = self.refresh_rate.get()
            _adpt = self.selected_adapter
            ts_one = self.lo()[_adpt]
            time.sleep(_rr)
            ts_two = self.lo()[_adpt]
            self.data_log["timestamp"].append(dt.now())
            self.data_log["data"].append(self.lo())
            net_in = to_mb(ts_two.bytes_recv - ts_one.bytes_recv, _rr)
            net_out = to_mb(ts_two.bytes_sent - ts_one.bytes_sent, _rr)
            self.rate_in_lbl.config(text=str(round(net_in, 2)).center(10))
            self.rate_out_lbl.config(text=str(round(net_out, 2)).center(10))

            self.table.model.setValueAt(get_timestamp(), 1, 0)
            diff_in = to_mb(ts_two.bytes_recv) - self.init_data[self.selected_adapter]["bytes_recv"]
            diff_out = to_mb(ts_two.bytes_sent) - self.init_data[self.selected_adapter]["bytes_sent"]
            self.table.model.setValueAt(str(round(diff_in, 2)), 1, 1)
            self.table.model.setValueAt(str(round(diff_out, 2)), 1, 2)
            self.table.redrawTable()

    def clear_log_file(self):
        """Delete logfile"""
        q = messagebox.askyesno(title="Clear logfile", message="Are you sure to clear the logfile?")
        if q:
            with open(self.log_fn, "w"):
                pass

    def add_timestamp(self):
        """Calculate data-difference between now and last timestamp"""
        self.timestamps += 1
        _data = self.lo()
        _iin, _iout = self.init_data[self.selected_adapter]["bytes_recv"], \
                      self.init_data[self.selected_adapter]["bytes_sent"]
        print(_iin, _iout)
        # TODO: denkfehler irgendwo, fix !
        if self.last_timestamp is None:
            _in = to_mb(_data[self.selected_adapter].bytes_recv) - _iin
            _out = to_mb(_data[self.selected_adapter].bytes_sent) - _iout
        else:
            _in = to_mb(_data[self.selected_adapter].bytes_recv) - self.last_timestamp[0] - _iin
            _out = to_mb(_data[self.selected_adapter].bytes_sent) - self.last_timestamp[1] - _iout

        self.last_timestamp = (_in, _out)
        print(self.last_timestamp)

        self.table.addRow(f"Timestamp {self.timestamps}",
                          **{"Timestamp": get_timestamp(), "In [MB]": str(round(_in, 2)),
                             "Out [MB]": str(round(_out, 2))})
        self.table.setSelectedRow(-1)
        # self.table.autoResizeColumns()
        self.table.redrawTable()
        logging.info(f"Timestamp created: {self.table.model.reclist[-1]}")

    def clear_timestamps(self):
        """Clear timestamps"""
        self.timestamps = 0
        self.last_timestamp = None
        logging.info(f"Timestamps cleared: {self.table.model.reclist[1:]}")
        self.table.model.deleteRows(range(2, len(self.table.model.reclist)))
        self.table.redrawTable()

    def open_last_log(self):
        """Open the logfile"""
        logging.debug("Logfile opened")
        os.startfile(self.log_fn)

    def show_plot(self):
        """Generates plot from this sessions network data"""
        logging.info("Showing plot")
        times = self.data_log["timestamp"]
        data_in = []
        data_out = []
        for _ in self.data_log["data"]:
            data_in.append(_[self.selected_adapter].bytes_recv)
            data_out.append(_[self.selected_adapter].bytes_sent)

        # TODO: continue here
        fig = Figure()
        ax = fig.add_subplot(111)
        df = pd.DataFrame(data={"time": times, "data_in": data_in, "data_out": data_out})
        df.set_index("time")
        # df.plot(x="time", y="data_in", ax=ax)
        df.plot(ax=ax)
        canvas = FigureCanvasTkAgg(fig, master=self.frm_plot)
        canvas.draw()
        canvas.get_tk_widget().pack()

    def adapter_callback(self, event):
        """Callback when switching network adapter"""
        self.selected_adapter = event.widget.get()
        logging.info(f"Selected adapter: {self.selected_adapter}")

        # write first row (initial data)
        self.table.model.setValueAt(round(self.init_data[self.selected_adapter]["bytes_recv"], 2), 0, 1)
        self.table.model.setValueAt(round(self.init_data[self.selected_adapter]["bytes_sent"], 2), 0, 2)
        self.table.redrawTable()

    def set_refresh_rate(self, decrease=None, increase=None):
        """Callback when changing refresh rate"""
        current = self.refresh_rate.get()
        tmp, target = None, None

        if increase:
            tmp = "Increased"
            if current < 1:
                target = current + 0.25
            else:
                target = current + 1
        elif decrease:
            tmp = "Decreased"
            # hard lower limit = 4Hz
            if current == 0.25:
                return
            if current <= 1:
                target = current - 0.25
            else:
                target = current - 1
        self.refresh_rate.set(target)
        logging.debug(f"{tmp} refresh-rate to {target}")
        self.rr_label.config(text=str(round(1/target, 2)).center(4))


if __name__ == "__main__":
    """Boilerplate code"""
    app = NetworkMonitor()
    app.mainloop()
