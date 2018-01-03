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


class InitializationFailed(Exception):
    """ Cannot complete the initialization """
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


class ArgumentParserError(Exception):
    """ Invalid command line arguments """
    pass


class FogLAMPStartError(RuntimeError):
    """ Unable to start FogLAMP """
    pass


class FogLAMPStopError(RuntimeError):
    """ Unable to stop FogLAMP """


class PgCommandUnAvailable(Exception):
    """ Postgres command is not available neither using the managed nor the unmanaged approach """
    pass


class PgCommandNotExecutable(Exception):
    """ Postgres command is not executable """
    pass


class CannotReadPostgres(Exception):
    """ It is not possible to read data from Postgres """
    pass


class NoBackupAvailableError(RuntimeError):
    """ No backup in the proper state is available """
    pass


class FileNameError(RuntimeError):
    """ Impossible to identify an unique backup to restore """
    pass


class InvalidFogLAMPEnvironment(RuntimeError):
    """ It is not possible to determine the environment in which the code is running
    neither Deployment nor Development """
    pass
