Configuration
=============

Importer Configuration
----------------------

The OSTree importer is configured by editing
``/etc/pulp/server/plugins.conf.d/ostree_importer.json``. This file must be valid `JSON`_.

.. _JSON: http://json.org/

The importer supports the settings documented in Pulp's `importer config docs`_ with the addition
of a the following OSTree specific properties:

- ``branches`` - A list of branch names to be pulled during repository synchronization.
  Only those branches listed will be pulled.
- ``gpg_keys`` - An (optional) list of GPG keys used to validate signed commits.


.. _importer config docs: https://pulp-user-guide.readthedocs.org/en/latest/server.html#importers
