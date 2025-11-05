.. Links

.. _here: ../scripts\\fledge_plugin_list

Keyword Introduction
====================

It consists of a collection of files, with names corresponding to keywords found in the plugin documentation directories.
These files are utilized by the script `here`_.

These files are used by the script to generate plugin groupings by category, where each category corresponds to a keyword for a specific plugin type.

If a file corresponding to the keyword exists, it will be used as the introduction to the table of plugins associated with that keyword.

If no such file exists for a given keyword, a standard header will be generated instead.

Adding new keywords to plugin repositories does not require adding new files to this directory; the files are primarily there to enhance the documentation. Additionally, the presence of a file with a specific name in this directory does not necessarily mean that the corresponding keyword is used elsewhere.

Keyword section headers
=======================

This directory contains a set of markdown files whose names match keywords used in plugins. The file will be used to create an introduction in the generated sections for each group of plugins that mention the keyword named in the filename.

It is optional to create a section header for a keyword, if one is not given then a default header is inserted.

The format of a keyword header is to include the title for the section and zero or more paragraphs of text in rich text format. The example below shows the header for the *Cleansing* keyword.

.. code-block:: RST

  Plugins That Improve The Data Quality
  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  A set of plugins whose purpose is to help improve the data quality in a pipeline by removing or highlighting data of poor quality or in some way anomalous.
