# sner -- slow network recon

GitHub Actions: [![Tests CI](https://github.com/bodik/sner4/workflows/Tests%20CI/badge.svg)](https://github.com/bodik/sner4/actions)

## Table of Contents

* [Project description](#1-project-description)
* [Features](#2-features)
* [Installation](#3-installation)
* [Usage](#4-usage)
* [Development](#5-development)



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

#### Components table

| Function            | Component     | Description |
| ------------------- | ------------- | ----------- |
| **reconnaissance**  |||
|                     | agent         | modular wrapper for scanning tools | 
|                     | scheduler     | job distribution |
|                     | planner       | management and scheduling for continuous recon |
| **data management** |||
|                     | parser        | agent module output data parsing |
|                     | storage       | long term ip-centric storage |
|                     | visuals       | read-only analytics and visualization user-interface |

#### Components interconnection graph

```
                                                    +---+  (raw) files
              agent  +--+--+  server                |
                        |                           |
     +-------------+    |      +--------------+     |     +-----------------+
     |             |    |      |              |     |     |                 |  plugin1
     |  agent      |<--------->|  scheduler   |---------->|  parser         |  plugin2
     |             |    |      |              |     |     |                 |  pluginX
     +-------------+    |      +--------------+     |     +-----------------+
                        |            ^              |              |
      plugin1           |            |              +              |
      plugin2           |            |                            \|/
      pluginX           |      +--------------+           +-----------------+
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

User web interface uses cookie based session management with username+password
w/o OTP, FIDO2 Webauthn and/or external OpenID Connect authentication. REST API
uses header-based apikey authentication.

Application features are grouped and authorized for roles: agent (scheduler
jobs), operator (scheduler, storage, visuals), user (profile, api), admin (user
mgmt). Web interface uses custom server-side file based session storage.

Components provides limited command-line interface through `server` command.
Flask shell can be used to access the ORM model directly for advanced analysis
or data management (see `scripts` for examples). Agent and parser subsystem uses
extendable plugin architecture.


### 2.2 Reconnaissance subsystem

#### Agent

Agent provides communication and execution layer for plugins implementing
various tools wrappers. Generally, handles task query/assignment and results
delivery. Allows to execute in default (continuous), one-time or manual
assignment, handles process management features (gracefull shutdown - SIGUSR1,
immediate termination - SIGTERM), supports fine-graned workload routing via
capabilities metadata.

For currently available plugins see `sner/plugin/*/agent.py`


#### Server: Scheduler

Scheduler provides workload configuration container, distribution mechanism
and rate-limiting scheduling.

* **Queue** -- a list of targets and coresponding agent module and scheduling
  attributes container.  Each module has a different config and target
  specification, see corresponding module implementation for details.

* **Excl** (exclusion) -- CIDR or regex targets exclusion specifications. During
  continuous recons, some parts of monitored networks must be avoided for
  policy, operations or security reasons. Exclusions are used during the
  assignment phase (not enqueue phase) because exclusion list might change
  between time of queue setup and target selection, scheduler silently discards
  all targets matching any configured exclusion during assignment creation
  process.

* **Job** -- workload unit object, eg. assignment and agent output tuple.

* **Heatmap**, **Readynet** -- internal structures for rate-limited target
  selection.

CLI helpers are available for IP ranges enumerations and queues/targets
management.


#### Server: Planner

Planner provides continuous orchestration of agents, scheduler and storage
data. Standalone daemon executing periodic defined and interconnected tasks
(stages).



### 2.3 Data management subsystem

#### Server: Storage and Parsers

Storage is a main IP-centric database model and user interface heavily inspired
by Metasploit framework PRO UI. Web interface allow somewhat flexible data
management including predefined aggregations and items tagging.

Parsers are used to parse agent output (zip archives) or raw files (nmap,
nessus) and import data into storage.



#### Server: Visuals

Visualization modules can be used to visualize various informations stored in
database or current configuration:

* Planner tree
* DNS tree
* Portmap explorer
* (Service) Port infos



#### Snerlytics: Storage vulnsearch (experimental)

Experimental subsystem. Uses https://github.com/cve-search/cve-search (by
circl.lu) to correlate and analyze storage CPE data via ELK stack. See
https://github.com/bodik/sner-ansible/blob/master/playbooks/snerlytics.yml
for install instructions.



#### Api: REST API interface (experimental)

Experimental subsystem. Provides basic access to managed data.



## 3 Installation

### 3.1 Install server

```
# prepare environment
apt-get -y install git sudo make
git clone https://github.com/bodik/sner4 /opt/sner
cd /opt/sner
make install

# prepare datastore
apt-get install postgresql-all
sudo -u postgres psql -c "CREATE DATABASE sner;"
sudo -u postgres psql -c "CREATE USER sner WITH ENCRYPTED PASSWORD 'password';"
mkdir -p /var/lib/sner
chown www-data /var/lib/sner

# configure sner and initialize database
cp sner.yaml.example /etc/sner.yaml
editor /etc/sner.yaml
. venv/bin/activate && make db

# configure gunicorn service
cp extra/sner-web.service /etc/systemd/system/sner-web.service
systemctl daemon-reload
systemctl enable --now sner-web.service

# configure apache2 reverse proxy
apt-get install apache2
a2enmod proxy proxy_http
cp extra/apache_proxy.conf /etc/apache2/conf-enabled/sner.conf
systemctl restart apache2

# configure agent service
bin/server auth add-agent
editor /etc/sner.yaml
cp extra/sner-agent@.service /etc/systemd/system/sner-agent@.service
systemctl daemon-reload
systemctl start sner-agent@1.service

# configure planner service
cp extra/sner-planner.service /etc/systemd/system/sner-planner.service
systemctl daemon-reload
systemctl enable --now sner-planner.service
```

### 3.2 Development cycle

```
# prepare environment
apt-get -y install git sudo make
git clone https://github.com/bodik/sner4 /opt/sner
cd /opt/sner
ln -s ../../extra/git_hookprecommit.sh .git/hooks/pre-commit
make install
make install-extra
make install-db
. venv/bin/activate
make db

# run tests
make test
make test-extra
make coverage

# run dev server
bin/server run

# pin certificate for snerlytics in devcloud
echo "ip dev-snerlytics" >> /etc/hosts
get_peer_certificate.py dev-snerlytics > /usr/local/share/ca-certificates/dev-snerlytics.crt
update-ca-certificates
ln -sf --backup /etc/ssl/certs/ca-certificates.crt venv/lib/python3.7/site-packages/certifi/cacert.pem
```



## 4 Usage

### 4.1 Simple reconnaissance scenario

1. Generate target list
  ```
  bin/server scheduler enumips 127.0.0.0/24 > targets1
  bin/server scheduler rangetocidr 127.0.0.1 127.0.3.5 | bin/server scheduler enumips --file=- > targets2
  ```
2. Setup exclusions (web: *scheduler > exclusions*)
3. Enqueue targets in queue (web: *scheduler > queue > enqueue*)
  ```
  bin/server scheduler queue-enqueue <queue.name> --file=targets
  ```
5. Run the agent
6. Monitor the queue until all jobs has been finished
7. Stop the agent `bin/agent --shutdown [PID]`
8. Gather recon data from queue directories (`<SNER_VAR>/scheduler/queue-<queue.id>`)


### 4.2 Data evaluation scenario

1. Import existing data with suitable parser
  ```
  bin/server storage import <parser name> <filename>
  ```
2. Use web interface, flask shell or raw database to consult or manage gathered data
4. Generate preliminary vulnerability report (web: *storage > vulns > Generate report*)


### 4.3 Examples

#### Use-case: DNS Enum

```
nmap -sL 192.168.2.0/24 -oA scan-dnsenum
bin/server storage import nmap scan-dnsenum.xml
```


#### Use-case: Basic recon

```
bin/server scheduler enumips 192.0.2.0/24 | bin/server scheduler queue-enqueue 'sner servicedisco nmap' --file=-
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
