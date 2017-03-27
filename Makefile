#!/usr/bin/make -f

VERSION=$(shell ./bin/bolt-pack | head -n1 | sed 's/Bolt OS Package Generator, version //g')
DESTDIR=install
BRANCH=$(shell git rev-parse --abbrev-ref HEAD)
SITE_PACKAGES=$(shell python3 -c "from distutils import sysconfig; print(sysconfig.get_python_lib())")
PREFIX=/usr
DESTDIR=/

.PHONY: install clean

install:
	python3 setup.py install --prefix=$(PREFIX) \
	    --root=$(DESTDIR) --install-lib="$(SITE_PACKAGES)"

tarball:
	git archive --format=tar.gz --prefix=bolt-package-$(VERSION)/ \
	    -o ../bolt-package-$(VERSION).tar.gz $(BRANCH)

clean:
	git clean -x -f -d
