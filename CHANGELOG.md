# sner4 changelog

## 0.8.0 - refining planner [BC BREAK]

* changed: nessus parser pull solution data
* changed: split CI jobs and update makefile targets
* changed: heavy planner refactoring
* changed: untagging ux
* changed: exclusion config from config, drop excl db storage
* fix: vulnsearch elasticapi 8.x
* fix: nessus pull solution element from xml
* fix: api logging
* fix: npe in vuln view
* fix: gracefull filter parser exception handling
* added: experimental screenshot_web plugin
* added: experimental testssl plugin
* added: add reportdata tag report generation workflow


## 0.7.1 - wrk and fix

* changed: bump packages
* changed: enhance logging in various components, use apache time format, refactor configuration and setup
* changed: server: local swagger assets
* changed: extra: gunicorn service add access log to output
* changed: extra: tune db_dump/restore scripts
* fixed: plugin: six_enum_discover usr local scanning if necessary
* fixed: server: webauthn credential management javascripts
* fixed: server: quickjump when host.hostname is None
* added: server: add ip and user for logs
* added: server: optional werkzeug proxyfix for proper remote_addr handling if server runs behing reverse proxy
* added: server: webui add moredata dropdowns for all storage objects (lists and views)


## 0.7.0 - towards ethical scanning [BC BREAK]

* bump used dependencies
* changed: internal refactorings
  * server/agent config loading refactoring
  * partial scheduler core refactoring to managers and services layer
  * parser full refactoring
  * json messages use "message" field as basic attribute
* changed: Debian Bullseye support/requirement
* changed: rate-limiting scheduler (nacelnik.mk1 design)
* changed: longer session idle timeout by default
* changed: `server db` refactored to `server dbx`
* changed: refactor installation process
* changed: create enabled queues by default
* changes: rename sner-web service to sner-server
* changes: enhance planner logging
* added: basic migrations support
* added: scripts: url generator
* added: add tag during storage import
* added: public api accesible with apikey (reject session auth to api; prevent csrf)
* added: user authentication simple OIDC support, user profile generate apikey
* added: basic quickjump via address or hostname
* added: readynet_recount command, update readynets for current heatmap_hot_level
* security: allow login only for active users


## 0.6.2 - bump packages and updates for prod

* bump used dependencies
* feature: vuln-report and vuln-export filtering and grouping
* feature: add nc/netcat zero io scanner parser
* feature: storage import command dry run support
* feature: report, export add brackets to ipv6 addrs
* scripts: various helper scripts


## 0.6.1 - handlebars security update

* security: bump handlebars (CVE-2021-23369)
* add skeleton script


## 0.6.0 - vulnoverwrite [BC BREAK]

* server, plugin: update database schema for vuln, note to contain via_target field which allows handling name based virtualhost reports data
* server: ui, change default datatables page length
* general: misc tests compatibility or stabilitiy fixes


## 0.5.2 - fixing stuff

* plugin nessus: nessus report can contain ip addres in host-rdns
* server: scheduler enumips enums 4 hosts on /31 ipv4 network
* server: ihost.starttime in nmap import can be empty (via -sL scan)


## 0.5.1 - cosmetics

* documentation cosmetics
* vulnserach ensure complete index
* tests naming cosmetics


## 0.5.0 - towards vulnsearch [BC BREAK]

* features
  * queue requirements and agent capabilities for node-grained workload management
  * local agent invocation id autogeneration
  * jarm scanning
  * syn scan as main service discovery, ack scan removal
  * ui cosmetics
  * service-list simple output
  * dev helpers add and cleanup (db, vim.local)
  * nmap parser pull cpe info for hosts and services
  * vulnsearch, use cpe info to create basic snerlytics view

* other
  * planner refactoring, all steps explicitly using and passing context, add run_group step
  * agent and parser modules refactored to plugins with dynamic loading
  * various tests cometics (sqlaf, pws)
  * parser internal structures uses stricter types (namedtuples)
  * nessus parser normalize protocol string

* bc breaks
  * protocol, get assignment parameters from url to qstring
  * api, dropped '/v1/' from url
  * db schema, queue model attrs

## 0.4.3 - fix bugs (unreleased)

