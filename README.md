# rrsync
A restriction script to limit access by rsync when run via SSH's authorized_keys file

## Usage
This is not meant to be run directly, but rather referred to in `~/.ssh/authorized_keys` on a server, as below:

    command="rrsync.py [-ro] [--log-file /path/to/log] topdir" ssh-rsa AAAA...

This will mean that any use of the corresponding SSH key can ONLY run that command. Further, the rrsync.py script itself ONLY allows itself to be run when `ssh` is being called by `rsync`. It examines what `rsync` is trying to do, and will only execute the real `rsync` server if it's allowed. The restrictions are to (1) ensure that the thing being copied is under the given `topdir` path and (2) that, if `-ro` is given, only reads are permitted. For additional security, you can also set an IP origin constraint in `authorized_keys`:

    from="192.168.0.80",command="rrsync.py [-ro] [--log-file /path/to/log] topdir" ssh-rsa AAAA...

The result is an rsync target that is signficiantly restricted. For example, you could use it in concern with `rsnapshot` to allow just read-only access. This means that a compromise of the backup server (which has the private key) cannot be used to compromise the server being backed up, and vice versa. This creates a ransomware-resilient backup scheme.

Further, accesses can be logged with `--log-file`, which will show timestamp, origin IP, requested rsync command, and whether the operation was allowed. 

Note: this can be deployed on a Synology box. If used as root, it best lives in `/usr/local/bin` (as other root-owned paths may be overwritten by updates). 

## Origin
This is a modern take on multiple rsync-restricting scripts I've seen over the years. Most recently, it was inspired by an old Perl-based `rrsync` from 2012 whose author I unfortunately cannot identify. It might even be me and I forgot writing it. In any case, this script uses modern pathlib-based parsing rather than a mile of Perl regex, so I think we're better off.
