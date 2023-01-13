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

.PHONY: help Makefile generated fledge_plugins.rst plugin_and_services_configuration clean

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile 
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

generated: fledge_plugins.rst plugin_and_services_configuration

fledge_plugins.rst: 
	@echo Building page with table of plugins
	@bash scripts/fledge_plugin_list fledge_plugins.rst $(DOCBRANCH)

plugin_and_services_configuration:
	@echo Building plugin and service configuration appendices
	@bash scripts/plugin_and_service_documentation $(DOCBRANCH)

clean:
	@echo Clean Doc build artifacts
	@rm -f fledge_plugins.rst
	@rm -rf plugins
	@rm -rf services
	@rm -rf "$(BUILDDIR)"
