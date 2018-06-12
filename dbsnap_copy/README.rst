dbsnap-copy
###########

example:

.. code-block:: bash

 dbsnap-copy --prune-old 3 us-east-1:my-database-id

help:

.. code-block:: bash

 dbsnap-copy --help
 usage: dbsnap-copy [-h] [-d DEST] [--prune-old PRUNE_OLD] [-n]
                    [--kms-key KMS_KEY]
                    source
 
 Used to copy AWS RDS DB Instance or Cluster snapshots. Copy to another region
 or just to keep snapshots around for longer than the maximum of 35 days that
 RDS allows.
 
 positional arguments:
   source                The source of the snapshot in the format: <region
                         >:<db-instance-identifier>
 
 optional arguments:
   -h, --help            show this help message and exit
   -d DEST, --dest DEST  The destination of the snapshot in the format:
                         [<region>]:[<snapshot-name>]). Defaults to the same
                         region as the source, and a snapshot-name of <source-
                         snapshot-identifier>:<timestamp>
   --prune-old PRUNE_OLD
                         If set, after the snapshot is taken, the command will
                         clean up old snapshots, keeping around as many copies
                         (the most recent) as you specify with this flag.
   -n, --dry-run         If set, do not actually change anything, just print
                         out what would happen.
   --kms-key KMS_KEY     The KMS Key ID to use when copying the snapshot. Not
                         necessary for most use-cases. See: http://docs.aws.ama
                         zon.com/AmazonRDS/latest/APIReference/API_CopyDBSnapsh
                         ot.html

