# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Exceptions module """


class ConfigRetrievalError(Exception):
    """ Unable to retrieve the parameters from the configuration manager """
    pass


class BackupOrRestoreAlreadyRunning(Exception):
    """ Backup or restore cannot proceed as another operation is already running """
    pass


class BackupFailed(Exception):
    """ An error occurred during the backup operation """
    pass


class RestoreFailed(Exception):
    """ An error occurred during the restore operation """
    pass


class NotUniqueBackup(Exception):
    """ There are more than one backups having the same backup id """
    pass


class BackupsDirDoesNotExist(Exception):
    """ Directory used to store backups doesn't exist """
    pass


class SemaphoresDirDoesNotExist(Exception):
    """ Directory used to store semaphores for backup/restore synchronization doesn't exist """
    pass


class DoesNotExist(Exception):
    """ The requested backup id doesn't exist """
    pass


class CannotCreateConfigurationCacheFile(Exception):
    """ It is not possible to create the configuration cache file to store information retrieved from the
        configuration manager """
    pass


class InvalidBackupsPath(Exception):
    """ The identified backups' path is not a valid directory """
    pass


class InvalidPath(Exception):
    """ The identified path is not a valid directory """
    pass


class PgCommandUnAvailable(Exception):
    """ Postgres command is not available neither using the managed nor the unmanaged approach """
    pass


class PgCommandNotExecutable(Exception):
    """ Postgres command is not executable """
    pass


class CannotReadPostgres(Exception):
    """ It is not possible to read data from Postgres """
    pass
