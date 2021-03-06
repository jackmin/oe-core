SUMMARY = "Distributed version control system"
SECTION = "console/utils"
LICENSE = "GPLv2"
DEPENDS = "openssl curl zlib expat"

PROVIDES_append_class-native = " git-replacement-native"

S = "${WORKDIR}/git-${PV}"

LIC_FILES_CHKSUM = "file://COPYING;md5=7c0d7ef03a7eb04ce795b0f60e68e7e1"

EXTRA_OECONF = "--with-perl=${STAGING_BINDIR_NATIVE}/perl-native/perl \
		--without-tcltk \
"

inherit autotools-brokensep perlnative

EXTRA_OEMAKE = "NO_PYTHON=1 RUNTIME_PREFIX=1"

do_compile_prepend () {
	# Remove perl/perl.mak to fix the out-of-date perl.mak error
	# during rebuild
	rm -f perl/perl.mak
}

do_install () {
	oe_runmake install DESTDIR="${D}" bindir=${bindir} \
		template_dir=${datadir}/git-core/templates \
		GIT_PYTHON_DIR=${D}${datadir}/git-core/python

	# ${libdir} is not applicable here, perl-native files are always
	# installed to /usr/lib on both 32/64 bits targets.
	rm -rf ${D}${exec_prefix}/lib/perl-native
	rmdir ${D}${exec_prefix}/lib || true
}

FILES_${PN} += "${datadir}/git-core ${libxecdir}/git-core/"
FILES_${PN}-dbg += "${libexecdir}/git-core/.debug"

# Git tools requiring perl
PACKAGES =+ "${PN}-perltools"
FILES_${PN}-perltools += " \
    ${libexecdir}/git-core/git-add--interactive \
    ${libexecdir}/git-core/git-archimport \
    ${libexecdir}/git-core/git-cvsexportcommit \
    ${libexecdir}/git-core/git-cvsimport \
    ${libexecdir}/git-core/git-cvsserver \
    ${bindir}/git-cvsserver \
    ${libexecdir}/git-core/git-difftool \
    ${libexecdir}/git-core/git-relink \
    ${libexecdir}/git-core/git-send-email \
    ${libexecdir}/git-core/git-svn \
    ${datadir}/perl \
"
RDEPENDS_${PN}-perltools = "${PN} perl perl-module-file-path findutils"

PACKAGES =+ "${PN}-python"
FILES_${PN}-python = "${libdir}/python*"


# git-tk package with gitk and git-gui
PACKAGES =+ "${PN}-tk"
#RDEPENDS_${PN}-tk = "${PN} tk tcl"
#EXTRA_OEMAKE = "TCL_PATH=${STAGING_BINDIR_CROSS}/tclsh"
FILES_${PN}-tk = " \
    ${bindir}/gitk \
    ${datadir}/gitk \
"

PACKAGES =+ "gitweb"
FILES_gitweb = "${datadir}/gitweb/"


BBCLASSEXTEND = "native nativesdk"
