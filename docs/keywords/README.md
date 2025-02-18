Keyword section headers
=======================

This directory contains a set of markdown files whose names match keywords used in plugins. The file will be used to create an introduction in the generated sections for each group of plugins that mention the keyword named in the filename.

It is optional to create a section header for a keyword, if one is not given then a default header is inserted.

The format of a keyword header is to include the title for the section and zero or more paragraphs of text in rich text format. The example below shows the header for the *Cleansing* keyword.

.. code-block:: RST

  Plugins That Improve The Data Quality
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  A set of plugins whose purpose is to help improve the data quality in a pipeline by removing or highlighting data of poor quality or in some way anomalous.

