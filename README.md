# sner -- slow network recon

GitHub Actions: [![Tests CI](https://github.com/bodik/sner4/workflows/Tests%20CI/badge.svg)](https://github.com/bodik/sner4/actions)

## Table of Contents

* [Project description](#1-project-description)
* [Features](#2-features)
* [Installation](#3-installation)
* [Usage](#4-usage)
* [Development](#5-development)



## 1 Project description

The main goal of this project is to create software suite for:

1. Distribution of network reconnaissance workload
    * Scanning/reconnaissance is performed by set of modular agents. Each
      agent module wraps one existing or implements new tool such as nmap,
      nikto, sslscan.
    * Agent architecture allows to do pivoted scans and elastic scan
      scheduling.

2. Data analysis and management
    * Flexible user-interface allows to analyze monitored infrastructure
      and manage information on on-demand and continuous basis.
    * Programmatical access to the data through ORM interface to
      provide further analysis capabilities.


### 1.1 Design overview

The application is divided into several components according to theirs main
functions. The *reconnaissance* part gathers standard data produced by scanning
tools, while *data management* part focuses on data analysis and management.

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
w/o OTP or FIDO2 Webauthn password-less authentication. REST API used by agents
uses header-based apikey authentication.

Role-based authorization is applied on web application request routing level.
Default Flask session implementation has been replaced with custom session
server-side file based storage. 

Various components provides limited command-line interface through `server`
command. Flask shell can be used to access the ORM model directly for advanced
analysis or out-of-interface data management.

Agent and parser features are partialy implemented via simple system of plugins
allowing to extend toolset used within those components.


### 2.2 Reconnaissance subsystem

#### Agent

Agent wraps an existing tools with the communication (agent) and execution
layer (modules). Generally, the agent instance fetches assignment from server,
performs the task and sends results back to the server (scheduler). Agent
provides several modes of execution (default, one-time execution, handling
specific queue) and includes functions for process management (shutdown after
current task - on SIGUSR1, immediate termination on SIGTERM).

All requests from agent must be authenticated with apikey for user account in
role *agent*. Key can be specified in configuration file or by command-line
switch. Agent can signal it's (special) capabilities, which can be used to
fine-grained workload routing.

For currently available modules see `sner/plugin/*/agent.py`


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

Planner is daemon periodicaly executing defined pipelines. Pipelines defines a
queues processing (imports data to storage, requeueing during two-phase
scanning) as well as periodic generators (rescanning storage, rediscovery of
netranges for IPv4 and IPv6 address space) or other generic pipelines (storage
cleanup).



### 2.3 Data management subsystem

#### Server: Storage and Parsers

Storage is a main IP-centric database model and user interface heavily inspired
by Metasploit framework PRO UI.

Web interface allows for CRUD operations on all models, filtering of list
views, grouping of vulnerabilities and services by properties, basic condensed
report datasheet generation (FLAB specific feature).

Parsers are used to import agent output data (zip archives) produced by
modules. See the `server storage import` for help. Parsers can also import
default output formats of various security tools and scanners (currently: nmap,
nessus).

#### Server: Visuals

Visualization modules can be used to visualize various informations stored in
database or current configuration:

* Workflow tree
* DNS tree
* Portmap explorer
* (Service) Port infos

#### Snerlytics: Storage vulnsearch (experimental)

Experimental subsystem allowing to corelate nmap detected service CPEs with
external https://github.com/cve-search/cve-search (by circl.lu) and analyze the
data via ELK stack.

* install via https://github.com/bodik/sner-ansible playbooks/snerlytics.yml
* configure external systems urls in config file
* run synchronization process `bin/server storage sync-vulnsearch`

Note: python requests does not use system ca-certificates, in dev environment
helper and mangling certifi store can be used to connect via non-globaly
trusted CAs.



## 3 Installation

### 3.1 Install server

```
# prepare environment
apt-get install git sudo make
git clone https://github.com/bodik/sner4 /opt/sner
cd /opt/sner
make venv
. venv/bin/activate
make install-deps

# database and datadir
apt-get install postgresql-all
sudo -u postgres psql -c "CREATE DATABASE sner;"
sudo -u postgres psql -c "CREATE USER sner WITH ENCRYPTED PASSWORD 'password';"
mkdir -p /var/lib/sner
chown www-data /var/lib/sner
cp sner.yaml.example /etc/sner.yaml
editor /etc/sner.yaml
make db

# configure gunicorn service
cp extra/sner-web.service /etc/systemd/system/sner-web.service
systemctl daemon-reload
systemctl enable --now sner-web.service

# configure apache2 reverse proxy
apt-get install apache2
a2enmod proxy
a2enmod proxy_http
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
apt-get install git sudo make
git clone https://github.com/bodik/sner4 /opt/sner
cd /opt/sner
ln -s ../../extra/git_hookprecommit.sh .git/hooks/pre-commit
make venv
. venv/bin/activate
make install-deps

# install database
apt-get install postgresql-all

# run tests
make db-create-test
make test
make coverage
make install-extra
make test-extra

# run dev server
make db-create-default
make db
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
    * manualy
    * from cidr: `bin/server scheduler enumips 127.0.0.0/24 > targets`
    * from network range: `bin/server scheduler rangetocidr 127.0.0.1 127.0.3.5 | bin/server scheduler enumips --file=- > targets`
2. Setup exclusions (*scheduler > exclusions > add | edit*)
3. Enqueue targets in queue
    * web: *scheduler > queues > [queue] > enqueue*
    * cli: `bin/server scheduler queue-enqueue <queue.name> --file=targets`
5. Run the agent
6. Monitor the queue until all jobs has been finished
7. Stop the agent `bin/agent --shutdown [PID]`
8. Recon data can be found in queue directories (`<SNER_VAR>/scheduler/queue-<queue.id>`)


### 4.2 Data evaluation scenario

1. Import existing data with suitable parser: `bin/server storage import <parser name> <filename>`
2. Use web interface to consult or manage the data: *storage > hosts | services | vulns | notes | ...*
    * use CRUD, comments or tags to sort the data out
    * use server shell for advanced analysis
4. Generate preliminary vulnerability report: *storage > vulns > Generate report*


### 4.3 Examples

#### Use-case: Basic recon

```
bin/server scheduler enumips 192.0.2.0/24 | bin/server scheduler queue-enqueue 'disco syn scan top10000' --file=-
bin/agent --debug
bin/server storage import nmap /var/lib/sner/scheduler/queue-<queue.id>/*
```


#### Use-case: Long-term scanning strategy with Planner

```
editor /etc/sner.yaml
systemctl restart sner-planer.service
```


#### Use-case: External scan data processing

```
# template
nmap SCANTYPE TIMING OUTPUT TARGETS

# example
bin/server storage service-list --filter 'Service.port == 22' --iponly > targets
nmap \
    -sV --version-intensity 4 -Pn \
    --max-retries 3 --script-timeout 30m --max-hostgroup 1 --max-rate 1 --scan-delay 10 \
    -oA output --reason \
    -p T:22 -iL targets

# import data
bin/server storage import nmap output.xml
```


#### Use-case: Shell interface

Flask shell (pre-loaded with sner models) is available for scripting and
programmatic manipulation with all objects.

```
$ bin/server shell
>>> webservices = Service.query.filter(Service.proto=='tcp', Service.port.in_([80, 443, 8080, 8443])).all()
>>> for tmp in webservices:
...   print('%s:%s' % (tmp.host.address, tmp.port))
```



## 5 Development

* Server is Flask based application with heavy usage of DataTable and
  Handlebars. Agent is an standalone python module.

* Project uses flake8, pylint, pytest, coverage, selenium and GitHub Actions to
  ensure functionality and coding standards.

* Any review or contribution is welcome.

### Known issues

* Selenium python driver does not correctly cleanup the urllib3 pool manager, which yields into ResourceWarning, it's fixed 4.0 branch currently in development (09/2020)
  The isssue is monkeypatched to `venv` during `install-deps`.
