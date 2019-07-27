# sner -- slow network recon

[![Build Status](https://travis-ci.org/bodik/sner4.svg?branch=master)](https://travis-ci.org/bodik/sner4)

## Table of Contents

* [Project description](#1-project-description)
* [Features](#2-features)
* [Installation](#3-installation)
* [Usage](#4-usage)
* [Development](#5-development)


## 1 Project description

Currently, an ad-hoc developed version of the orchestration tool/wrapper for
distributing, partitioning and analysis of various nmap and nikto workloads is
used during first phases of FLAB pentesting methodology.

The main goals of this project is to create server-client software suite for:

* Distributing network reconaissance workload
	* scanning performed by the layer of modular agents, wrapping already
	  existing tools such as nmap, nikto, sslscan, nessus and metasploit
	* pivoting, long term timing, performance
		
* Analysis and data management
	* analysis of the gathered recon data for monitoring of discovered services
	  in large networks similary to the shodan and censys public services
	* managing of recon and vulnerability data for the purposes of the pentesting
	  processes

Several existing solutions has been found, but not any of them meets our long term 
requirements. Typically the existing project are too big to customize (Faraday), does
not have simple extendable support for multiple scanning tools (ivre), does not allow
to easy modify the UI (metasploit) or does not have web-based UI at all (VulntoES, sparta).


### 1.1 Design overview

* Distributing network reconaissance workload
	* planner		-- management and scheduling for repetitive recon of the monitored networks
	* scheduler		-- job/task distribution
	* agent			-- modular wrapper for scanning tools

The output of the recon components are the typical machine readable data from
wrapped tools for the analysis and data management components.

* Analysis and data management
	* processor/parser	-- recon and vulnerability data preprocessing and analytics layer
	* storage		-- long term host/ip centric storage
	* visualization		-- management/view interface


```
                                                    +---+  raw files
              agent  +--+--+  server                |
                        |                           |
     +-------------+    |      +--------------+     |      +----------------------+
     |             |    |      |              |     |      |                      |  module1
     |  agent      +<--------->+  scheduler   +----------->+  processor/parser    |  module2
     |             |    |      |              |     |      |                      |  modulex
     +-------------+    |      +--------------+     |      +----------------------+
                        |            ^              |             |
      module1           |            |              +             |
      module2           |            |                           \|/
      modulex           |            |                      +--------------+
                        |            |                      |              |
                        |            |                      |  db/storage  |
                        |      +--------------+             |              |
                        |      |              |             +--------------+
                        |      |  planner     |                    ^
                        |      |              |                    |
                        |      +--------------+             +---------------------+
                        |                                   |                     |
                        |                                   |  visualizations     |
                        |                                   |                     |
                        |                                   +---------------------+
                        |
                        |                                     module1
                        +                                     module2
                                                              modulex
```


## 2 Features

All implemented features supports penetration testing or continuous monitoring
processes.


### 2.1 Agent

* Wraps existing tools with the communication and execution layer.

* For agent-server protocol specification see the `sner/agent/procotol.py`.

* Server authentication requires valid apikey for account with role *agent*.
  Apikey should be placed in config file (note that passing apikey by
  command-line argument might leak the apikey).

* Agent can run periodicaly or one-time only (`--oneshot`) against server or
  just for specific queue (`--queue`)

* If running, agent can be stopped gracefully (`--shutdown`, might take time if
  long running job/assignment is executing, or terminated immediately
  (`--terminate`).


#### 2.1.1 Agent modules

* dummy
* nmap
* inetverscan


### 2.2 Server

Server itself is flask-based application with web and command line interface.
The main components are roughly devided to python modules (also flask
blueprints) but with tight coupling.


#### 2.2.1 Auth

Component provides AAA mechanisms for the server.

* Authentication
	* Schemas supported
		-- username+password, w/o OTP as second factor;
		   FIDO2/webauthn password-less;
		   Header-based authentication for scheduler API (agents only)
	* Session based implementation
		-- default flask sessions replaced with server-side file-backed implementation;
		   no save sessions for agents
	* Password storage
		-- `user.password` salted-sha512, should allow transitions if needed;
		   `user.apikey` sha512;
		   managed by `sner/server/password_supervisor.py`

* Authorization
	* static set of roles used for very simple route-based authorization

* Account management
	* user CRUD
	* roles management: admin, operator, user (no privileges, planned for shodan-like RO interface), agent
	* apikey (re)generation

* Command-line interface
	* user password reset (`passwordreset`)


#### 2.2.2 Scheduler

Components provides workload configuration and distribution mechanisms for the
recon subsystem. Each agents draws (repeatedly) an `assignment` from server,
executes the workload, packs the output and post-back the results of the
assigned `job`.

* Models:
	* `task` -- general settings for module executed by agent. Agent
	  module is responsible for interpreting the `task.params` property.

	* `queue` -- holds list of targets for specific task. When creating
	  assignment for agent, server select active queue with highest priority and
          draws N targets (`queue.group_size`) from queue randomly.

	  Each agent module requires own target specification, consult corresponding agent module class
	  docstring for more information.

	* `job` -- represents one assignment/job for the agent. `assignment` is represented 
          by JSON object and output as `job.retval` and `job.output`.
	  `output` should be a zip file and corresponding parser in `storage` component
	  should be able to understand it's contents. Output archive must include
	  `assignment.txt` file with appropriate data. Archives are stored directly on disk
          in directory structure corresponding to queues for better manipulation (listing, backup, import).

	* `excl` -- model for target exclusion. During large or long recons, some parts
	  of monitored networks must be avoided for policy, operations or security reasons.
          `excl` models holds information which CIDR or regex specified targets must not
          be assigned from queues. Exclusions are used during the assignment phase (not
	  enqueue phase because exclusion list might change between time of queue setup and target selection),
          scheduler silently discards all drawed targets matching any configured exclusion.

* Web interface
	* CRUD operations for all models except `job` model.
	* assignment and ouput gathering functionality for agents is available through `/api` endpoints

* Command-line interface
	* ip/targets enumeration helpers (`enumips`, `rangetocird`)
	* queue management (`queue_enqueue`, `queue_flush`, `queue_prune`)


#### 2.2.3 Storage and parsers

Storage component is main long-term data database. It's design is host/ip
centric and should represent complete state of discovered hosts, services among
with associated vulnerabilities and notes.

Parsers are components responsible for parsing and interpreting agent output
data (typically zip blobs) and translating it into storage models/entities.

* Models:
	* `host` -- host/ip based basic information
	* `service` -- service information
	* `vuln` -- vulnerability data associated with host (or service)
	* `note` -- additional data associated with host (or service)

Note: The storage model is heavily inspired by Metasploit framework. `[model].xtype`
property is used to differentiate categories of information held in the model
instance, the property is mainly used by parsers.

* Web interface
	* CRUD operation for all models
	* multi-item operations on `vuln` model for vulnerability evaluation process (tag, delete)
	* filtering for preset categories (not tagged, exclude reviewed, ...)
	* vulnerability report generation
	* basic visualizations: hostnames tree interactive graph, service port map

* Command-line interface
	* storage data management (`import`, `flush`)
	* report generation (`report`)
	* host management (`host_cleanup`)
	* service management (`service_list`, `service_cleanup`)


#### 3.2.4 Visualizations and planner

* Not implemented yet
	* Visualisations should allow for end-user read-only visualization and searching features.
	* Planner component should take care of periodic queueing of existing or new targets to refresh information in storage.


#### 2.2.5 Shell

For scripting and programmatic manipulation with objects in all parts of the
server a shell with pre loaded model is available. The usage is according to
normal flask cli shell.

```
webservices = Service.query.filter(Service.proto=='tcp', Service.port.in_([80, 443, 8080, 8443])).all()
for tmp in webservices:
  print('%s:%s' % (tmp.host.address, tmp.port))
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
mkdir -p /var/sner
chown www-data /var/sner

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

### 4.1 Recon scenario

1. Define new or select existing task (*scheduler > tasks > add | edit*)
2. Define new queue for task (*scheduler > queues > add | edit*)
3. Generate target list
	* manualy
	* from cidr: `bin/server scheduler enumips 127.0.0.0/24 > targets`
	* from network range: `bin/server scheduler rangetocidr 127.0.0.1 127.0.3.5 | bin/server scheduler enumips --file=- > targets`
4. Setup exclusions (*scheduler > exclusions > add | edit*)
5. Enqueue targets
	* web: *scheduler > queues > [queue] > enqueue*
	* shell: `bin/server scheduler queue_enqueue [queue_id | queue_name] --file=targets`
6. Run the agent `bin/agent &` (but screen is better)
7. Monitor the queue until drained and all jobs has been finished by agent(s)
8. Stop the agent `bin/agent --shutdown [PID]`
9. Gathered recon data found in corresponding `SNER_VAR/scheduler/[queue.id]` directory can be used for analysis


### 4.2 Data evaluation scenario

1. Import existing data with one of the available parsers (import command is
   able to detect zip or raw data and handover it to the parser accordingly).
   Import adds information to the storage, to replace either delete specific the
   information first or flush whole storage.
   ```
   bin/server storage import [parser name] [filename]
   ```
2. Use web interface to consult the data *storage > hosts | services | vulns | notes | vizdns | vizports/portmap*
3. Manage data in storage
	* use comments to pinpoint important nodes and services
	* use server shell for further analysis and data management (eg. collect service list for further examination)
	* review and tag or delete vulnerabilities one-by-one or use groupped view to speed up the process
4. Generate preliminary vulnerability report for monitored network


### 4.3 Examples

#### 1.3.1 Basic dns recon
```
bin/server scheduler enumips 192.0.2.0/24 | bin/server scheduler queue_enqueue 'dns_recon' --file -
bin/agent --debug --queue 'dns recon'
```


## 5 Development

* Server part is flask-based application, while agent is standalone python
  module. Consult `.travis.yml` to get started.

* Project uses flake8, pylint (mostly defaults) pytest, coverage, selenium and
  travis-ci.org to ensure some coding standard and functionality.

* Web interface is a *simple form based airship rental like application* based
  on DataTables glued together with jQuery and a few enhancements for multi
  item operations.

* EmberJS/React for UI is under evaluation, but yet in not_this_time category.

* Any review or contribution is welcome.
