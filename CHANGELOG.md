# sner4 changelog

## 0.3.1 - prod planner (unreleased)

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
