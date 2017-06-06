###############################################################################
#
# Installs a Python package using distutils setup tools. Understands the
# following parameters:
#
# --build           Run the build action.
# --install         Run the install action.
# --python3, --py3  Use the appropriate Python3 interpreter.
# --python2, --py2  Use the appropriate Python2 interpreter.
#
# $1: The installation path.
#
###############################################################################
bh_python_install()
{
    local py_interp="python2"
    local py_action="install"

    while true; do
        case "$1" in
            --python2|--py2)
                local py_interp="python2"
                shift
                ;;
            --python3|--py3)
                local py_interp="python3"
                shift
                ;;
            --build)
                local py_action="build"
                shift
                ;;
            --install)
                local py_action="install"
                shift
                ;;
            --root)
                local py_root="$2"
                shift 2
                ;;
            --)
                shift
                break
                ;;
            *)
                # unknown argument
                break
                ;;
        esac
    done

    local py_interp="$BOLT_INSTALL_PREFIX/bin/$py_interp"

    if [ "$py_action" = "install" ]; then
        if [ -z "$py_root" ] || [ ! -d "$py_root" ]; then
            echo "bh_python_install: invalid or empty installation path '$1', aborting." >&2
            exit 17
        fi

        local py_site_packages=`$py_interp -c \
            "from distutils import sysconfig; print(sysconfig.get_python_lib())"`
        "$py_interp" setup.py install \
            --force \
            --root="$py_root" \
            --prefix="$BOLT_INSTALL_PREFIX" \
            --install-lib="$py_site_packages" \
            "$@"
    else
        "$py_interp" setup.py build "$@"
    fi
}