* fix:
  * fix add-agent command

## 0.4.2 - towards continuous prod

* features
  * bin/server psql helper, drops psql shell logged in configured database
  * api adds prometheus statistics
  * planner switch to syn scan by default, add filter_tarpits to default pipeline
  * nftables notrack config example
  * doc and other cleanups to orchestrate with sner-ansible
  * add support for github actions

* other
  * password hasing refactored, moved from ORM to app logic

## 0.4.1 - prod updates

* featues
  * vuln export (non grouped data export)
  * configurable action buttons for vulns and hosts

## 0.4.0 - pipelined planner [BC BREAK]

* features
  * scheduler: add job repeat feature
  * tune default queues (drop unused, add generic script scan queue)
  * decouple module output parsing from storage imports
  * refactor planner to be drived by configured pipelines, remove celery and implement as simple loop daemon
  * add default script scanning queue
  * add ipv6 handling to nmap agent module and server parser, update on default queues and planner steps config
  * add filtering form/field for storage and visuals + add join host model to allow filtering by host properties
  * main menu active item highlighting
  * new helpers: scripts, added portlist file service lister
  * add service endpoint URIs dropdown for storage ui (including selenium tests)
  * add MSFT and MSKB vuln refs links
  * minor UI cosmetics tweaks
  * add severity to generated report
  * add filtering form for scheduler job list page

* fixes:
  * fix annotate modal dialogue form action to work properly with gunicorn
  * hotfix python selenium to correctly close sockets
  * fix storage_cleanup and handle empty hosts with only note.xtype hostnames
  * fix planner step project_servicelist ipv6 address handling
  * sqlafilter fix parsing '>' vs '>='
  * fix user profile page layout
  * fit add user button placement
  * fix six enum discover test
  * fix bin/server commands --debug handling and setup
  * fix logging vs print output

* security:
  * update handlbars library

## 0.3.1 - prod planner

* features:
  * general: add syslogidentifiers to systemd services
  * server: randomize queue selection among same priority
  * server: [BC BREAK] add import_time for selected models
  * agent, server, planner: add six_enum_discover module and discover_ipv6_enum stage
  * agent: add six_dns_discover result filter

* fix:
  * bypass ipv6 tests for travis env

## 0.3.0 - the staged planner

* features
  * planner:
    * [BC BREAK] refactored queues workflows to stages
    * implemented as celery worker and beats
  * agent: [BC BREAK] restructured code from __init__ to core
  * agent: six_dns_discover module to discover ipv6 addresses from ipv4 addrs and dns records

## 0.2.0 - towards planner

* fixes
  * general: use upstream sqlalchemy-filters
  * scheduler: fix runnaway assignments when server busy
  * storage: fix report generation when cells would contain >=64k chars
  * storage: handling line-endings during import and editing
  * storage: fix row ordering upon annotation

* features
  * general: all test models and data created through factoryboy
  * general: mod_wsgi integration changed to gunicorn and proxy setup
  * scheduler: simplified task/queue concept only to queues
  * scheduler: server modules refactored heavily to reflect somewhat standard flask app architecture
  * scheduler: droped support to reference queue by numeric id
  * scheduler: added rich module configuration
  * storage: added timestams to all storage models
  * storage: add refs for metasploit modules

## 0.1.2 - prod feedbacks

* fixes and refactorings
  * storage/host/list missing unfilter
  * enumips enumerate host addresses
  * misc styling and cosmetic
  * tests stabilization
  * multiple ids components naming
  * visuals internal refactoring

* features
  * new tags and configurable tag helpers buttons
  * dynamic distance for dns tree graph
  * badge numbers for models in host/view tabs


## 0.1.1 - package upgrades

* removed direct calling live_server fixture, replacet with httpserver fixture
* updated all libraries to recent versions
* ui cosmetics


## 0.1.0 - newui

* Bootstrap4 full ui redress
* user interface ajvascript refactoring from sparse functions into ES6 objects
* enhanced tagging and commenting
* empty strings represented as database nulls
	

## 0.0.2 - minor fixes and enhancements

* replace nessus_report_parser with pytenable
* fix report generation
* code cosmetics
* old password required for password changea


## 0.0.1 - initial release

* initial implementation
