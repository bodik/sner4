# sner -- slow network recon


## Quick start


### Installation
```
## install basic utils
apt-get install -y git make

## clone and tune repository
git clone https://gitlab.flab.cesnet.cz/bodik/sner4 /opt/sner
cd /opt/sner || exit 1
ln -s ../../bin/git_hookprecommit.sh .git/hooks/pre-commit

## install packages dependencies and create python virtual environment
make install-deps
make venv

## activate venv and run tests
. venv/bin/activate
make pylint
make test

## activate venv and run dev server
. venv/bin/activate
make db
screen -S sner4-server -dm bin/server run
```

### Basic dns recon
```
bin/server scheduler queue_add 'dns recon' --name 'example_dns_recon' --priority 20 --active
bin/server scheduler enumips 192.0.2.0/24 | sh bin/server scheduler queue_enqueue 'example_dns_recon' --file -
bin/agent --debug --queue 'example_dns_recon'
```



## Project description

Currently, an ad-hoc developed version of the orchestration tool/wrapper for
distributing, partitioning and analysis of various nmap and nikto workloads is
used during first phases of FLAB pentesting methodology.

The main goals of this project is to create server-client software suite for:

* distributing network reconaissance workload
	* scanning performed by the layer of modular agents, wrapping already
	  existing tools such as nmap, nikto, sslscan, nessus and metasploit
	* pivoting, long term timing, performance
		
* analysis of the gathered recon data for monitoring of operated services in
  the large networks similary to the shodan and censys public services

* managing of recon and vulnerability data for the purposes of the pentesting
  processes


### Considered existing solutions

* https://github.com/infobyte/faraday -- too big to customize
* https://ivre.rocks/ -- only limited set of scanning tools supported
* https://github.com/ChrisRimondi/VulntoES -- too simple, without management interface
* https://github.com/secforce/sparta.git -- only heavy gui



## Design overview

* Recon
	* planner		-- management and scheduling for repetitive recon of the monitored networks
	* scheduler		-- job/task distribution
	* agent			-- modular wrapper for scanning tools

The output of the recon components are the typical machine readable data from
wrapped tools for the analysis and data management components.

* Analysis and data management
	* processor/parser	-- recon and vulnerability data preprocessing and analytics layer
	* storage		-- long term host/ip centric storage for r/v data
	* visualization		-- management/view interface for r/v data


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
                        |                                   |  vizualizations     |
                        |                                   |                     |
                        |                                   +---------------------+
                        |
                        |                                     module1
                        +                                     module2
                                                              modulex
```



## agent to server.scheduler protocol description

Simple REST/HTTP based protocol with JSON data encoding.
TODO: authentication

```
;; definitions

queue-id		= 1*DIGIT / 1*ALPHA
				; queue identifier

assignment		= jsonobject
				; {
				;	"id": uuid,
				;	"module": string,
				;	"params": string,
				;	"targets": array of strings
				; }
				; full schema defined in agent.protocol module

output			= jsonobject
				; {
				;	"id": uuid,
				;	"retval": int,
				;	"output": string, base64 encoded data
				; }
				; full schema defined in agent.protocol module

http-ok			= "HTTP/x.x 200 OK" ; standard http response
http-bad-request	= "HTTP/x.x 400 Bad Request" ; standard http response



;; agent to server - request assignment/job

request-assign-job	= "GET /scheduler/job/assign" ["/" queue-id]

response-assign-job	= response-nowork / response-assignment

response-nowork		= http-ok "{}"
				; no assignment/job available

response-assignment	= http-ok assignment
				; assignment object in response body



;; agent to server - upload assignment/job output

request-job-output	= "POST /scheduler/job/output" output
				; output object in request body

response-job-output	= response-accepted / response-refused

response-accepted	= http-ok
				; output accepted			
response-refused	= http-bad-request
				; malformed request or output refused
```
