if [ "x$BOLT_PACKAGE_SOURCED" = "x" ]; then
    export FLASK_APP="org.boltlinux.repository.flaskapp:app"
    export FLASK_STATIC_URL_PATH=""
    export FLASK_STATIC_FOLDER="ui/_site"
    export FLASK_ROOT_PATH="."
    export PYTHONPATH="`pwd`/lib:$PYTHONPATH"
    export PATH="`pwd`/bin:$PATH"
    export PS1="(bolt-package)$PS1"
    export BOLT_PACKAGE_SOURCED="yes"
fi
