# sner -- slow network recon

GitHub Actions: [![Tests CI](https://github.com/bodik/sner4/workflows/Tests%20CI/badge.svg)](https://github.com/bodik/sner4/actions)

## Table of Contents

* [Project description](#1-project-description)
* [Features](#2-features)
* [Installation](#3-installation)
* [Usage](#4-usage)
* [Known issues](#5-known-issues)



## 1 Project description

Project goals:

1. Distribution of network reconnaissance workload
    * Scanning/reconnaissance is performed by set of agents allowing to perform
      pivoted scans and dynamic scheduling.
    * Support for continuous scanning (periodic rescans)

2. Data analysis and management
    * User-interface and API allows to analyze monitored infrastructure.
    * ORM interface allows detailed automatic, semi-automatic or manual
      analysis.


### 1.1 Design overview

#### Components

* **reconnaissance**
    * agent -- modular wrapper for scanning tools
    * scheduler -- job distribution
    * planner -- management and scheduling for continuous scanning

* **data management**
    * parser -- agent outputs data parsing
    * storage -- long term ip-centric storage
    * visuals -- read-only analytics and visualization user-interface
    * api -- REST-like api


```
                                                    +---+  (raw) files
              agent  +--+--+  server                |
                        |                           |
     +-------------+    |      +--------------+     |     +-----------------+
     |             |    |      |              |     |     |                 |  plugin1..N
     |  agent      |<--------->|  scheduler   |---------->|  parser         |
     |             |    |      |              |     |     |                 |
     +-------------+    |      +--------------+     |     +-----------------+
                        |            ^   queue1..N  |              |
      plugin1..N        |            |              +              |
                        |            |                            \|/
                        |      +--------------+           +-----------------+
                        |      |              |           |                 |
                        |      |   planner    |---------->|  db/storage     |
                        |      |              |           |                 |
                        |      +--------------+           +-----------------+
                        |                                          ^
                        |                                          |
                        |                                 +-----------------+
                        |                                 |                 |
                        |                                 |  visuals        |
                        |                                 |                 |
                        |                                 +-----------------+
                        + 
```



## 2 Features

### 2.1 General features

* Flask-based web interface
* Authentication
  * username/password with optional OTP
  * FIDO2 / WebAuthn
  * OIDC
* Per-route role-based authorization
* Server-side session storage (DEPRECATED)
* CLI interface and automation scripts
* Extendable plugin mechanims for extending agents and parsers


### 2.2 Reconnaissance subsystem

#### Agent

Agent provides communication and execution layer for plugins implementing
various tools wrappers and supports fine-graned workload routing via
capabilities metadata (DEPRECATED).

For list of currently available agent plugins see `sner/plugin/*/agent.py`


#### Server: Scheduler

Scheduler provides workload configuration management and distribution with
heatmap based rate-limiting scheduling.

* **Queue** -- a list of targets and coresponding agent module and scheduling
  attributes container.  Each module has a different config and target
  specification, see corresponding module implementation for details.

* **Job** -- workload unit object, eg. assignment and output tuple.
  Job assignment features CIDR or regex targets exclusions based
  on configuration values.

* **Heatmap**, **Readynet** -- internal structures for rate-limited target
  selection.

CLI helpers are available for IP ranges enumerations and queues/targets
management.


#### Server: Planner

Long-running daemon providing continuous orchestration of agents and output
data processing in order to keep storage up-to-date with monitored networks
reconnaissance data.



### 2.3 Data management subsystem

#### 2.3.1 Storage and Parsers

Storage is a main IP-centric database model and user interface heavily inspired
by Metasploit framework PRO UI. Allows somewhat flexible data management
including predefined aggregations and items tagging.

##### Special tags

Tags are being evaluated in certain usecases:

* `i:anything` is ignored in vuln grouping (view and report generation).
  Tag is used to differentiate availability of the vuln/service/host/note from
  different scanning pivots (eg. i:via_externalnetwork, i:via_internalvpn), but
  visibility is ignored during report aggregations.

* `report`, `report:data`, `info` are used to sort out issues already been processed
  by operator during engagement. Can be used to filter out and get "to be processed"
  vulns.

Parsers are used to parse and ingest agent output data or raw files to storage.

For list of currently available parser plugins see `sner/plugin/*/parser.py`

##### Versioninfo

(EXPERIMENTAL) Pre-compiled view from various storage objects mapping product-version tuple to
corresponding endpoints.

##### Vulnsearch

(EXPERIMENTAL) Pre-compiled view of CPE-CVE correlations.


#### 2.3.2 Visuals

Visualization modules for configuration and storage.


#### 2.3.3 API interface

Basic access to managed data.


### 2.4 Snerlytics

(EXPERIMENTAL) Set of external services for data analysis.

  * Elastic storage (copy of storage data for analysis)
  * CVE-Search (local instance used for CPE-CVE corelations)



## 3 Installation

### 3.1 Install server

```
# prepare environment
apt-get -y install git sudo make
git clone https://github.com/bodik/sner4 /opt/sner
cd /opt/sner
make install

# config and datastore
make install-db
editor /etc/sner.yaml
. venv/bin/activate && make db

# run prod server
apt-get -y install apache2 && a2enmod proxy proxy_http
cp extra/apache_proxy.conf /etc/apache2/conf-enabled/sner.conf
systemctl restart apache2
systemctl enable --now sner-server.service

# run agent
bin/server auth add-agent
editor /etc/sner.yaml
systemctl enable --now sner-agent@1.service

# run planner
systemctl enable --now sner-planner.service
```

### 3.2 Development cycle

```
# prepare environment
apt-get -y install git sudo make
git clone https://github.com/bodik/sner4 /opt/sner
cd /opt/sner
make githook
make install
make install-extra
make install-db
. venv/bin/activate
make db

# run tests
make lint
make coverage
make test-extra

# run dev server
bin/server run
```

### 3.3 Upgrade procedure

* restart server with maintenance flag (`sner_maintenance: True`)
* wait for agents to finish
* stop agents, server and planner
* pull new version
* update dependencies
* perform db migrations
* start all components
* restart server without maintenance flag

```
systemctl stop sner-server
systemctl stop 'sner-agent@*'
cd /opt/sner
. venv/bin/activate
bin/server db stamp head
git fetch --all
git checkout origin/devel
pip install -r requirements.lock
bin/server db upgrade
systemctl start sner-server
```


## 4 Usage

### 4.1 Simple reconnaissance scenario

1. Generate target list
  ```
  bin/server scheduler enumips 127.0.0.0/24 > targets1
  bin/server scheduler rangetocidr 127.0.0.1 127.0.3.5 | bin/server scheduler enumips > targets2
  ```
2. Enqueue targets in queue (web: *scheduler > queue > enqueue*)
  ```
  bin/server scheduler queue-enqueue <queue.name> --file=targets
  ```
3. Run the agent
4. Monitor the queue until all jobs has been finished
5. Stop the agent `bin/agent --shutdown [PID]`
6. Gather recon data from queue directories (`<SNER_VAR>/scheduler/queue-<queue.id>`)


### 4.2 Data evaluation scenario

1. Import existing data with suitable parser
  ```
  bin/server storage import <parser name> <filename>
  ```
2. Use web interface, flask shell or raw database to consult or manage gathered data
3. Generate preliminary vulnerability report (web: *storage > vulns > Generate report*)


### 4.3 Examples

#### Use-case: DNS Enum

```
nmap -sL 192.168.2.0/24 -oA scan-dnsenum
bin/server storage import nmap scan-dnsenum.xml
```


#### Use-case: Basic recon

```
bin/server scheduler enumips 192.0.2.0/24 | bin/server scheduler queue-enqueue 'sner servicedisco nmap'
bin/agent --debug
bin/server storage import nmap /var/lib/sner/scheduler/queue-<queue.id>/*
```


#### Use-case: External scan data processing

```
# template
nmap SCANTYPE TIMING OUTPUT TARGETS

# example
bin/server storage service-list --filter 'Service.port == 22' --short > targets
nmap \
    -sV --version-intensity 4 -Pn \
    --max-retries 3 --script-timeout 30m --max-hostgroup 1 --max-rate 1 --scan-delay 10 \
    -oA output --reason \
    -p T:22 -iL targets

# import data
bin/server storage import nmap output.xml
```


#### Use-case: Shell interface and scripting

See `scripts/`.



## 5 Known issues

* Swagger UI does not work well for session authenticated users. In order to
  prevent CSRF for API endpoints only apikey must be used in the request. Use
  private-browser window.
