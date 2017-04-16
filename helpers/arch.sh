###############################################################################
#
# Converts a machine name (armv6, x86_64) or a target triplet
# (armv6-linux-gnueabihf, x86_64-pc-linux-gnu) to the corresponding kernel
# ARCH.
#
# $1: a machine name or target triplet
#
# Prints the corresponding kernel ARCH name.
#
###############################################################################
bh_kernel_arch_from_target_triplet()
{
    local uname="`echo $1 | cut -d'-' -f1`"

    echo $(
        # The following is stolen from a kernel makefile
        echo $uname | sed -e 's/i.86/x86/'      -e 's/x86_64/x86/'       \
                          -e 's/sun4u/sparc64/'                          \
                          -e 's/arm.*/arm/'     -e 's/sa110/arm/'        \
                          -e 's/s390x/s390/'    -e 's/parisc64/parisc/'  \
                          -e 's/ppc.*/powerpc/' -e 's/mips.*/mips/'      \
                          -e 's/sh[234].*/sh/'  -e 's/aarch64.*/arm64/'
    )
}

