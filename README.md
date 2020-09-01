# sner -- slow network recon

[![Build Status](https://travis-ci.org/bodik/sner4.svg?branch=master)](https://travis-ci.org/bodik/sner4)

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
     |             |    |      |              |     |     |                 |  module1
     |  agent      |<--------->|  scheduler   |---------->|  parser         |  module2
     |             |    |      |              |     |     |                 |  moduleX
     +-------------+    |      +--------------+     |     +-----------------+
                        |            ^              |              |
      module1           |            |              +              |
      module2           |            |                            \|/
      moduleX           |      +--------------+           +-----------------+
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
                        |
                        |                                  visual1
                        +                                  visual2
                                                           visual3
```



## 2 Features

### 2.1 Common features

User web interface uses cookie based session management with username+password
w/o OTP or FIDO2 Webauthn password-less authentication. REST API used by agents
uses header-based apikey authentication. Role-based authorization is applied on
web application request routing level.

Default Flask session implementation has been replaced with custom session
server-side file based storage. 

Various components provides limited command-line interface through `server`
command. Flask shell can be used to access the ORM model directly for advanced
analysis or out-of-interface data management.


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
switch.

Currently available modules are: dummy (testing), nmap (IP address scanning or
service sweep scanning), manymap (specific service scanning), six_dns_discover
(IPv6 address discovery from IPv4 and DNS records).


#### Server: Scheduler

Scheduler provides workload configuration and distribution mechanism throug
definitions of Queues, Exclusions and Jobs.

* **Queue** -- an agent module configuration (yaml encoded), scheduling specs
  (group_size, priority, active) and list of targets. Each module has a
  different config and target specification, see corresponding module
  implementation for details.

* **Excl** (exclusion) -- CIDR or regex targets exclusion specifications. During
  continuous recons, some parts of monitored networks must be avoided for
  policy, operations or security reasons. Exclusions are used during the
  assignment phase (not enqueue phase) because exclusion list might change
  between time of queue setup and target selection, scheduler silently discards
  all targets matching any configured exclusion during assignment creation
  process.

* **Job** -- one assignment/job for the agent. JSON encoded assignment and the
  job output in the form of a ZIP archive, parseable by *Data management* (Storage)
  subsystem.

CLI helpers are available for IP ranges enumerations and queues/targets
management.


#### Server: Planner

Planner is a Celery worker based daemon, works as automation layer over
scheduler subsystem. According to it's configuration, planner can execute
stages to handle:

* automatic import of jobs output from queues (import_jobs)
* requeueing targets from discovery queues into data queues (enqueue_servicelist, enqueue_hostlist)
* scheduling rescans of services and hosts from current storage (rescan_services, rescan_hosts)
* periodic rescan or ipv6 rediscovery in specified netranges (discover_ipv4, discover_ipv6_dns, discover_ipv6_enum)


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



## 3 Installation

### 3.1 Installation

```
# pre-requisities
apt-get install git sudo make postgresql-all redis-server

# clone from repository
git clone https://github.com/bodik/sner4 /opt/sner
cd /opt/sner

# OPTIONAL: create and activate virtualenv
make venv
. venv/bin/activate

# install dependencies
make install-deps
```

### 3.2 Production post-installation

```
# prepare database and datadir
sudo -u postgres psql -c "CREATE DATABASE sner;"
sudo -u postgres psql -c "CREATE USER sner WITH ENCRYPTED PASSWORD 'password';"
mkdir -p /var/lib/sner
chown www-data /var/lib/sner

# configure and create db schema
cp sner.yaml.example /etc/sner.yaml
editor /etc/sner.yaml
make db

# configure gunicorn service
cp extra/sner-web.service /etc/systemd/system/sner-web.service
systemctl daemon-reload
systemctl enable --now sner-web.service

# configure apache proxy
apt-get install apache2
cp extra/apache_proxy.conf /etc/apache2/conf-enabled/sner.conf
a2enmod proxy
a2enmod proxy_http
systemctl restart apache2

# configure agent service
bin/server auth add-agent
editor /etc/sner.yaml << agent apikey
cp extra/sner-agent@.service /etc/systemd/system/sner-agent@.service
systemctl daemon-reload
systemctl start sner-agent@1.service

# configure planner service
cp extra/sner-planner.service /etc/systemd/system/sner-planner.service
systemctl daemon-reload
systemctl enable --now sner-planner.service
```

### 3.4 Development cycle

```
# ensure git settings on cloud nodes
ln -s ../../extra/git_hookprecommit.sh .git/hooks/pre-commit

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

#### Use-case: Basic dns recon

```
bin/server scheduler enumips 192.0.2.0/24 | bin/server scheduler queue-enqueue 'pentest dns recon' --file=-
bin/agent --debug --queue 'pentest dns recon'
bin/server storage import nmap /var/lib/sner/scheduler/queue-<queue.id>/*
```

#### Use-case: Long-term scanning strategy aka the Planner

1. Configure and run planner, configure stages as needed.

    ```
    editor /etc/sner.yaml
    systemctl restart sner-planer.service
    ```

2. Queue targets for service discovery (if not using discovery stages)

    ```
    bin/server scheduler enumips 192.168.0.0/16 \
        | bin/server scheduler queue-enqueue 'sner_disco ack scan top10000' --file=-
    ```

3. Optionaly: Services without identification can be requeued for high intensity version scan.

    ```
    bin/server storage service-list --filter 'Service.state ilike "open%" AND (Service.info == "" OR Service.info is_null "")' \
        | bin/server scheduler queue-enqueue 'sner_data version scan intense' --file=-
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
  Handlebars. Agent is an standalone python module. See `.travis.yml` to get
  started.

* Project uses flake8, pylint, pytest, coverage, selenium and travis-ci.org to
  ensure functionality and coding standards.

* Any review or contribution is welcome.
