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
	  and manage information on on-demand and continuous basis
	* Programmatical access to the data through standard ORM interface to
	  provide further analysis capabilities


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
|                     | parser        | agent module data parsing |
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
      moduleX           |            |                    +-----------------+
                        |            |                    |                 |
                        |            |                    |  db/storage     |
                        |      +--------------+           |                 |
                        |      |              |           +-----------------+
                        |      |  planner     |                    ^
                        |      |              |                    |
                        |      +--------------+           +-----------------+
                        |                                 |                 |
                        |                                 |  visuals        |
                        |                                 |                 |
                        |                                 +-----------------+
                        |
                        |                                  module1
                        +                                  module2
                                                           moduleX
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
layer (modules). Generally, the agent instance gets assignment from server,
performs the task, marshalls output and delivers it to the server. Agent
provides several modes of execution (default, one-time execution, handling
specific queue) and main module provides functions for process handling
(shutdown after current task, immediate termination).

All requests from agent must be authenticated with apikey for user account in
role *agent*. Key can be specified in configuration file or by command-line
switch.

Currently available modules are: dummy (testing), nmap (IP address scanning or
service sweep scanning), manymap (specific service scanning). 


#### Server: Scheduler

Scheduler provides workload configuration and distribution mechanism throug
definitions of Tasks, Queues, Exclusions and Jobs.

* **Queue** -- an agent module configuration (yaml encoded), scheduling specs
  (group_size, priority, active) and list of targets and optional workflow
  config. Each module has a different config and target specification, see
  corresponding module implementation for details.

* **Excl** (exclusion) -- CIDR or regex targets exclusion specifications. During
  continuous recons, some parts of monitored networks must be avoided for
  policy, operations or security reasons. Exclusions are used during the
  assignment phase (not enqueue phase) because exclusion list might change
  between time of queue setup and target selection, scheduler silently discards
  all targets matching any configured exclusion during assignment creation
  process.

* **Job** -- one assignment/job for the agent. JSON data and ZIP archive containing
  input for agent/module and it's corresponding output parseable by *Data
  management* (Storage) subsystem.

CLI helpers are available for IP ranges enumerations and queues/targets
management.


#### Server: Planner

Planner is a daemon handling simple automation for discovery and version
scanning as well as importing data into Storage subsystem. Planner handles
finished jobs acording it's queue workflow configuration.


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

Visualization modules can be used to visualize various informations stored in database:

* Workflow tree
* DNS tree
* Portmap explorer
* (Service) Port infos



## 3 Installation

### 3.1 Installation

```
# pre-requisities
apt-get install git sudo make postgresql-all

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

# configure project and create db schema
cp sner.yaml.example /etc/sner.yaml
editor /etc/sner.yaml
make db

# configure gunicorn service
cp extra/sner.service /etc/systemd/system/sner.service
systemctl daemon-reload
systemctl enable --now sner.service

# configure apache proxy
apt-get install apache2
cp extra/apache_proxy.conf /etc/apache2/conf-enabled/sner.conf
a2enmod proxy
a2enmod proxy_html
systemctl restart apache2
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

### 4.1 Reconnaissance scenario

1. Select existing or define new queue: *scheduler > queues > add | edit*
2. Generate target list
	* manualy
	* from cidr: `bin/server scheduler enumips 127.0.0.0/24 > targets`
	* from network range: `bin/server scheduler rangetocidr 127.0.0.1 127.0.3.5 | bin/server scheduler enumips --file=- > targets`
3. Setup exclusions (*scheduler > exclusions > add | edit*)
4. Enqueue targets
	* web: *scheduler > queues > [queue] > enqueue*
	* cli: `bin/server scheduler queue-enqueue <queue.name> --file=targets`
5. Run the agent `bin/agent &` (TODO: screen or systemd service)
6. Monitor the queue until all jobs has been finished by agent
7. Stop the agent `bin/agent --shutdown [PID]`
8. Recon data can be found in queue directories (`<SNER_VAR>/scheduler/<queue.id>`)


### 4.2 Data evaluation scenario

1. Import existing data with one of the available parsers: `bin/server storage import <parser name> <filename>`
2. Use web interface to consult the data: *storage > hosts | services | vulns | notes | ...*
3. Manage data in storage
	* use CRUD, comments or tags to sort the data out
	* use server shell for advanced analysis
4. Generate preliminary vulnerability report: *storage > vulns > Generate report*


### 4.3 Examples

#### Use-case: Basic dns recon

```
bin/server scheduler enumips 192.0.2.0/24 | bin/server scheduler queue-enqueue 'dns recon' --file=-
bin/agent --debug --queue 'dns recon'
```

#### Use-case: Long-term scanning strategy aka the Planner

1. Run planner

    ```
    bin/server scheduler planner &
    ```

2. Queue targets for (service) discovery

    ```
    bin/server scheduler enumips 192.168.0.0/16 \
        | bin/server scheduler queue-enqueue 'sner_115_disco top10000 ack scan' --file=-
    ```

3. Possible targets will be selected from discovery results and enqueued for
   version scanning (automated by planner). Version scan results will be pushed
   into Storage subsystem.

4. Optionaly: services without identification can be requeued for high intensity version scan.

    ```
    bin/server storage service-list --filter 'Service.state ilike "open%" AND (Service.info == "" OR Service.info is_null "")' \
        | bin/server scheduler queue-enqueue 'sner_211_data inet version scan intense' --file=-
    ```

6. TBD: ???Fully rescan alive hosts


#### Use-case: Service specific scanning

##### Automated (module manymap)

```
# ftp sweep
bin/server storage service-list --filter 'Service.state ilike "open%" AND Service.name == "ftp"' \
    | bin/server scheduler queue-enqueue 'sner_250_data ftp sweep' --file=-
```

##### Manual

Generally pure nmap can be used to do specific sweeps/scanning.

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
