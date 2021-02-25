# Watchdog
Watchdog functionality 

## Requirements
Create a script that runs as a daemon or Cron job on Ubuntu 16.04 and 20.04.
python: 3.5.2 & 3.8

- manage disk space by deleting files
- config file to specify folders where files may be deleted
- delete oldest files first
- specify threshold to begin deleting in config file (disk-full percentage or 5GB free for example)
- if Cron, then must be efficient enough to run every few minutes

- restart monitored applications and restart them if they exit 

## installation

sudo apt install python3-pip

### python 3.8 installation:
```
$ sudo add-apt-repository ppa:deadsnakes/ppa

$ sudo apt update

$ sudo apt install python3.8

$ python3.8 --version
Python 3.8.8

```
Virtual environment
```
$ sudo apt-get install python3-venv
$ python3 -m venv pyenv35
```
## Configuration

## Usage
