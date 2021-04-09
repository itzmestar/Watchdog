# Watchdog
Watchdog functionality in `Python`

## Requirements

[![Python 3.5.2](https://img.shields.io/badge/python-3.5.2-blue.svg)](https://www.python.org/downloads/release/python-352/)
[![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)

Create a script that runs as a daemon or Cron job on Ubuntu 16.04 and 20.04.

- manage disk space by deleting files
- config file to specify folders where files may be deleted
- delete oldest files first
- specify threshold to begin deleting in config file (disk-full percentage)
- it is scheduled in crontab to run every minute to ensure that watchdog keeps running if exited somehow
- start monitored applications if not already running and restart them if they exit 
- only once instance of script runs at a time ensuring consistency 

## setup
```
sudo apt install python3-pip
```
Virtual environment setup
```
$ sudo apt-get install python3-venv
$ python3 -m venv pyenv35
$ source pyenv35/bin/activate
$ pip install psutil
```
## Configuration
### config file
`watchdog.ini` file can be configured for different settings. 
See the file for details.

### cronjob setup
```
* * * * * PATH=$PATH:/home/ubuntu/pyenv35/bin/ && cd /home/ubuntu/Watchdog && python watchdog.py > cron.out  2>&1
```
