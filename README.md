[![Total alerts](https://img.shields.io/lgtm/alerts/g/Mnikley/network-traffic-monitor.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/Mnikley/network-traffic-monitor/alerts/) [![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/Mnikley/network-traffic-monitor.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/Mnikley/network-traffic-monitor/context:python)
# network-traffic-monitor
A simple command-line based application to track network traffic

# Installation
1. Clone repository: `git clone https://github.com/Mnikley/network-traffic-monitor`
2. Install dependencies: `pip install -r requirements.txt`

# Usage
- The most forward method to start the network monitor (uses WiFi network per default):
`python network_monitor.py`
- Display available network names:
`python network_monitor.py --lan_name=?`
- Select different network:
`python network_monior.py --lan_name="Ethernet 4"`
- Enable logging to file:
`python network_monitor.py --log=True`
- Change update interval to 2s:
`python network_monitor.py --update_interval=2`
- Show help:
`python network_monitor.py --help`

# Screenshots
<img width="364" alt="image" src="https://user-images.githubusercontent.com/75040444/157470543-58c88209-70de-437a-9a12-29aaf9050b9e.png">

# Todo
- non-global hotkeys
- adapt mb/s when interval changes
- select ethernet automatically if wifi not available
- include `--lan-name` in message if network wasnt found
