# sner -- slow network recon

[![Build Status](https://travis-ci.org/bodik/sner4.svg?branch=master)](https://travis-ci.org/bodik/sner4)

## Table of Contents

* [Project description](#1-project-description)
* [Features](#2-features)
* [Installation](#3-installation)
* [Usage](#4-usage)
* [Development](#5-development)


## 1 Project description

Currently, an ad-hoc developed version of the orchestration tool/wrapper is
used for distributing, partitioning and analysis of various nmap and nikto
workloads during first phases of FLAB penetration testing methodology.

The main goal of this project is to create server-client software suite for:

* Distributing network reconnaissance workload
	* scanning performed by modular agents, wrapping already existing tools
	  such as nmap, nikto, sslscan, nessus and metasploit
	* pivoting, long term timing and performance management

* Data analysis and management
	* analysis of the data for service monitoring in large networks similarly
	  to the Shodan and Censys services
	* managing recon and vulnerability data for penetration testing tasks

Several existing solutions are available, but none of them meets our long term
requirements. Typically the existing projects are too heavy to customize
(Faraday), does not have simple extendable support for multiple scanning tools
(ivre), does not allow to easy modify the user-interface (metasploit) or does
not have web-based user-interface at all (VulntoES, sparta).


### 1.1 Design overview

The application is divided into several components according to main functions.
The output of the reconnaissance subsystem are the standard output data from
the wrapped tools and should be parser by respective parser components/modules
to push the data into data management subsystem (eg. storage).

| Function            | Component     | Description |
| ------------------- | ------------- | ----------- |
| **reconnaissance**  |||
|                     | planner       | management and scheduling for continuous recon |
|                     | scheduler     | job/task distribution |
|                     | agent         | modular wrapper for scanning tools | 
| **data management** |||
|                     | parser        | agent module data parsing |
|                     | storage       | long term ip-centric storage |
|                     | visualization | read-only analytics and visualization user-interface |

Components interconnection graph.

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
                        |                                 |  visualization  |
                        |                                 |                 |
                        |                                 +-----------------+
                        |
                        |                                  module1
                        +                                  module2
                                                           moduleX
```


## 2 Features


### 2.1 Agent

Agent wraps an existing tools with the communication (agent) and execution
layers (modules). Typically agent draws assignment from server, performs the
task, packs the output and posts it back to the server.

Agent can run periodicaly (default) or one-time only (`--oneshot`). A specific
queue to draw assignments from can be forced with `--queue` argument. Also
agent can execute static assignment (`--assignment`). Running agent can be
stopped gracefully (`--shutdown`) or terminated immediately (`--terminate`).

Server requires the agent to authenticate itself by valid apikey for an account
in role *agent*. The apikey should be placed in config file, passing apikey
through `--appikey` is possible, but not recommended.

For agent-server protocol specification see the `sner/agent/procotol.py`.
Currently implemented modules are:

* dummy
* nmap
* manymap


### 2.2 Server

Server is an flask-based application with web and command line interface.


#### 2.2.1 Auth

Component which provides AA mechanisms for the server. 

Authentication mechanisms supported are: username+password w/o OTP as second
factor, FIDO2 Webauthn password-less authentication and header-based apikey
authentication (agent only). Passwords and apikeys are governed by
*PasswordSupervisor* module. Default Flask session implementation has been
replaced with custom session server-side file based storage.

Authorization is based on routes role-based access lists and user roles.

Account management allows CRUD operations on users, role and apikey
management and user profile self-management.

##### CLI

* user password reset (`reset-password`)


#### 2.2.2 Scheduler

Component which provides workload configuration and distribution mechanism.
Each agents draws (repeatedly) an `assignment` from scheduler component,
executes the workload, packs the output and posts back the results of the
assigned `job`.

##### Task

A work settings for module executed by agent. Modules itself are responsible
for interpreting the `params` property.

##### Queue

Represents list of targets for specific task. When creating an assignment for
agent, server select active, non-empty queue with highest priority and draws
`group_size` number of random targets.

Each module might require specific target format, consult the corresponding
module class docstring for more information.

##### Job

Represents one assignment/job for the agent. `assignment` is a JSON object and
*output* as tuple of `retval` and output data.  Output data is a zip archive
which contents should be understood by a respective parser in *storage*
component. Archive must include at least an `assignment.txt` file with
assignment JSON. Archives are stored directly on disk in directory structure
corresponding to queues for better manipulation (listing, backup, import).

Assignment and ouput gathering function is available through `/api` endpoints.

##### Excl (exclusion)

A setting for target exclusion. During large or long recons, some parts of
monitored networks must be avoided for policy, operations or security reasons.
Excl(usions) holds information which CIDR or regex specified targets must not
be assigned from queues. Exclusions are used during the assignment phase (not
enqueue phase) because exclusion list might change between time of queue setup
and target selection, scheduler silently discards all targets matching any
configured exclusion during drawing process.

##### CLI

* ip/targets enumeration helpers (`enumips`, `rangetocird`)
* queue management (`queue-enqueue`, `queue-flush`, `queue-prune`)


#### 2.2.3 Storage and parsers

Parsers are components used to import agent output data (zip archives) of
various formats to corresponding storage models.

Storage component is a main long term database. It's design is IP-centric and
holds information about discovered hosts, services with associated
vulnerabilities and notes. The storage models (`Host`, `Service`, `Vuln` and
`Note`) are heavily inspired by Metasploit framework, thou most of the
properties are self explanatory, the `[model].xtype` property is used to
describe category of the data and used mainly by parsers.

Web interface allows for CRUD operations on all models, on some also multi-item
operations such as tag and delete, filtering, vulnerability report generation
(FLAB specific) and basic visualizations (dns tree graph, service port map,
service info word cloud).

##### CLI

* storage data management (`import`, `flush`)
* report generation (`report`)
* host management (`host-cleanup`)
* service management (`service-list`, `service-cleanup`)


#### 2.2.4 Visualizations and planner

**Not implemented**

Visualisations should allow for end-user read-only visualization and searching
features.

Planner component should take care of periodic queueing of existing or new
targets to refresh information in storage.


#### 2.2.5 Shell

Flask shell (pre-loaded with sner models) is available for scripting and
programmatic manipulation with objects of all components.

```
$ bin/server shell
>>> webservices = Service.query.filter(Service.proto=='tcp', Service.port.in_([80, 443, 8080, 8443])).all()
>>> for tmp in webservices:
...   print('%s:%s' % (tmp.host.address, tmp.port))
```


## 3 Installation

### 3.1 Pre-requisities

```
# general
apt-get install git sudo make postgresql-all

# OPTIONAL: apache + wsgi
apt-get install apache2 libapache2-mod-wsgi-py3
```

### 3.2 Installation

```
# clone from repository
git clone https://github.com/bodik/sner4 /opt/sner
cd /opt/sner

# OPTIONAL: create and activate virtualenv
make venv
. venv/bin/activate

# install dependencies
make install-deps
```

### 3.3 Production post-installation

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

# configure apache WSGI proxy
cp wsgi.conf.example /etc/apache2/conf-enabled/sner-wsgi.conf
editor /etc/apache2/conf-enabled/sner-wsgi.conf
/etc/init.d/apache2 restart
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

1. Select existing or define new task: *scheduler > tasks > add | edit*
2. Select existing or define new queue: *scheduler > queues > add | edit*
3. Generate target list
	* manualy
	* from cidr: `bin/server scheduler enumips 127.0.0.0/24 > targets`
	* from network range: `bin/server scheduler rangetocidr 127.0.0.1 127.0.3.5 | bin/server scheduler enumips --file=- > targets`
4. Setup exclusions (*scheduler > exclusions > add | edit*)
5. Enqueue targets
	* web: *scheduler > queues > [queue] > enqueue*
	* shell: `bin/server scheduler queue-enqueue [queue_id | queue_name] --file=targets`
6. Run the agent `bin/agent &` (use screen for convenience)
7. Monitor the queue until drained and all jobs has been finished by agent
8. Stop the agent `bin/agent --shutdown [PID]`
9. Gathered reconnaissance data can be found in correspondig queue directory (`[SNER_VAR]/scheduler/[queue.id]`)


### 4.2 Data evaluation scenario

1. Import existing data with one of the available parsers: `bin/server storage import [parser name] [filename]`
2. Use web interface to consult the data: *storage > hosts | services | vulns | notes | ...*
3. Manage data in storage
	* use comments to sort the data
	* use server shell for advanced analysis
	* review, tag or delete vulnerabilities
4. Generate preliminary vulnerability report: *storage > vulns > Generate report*


### 4.3 Examples

#### 4.3.1 Basic dns recon

```
bin/server scheduler enumips 192.0.2.0/24 | bin/server scheduler queue-enqueue 'dns_recon' --file=-
bin/agent --debug --queue 'dns recon'
```

#### 4.3.2 General long-term scanning strategy

Import gathered data after each step.

1. Service discovery, TCP ACK scan to search for alive hosts and probable services (avoids some flow based IDS/IPS systems).

    ```
    bin/server scheduler enumips 192.168.0.0/16 \
        | bin/server scheduler queue-enqueue 'sner_011 top10000 ack scan' --file=-
    ```

2. Service fingerprinting, use lower intensity for first wave, scan most common services first, avoid tcp/22 with regex exclusion on `^tcp://.*:22$`.

    ```
    # fast track
    bin/server storage service-list --filter 'Service.port in [21,80,179,443,1723,3128,8000,8080,8443]' \
        | bin/server scheduler queue-enqueue 'sner_020 inet version scan basic commonports' --file=-
    # rest of the ports
    bin/server storage service-list --filter 'Service.port not_in [21,80,179,443,1723,3128,8000,8080,8443]' \
        | bin/server scheduler queue-enqueue 'sner_020 inet version scan basic normal' --file=-
    ```

3. Re-queue services without identification for high intensity version scan.

    ```
    bin/server storage service-list --filter 'Service.state ilike "open%" AND (Service.info == "" OR Service.info is_null "")' \
        | bin/server scheduler queue-enqueue 'sner_025 inet version scan intense' --file=-
    ```

4. Cleanup storage, remove services in filtered state (ack scan artifacts) and prune hosts without any data

    ```
    bin/server storage service-cleanup
    bin/server storage host-cleanup
    ```

5. ?Fully rescan alive hosts


#### 4.3.3 Service specific scanning

##### Automated (module manymap)

```
# ftp sweep
bin/server storage service-list --filter 'Service.state ilike "open%" AND Service.name == "ftp"' \
    | bin/server scheduler queue-enqueue 'sner_030 ftp sweep' --file=-

# http titles
bin/server storage service-list --filter 'Service.state ilike "open%" AND Service.name ilike "http%"' \
    | bin/server scheduler queue-enqueue 'sner_031 http titles' --file=-

# ldap info
bin/server storage service-list --filter 'Service.state ilike "open%" AND Service.name == "ldap"' \
    | bin/server scheduler queue-enqueue 'sner_032 ldap rootdse' --file=-
```

##### Manual

Generally pure nmap can be used to do specific sweeps/scanning.

```
# template
nmap SCANTYPE TIMING(-Pn --reason --scan-delay 10 --max-rate 1 --max-hostgroup 1) TARGETING OUTPUT(-oA output)

# example
bin/server storage service-list --filter 'Service.port == 22' --iponly > targets
nmap \
    -sV --version-intensity 4 \
    -Pn --reason --scan-delay 10 --max-rate 1 --max-hostgroup 1 \
    -p T:22 -iL targets \
    -oA output
bin/server storage import nmap output.xml
```


## 5 Development

* Server is Flask based application, agent is standalone python module. See
  `.travis.yml` to get started.

* Web interface is a *simple form based airship rental like application* based
  on DataTables glued together with jQuery and a few enhancements for
  multi-item operations.

* Project uses flake8, pylint, pytest, coverage, selenium and travis-ci.org to
  ensure functionality and coding standards.

* Any review or contribution is welcome.
