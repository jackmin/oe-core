SUMMARY = "Gummiboot is a simple UEFI boot manager which executes configured EFI images."
HOMEPAGE = "http://freedesktop.org/wiki/Software/gummiboot"

LICENSE = "LGPLv2.1"
LIC_FILES_CHKSUM = "file://LICENSE;md5=4fbd65380cdd255951079008b364516c"

DEPENDS = "gnu-efi util-linux"

inherit autotools
inherit deploy

PV = "43+git${SRCPV}"
SRCREV = "4062c51075ba054d4949c714fe06123f9ad3097d"
SRC_URI = "git://anongit.freedesktop.org/gummiboot"

S = "${WORKDIR}/git"

EXTRA_OECONF = "--disable-manpages --with-efi-includedir=${STAGING_INCDIR} \
                --with-efi-ldsdir=${STAGING_LIBDIR} \
                --with-efi-libdir=${STAGING_LIBDIR}"

do_deploy () {
        install ${B}/gummiboot*.efi ${DEPLOYDIR}
}
addtask deploy before do_build after do_compile
