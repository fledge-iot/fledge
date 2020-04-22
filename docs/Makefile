# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = python3 -msphinx
SPHINXPROJ    = Fledge
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:	fledge_plugins.rst
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile fledge_plugins.rst plugins clean

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile fledge_plugins.rst plugins
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

fledge_plugins.rst: 
	@echo Building page with table of plugins
	@bash scripts/fledge_plugin_list fledge_plugins.rst

plugins: 
	@echo Building plugin configuration appendices
	@bash scripts/plugin_documentation

clean:
	@rm -f fledge_plugins.rst
	@rm -rf "$(BUILDDIR)"
