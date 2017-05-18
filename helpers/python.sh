###############################################################################
#
# Installs a Python package using distutils setup tools. Understands the
# following parameters:
#
# --python3, --py3  Use the appropriate Python3 interpreter.
# --python2, --py2  Use the appropriate Python2 interpreter.
#
# It looks at the value of `$BOLT_BUILD_FOR` to choose the correct prefix.
#
# $1: The installation path.
#
###############################################################################
bh_python_install()
{
    if [ "$BOLT_BUILD_FOR" = "tools" ]; then
        local py_prefix="/tools"
    else
        local py_prefix="/usr"
    fi

    local py_interp="python2"

    while true; do
        case "$1" in
            --python2|--py2)
                py_interp="python2"
                shift
                ;;
            --python3|--py3)
                py_interp="python3"
                shift
                ;;
            *)
                break
                ;;
        esac
    done

    if [ -z "$1" ] || [ ! -d "$1" ]; then
        echo "Invalid or empty installation path '$1'. Aborting." >&2
        exit 1
    fi

    local py_root="$1"
    local py_interp="$py_prefix/bin/$py_interp"

    local __python_site_packages=`$py_interp -c \
        "from distutils import sysconfig; print(sysconfig.get_python_lib())"`
    "$py_interp" setup.py install \
        --prefix="$py_prefix" \
        --root="$py_root" \
        --install-lib="${__python_site_packages}"
}

