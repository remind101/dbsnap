dbsnap-verify
#####################

verify AWS RDS DB snapshots.

This program may execute as either a CLI tool or an AWS Lambda.

The program uses the "unreliable town clock" pattern.
This means it expects to be "chimed" every 15m or so using a mechanism like crontab or a scheduled Cloudwatch Rule. 

The program is a state machine, it changes behavior based on the current state.
It will store execution state as a JSON document in a local file or in ``S3``.

.. contents::

Install
===============

You may install this tool into your Python environment by running::

 make build
 
CLI Tool
===============

Verify install::

 ./dbsnap-version --help

The tool expects to be passed a JSON config file that mirrors the same config that the AWS Lambda would be provided.

An example `dbsnap-verify-config.json <https://github.com/remind101/dbsnap-verify/blob/import/tests/fixtures/config_or_event.json>`_ may be found here.


AWS Lambda
===============

You may build an AWS Lambda zip. This command assumes you have Python ``virtualenv`` installed::

 make build-lambda

In our case use use a Cloudwatch Rule Event Trigger to invoke our Lambda at a ``rate(15 minutes)``.

The payload of this Cloudwatch Rule is a Static JSON value and is in the same form as the config used for the CLI.

An example `dbsnap-verify-config.json <https://github.com/remind101/dbsnap-verify/blob/import/tests/fixtures/config_or_event.json>`_ may be found here.

config.json
===============

An example `dbsnap-verify-config.json <https://github.com/remind101/dbsnap-verify/blob/import/tests/fixtures/config_or_event.json>`_ may be found here.

database (string):
 The AWS RDS DB Identifier whose snapshot we should restore/verify.

database_security_group_ids (string):
 A CSV of security group ids to add to the newly restored temporary database instance.

database_subnet_ids (string):
 A CSV of subnet ids to create a database subnet group with.

snapshot_region (string):
 The region to find the snapshot and restore/verify into.

snapshot_deadman_switch_days (integer):
 The amount of days to wait for snapshot before alarming. (default: 3)

state_doc_path (string):
 The path to the local file to store the state document.
 If you choose this, do not set ``state_doc_bucket``.

state_doc_bucket (string):
 The S3 bucket to store the state document.
 If you choose this, do not set ``state_doc_path``.

IAM Permissions
================

If you decide to store the state document in ``S3`` the executing role will need read and write access.

The role will also need the ability to do most ``RDS`` actions.
TODO: harden the list of ``RDS`` and put them here.

states
================

The following transitions will fire asynchronously and quit: ``wait``, ``restore``, ``modify``, ``clean``, ``alarm``.

There is no true "end state", once ``clean`` we ``wait`` for the next day's snapshot.

wait:
 currently waiting for the next snapshot to appear.
 
restore:
 currently restoring a copy of the snapshot into a temporary RDS database instance.
 
modify:
 currently modifying the temporary RDS database settings to allow the script access.
 
verify:
 currently verifying the restore using the supplied checks. (not implemented)
 
clean:
 currently tearing down the temporary RDS database instance and anything else we created or modified.
 
alarm:
 something went wrong we are going to scream about it.
 
Each time this tool "wakes up" it uses the ``state_doc`` to remember where it left off.

state_doc
================

The state machine uses a JSON ``state_doc`` to keep track of it's state and configuration.
This ``state_doc`` may be stored in either a local file or ``S3``.

You do not need to create this document, the tool manages it automatically.

An `example_state_doc.json <https://github.com/remind101/dbsnap-verify/blob/import/tests/fixtures/example_state_doc.json>`_ may be found here.


State Machine Diagram
====================================

Here is a diagram of the state machine transitions and states.

.. image:: https://github.com/remind101/dbsnap-verify/raw/import/dbsnap-verify-rds-snapshot-verification-lambda-s3-state-machine.png
  :align: center

