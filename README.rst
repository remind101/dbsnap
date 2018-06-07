dbsnap
######

Here at `Remind <https://www.remind.com>`_ we maintain a set of tools and
Python libraries to copy and verify AWS RDS DB Instance and Cluster Snapshots.

``dbsnap-copy``:
 AWS RDS allows a maximum of 35 "automatic" daily snapshots.
 We wrote this tool to copy "automatic" snapshots as "manual" snapshots.
 We also use this tool to increase our disaster recovery fitness by
 copying snapshots to remote regions.

For more details read: `dbsnap_copy/README.rst <https://github.com/remind101/dbsnap-verify/blob/master/dbsnap_copy/README.rst>`_

``dbsnap-verify``:
 We use this tool to automate testing RDS snapshot restore process.
 This gives us confidence that we have the ability to recover from
 our database backups in case of a disaster.

For more details read: `dbsnap_verify/README.rst <https://github.com/remind101/dbsnap-verify/blob/master/dbsnap_verify/README.rst>`_

