# sner4 changelog

## 0.13.0 - wormilable [BC BREAK]

* changed: minor fixes for six_enum_discover
* changed: enforce paging on all public API enpoints
* changed: python dependencies required for Debian 12 Bookworm
* fixed: bookworm postgres permissions setup
* added: vulnsearch add request timeout


## 0.12.0 - taglytics [BC BREAK]

* changed: server, full-fat taggable models for versioninfo and vulnsearch (requires db migratin)
* changed: server, configurable filters on vulnsearch list
* changed: server: api, paginate vulnsearch by default (can produce large output)
* changed: server: remove host_filter from elastic rebuilders
* added: server, host list tabs for versioninfo and vulnsearch
* added: server, add astext_ilike sqlafilter (naive JSON columns filtering)
* added: server: sqlafilters, add inet_in, inet_not_in, bumps sqlalchemy-filters
* added: coverage server-storage helper
* fixed: server, handle null value for sum in metrics
* fixed: fix versioninfo paging for datatables


## 0.11.0 - local analytics [BC BREAK]

* changed: syncstorage to elasticstorage refactoring
* changed: bump misc javascript libraries
* changed: storage queue-enqueue read from stdin
* changed: scheduler enumips read from stdin
* changed: rename syncstorage and syncvulnsearch to rebuild-\* commands
* changed: other minor ui tweaks
* changed: public api with parameters use only post json
* added: grouped notes
* added: api note list
* added: plugin nmap, save banner_dict
* added: storage versioninfo
* added: storage heatmap-check
* added: storage heatmap metrics
* added: show metrics in internal visual
* added: vulnsearch localdb and sync to elastic 
* fixed: migrations
* fixed: ui dt sorting
* fixed: elasticstorage note sync
* fixed: vuln group aggegation with tags in different order
* security: bump datatables plugin.ellipsis, fixes possible XSS (no CVE)


## 0.10.0 - clicker clicker [BC BREAK]

* changed: server: ux, storage service dropdown add copy to clipboard button/icon
* changed: server: updates for report and reportdata (report:data) tags
* changed: server: vulnerabilities group aggregate tags with 'i:' exclusion
* changed: ci: update github actions to use current versions
* changed: server: also other minor ux
* added: server: ux, copy vulnerability to other host/service, add autocomplete for vuln addedit
* added: coverage-plugin helper
* added: nuclei plugin
* added: server: ux, fuller storage datatables toolbar multi-action toolboxes
* added: planner, 'load_standalone' stages
* added: server: scheduler maintenance mode
* fixed: server: fix filter POST request
* fixed: timeout for OIDC calls
* security: bump jquery


## 0.9.2 - deploying snerlytics

* changed: various snerlytics indexes updates
* changed: elastic sync features add file based filter
* fixed: network exclusion matcher fix sixenum:// matching


## 0.9.1 - finetuning lytics

* changed: agent, planner, tiny better logging
* changed: storage sync features configurable elastic indexer buffers
* changes: oidc scope omit profile
* added: auth add-user command


## 0.9.0 - deploying snerlytics [BC BREAK]

* changed: runtime queue cosmetics
* changed: tests use Mock instead of local functions where possible
* changed: six_enum_discover target format vs heatmap hasvals [BC BREAK]
* changed: view note list table truncate data column with ellipsis to 4k chars
* added: vulnsearch use optional client tls authentication
* added: add storage sync-storage command
* fixed: planner QueueHandler handle exception during draining/job parsing
* fixed: handle delete queue OSerror for UI/UX


## 0.8.0 - refining planner [BC BREAK]

* changed: nessus parser pull solution data
* changed: split CI jobs and update makefile targets
* changed: heavy planner refactoring
* changed: untagging ux
* changed: exclusion config from config, drop excl db storage [BC BREAK]
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
