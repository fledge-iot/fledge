# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = FogLAMP
SOURCEDIR     = .
BUILDDIR      = _build
CODEDIR       = ../src/python/foglamp
HOSTADDRESS   = 0.0.0.0
PORTNO        = 8000

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

livehtml:
	sphinx-autobuild -b html "$(SPHINXOPTS)" "$(BUILDDIR)/html" --host "$(HOSTADDRESS)" --port "$(PORTNO)" --watch "$(CODEDIR)"

.PHONY: help livehtml Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)