import time
import psutil
from functools import partial
from pynput.keyboard import Listener, Key, KeyCode
import fire
from datetime import datetime as dt
import sys
import os

if sys.platform == "win32":
    import pygetwindow as gw
    os.system("")


def to_mb(val, update_interval=None):
    """Convert bytes to MB with 2 decimals"""
    tmp = 1
    if update_interval:
        tmp = 1/update_interval

    return "{:0.2f}".format((val / 1024 / 1024) * tmp)


def show_stats(first_timestamp: float = None, interim_timestamp: float = None,
               first_data: psutil._common.snetio = None, interim_data: psutil._common.snetio = None,
               cent: int = None, text: str = None, last_data: psutil._common.snetio = None):
    """Function called when pressing esc, q, space or s"""
    if text == "END STATISTICS":
        _ts = first_timestamp
        _data = first_data
    elif text == "INTERIM STATISTICS":
        _ts = interim_timestamp
        _data = interim_data

    time_diff = time.strftime("%H:%M:%S", time.gmtime(time.time() - _ts))
    total_in = to_mb(last_data.bytes_recv - _data.bytes_recv)
    total_out = to_mb(last_data.bytes_sent - _data.bytes_sent)

    if text == "END STATISTICS":
        print("\n" + text.center(57 + cent, "*"))
        print(f"{'DURATION'.center(cent)}|{'RECEIVED [MB]'.center(24)}|{'TRANSMITTED [MB]'.center(30)}")
        print("-" * (57+cent))
        print(f"{time_diff.center(cent)}|{total_in.center(24)}|{total_out.center(30)}")
        print("*" * (57 + cent))
    elif text == "INTERIM STATISTICS":
        tmp = " elapsed: " + time_diff + " | received: " + total_in + " MB | sent: " + total_out + " MB "
        return tmp.center(57 + cent, "*")


def on_press_release(event):
    """Function for both (key down & key up) events"""
    global esc_pressed, space_pressed

    # check if window is active to prohibit global hotkeys (windows only)
    if sys.platform == "win32":
        if "network_monitor" not in gw.getActiveWindowTitle():
            return

    if event == Key.esc or event == KeyCode.from_char("q"):
        esc_pressed = True
    if event == Key.space or event == KeyCode.from_char("s"):
        space_pressed = True


def run(lan_name="WiFi", update_interval=1, log=False):
    """Runs the network monitor

    Parameters
    ----------
    lan_name : string
        Name of the network connection
    update_interval : int or float
        Update interval
    log : bool
        Log results to file
    """
    global space_pressed

    # lan objects
    lo = partial(psutil.net_io_counters, pernic=True, nowrap=True)

    # prohibit invalid lan names
    available_objs = lo().keys()
    if len(available_objs) == 0:
        print("No Network adapters available.")
        return

    if lan_name not in available_objs:
        tmp = "', '".join(available_objs)
        fallback_connection = None
        for f in list(available_objs):
            if f.lower().startswith("eth"):
                fallback_connection = f
        if not fallback_connection:
            fallback_connection = list(available_objs)[0]

        print(f"Connection '{lan_name}' not available in: '{tmp}'. Using '{fallback_connection}' instead."
              f" Use --lan_name='NAME' to change adapter manually.")
        lan_name = fallback_connection

    # centering variable
    if update_interval < 1:
        cent = 12
    else:
        cent = 10

    first_data, interim_data = lo()[lan_name], lo()[lan_name]
    first_timestamp, interim_timestamp = time.time(), time.time()

    log_file_name = dt.now().strftime("network_traffic_%y-%m-%d_%H-%M-%S.log")

    cursor_up = "\u001b[1A"
    cursor_clear = "\u001b[2J"

    # setup blank lines
    total_rows = 5
    print(f"\n" * total_rows)

    # underlined strings
    change_u = "\033[4m" + "C" + "\033[0m" + "hange"
    quit_u = "\033[4m" + "Q" + "\033[0m" + "uit"
    timestamp_u = "\033[4m" + "T" + "\033[0m" + "imestamp"
    mbps_u = "\033[4m" + "M" + "\033[0m" + "B/s <> Mbps"

    while True:
        if esc_pressed:
            show_stats(first_timestamp=first_timestamp, first_data=first_data,
                       cent=cent, text="END STATISTICS", last_data=lo()[lan_name])
            break
        if space_pressed:
            TIMESTAMP = show_stats(interim_timestamp=interim_timestamp, interim_data=interim_data,
                                   cent=cent, text="INTERIM STATISTICS", last_data=lo()[lan_name])

            interim_timestamp = time.time()
            interim_data = lo()[lan_name]
            space_pressed = False

        # two timestamps to measure diff
        ts_one = lo()[lan_name]
        time.sleep(update_interval)
        ts_two = lo()[lan_name]
        net_in = to_mb(ts_two.bytes_recv - ts_one.bytes_recv, update_interval)
        net_out = to_mb(ts_two.bytes_sent - ts_one.bytes_sent, update_interval)

        # header
        ROW_1 = f"Adapter: {lan_name} [{change_u}] | Update-Interval: {update_interval} [\u00B1]".center(57+cent, "*")
        ROW_2 = "-" * (57+cent)
        ROW_3 = f"{'TIME'.center(cent)}| IN [MB/s] | OUT [MB/s] | TOTAL IN [MB] | TOTAL OUT [MB]"
        ROW_4 = "-" * (57+cent)
        if log:
            with open(log_file_name, mode="a") as f:
                f.write("LOG START".center(57+cent, "*") + "\n" + "TIMESTAMP\tIN [MB/s]\tOUT [MB/s]\t"
                                                                  "TOTAL IN [MB]\tTOTAL OUT [MB]\n")

        if update_interval < 1:
            tmp_time = dt.now().strftime("%H:%M:%S:%f")[:-4]
        else:
            tmp_time = time.strftime("%H:%M:%S")

        # status
        ROW_5 = f"{tmp_time.center(cent)}| {net_in.center(9)} | {net_out.center(10)} | " \
                f"{to_mb(ts_two.bytes_recv).center(13)} | {to_mb(ts_two.bytes_sent).center(14)}"

        print(f"{TIMESTAMPS}{cursor_up * total_rows}{ROW_1}\n{ROW_2}\n{ROW_3}\n{ROW_4}\n{ROW_5}")

        if log:
            with open(log_file_name, mode="a") as f:
                f.write(ROW_5.replace("|", "\t") + "\n")


if __name__ == "__main__":
    esc_pressed = False
    space_pressed = False

    # key-listenera
    listener = Listener(on_press=None, on_release=on_press_release)
    listener.start()

    # run network monitor
    fire.Fire(run)

    # join threads
    listener.stop()
    listener.join()

    input("Exit with any key..")
