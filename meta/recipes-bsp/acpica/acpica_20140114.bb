SRC_URI = "http://acpica.org/sites/acpica/files/acpica-unix2-20140114.tar.gz"
LICENSE = "GPLv2.0 | ACPICA"
LIC_FILES_CHKSUM = "file://source/include/acpi.h;endline=42;md5=23044abac8549f92999615207f2b8f56"

S = "${WORKDIR}/acpica-unix2-${PV}/"

EXTRA_OEMAKE = "CC='${CC}'"

do_install () {
	oe_runmake install DESTDIR='${D}' INSTALLFLAGS='-m 555' INSTALLDIR=${bindir}
}

SRC_URI[md5sum] = "fcd4b7304f1bfabc7d4b9cfdecc6b0c6"
SRC_URI[sha256sum] = "0d5bd32690ab77e21ab143ef25361c314a4ed13c33a5fb3ddd6f5559ab24ebc3"

BBCLASSEXTEND = "native"
