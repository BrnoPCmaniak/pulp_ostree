import sys

from gettext import gettext as _

from pulp.common.config import read_json_config
from pulp.plugins.importer import Importer

from pulp_ostree.common import constants
from pulp_ostree.plugins.importers.steps import Main


def entry_point():
    """
    Entry point that pulp platform uses to load the importer
    :return: importer class and its config
    :rtype:  Importer, dict
    """
    config = read_json_config(constants.IMPORTER_CONFIG_FILE_PATH)
    return WebImporter, config


class WebImporter(Importer):

    def __init__(self):
        super(WebImporter, self).__init__()

    @classmethod
    def metadata(cls):
        """
        Used by Pulp to classify the capabilities of this importer. The
        following keys must be present in the returned dictionary:

        * id - Programmatic way to refer to this importer. Must be unique
          across all importers. Only letters and underscores are valid.
        * display_name - User-friendly identification of the importer.
        * types - List of all content type IDs that may be imported using this
          importer.

        :return:    keys and values listed above
        :rtype:     dict
        """
        return {
            'id': constants.WEB_IMPORTER_TYPE_ID,
            'display_name': _('OSTree Web Importer'),
            'types': [constants.OSTREE_TYPE_ID]
        }

    def validate_config(self, repo, config):
        """
        Validate the configuration.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration
        """
        return True, ''

    def sync_repo(self, repo, conduit, config):
        """
        Synchronizes content into the given repository. This call is responsible
        for adding new content units to Pulp as well as associating them to the
        given repository.

        While this call may be implemented using multiple threads, its execution
        from the Pulp server's standpoint should be synchronous. This call should
        not return until the sync is complete.

        It is not expected that this call be atomic. Should an error occur, it
        is not the responsibility of the importer to rollback any unit additions
        or associations that have been made.

        The returned report object is used to communicate the results of the
        sync back to the user. Care should be taken to i18n the free text "log"
        attribute in the report if applicable.

        :param repo: metadata describing the repository
        :type  repo: pulp.plugins.model.Repository

        :param conduit: provides access to relevant Pulp functionality
        :type  conduit: pulp.plugins.conduits.repo_sync.RepoSyncConduit

        :param config: plugin configuration
        :type  config: pulp.plugins.config.PluginCallConfiguration

        :return: report of the details of the sync
        :rtype:  pulp.plugins.model.SyncReport
        """
        step = Main(repo, conduit, config)
        report = step.process_lifecycle()
        return report

    def cancel_sync_repo(self):
        """
        Cancels an in-progress sync.

        This call is responsible for halting a current sync by stopping any
        in-progress downloads and performing any cleanup necessary to get the
        system back into a stable state.
        """
        sys.exit(0)
