import time
import psutil
from functools import partial
from pynput.keyboard import Listener, Key, KeyCode
import fire
from datetime import datetime as dt


def to_mb(val):
    """Convert bytes to MB with 2 decimals"""
    return "{:0.2f}".format(val / 1024 / 1024)


def show_stats(first_timestamp=None, interim_timestamp=None, first_data=None, interim_data=None,
               cent=None, text=None, last_data=None):
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
        print("\n" + tmp.center(57 + cent, "*"))


def on_press_release(event):
    """Function for both (key down & key up) events"""
    global esc_pressed, space_pressed
    if event == Key.esc or event == KeyCode.from_char("q"):
        esc_pressed = True
    if event == Key.space or event == KeyCode.from_char("s"):
        space_pressed = True


def run(lan_name="WiFi", update_interval=0.25, log=False):
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
    if lan_name not in available_objs:
        tmp = "', '".join(available_objs)
        print(f"Connection '{lan_name}' not available in: '{tmp}'")
        return

    # centering variable
    if update_interval < 1:
        cent = 12
    else:
        cent = 10

    print_header = True
    first_data, interim_data = lo()[lan_name], lo()[lan_name]
    first_timestamp, interim_timestamp = time.time(), time.time()

    log_file_name = dt.now().strftime("network_traffic_%y-%m-%d_%H-%M-%S.log")

    while True:
        if esc_pressed:
            show_stats(first_timestamp=first_timestamp, first_data=first_data,
                       cent=cent, text="END STATISTICS", last_data=lo()[lan_name])
            break
        if space_pressed:
            show_stats(interim_timestamp=interim_timestamp, interim_data=interim_data,
                       cent=cent, text="INTERIM STATISTICS", last_data=lo()[lan_name])
            interim_timestamp = time.time()
            interim_data = lo()[lan_name]
            space_pressed = False

        # two timestamps to measure diff
        ts_one = lo()[lan_name]
        time.sleep(update_interval)
        ts_two = lo()[lan_name]
        net_in, net_out = to_mb(ts_two.bytes_recv - ts_one.bytes_recv), to_mb(ts_two.bytes_sent - ts_one.bytes_sent)

        if print_header:
            print("NETWORK MONITOR".center(57+cent, "*"))
            print(f"{'TIMESTAMP'.center(cent)}| IN [MB/s] | OUT [MB/s] | TOTAL IN [MB] | TOTAL OUT [MB]")
            print("-" * (57+cent))
            print_header = False
            if log:
                with open(log_file_name, mode="a") as f:
                    f.write("LOG START".center(57+cent, "*") + "\n" + "TIMESTAMP\tIN [MB/s]\tOUT [MB/s]\t"
                                                                      "TOTAL IN [MB]\tTOTAL OUT [MB]\n")

        if update_interval < 1:
            tmp_time = dt.now().strftime("%H:%M:%S:%f")[:-4]
        else:
            tmp_time = time.strftime("%H:%M:%S")

        # status
        status = f"{tmp_time.center(cent)}| {net_in.center(9)} | {net_out.center(10)} | " \
                 f"{to_mb(ts_two.bytes_recv).center(13)} | {to_mb(ts_two.bytes_sent).center(14)}"
        print(status, end="\r")

        if log:
            with open(log_file_name, mode="a") as f:
                f.write(status.replace("|", "\t") + "\n")


if __name__ == "__main__":
    esc_pressed = False
    space_pressed = False

    # key-listener
    listener = Listener(on_press=None, on_release=on_press_release)
    listener.start()

    # run network monitor
    fire.Fire(run)

    # join threads
    listener.stop()
    listener.join()

    input("Exit with any key..")
